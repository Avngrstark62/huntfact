# Production Concern: Android App Readiness

Focus: Android release readiness, UX reliability, security/privacy, and compatibility with the current backend contracts.

## Release Blockers

- [x] **Fix `start-hunt` response contract mismatch before release** (`android/app/src/main/java/com/abhijeet/huntfact/network/ApiService.kt`, `android/app/src/main/java/com/abhijeet/huntfact/workers/ReelProcessingWorker.kt`, `backend/schemas.py`)  
  Android expects `status` in `StartHuntResponse` and uses it immediately, but backend `StartHuntResponse` only guarantees `success`, `message`, and `hunt_id`. This can cause runtime failures when creating local `HuntItem` from the response.

- [x] **Fix hunt result type mismatch for `/hunts` and `/hunts/{hunt_id}`** (`android/app/src/main/java/com/abhijeet/huntfact/network/ApiService.kt`, `android/app/src/main/java/com/abhijeet/huntfact/ResultActivity.kt`, `backend/schemas.py`)  
  Android models `HuntDto.result` as `String?`, while backend returns structured JSON rows (`list[FactCheckRow]`). This can break deserialization and prevent hunt list/detail rendering.

- [x] **Point release builds to stable production backend URL** (`android/app/build.gradle.kts`)  
  Current default backend points to an `ngrok` endpoint, which is ephemeral and not release-safe.

- [x] **Harden backup policy for auth/session data** (`android/app/src/main/AndroidManifest.xml`, `android/app/src/main/res/xml/backup_rules.xml`, `android/app/src/main/res/xml/data_extraction_rules.xml`)  
  `allowBackup=true` with default/sample backup rules risks backing up shared preferences containing auth/session-related data on user cloud/device backups.

## High Severity

- [x] **Decouple hunt creation from FCM token availability** (`android/app/src/main/java/com/abhijeet/huntfact/workers/ReelProcessingWorker.kt`)  
  If FCM token fetch fails, hunt creation fails entirely, even though users could still poll status manually from API.

- [x] **Add explicit UX handling for backend throttling and service-unhealthy states** (`android/app/src/main/java/com/abhijeet/huntfact/workers/ReelProcessingWorker.kt`, `android/app/src/main/java/com/abhijeet/huntfact/ui/hunts/HuntsViewModel.kt`)  
  Backend can return 429/503, but app mostly maps failures to generic error messages/notifications; users do not know whether to retry later, sign in again, or change input.

- [x] **Handle notification-permission denied path with a fallback user journey** (`android/app/src/main/java/com/abhijeet/huntfact/MainActivity.kt`, `android/app/src/main/java/com/abhijeet/huntfact/notifications/FactCheckMessagingService.kt`)  
  App depends on notifications for result discovery, but permission-denied users get no guided fallback (e.g., in-app polling/status prompt).

- [x] **Remove or gate development-only cleartext network exception in release** (`android/app/src/main/res/xml/network_security_config.xml`)  
  Release builds should avoid unnecessary cleartext allowances unless strictly required and justified.

- [x] **Protect local hunt/auth artifacts at rest** (`android/app/src/main/java/com/abhijeet/huntfact/hunts/HuntLocalStore.kt`, `android/app/src/main/java/com/abhijeet/huntfact/utils/AuthSessionManager.kt`)  
  Hunt history and cached token are persisted in plain SharedPreferences. Consider encrypted storage for production privacy posture.

## Important Gaps

- [x] **Send real reel metadata when available** (`android/app/src/main/java/com/abhijeet/huntfact/workers/ReelProcessingWorker.kt`)  
  Request currently sends placeholder values (`thumbnail_url`, `caption` set to URL; `creator_handle = "unknown_creator"`), reducing backend metadata quality and final UX clarity.

- [ ] **Use idempotent/unique work policy for duplicate share actions** (`android/app/src/main/java/com/abhijeet/huntfact/ShareReceiverActivity.kt`)  
  Rapid repeated shares enqueue multiple workers; backend has duplicate protections, but client-side dedupe improves UX and reduces avoidable load.

- [x] **Convert generic failure notifications into actionable states** (`android/app/src/main/java/com/abhijeet/huntfact/workers/ReelProcessingWorker.kt`)  
  Current “Error processing reel” messaging is too broad for common failures (auth expired, rate-limited, temporary backend outage, invalid/private reel).

- [x] **Decide release behavior for unfinished/placeholder surfaces** (`android/app/src/main/java/com/abhijeet/huntfact/MainActivity.kt`, `android/app/src/main/java/com/abhijeet/huntfact/ui/resources/ResourcesViewModel.kt`)  
  Analyze tab is intentionally disabled and resources flow uses stub data; either hide these paths for release or clearly label as beta/coming soon.

- [x] **Review debug log export for PII/privacy boundaries** (`android/app/src/main/java/com/abhijeet/huntfact/MainActivity.kt`, `android/app/src/main/java/com/abhijeet/huntfact/utils/DebugLogger.kt`)  
  Exported logs can include user-shared URLs and operational traces. Define production policy (opt-in, redaction scope, support-only flow).

## Nice to Have (Post-Release Quality)

- [x] **Add explicit loading/progress phases for hunt lifecycle in UI** (`android/app/src/main/java/com/abhijeet/huntfact/ui/hunts/HuntsScreen.kt`, `android/app/src/main/java/com/abhijeet/huntfact/ResultActivity.kt`)  
  Distinguish queued/extracting/verifying/saving to reduce uncertainty during long processing windows.

- [ ] **Add structured telemetry for client failures by category** (Android app-wide)  
  Track auth failures vs rate limits vs extractor/network issues vs backend errors to prioritize fixes after launch.

- [ ] **Clean up legacy extractor code path from production source set** (`android/app/src/main/java/com/abhijeet/huntfact/extraction/ReelExtractor_old.kt`)  
  Keeping unused production code increases maintenance and confusion risk.
