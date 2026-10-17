# 06 — UX and Screen Requirements

## 1. TV-first principles
- Design for viewing distance, low-friction remote navigation and 10-foot readability.
- Every interactive control must have a visible focus state.
- No flow may require a mouse, hover, drag gesture or phone-only interaction.
- Keep the number of actions per screen low; avoid dense tables and tiny text.
- Preserve context when opening the companion over or alongside viewing, where platform APIs permit it.
- Verify actual Fire TV safe areas, focus behavior, back navigation, keyboard/input method and lifecycle constraints against the selected runtime.

## 2. Required screens
### S1 — Welcome / identity
Explain what Rewind does and its limits. Sign-in is shown only if authentication is selected as a product requirement. Provide privacy notice and clear exit/back behavior.

### S2 — Title catalog
Show searchable, published supported titles. Distinguish “ready to ask questions” from “not currently available.” Do not display unpublished titles or internal asset metadata.

### S3 — Title details / progress setup
Show title identity and current progress state. If automatic playback synchronization is not verified, explicitly ask the viewer to select or confirm a point (time or episode/scene). Show whether progress is manual or verified.

### S4 — Companion / question
Display title, progress boundary, spoiler mode and question input. Remote keyboard and voice input are optional capabilities; if voice is implemented, provide text fallback and clear microphone permission behavior.

### S5 — Answer
Show concise answer first, then citations/scene timestamps and optional “why this answer” detail. Distinguish verified answer from uncertainty. Citation selection must not jump playback unless an authorized supported mechanism exists.

### S6 — Clarification / insufficient evidence
Explain what is missing and provide next actions: refine question, confirm progress, choose another title, or try later. Do not present a guess as an answer.

### S7 — Spoiler confirmation
Clearly identify that the requested answer may reveal later plot information. Require a deliberate confirmation action. Default focus should not accidentally confirm. Explain scope if consent persists.

### S8 — Settings / privacy
Allow relevant settings, session/history deletion if offered, locale, accessibility options and privacy controls. Never promise deletion beyond what backend retention systems actually implement.

### S9 — Admin/operations (restricted, may be separate web UI)
Show ingestion status, safe error summaries, published index version and available actions. Destructive operations require confirmation and audit.

## 3. Navigation and focus
- Provide a predictable focus order and focus restoration when returning from a screen.
- Back must not accidentally submit a question or confirm a spoiler.
- Loading, empty, offline, timeout, unauthorized and error states must be designed.
- Prevent double-submit; show progress and allow cancellation when supported.
- Never trap focus in a modal without an escape route.
- Support remote-only end-to-end operation.

## 4. Accessibility
Use readable typography, adequate contrast, clear labels, non-color-only status indicators, captions/text alternatives where applicable, scalable text where the platform supports it, and predictable focus. Avoid rapid flashing and unnecessary motion. Voice input cannot be the only input path.

## 5. Copy and answer presentation
- Be concise and conversational, but never at the cost of accuracy.
- Use “I can’t verify that from the available scenes” rather than fabricate.
- Display timestamp format consistently, with episode/season where applicable.
- Make uncertainty and spoiler status visible.
- Avoid exposing internal model/provider names to end users unless useful and approved.

## 6. UX acceptance
Test with remote control on actual target devices/emulators. Verify focus order, screen scaling, keyboard behavior, long questions, long answers, slow network, expired sessions, unavailable title, spoiler confirmation, and backend errors. A browser preview alone is not sufficient proof of TV-platform correctness.
