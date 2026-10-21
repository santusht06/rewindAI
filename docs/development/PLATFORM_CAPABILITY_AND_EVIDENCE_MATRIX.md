# Platform Capability and Evidence Matrix — Rewind AI Assistant

**Document Reference:** `17_REWIND_CROSS_APP_ASSISTANT_PRODUCT_REQUIREMENT.md`  
**Last Updated:** 2026-10-21  
**Status:** Canonical Platform Research & Audit  

This document evaluates the technical feasibility of cross-application AI assistant capabilities across Amazon Fire OS (Android AOSP-based) and Amazon Vega OS (Linux microkernel/Web runtime), establishing what an ordinary third-party application can and cannot perform when paired with major commercial streaming providers (Netflix, Amazon Prime Video, Disney+, YouTube).

---

## 1. Executive Feasibility Summary

> [!IMPORTANT]
> **Core Principle of Platform Feasibility:**  
> An ordinary third-party TV app **cannot** secretly inspect, pause, or read playback state, DRM video frames, or subtitle tracks from another commercial streaming application (such as Netflix or Disney+) on either Fire OS or Vega OS.  
> 
> Any system claiming to "silently know" what is playing across arbitrary third-party streaming apps without user consent, system-level OEM privileges, or explicit partner APIs is either fabricating claims or relying on fragile, prohibited security vulnerabilities (e.g., accessibility abuse, hidden private APIs, or DRM circumvention) that are rejected by Amazon Appstore and Widevine security compliance.

Rewind maintains absolute transparency: where automatic cross-app synchronization is prohibited by OS sandbox boundaries, Rewind activates verified **Level 2 (Foreground Assistant with Context Preservation)** or **Level 3 (Companion Pairing / Manual Timestamp Confirmation)** fallbacks.

---

## 2. Platform Capability & Evidence Matrix

| Capability | Target OS / Version | Provider | Official Documentation / Evidence | Prototype Test Result | Real Result | Limitation | Approved Fallback |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Draw Floating Overlay Over Active Video** | Fire OS 7 / 8 (Android 9/11 AOSP) | Netflix, Disney+, Prime Video | `SYSTEM_ALERT_WINDOW` permission requires special app-ops grant; Widevine L1 secure surfaces block window compositing on TV | `FAIL`: Secure video surfaces render on hardware overlay layer above ordinary third-party windows | `UNAVAILABLE` | Amazon Appstore policy restricts `SYSTEM_ALERT_WINDOW` for TV apps; DRM layer blocks overlay rendering | **Level 2**: Foreground assistant surface with back-to-app resumption, or **Level 3**: Companion device/web UI |
| **Draw Floating Overlay Over Active Video** | Vega OS (Linux microkernel / Web) | All providers | Vega Application Lifecycle & Window Management Guide | `FAIL`: Web apps run in standalone fullscreen container without arbitrary overlay permissions | `UNAVAILABLE` | Vega OS web runtime isolates apps in fullscreen viewport | **Level 2**: Side-panel split-view or foreground companion mode |
| **Detect Active Foreground App/Package** | Fire OS 7 / 8 | All providers | Android `UsageStatsManager` / `ActivityManager.getRunningAppProcesses()` | `FAIL`: Returns only Rewind's own package name without privileged `PACKAGE_USAGE_STATS` | `UNAVAILABLE` | Requires explicit user adb grant or system-app signature | Prompt user to select active streaming service (Netflix, Prime Video, Disney+) |
| **Detect Active Foreground App/Package** | Vega OS | All providers | Vega OS Process Model documentation | `FAIL`: Microkernel process isolation hides peer processes from Web sandboxes | `UNAVAILABLE` | Web runtime cannot query system process table | User selects provider from quick-switch companion dock |
| **Read Playback Position (Seconds)** | Fire OS 7 / 8 | Netflix | Netflix proprietary player (`com.netflix.ninja`); no public ContentProvider or BroadcastReceiver | `FAIL`: No exported intent or AIDL interface accessible to third parties | `UNAVAILABLE` | Sandboxed proprietary media player | **Manual Progress Sync**: Quick +5m / +15m jumps, scrub bar, or audio fingerprinting |
| **Read Playback Position (Seconds)** | Fire OS 7 / 8 | Prime Video | Amazon Fire TV X-Ray & MediaSession integration | `PARTIAL`: Standard `MediaSession` token may broadcast playback state if enabled, but token inspection restricted | `PARTIAL` | Third-party apps cannot bind to `MediaSessionManager` without notification listener permissions | User confirms timestamp; default to manual offset input |
| **Read Playback Position (Seconds)** | Vega OS | All providers | Vega OS Media Playback Architecture | `FAIL`: Sandboxed web apps cannot access peer media playback tokens | `UNAVAILABLE` | Complete container isolation | Fast manual slider / remote timestamp selector |
| **Read Subtitle / Closed Caption Stream** | Fire OS 7 / 8 | Netflix, Disney+, Prime Video | Widevine DRM & MediaCodec secure decoder pipeline | `FAIL`: Subtitles rendered directly to secure surface buffer; not exposed via AccessibilityEvent | `UNAVAILABLE` | Captions are protected under content DRM | **Server-Side Pre-Indexed Transcripts**: Rewind matches authorized transcripts server-side; zero on-device scraping |
| **Read Subtitle / Closed Caption Stream** | Vega OS | All providers | Vega OS Secure Media Pipeline | `FAIL`: Web runtime cannot intercept DRM subtitle decoders | `UNAVAILABLE` | DRM hardware protection | **Server-Side Pre-Indexed Transcripts** with authorized cryptographic provenance |
| **Invoke via Voice / Remote Shortcut** | Fire OS 7 / 8 | All providers | Alexa Voice Services (AVS) / Fire TV Custom Skill & Voice Interaction API | `PASS`: "Alexa, open Rewind" launches assistant intent | `VERIFIED` | Cold-start switch moves user from Netflix to Rewind foreground | Launch Rewind foreground companion; Back button returns to Netflix |
| **Invoke via Remote / Companion Pairing** | Fire OS 7 / 8 & Vega OS | All providers | W3C WebSockets / Companion Pairing Web API (`/tv` companion paired to phone/tablet) | `PASS`: Second screen or background web receiver triggers instant assistant Q&A | `VERIFIED` | Requires companion device or TV side dock | Second-screen phone/tablet companion preserves 100% uninterrupted TV playback |
| **Return to Previous App on Dismiss** | Fire OS 7 / 8 | All providers | Android Activity Back Stack / `moveTaskToBack(true)` or `Intent.FLAG_ACTIVITY_REORDER_TO_FRONT` | `PASS`: Pressing Back/Return dismisses Rewind and restores previously running app | `VERIFIED` | Depends on OS memory pressure not killing background Netflix task | Standard TV `Back` / `Escape` key event resumes previous task |
| **Return to Previous App on Dismiss** | Vega OS | All providers | Vega OS App Switcher / History API | `PASS`: Closing assistant view resumes previous application state | `VERIFIED` | Handled by Vega system window manager | `Back` button closes assistant shell |

---

## 3. Approved Integration & Fallback Modes

Based on the empirical evidence above, Rewind implements four distinct, transparent integration modes:

```
+-----------------------------------------------------------------------------------+
|                            REWIND INTEGRATION MODES                               |
+-----------------------------------------------------------------------------------+
|  MODE 1: TV Split/Side-Panel Assistant (Primary 10-Ft Experience)                 |
|  - Occupies dedicated side panel (right 35% of 10-ft canvas)                      |
|  - Works over simulated video streams or as a dedicated foreground companion      |
|  - D-pad spatial navigation preserves instant focus                               |
+-----------------------------------------------------------------------------------+
|  MODE 2: Companion Device / Second Screen (Uninterrupted Viewing)                |
|  - Viewer scans QR code / pairs phone or tablet at http://localhost:8000/tv/     |
|  - TV keeps playing Netflix/Prime Video full-screen with ZERO interruption       |
|  - Real-time Q&A, translations, and character facts run on companion phone        |
+-----------------------------------------------------------------------------------+
|  MODE 3: Quick-Switch Foreground Assistant (Standard Remote Entry)                |
|  - Invoked via Voice ("Alexa, ask Rewind") or TV App Switcher                    |
|  - Fast modal Q&A; pressing "Back" or "Return to Stream" immediately resumes app   |
+-----------------------------------------------------------------------------------+
|  MODE 4: Manual Playback Synchronization (Fail-Safe Truthfulness)                 |
|  - When streaming provider does not expose playback timestamp:                     |
|  - Viewer selects approximate timestamp (+5m, +15m, or HH:MM:SS input)           |
|  - Prevents ANY accidental spoiler leaks by assuming strict conservative boundary |
+-----------------------------------------------------------------------------------+
```

---

## 4. Provider-Neutral Architecture Contract

The backend decouples all question answering and spoiler safety from specific streaming apps through five foundational interfaces in `services/api/assistant/`:

1. **`PlaybackContextProvider`**: Defines the contract for acquiring current title, timestamp, and language.
2. **`AssistantEntryPoint`**: Encapsulates invocation channels (Voice, Remote Shortcut, Companion Web, UI Button).
3. **`AssistantPresentationAdapter`**: Manages presentation styles (Side Panel, Modal Overlay, Companion Device, Fullscreen).
4. **`ContentEvidenceProvider`**: Supplies authorized, pre-indexed subtitle transcripts with cryptographic verification.
5. **`ProviderCapabilityRegistry`**: Maintains an auditable registry of what each streaming provider supports on Fire OS and Vega OS.
