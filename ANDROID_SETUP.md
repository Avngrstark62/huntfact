# Android App Setup Guide

## Overview

This Android app implements the Fact Check Reel Sharer MVP as per the plan in `android/plan.md`. The app:

1. Appears in the share menu when sharing Instagram reels
2. Extracts the CDN video URL using Instagram's GraphQL API
3. Processes requests in the background using WorkManager
4. Sends the CDN URL to a backend server
5. Receives results via Firebase Cloud Messaging (FCM)
6. Displays results in a notification

## Architecture

### Components Implemented

1. **ShareReceiverActivity** - Entry point for share intent
   - No UI, immediately triggers background job
   - Location: `app/src/main/java/com/example/android/ShareReceiverActivity.kt`

2. **ReelProcessingWorker** - Background job processor
   - Extracts CDN URL from reel URL
   - Submits to backend API
   - Retries on failure
   - Location: `app/src/main/java/com/example/android/workers/ReelProcessingWorker.kt`

3. **ReelExtractor** - Kotlin port of Python extraction logic
   - Mirrors `android/reel_extractor.py` exactly
   - Uses OkHttp and Retrofit for network calls
   - Parses Instagram GraphQL responses
   - Location: `app/src/main/java/com/example/android/extraction/ReelExtractor.kt`

4. **FactCheckMessagingService** - FCM message handler
   - Receives push notifications
   - Shows notification with result
   - Clicks open ResultActivity with payload
   - Location: `app/src/main/java/com/example/android/notifications/FactCheckMessagingService.kt`

5. **ResultActivity** - Result display screen
   - Shows fact-check result from notification
   - Simple XML-based layout
   - Location: `app/src/main/java/com/example/android/ResultActivity.kt`

6. **ApiService** - Retrofit interface
   - POST /fact-check endpoint
   - Request: `{cdn_url, fcm_token}`
   - Location: `app/src/main/java/com/example/android/network/ApiService.kt`

7. **RetrofitClient** - HTTP client singleton
   - Configures Retrofit with base URL
   - Location: `app/src/main/java/com/example/android/network/RetrofitClient.kt`

### Manifest Configuration

Updated `AndroidManifest.xml` with:
- Internet and POST_NOTIFICATIONS permissions
- ShareReceiverActivity with ACTION_SEND intent filter
- ResultActivity (no export)
- FactCheckMessagingService for FCM
- Firebase messaging service registration

### Layout

- `activity_result.xml` - Simple result display with title and scrollable text

## Dependencies Added

The following dependencies have been added to `app/build.gradle.kts`:

```gradle
// WorkManager for background jobs
implementation("androidx.work:work-runtime-ktx:2.8.1")

// AppCompat
implementation("androidx.appcompat:appcompat:1.6.1")

// Retrofit for networking
implementation("com.squareup.retrofit2:retrofit:2.9.0")
implementation("com.squareup.retrofit2:converter-gson:2.9.0")
implementation("com.squareup.okhttp3:okhttp:4.11.0")

// Firebase Cloud Messaging
implementation(platform("com.google.firebase:firebase-bom:33.1.0"))
implementation("com.google.firebase:firebase-messaging-ktx")

// JSON parsing
implementation("com.google.code.gson:gson:2.10.1")

// Coroutines
implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.3")
implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
```

## Setup Instructions

### Prerequisites

1. **Java Development Kit (JDK) 21+** - Required for Kotlin compilation
   ```bash
   # Install on Ubuntu/Debian
   sudo apt-get install openjdk-21-jdk-headless
   ```

2. **Android Studio** - Latest version recommended
   - Download from: https://developer.android.com/studio

3. **Android SDK** - API Level 29+ (minSdk in build.gradle)

### Firebase Setup

1. Create a Firebase project at https://console.firebase.google.com
2. Register the Android app with package name `com.example.android`
3. Download `google-services.json` from Firebase Console
4. Place `google-services.json` in `app/` directory:
   ```
   android/app/google-services.json
   ```
5. Add Google Services plugin to `app/build.gradle.kts`:
   ```kotlin
   plugins {
       ...
       id("com.google.gms.google-services")
   }
   ```
6. Add to root `build.gradle.kts`:
   ```kotlin
   plugins {
       ...
       id("com.google.gms.google-services") apply false
   }
   ```

### Backend API Configuration

Update the base URL in `RetrofitClient.kt`:

```kotlin
object RetrofitClient {
    fun getApiService(baseUrl: String = "https://your-api-domain.com"): ApiService {
        // Configure with your actual backend URL
    }
}
```

### Building the App

1. **Open in Android Studio**:
   ```bash
   # From the android directory
   cd android
   # Open with Android Studio or
   ./gradlew assembleDebug
   ```

2. **Build APK**:
   ```bash
   ./gradlew assembleDebug
   ```

3. **Run on device/emulator**:
   ```bash
   ./gradlew installDebug
   ```

## Key Implementation Details

### Share Flow

1. User shares Instagram reel
2. App appears in share menu (via intent filter)
3. ShareReceiverActivity receives Intent.EXTRA_TEXT
4. Immediately enqueues ReelProcessingWorker
5. Activity finishes (no UI shown)

### Background Processing

1. ReelProcessingWorker extracts shortcode from reel URL
2. Fetches reel page to establish context
3. Extracts CSRF token from HTML
4. Sends GraphQL query with browser-like headers
5. Parses response to extract video_url
6. Gets FCM token from FirebaseMessaging
7. POSTs cdn_url + fcm_token to backend
8. Retries on network/extraction failures

### Notification Handling

1. Backend processes fact-check
2. Sends FCM message via Firebase
3. FactCheckMessagingService receives message
4. Shows notification with title and result summary
5. User taps notification → opens ResultActivity
6. Result text passed via intent extras

### Error Handling

- **Invalid URL** → Worker fails without retry
- **Extraction failure** → Worker retries (network error)
- **API failure** → Worker retries
- **Missing FCM token** → Worker retries

## Testing

### Manual Testing

1. **Share Test**:
   - Open Instagram, find a reel
   - Tap Share → select this app
   - App should handle share silently
   - Check logs: `adb logcat | grep ReelExtractor`

2. **FCM Test**:
   - Get device FCM token: Check Firebase Console
   - Send test message: Firebase Console → Cloud Messaging
   - Notification should appear

3. **Result Display**:
   - Tap notification in notification shade
   - ResultActivity should open with result text

## Code Structure

```
app/src/main/
├── java/com/example/android/
│   ├── extraction/
│   │   └── ReelExtractor.kt          # CDN extraction logic
│   ├── network/
│   │   ├── ApiService.kt            # Retrofit API interface
│   │   └── RetrofitClient.kt        # HTTP client setup
│   ├── workers/
│   │   └── ReelProcessingWorker.kt  # Background job
│   ├── notifications/
│   │   └── FactCheckMessagingService.kt  # FCM handler
│   ├── ShareReceiverActivity.kt     # Share entry point
│   ├── ResultActivity.kt            # Result display
│   └── MainActivity.kt              # Main launcher activity
├── res/
│   ├── layout/
│   │   └── activity_result.xml      # Result screen layout
│   └── values/
│       ├── strings.xml
│       ├── colors.xml
│       └── themes.xml
└── AndroidManifest.xml              # App configuration
```

## Important Notes

1. **No Authentication**: App doesn't require login (MVP)
2. **No Persistence**: Results not stored (MVP)
3. **No History**: Each reel is independent
4. **Background Only**: All heavy work in WorkManager
5. **Browser Headers**: Instagram requests use real browser headers to avoid blocking
6. **Coroutines**: Network calls use Kotlin coroutines for async operations

## Troubleshooting

### Build Issues

**Error: "Toolchain installation does not provide capabilities"**
- Install JDK 21: `sudo apt-get install openjdk-21-jdk-headless`
- Or update `compileOptions` and `kotlinOptions` in build.gradle.kts

**Error: "Failed to resolve dependency"**
- Run: `./gradlew --refresh-dependencies`
- Check internet connection

### Runtime Issues

**Share doesn't appear in menu**
- Verify intent filter in AndroidManifest.xml
- Ensure `android:exported="true"` on ShareReceiverActivity
- Clear app cache: `adb shell pm clear com.example.android`

**FCM tokens not received**
- Ensure google-services.json is in app/ directory
- Check Firebase Console → Cloud Messaging settings
- Verify POST_NOTIFICATIONS permission granted in Android 13+

**Extraction fails**
- Check Instagram headers in ReelExtractor
- Verify GraphQL doc_id is current (may change)
- Check network logs in logcat

## Next Steps (Post-MVP)

- Add database for history
- Implement authentication
- Add result persistence
- Build analytics
- Optimize extraction performance
- Add multiple GraphQL doc_id fallbacks
