"""Automated Database Disaster Recovery, Backup, and Integrity Verification for Rewind.

Implements:
- OPS-005: Database backup and restore procedures with automated verification
- NFR-DR-001: Point-in-time recovery and verifiable cryptographic integrity
- REL-004: Disaster recovery validation for production launch
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any


def calculate_sha256(file_path: Path) -> str:
    """Calculate cryptographic SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_sqlite_integrity(db_path: Path) -> bool:
    """Verify SQLite database structural integrity using PRAGMA integrity_check."""
    if not db_path.exists():
        return False
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        return bool(result and result[0] == "ok")
    except Exception as exc:
        print(f"Integrity check failed with error: {exc}", file=sys.stderr)
        return False


def get_table_counts(db_path: Path) -> dict[str, int]:
    """Retrieve row counts across core domain tables."""
    counts: dict[str, int] = {}
    if not db_path.exists():
        return counts

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM \"{table}\";")
                counts[table] = cursor.fetchone()[0]
            except Exception:
                pass
        conn.close()
    except Exception:
        pass
    return counts


def create_backup(db_path: Path, output_dir: Path) -> tuple[Path, Path]:
    """Create a verified, point-in-time SQLite backup with SHA-256 manifest.

    Returns (backup_file_path, manifest_file_path).
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Source database file not found: {db_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = output_dir / f"rewind_backup_{timestamp_str}.db"
    manifest_file = output_dir / f"rewind_backup_{timestamp_str}.json"

    # 1. Use SQLite Online Backup API for atomic, lock-safe point-in-time copy
    src_conn = sqlite3.connect(str(db_path))
    dst_conn = sqlite3.connect(str(backup_file))
    with dst_conn:
        src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()

    # 2. Verify structural integrity of newly created backup
    if not verify_sqlite_integrity(backup_file):
        if backup_file.exists():
            backup_file.unlink()
        raise RuntimeError(f"Integrity check failed for backup file: {backup_file}")

    # 3. Calculate checksum and metadata
    checksum = calculate_sha256(backup_file)
    table_counts = get_table_counts(backup_file)
    size_bytes = backup_file.stat().st_size

    manifest_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_db": str(db_path.resolve()),
        "backup_file": backup_file.name,
        "sha256_checksum": checksum,
        "size_bytes": size_bytes,
        "table_counts": table_counts,
        "status": "verified",
    }

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    return backup_file, manifest_file


def restore_backup(
    backup_path: Path,
    target_path: Path,
    manifest_path: Path | None = None,
) -> bool:
    """Restore database from backup with cryptographic and schema validation.

    Returns True upon successful restoration.
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    # 1. Verify manifest checksum if manifest provided or exists alongside backup
    candidate_manifest = manifest_path or backup_path.with_suffix(".json")
    if candidate_manifest.exists():
        with open(candidate_manifest, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        expected_checksum = manifest.get("sha256_checksum")
        actual_checksum = calculate_sha256(backup_path)
        if expected_checksum and actual_checksum != expected_checksum:
            raise ValueError(
                f"Cryptographic checksum mismatch! Expected: {expected_checksum}, Actual: {actual_checksum}"
            )

    # 2. Verify backup integrity before restoring
    if not verify_sqlite_integrity(backup_path):
        raise RuntimeError(f"Source backup file failed PRAGMA integrity check: {backup_path}")

    # 3. Atomic SQLite restore into target
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target_path.with_suffix(".tmp_restore")

    src_conn = sqlite3.connect(str(backup_path))
    dst_conn = sqlite3.connect(str(temp_target))
    with dst_conn:
        src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()

    # 4. Verify target integrity
    if not verify_sqlite_integrity(temp_target):
        if temp_target.exists():
            temp_target.unlink()
        raise RuntimeError("Restored temporary database failed integrity check.")

    # 5. Atomically replace target
    temp_target.replace(target_path)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Rewind Disaster Recovery & Backup Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Create verified point-in-time backup")
    backup_parser.add_argument("--db-path", type=Path, default=Path("rewind_local.db"), help="Path to database")
    backup_parser.add_argument("--out-dir", type=Path, default=Path("ops/backups"), help="Directory for backups")

    restore_parser = subparsers.add_parser("restore", help="Restore database from backup")
    restore_parser.add_argument("--backup-path", type=Path, required=True, help="Path to backup .db file")
    restore_parser.add_argument("--target-path", type=Path, default=Path("rewind_local.db"), help="Target DB path")
    restore_parser.add_argument("--manifest-path", type=Path, default=None, help="Optional manifest path")

    verify_parser = subparsers.add_parser("verify", help="Verify database integrity")
    verify_parser.add_argument("--db-path", type=Path, default=Path("rewind_local.db"), help="Path to database")

    args = parser.parse_args()

    if args.command == "backup":
        backup_file, manifest = create_backup(args.db_path, args.out_dir)
        print(f"SUCCESS: Created backup at {backup_file}")
        print(f"SUCCESS: Manifest written to {manifest}")
    elif args.command == "restore":
        success = restore_backup(args.backup_path, args.target_path, args.manifest_path)
        if success:
            print(f"SUCCESS: Database restored to {args.target_path}")
        else:
            sys.exit(1)
    elif args.command == "verify":
        ok = verify_sqlite_integrity(args.db_path)
        if ok:
            print(f"SUCCESS: {args.db_path} integrity check PASSED.")
        else:
            print(f"FAILURE: {args.db_path} integrity check FAILED.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
