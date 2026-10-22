# 16 — Fire TV / Vega OS Demo Requirement (Superseded Clarification)

**Important:** This document is superseded wherever it conflicts with `17_REWIND_CROSS_APP_ASSISTANT_PRODUCT_REQUIREMENT.md`. Read document 17 first for the authoritative product definition.

Rewind must be a demo-ready, AI-enhanced viewing assistant that runs on a verified Fire OS or Vega OS target. It must work alongside existing streaming apps where platform/provider capabilities permit; it must not become a Rewind-owned OTT service or require users to watch content in a Rewind player.

A system-level overlay, invocation shortcut, active-app detection, playback-position access, subtitle access, and reliable return to a third-party app are **unverified assumptions until proven** for the exact OS/device/provider. The implementation agent must complete the platform capability matrix and a minimal feasibility prototype early. Do not use unsupported APIs, hidden permissions, screen scraping, or DRM circumvention. If a true overlay is unavailable, propose and document an honest supported fallback and obtain approval before treating it as the MVP behavior.

The demo must distinguish real integration from mocked or manually supplied context. Backend correctness alone does not satisfy the Fire TV/Vega demo requirement.
