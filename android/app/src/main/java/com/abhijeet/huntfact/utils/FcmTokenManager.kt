package com.abhijeet.huntfact.utils

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.tasks.await

object FcmTokenManager {
    private const val SHARED_PREF_NAME_LEGACY = "fact_check_prefs"
    private const val SHARED_PREF_NAME_SECURE = "fact_check_prefs_secure"
    private const val FCM_TOKEN_KEY = "fcm_token"
    private val securePrefsLock = Any()

    private fun legacyPrefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(SHARED_PREF_NAME_LEGACY, Context.MODE_PRIVATE)
    }

    private fun securePrefsOrNull(context: Context): SharedPreferences? {
        return runCatching {
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()
            EncryptedSharedPreferences.create(
                context,
                SHARED_PREF_NAME_SECURE,
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
            )
        }.getOrNull()
    }

    private fun tokenPrefs(context: Context): SharedPreferences {
        val securePrefs = securePrefsOrNull(context)
        if (securePrefs == null) {
            return legacyPrefs(context)
        }
        migrateLegacyTokenToSecure(context, securePrefs)
        return securePrefs
    }

    private fun migrateLegacyTokenToSecure(context: Context, securePrefs: SharedPreferences) {
        synchronized(securePrefsLock) {
            val secureToken = securePrefs.getString(FCM_TOKEN_KEY, null)
            if (!secureToken.isNullOrBlank()) {
                return
            }
            val legacyStore = legacyPrefs(context)
            val legacyToken = legacyStore.getString(FCM_TOKEN_KEY, null)
            if (legacyToken.isNullOrBlank()) {
                return
            }
            securePrefs.edit().putString(FCM_TOKEN_KEY, legacyToken).apply()
            legacyStore.edit().remove(FCM_TOKEN_KEY).apply()
        }
    }

    fun getSavedToken(context: Context): String? {
        val appContext = context.applicationContext
        return tokenPrefs(appContext).getString(FCM_TOKEN_KEY, null)
    }

    suspend fun getFcmToken(): String {
        return try {
            FirebaseMessaging.getInstance().token.await()
        } catch (e: Exception) {
            ""
        }
    }

    fun saveToken(context: Context, token: String) {
        val appContext = context.applicationContext
        tokenPrefs(appContext).edit().putString(FCM_TOKEN_KEY, token).apply()
        securePrefsOrNull(appContext)?.let {
            legacyPrefs(appContext).edit().remove(FCM_TOKEN_KEY).apply()
        }
    }
}
