package com.example.factchecksharer.fcm

import android.content.Context
import android.content.SharedPreferences
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.tasks.await

object FcmTokenManager {
    private const val PREF_NAME = "fcm_prefs"
    private const val TOKEN_KEY = "fcm_token"
    private lateinit var prefs: SharedPreferences

    fun initialize(context: Context) {
        prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
    }

    fun getToken(): String? {
        return prefs.getString(TOKEN_KEY, null)
    }

    suspend fun refreshToken() {
        try {
            val token = FirebaseMessaging.getInstance().token.await()
            prefs.edit().putString(TOKEN_KEY, token).apply()
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun saveToken(token: String) {
        prefs.edit().putString(TOKEN_KEY, token).apply()
    }
}
