package com.abhijeet.huntfact.utils

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import io.github.jan.supabase.auth.auth
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

object AuthSessionManager {
    private const val AUTH_PREFS_LEGACY = "huntfact_auth"
    private const val AUTH_PREFS_SECURE = "huntfact_auth_secure"
    private const val ACCESS_TOKEN_KEY = "access_token"
    private val securePrefsLock = Any()

    private val _isAuthenticated = MutableStateFlow(false)
    val isAuthenticated: StateFlow<Boolean> = _isAuthenticated.asStateFlow()

    private fun legacyPrefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(AUTH_PREFS_LEGACY, Context.MODE_PRIVATE)
    }

    private fun securePrefsOrNull(context: Context): SharedPreferences? {
        return runCatching {
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()
            EncryptedSharedPreferences.create(
                context,
                AUTH_PREFS_SECURE,
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
            )
        }.getOrNull()
    }

    private fun authPrefs(context: Context): SharedPreferences {
        val securePrefs = securePrefsOrNull(context)
        if (securePrefs == null) {
            return legacyPrefs(context)
        }
        migrateLegacyTokenToSecure(context, securePrefs)
        return securePrefs
    }

    private fun migrateLegacyTokenToSecure(context: Context, securePrefs: SharedPreferences) {
        synchronized(securePrefsLock) {
            val secureToken = securePrefs.getString(ACCESS_TOKEN_KEY, null)
            if (!secureToken.isNullOrBlank()) {
                return
            }
            val legacyStore = legacyPrefs(context)
            val legacyToken = legacyStore.getString(ACCESS_TOKEN_KEY, null)
            if (legacyToken.isNullOrBlank()) {
                return
            }
            securePrefs.edit().putString(ACCESS_TOKEN_KEY, legacyToken).apply()
            legacyStore.edit().remove(ACCESS_TOKEN_KEY).apply()
        }
    }

    private fun readCachedToken(context: Context?): String? {
        if (context == null) {
            return null
        }
        val appContext = context.applicationContext
        val cached = authPrefs(appContext).getString(ACCESS_TOKEN_KEY, null)
        return cached?.takeIf { it.isNotBlank() }
    }

    private fun writeCachedToken(context: Context?, token: String?) {
        if (context == null) {
            return
        }
        val appContext = context.applicationContext
        val prefs = authPrefs(appContext)
        prefs
            .edit()
            .apply {
                if (token.isNullOrBlank()) {
                    remove(ACCESS_TOKEN_KEY)
                } else {
                    putString(ACCESS_TOKEN_KEY, token)
                }
            }
            .apply()
        securePrefsOrNull(appContext)?.let {
            legacyPrefs(appContext).edit().remove(ACCESS_TOKEN_KEY).apply()
        }
    }

    fun invalidateLocalSession(context: Context? = null) {
        writeCachedToken(context, null)
        _isAuthenticated.value = false
    }

    fun getAccessToken(context: Context? = null): String? {
        val liveToken = try {
            SupabaseClientProvider.client.auth.currentSessionOrNull()?.accessToken
        } catch (_: Exception) {
            null
        }
        if (!liveToken.isNullOrBlank()) {
            writeCachedToken(context, liveToken)
            return liveToken
        }
        return readCachedToken(context)
    }

    suspend fun refreshAuthState(context: Context? = null): Boolean {
        val hasSession = !getAccessToken(context).isNullOrBlank()
        _isAuthenticated.value = hasSession
        return hasSession
    }

    suspend fun hasValidSession(context: Context? = null): Boolean {
        return refreshAuthState(context)
    }

    suspend fun signOut(context: Context? = null): Boolean {
        return try {
            SupabaseClientProvider.client.auth.signOut()
            invalidateLocalSession(context)
            true
        } catch (_: Exception) {
            false
        }
    }
}
