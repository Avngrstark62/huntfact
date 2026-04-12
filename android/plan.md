# 📱 Android App Plan — Fact Check Reel Sharer (MVP)

## 1. Goal

Build an Android app that:

* Appears in the share menu when a user shares a reel from Instagram
* Receives the reel URL without opening UI
* Extracts CDN video URL
* Sends it to backend
* Receives result later via push notification

---

## 2. Tech Stack

* Language: **Kotlin**
* Background jobs: **WorkManager**
* Networking: **Retrofit**
* Notifications: **Firebase Cloud Messaging**
* Async: Kotlin Coroutines
* UI: **XML-based layouts (Android Views)**

---

## 3. Core Flow

```id="93e7ro"
User taps "Share" on Instagram reel
→ Selects this app from share list
→ App receives reel URL
→ Immediately enqueue background job
→ Extract CDN URL using existing logic (ported from Python)
→ Send CDN URL + FCM token to backend
→ Backend processes
→ Backend sends FCM notification
→ App shows notification
→ (Optional) user taps → open result screen
```

---

## 4. Features to Implement

### 4.1 Share Target (Entry Point)

* Use Android Intent system
* Accept:

  * `action = ACTION_SEND`
  * `type = "text/plain"`
* Extract reel URL from:

  * `intent.getStringExtra(Intent.EXTRA_TEXT)`

Behavior:

* Do NOT show UI
* Immediately trigger background job
* Finish activity immediately

---

### 4.2 Background Processing

Use **WorkManager**

Create:

* `ReelProcessingWorker`

Responsibilities:

1. Input: reel URL
2. Extract CDN URL using Kotlin implementation (see section 4.6)
3. Validate extracted CDN URL
4. Call backend API

Retry:

* Enable retry on failure

Constraints:

* No heavy CPU work
* Timeout-safe

---

### 4.3 Networking

Use Retrofit

API request:

```id="a0dul5"
POST /fact-check

Body:
{
  "cdn_url": "<video_cdn_url>",
  "fcm_token": "<device_token>"
}
```

Expected:

* Success response (no need to wait for result)

---

### 4.4 Push Notifications (FCM)

Setup:

* Integrate Firebase
* Generate FCM token on app start
* Store token locally
* Send token with every request

Handle:

* Incoming FCM message
* Show notification with:

  * Title: "Fact Check Ready"
  * Body: short summary (from backend)

---

### 4.5 Notification Click Behavior

* Open `ResultActivity`
* Pass result data from notification payload via intent extras

(MVP: basic screen, no persistence required)

---

### 4.6 Reel URL → CDN URL Extraction (Critical)

#### Source of Truth

* Existing file: `android/reel_extractor.py`
* This file contains the **exact working logic**

---

#### Requirement

* DO NOT use Python in Android app
* Reimplement the same logic in Kotlin

---

#### Implementation Rules

* Create a Kotlin utility:

```id="kq3s0p"
object ReelExtractor {
    suspend fun extractCdnUrl(reelUrl: String): String?
}
```

---

#### Porting Instructions

* Carefully read `reel_extractor.py`
* Replicate logic exactly:

  * Same request flow (GraphQL / endpoints)
  * Same headers (very important for Instagram)
  * Same parsing logic
* Use:

  * Retrofit / OkHttp for HTTP calls
  * JSON parsing using standard Kotlin libraries

---

#### Constraints

* Must behave identically to Python version
* Must not introduce extra proxying
* Must run inside WorkManager
* Must handle:

  * Invalid reel URL → return null
  * Extraction failure → throw retryable error

---

## 4.7 UI Implementation (MVP)

#### UI Approach

* Use XML layouts (Android Views)
* No Jetpack Compose
* Minimal UI only where required

---

#### Screens

##### 1. Result Screen

Activity: `ResultActivity`

Purpose:

* Display fact-check result received from notification

Layout file:

* `res/layout/activity_result.xml`

UI Elements:

```id="miv0qa"
- TextView (id: titleText)
  → Static text: "Fact Check Result"

- TextView (id: resultText)
  → Dynamic content from backend

- (Optional) ScrollView wrapper for long text
```

Behavior:

* Read data from intent extras:

  * `result_text`
* Set text to `resultText`

---

#### 2. No UI for Share Flow

* `ShareReceiverActivity` should:

  * Have NO layout
  * Not call `setContentView`
  * Immediately enqueue WorkManager job
  * Call `finish()`

---

#### 3. Notification UI

Notification should include:

* Title: `"Fact Check Ready"`
* Body: short summary
* PendingIntent:

  * Opens `ResultActivity`
  * Passes full result in extras

---

## 5. App Components

### Required

* `ShareReceiverActivity` (no UI)
* `ReelProcessingWorker`
* `ReelExtractor` (Kotlin port of Python logic)
* `ApiService` (Retrofit)
* `FirebaseMessagingService` (FCM handler)
* `ResultActivity` (only UI screen)

---

## 6. AndroidManifest Requirements

* Intent filter for share:

```id="98gclt"
<action android:name="android.intent.action.SEND" />
<category android:name="android.intent.category.DEFAULT" />
<data android:mimeType="text/plain" />
```

* Register:

  * Firebase Messaging Service
  * Internet permission

---

## 7. Error Handling

Worker should handle:

* Invalid URL → fail (no retry)
* CDN extraction failure → retry
* Network failure → retry

Do NOT crash app

---

## 8. Non-Goals (for MVP)

* No authentication
* No database/storage
* No history
* No analytics
* No complex UI

---

## 9. Constraints

* App should not block UI
* All processing must be background
* Must work even if app is closed after sharing

---

## 10. Deliverables

* Working APK
* Able to:

  1. Receive Instagram reel via share
  2. Extract CDN URL using Kotlin (ported from Python)
  3. Process in background
  4. Send to backend
  5. Receive FCM notification
  6. Open result screen and display fact-check output

