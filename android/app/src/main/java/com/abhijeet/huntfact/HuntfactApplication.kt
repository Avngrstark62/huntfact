package com.abhijeet.huntfact

import android.app.Application
import com.google.firebase.Firebase
import com.google.firebase.crashlytics.crashlytics

class HuntfactApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        if (BuildConfig.DEBUG) {
            Firebase.crashlytics.setCrashlyticsCollectionEnabled(true)
            Firebase.crashlytics.log("HuntfactApplication.onCreate: Crashlytics collection enabled for debug build")
        }
    }
}
