package com.example.android.utils

import android.content.Context
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.tasks.await

object FcmTokenManager {
    private const val SHARED_PREF_NAME = "fact_check_prefs"
    private const val FCM_TOKEN_KEY = "fcm_token"

    fun getSavedToken(context: Context): String? {
        val sharedPref = context.getSharedPreferences(SHARED_PREF_NAME, Context.MODE_PRIVATE)
        return sharedPref.getString(FCM_TOKEN_KEY, null)
    }

    suspend fun getFcmToken(): String {
        return try {
            FirebaseMessaging.getInstance().token.await()
        } catch (e: Exception) {
            ""
        }
    }

    fun saveToken(context: Context, token: String) {
        val sharedPref = context.getSharedPreferences(SHARED_PREF_NAME, Context.MODE_PRIVATE)
        sharedPref.edit().putString(FCM_TOKEN_KEY, token).apply()
    }
}
