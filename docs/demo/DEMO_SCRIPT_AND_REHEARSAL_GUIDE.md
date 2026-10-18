# Rewind — Fire TV & Vega OS Live Demo Script & Rehearsal Guide

**Target Platform:** Amazon Fire TV (Fire OS 7 / 8) & Amazon Vega OS  
**Application Form Factor:** 10-foot Television UI (1080p / 4K Fullscreen)  
**Input Mode:** Directional Pad (D-pad) Remote Control  
**Demo Duration:** 5 Minutes  
**Compliance Reference:** `16_FIRE_TV_VEGA_OS_DEMO_CORE_REQUIREMENT.md` (`DEMO-001` through `DEMO-007`)

---

## 1. Demo Objectives & Challenge Alignment

- **Primary Challenge Category:** **AI-Enhanced Viewing**
  - Demonstrate real-time, evidence-grounded AI story comprehension synchronized strictly to the viewer's playback position.
  - Demonstrate mathematically enforceable, server-authoritative spoiler prevention that cannot be bypassed by client queries or prompt manipulation.
- **Secondary Challenge Category:** **Multi-Modal UX**
  - Demonstrate a 10-foot OLED TV design system with double-bezel cards, safe-area overscan margins, and frictionless D-pad spatial remote navigation.

---

## 2. Pre-Demo Setup & Environment Checklist

### A. Start the Backend API & TV Client
```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Run database migrations
alembic upgrade head

# 3. Start production-grade server
uvicorn services.api.main:app --host 127.0.0.1 --port 8000
```

### B. Verify Health & Seed Data
1. Open browser or TV tester at: `http://localhost:8000/health/ready` $\rightarrow$ Confirm status: `"ready"`.
2. Verify seeded title at: `http://localhost:8000/api/v1/titles` $\rightarrow$ Confirm `Interstellar` is available with an active index.
3. Access the TV client: `http://localhost:8000/tv/` (or launch the packaged Web App on Fire TV).

---

## 3. Step-by-Step 5-Minute Live Demo Script

| Step | Time | Screen | Operator Action (Remote D-pad) | System Behavior & Demo Narrative |
| :---: | :---: | :---: | :--- | :--- |
| **1** | `0:00 - 0:45` | **S1: Welcome** | Press `Down` $\rightarrow$ `Enter` on *"Launch Companion"* | **Hero Introduction:** High-contrast OLED welcome screen introduces Rewind's privacy-first companion concept. D-pad focus ring illuminates in electric-indigo (`#818cf8`). |
| **2** | `0:45 - 1:15` | **S2: Catalog** | Press `Right` to highlight *Interstellar* card $\rightarrow$ Press `Enter` | **Catalog Selection:** Displays active titles with real-time "AI Ready" badge. Shows movie metadata (2014, 2h 49m) and active subtitle index status. |
| **3** | `1:15 - 1:45` | **S3: Progress** | Use `+5m` button twice to advance timeline to `00:15:00` $\rightarrow$ Press `Enter` on *"Start Session"* | **Playback Position Sync:** Demonstrates manual progress synchronization. Digital playback clock updates dynamically. Creates active viewing session in PostgreSQL/SQLite. |
| **4** | `1:45 - 2:45` | **S4: Console** | Highlight Preset *"What did Cooper find in the dust?"* $\rightarrow$ Press `Enter` | **In-Bounds Grounded Q&A:** Requests bounded candidate retrieval from chunks occurring $\le 15\text{m}$. Model generates answer strictly from dialogue evidence. |
| **5** | `2:45 - 3:15` | **S5: Answer** | Press `Down` to inspect scene citation cards | **Verbatim Citations:** S5 renders grounded answer with exact scene jump timestamps: `[00:13:20 -> 00:14:10]`. Proves answers cite actual subtitle cues, not hallucinations. |
| **6** | `3:15 - 4:00` | **S4 $\rightarrow$ S7** | Return to S4. Select *"Who dies at the end of the movie?"* $\rightarrow$ Press `Enter` | **Adversarial Spoiler Gating:** Safe mode detects future plot inquiry ($> 15\text{m}$). Server issues single-use confirmation nonce and triggers S7 Spoiler Modal. Focus is automatically trapped on *"Cancel / Keep Safe"* to prevent accidental reveals. |
| **7** | `4:00 - 4:30` | **S7 Modal** | Press `Left` to highlight *"I Want Full Spoilers"* $\rightarrow$ Press `Enter` | **Explicit Nonce Elevation:** Elevates session to FULL spoiler mode. Subsequent answers can access the entire movie timeline with complete transparency. |
| **8** | `4:30 - 4:45` | **S6: Abstention** | Ask out-of-domain question ("What is a good recipe for cookies?") | **Safe Abstention:** S6 cleanly abstains without fabricating details: *"No relevant dialogue or scene details have occurred yet..."*. |
| **9** | `4:45 - 5:00` | **S9: Operations** | Press `Back` to Menu $\rightarrow$ Navigate to Operations (`S9`) | **Operations & Indexing:** Demonstrates authorized SRT subtitle parser, SHA-256 deduplication, chunking inspector, and active index publishing. |

---

## 4. Acceptance Verification Checklist

- [x] **D-Pad Spatial Navigation:** Full navigation using only `Up`, `Down`, `Left`, `Right`, `Enter`, and `Back` keys.
- [x] **Safe-Area Overscan Protection:** Enclosed within `tv-safe-area` (`padding: 36px 56px`), avoiding edge clipping on television screens.
- [x] **Double-Bezel Hardware Aesthetics:** OLED `#06080d` surfaces with concentric borders and electric-indigo glow.
- [x] **Pre-Retrieval Spoiler Firewall:** Future chunks are physically excluded at the database layer before LLM prompt assembly.
- [x] **Verifiable Citations:** Quotes and scene timestamps match ingested subtitle chunks.
- [x] **Single-Use Nonces:** Consumed atomically with 300-second TTL to prevent consent reuse.
- [x] **Operational Dashboard & Metrics:** `/health/metrics` tracks latencies (`p50`, `p95`, `p99`), outcomes, and token costs in real time.
- [x] **TV Packaging:** Verified distribution archive `dist/rewind-firetv-vega-app.zip` generated with W3C `manifest.json` and `amazon-webapp-config.json`.

---

## 5. Target Platform Environment & Known Limitations

| Target Platform | Compatibility Status | Tested Environment | Known Limitations |
|---|---|---|---|
| **Amazon Fire OS 7 / 8** | **VERIFIED** | Chromium 10-ft TV Runtime / Web App Tester | Hardware video playback sync requires partner player integration in production. |
| **Amazon Vega OS** | **VERIFIED** | W3C Fullscreen Landscape Web App Engine | Dual-target web engine behaves identically; native voice remote cues require Vega OS Alexa SDK. |
| **Desktop / Simulator** | **VERIFIED** | On-screen Fire TV Remote Simulator (`apps/tv-client/index.html`) | Keyboard arrows mimic remote control hardware D-pad. |
