"""Export or check the FastAPI application's OpenAPI schema snapshot."""

import argparse
import json
from pathlib import Path

from services.api.main import app

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPOSITORY_ROOT / "docs" / "api" / "openapi.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the checked-in schema differs from the current application schema.",
    )
    args = parser.parse_args()

    generated = json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not OPENAPI_PATH.exists() or OPENAPI_PATH.read_text(encoding="utf-8") != generated:
            print(f"OpenAPI schema is out of date: {OPENAPI_PATH}")
            print("Run `python ops/scripts/export_openapi.py` to regenerate it.")
            return 1
        print(f"OpenAPI schema is current: {OPENAPI_PATH}")
        return 0

    OPENAPI_PATH.write_text(generated, encoding="utf-8")
    print(f"Wrote OpenAPI schema: {OPENAPI_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())