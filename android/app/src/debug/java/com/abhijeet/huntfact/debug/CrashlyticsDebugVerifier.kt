package com.abhijeet.huntfact.debug

import com.abhijeet.huntfact.BuildConfig
import com.google.firebase.Firebase
import com.google.firebase.crashlytics.crashlytics

/**
 * Temporary debug-only Crashlytics verification helpers.
 * Remove this object after validating Crashlytics end-to-end.
 */
object CrashlyticsDebugVerifier {
    fun runNonFatalTest() {
        Firebase.crashlytics.log("Crashlytics test started")
        Firebase.crashlytics.log(
            "Current app version: ${BuildConfig.VERSION_NAME} (${BuildConfig.VERSION_CODE})"
        )
        Firebase.crashlytics.recordException(Exception("Crashlytics non-fatal test"))
        Firebase.crashlytics.log("Crashlytics non-fatal test completed")
    }

    fun runFatalTest() {
        throw RuntimeException("Crashlytics fatal test")
    }
}
