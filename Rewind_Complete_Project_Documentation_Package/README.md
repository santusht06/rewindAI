# Rewind Complete Project Documentation Package

This package contains product and software requirements, implementation backlog and status tracking, platform integration constraints, coding-agent rules, production PRD, and system design diagrams.

## Critical product definition

Rewind is a **cross-app AI viewing assistant**, not an OTT service or video player. The user continues watching in Netflix, Prime Video, or another supported streaming app and invokes Rewind through a platform/provider capability that must be verified. See `requirements/17_REWIND_CROSS_APP_ASSISTANT_PRODUCT_REQUIREMENT.md` first.

## Suggested start sequence

1. Read `requirements/00_README.md` and all requirements.
2. Read `requirements/17_REWIND_CROSS_APP_ASSISTANT_PRODUCT_REQUIREMENT.md`.
3. Complete platform feasibility and repository discovery before substantial implementation.
4. Follow `requirements/14_IMPLEMENTATION_STATUS_AND_BACKEND_FIRST_EXECUTION_PLAN.md` and `requirements/15_DETAILED_PRODUCT_BACKLOG_AND_IMPLEMENTATION_ORDER.md`.
5. Follow Git rules in `requirements/13_GIT_WORKFLOW_AGILE_DELIVERY_AND_RELEASE_RULES.md`.
6. Use the status template and keep all claims backed by actual verification evidence.

The presence of a provider-neutral interface does not prove a streaming provider supports overlay, playback-position, subtitle, or active-app access. Record real capabilities and limitations in the platform capability matrix.
