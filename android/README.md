# Fact Check Reel Sharer

An Android app that appears in the Instagram share menu, extracts reel CDN URLs, and sends them to a backend for fact-checking.

## What It Does

1. User shares an Instagram reel → App appears in share menu
2. App extracts the reel URL (no UI shown)
3. Enqueues background job to extract CDN video URL
4. Sends CDN URL + FCM token to backend
5. Receives notification when result is ready
6. Opens result screen with fact-check output

## Project Structure

```
app/src/main/java/com/example/factchecksharer/
├── api/              - Retrofit API client & service
├── extractor/        - Instagram reel CDN URL extraction (Kotlin port)
├── fcm/              - Firebase messaging & token management
├── ui/               - Activities (ShareReceiverActivity, ResultActivity)
├── worker/           - WorkManager background job
└── R.kt              - Resource constants
```

## Entry Points

### ShareReceiverActivity
- **When:** User shares reel from Instagram
- **What it does:** Receives URL, enqueues job, finishes immediately (no UI)
- **Exported:** Yes (part of share menu)

### ResultActivity
- **When:** User taps notification
- **What it does:** Displays fact-check result from notification payload
- **Extras:** `result_text` (String)

## How to Run

### Prerequisites
- Android Studio (latest)
- Android SDK 34+
- Firebase project configured

### Setup

1. Replace `BASE_URL` in `ApiClient.kt` with actual backend URL
2. Replace `app/google-services.json` with real Firebase config
3. Sync Gradle dependencies

### Build

```bash
./gradlew build          # Build APK
./gradlew assembleDebug  # Debug APK
```

### Install

```bash
./gradlew installDebug   # Install on device/emulator
```

## Key Components

| Component | Purpose |
|-----------|---------|
| `ReelExtractor` | Ported from Python - extracts CDN URL from Instagram reel |
| `ReelProcessingWorker` | Background job via WorkManager |
| `FactCheckMessagingService` | Handles FCM notifications |
| `FcmTokenManager` | Stores & retrieves FCM token |
| `ApiClient` | Retrofit setup for backend calls |

## Dependencies

- **Retrofit** - HTTP client
- **Firebase** - Push notifications (FCM)
- **WorkManager** - Background jobs
- **Gson** - JSON parsing
- **OkHttp** - HTTP layer
- **Coroutines** - Async operations

## Configuration

Update in `ApiClient.kt`:
```kotlin
private const val BASE_URL = "https://your-backend-api.com"
```

## Manifest Intents

The app is registered for:
- **Action:** `android.intent.action.SEND`
- **Type:** `text/plain`
- **Category:** `android.intent.category.DEFAULT`

This makes it appear in share menu for text shares (like Instagram reel links).

## Testing Flow

1. Open Instagram, find a reel
2. Tap Share → Select this app
3. App finishes (no UI shown)
4. Check WorkManager logs for background job
5. On backend completion, FCM notification sent
6. Tap notification → ResultActivity opens with result

## Notes

- No UI during share (immediate finish)
- All work done in background (WorkManager)
- Works even if app is closed
- Browser-like headers for Instagram requests
- Retry logic on failure
- FCM token stored locally in SharedPreferences
