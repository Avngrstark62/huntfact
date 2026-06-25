package com.abhijeet.huntfact.utils

import android.content.Context
import com.google.firebase.Firebase
import com.google.firebase.crashlytics.crashlytics
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.tasks.await

object FcmTokenManager {
    private const val SHARED_PREF_NAME = "fact_check_prefs"
    private const val FCM_TOKEN_KEY = "fcm_token"

    fun getSavedToken(context: Context): String? {
        Firebase.crashlytics.log("FcmTokenManager.getSavedToken: reading from SharedPreferences")
        val sharedPref = context.getSharedPreferences(SHARED_PREF_NAME, Context.MODE_PRIVATE)
        return sharedPref.getString(FCM_TOKEN_KEY, null).also {
            Firebase.crashlytics.log("FcmTokenManager.getSavedToken: completed hasToken=${!it.isNullOrBlank()}")
        }
    }

    suspend fun getFcmToken(): String {
        Firebase.crashlytics.log("FcmTokenManager.getFcmToken: started")
        return try {
            Firebase.crashlytics.log("FcmTokenManager.getFcmToken: requesting FirebaseMessaging token")
            FirebaseMessaging.getInstance().token.await()
        } catch (exception: Exception) {
            Firebase.crashlytics.log("FcmTokenManager.getFcmToken: failed to fetch token")
            Firebase.crashlytics.recordException(exception)
            ""
        }
    }

    fun saveToken(context: Context, token: String) {
        Firebase.crashlytics.log("FcmTokenManager.saveToken: writing token hasToken=${token.isNotBlank()}")
        val sharedPref = context.getSharedPreferences(SHARED_PREF_NAME, Context.MODE_PRIVATE)
        sharedPref.edit().putString(FCM_TOKEN_KEY, token).apply()
        Firebase.crashlytics.log("FcmTokenManager.saveToken: completed")
    }
}
