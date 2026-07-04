package com.abhijeet.huntfact.utils

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import io.github.jan.supabase.auth.auth
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import org.json.JSONObject
import java.util.Base64

object AuthSessionManager {
    private const val AUTH_PREFS_LEGACY = "huntfact_auth"
    private const val AUTH_PREFS_SECURE = "huntfact_auth_secure"
    private const val ACCESS_TOKEN_KEY = "access_token"
    private const val REFRESH_TOKEN_KEY = "refresh_token"
    private const val ACCESS_TOKEN_EXPIRY_EPOCH_SECONDS_KEY = "access_token_expiry_epoch_seconds"
    private const val SESSION_CACHED_AT_EPOCH_MS_KEY = "session_cached_at_epoch_ms"
    private val securePrefsLock = Any()
    private val refreshLock = Mutex()

    private val _isAuthenticated = MutableStateFlow(false)
    val isAuthenticated: StateFlow<Boolean> = _isAuthenticated.asStateFlow()

    private data class CachedSession(
        val accessToken: String?,
        val refreshToken: String?,
        val accessTokenExpiryEpochSeconds: Long?,
        val sessionCachedAtEpochMs: Long?,
    )

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
            val secureSession = readCachedSession(securePrefs)
            if (!secureSession.accessToken.isNullOrBlank()) {
                return
            }
            val legacyStore = legacyPrefs(context)
            val legacyToken = legacyStore.getString(ACCESS_TOKEN_KEY, null)
            if (legacyToken.isNullOrBlank()) {
                return
            }
            securePrefs
                .edit()
                .putString(ACCESS_TOKEN_KEY, legacyToken)
                .putLong(SESSION_CACHED_AT_EPOCH_MS_KEY, System.currentTimeMillis())
                .putLong(
                    ACCESS_TOKEN_EXPIRY_EPOCH_SECONDS_KEY,
                    decodeJwtExpiryEpochSecondsOrNull(legacyToken) ?: UNSET_LONG_SENTINEL,
                )
                .apply()
            legacyStore.edit().remove(ACCESS_TOKEN_KEY).apply()
        }
    }

    private fun readCachedSession(prefs: SharedPreferences): CachedSession {
        val accessToken = prefs.getString(ACCESS_TOKEN_KEY, null)?.takeIf { it.isNotBlank() }
        val refreshToken = prefs.getString(REFRESH_TOKEN_KEY, null)?.takeIf { it.isNotBlank() }
        val tokenExpiryEpochSeconds = prefs
            .getLong(ACCESS_TOKEN_EXPIRY_EPOCH_SECONDS_KEY, UNSET_LONG_SENTINEL)
            .takeIf { it > 0 }
        val sessionCachedAtEpochMs = prefs
            .getLong(SESSION_CACHED_AT_EPOCH_MS_KEY, UNSET_LONG_SENTINEL)
            .takeIf { it > 0 }
        return CachedSession(
            accessToken = accessToken,
            refreshToken = refreshToken,
            accessTokenExpiryEpochSeconds = tokenExpiryEpochSeconds,
            sessionCachedAtEpochMs = sessionCachedAtEpochMs,
        )
    }

    private fun readCachedToken(context: Context?): String? {
        if (context == null) {
            return null
        }
        val appContext = context.applicationContext
        return readCachedSession(authPrefs(appContext)).accessToken
    }

    private fun readCachedRefreshToken(context: Context?): String? {
        if (context == null) {
            return null
        }
        val appContext = context.applicationContext
        return readCachedSession(authPrefs(appContext)).refreshToken
    }

    private fun writeCachedSession(
        context: Context?,
        accessToken: String?,
        refreshToken: String?,
    ) {
        if (context == null) {
            return
        }
        val appContext = context.applicationContext
        val prefs = authPrefs(appContext)
        val accessTokenExpiryEpochSeconds = accessToken?.let { decodeJwtExpiryEpochSecondsOrNull(it) }
        prefs
            .edit()
            .apply {
                if (accessToken.isNullOrBlank()) {
                    remove(ACCESS_TOKEN_KEY)
                    remove(ACCESS_TOKEN_EXPIRY_EPOCH_SECONDS_KEY)
                    remove(SESSION_CACHED_AT_EPOCH_MS_KEY)
                } else {
                    putString(ACCESS_TOKEN_KEY, accessToken)
                    putLong(
                        ACCESS_TOKEN_EXPIRY_EPOCH_SECONDS_KEY,
                        accessTokenExpiryEpochSeconds ?: UNSET_LONG_SENTINEL,
                    )
                    putLong(SESSION_CACHED_AT_EPOCH_MS_KEY, System.currentTimeMillis())
                }
                if (refreshToken.isNullOrBlank()) {
                    remove(REFRESH_TOKEN_KEY)
                } else {
                    putString(REFRESH_TOKEN_KEY, refreshToken)
                }
            }
            .apply()
        securePrefsOrNull(appContext)?.let {
            legacyPrefs(appContext).edit().remove(ACCESS_TOKEN_KEY).apply()
        }
    }

    fun invalidateLocalSession(context: Context? = null) {
        writeCachedSession(context, null, null)
        _isAuthenticated.value = false
    }

    private fun cacheLiveSession(context: Context?, accessToken: String, refreshToken: String?) {
        writeCachedSession(
            context = context,
            accessToken = accessToken,
            refreshToken = refreshToken ?: readCachedRefreshToken(context),
        )
    }

    fun getAccessToken(context: Context? = null): String? {
        val liveSession = try {
            SupabaseClientProvider.client.auth.currentSessionOrNull()
        } catch (_: Exception) {
            null
        }
        val liveToken = liveSession?.accessToken
        if (!liveToken.isNullOrBlank()) {
            cacheLiveSession(context, liveToken, liveSession.refreshToken)
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

    suspend fun attemptSessionRefresh(context: Context? = null): Boolean {
        val appContext = context?.applicationContext
        return refreshLock.withLock {
            val hasRefreshToken = !readCachedRefreshToken(appContext).isNullOrBlank() ||
                runCatching {
                    !SupabaseClientProvider.client.auth.currentSessionOrNull()?.refreshToken.isNullOrBlank()
                }.getOrDefault(false)
            if (!hasRefreshToken) {
                return@withLock false
            }

            val refreshSucceeded = runCatching {
                SupabaseClientProvider.client.auth.refreshCurrentSession()
            }.isSuccess

            val refreshedSession = runCatching {
                SupabaseClientProvider.client.auth.currentSessionOrNull()
            }.getOrNull()

            val refreshedAccessToken = refreshedSession?.accessToken
            if (!refreshSucceeded || refreshedAccessToken.isNullOrBlank()) {
                return@withLock false
            }

            cacheLiveSession(appContext, refreshedAccessToken, refreshedSession.refreshToken)
            _isAuthenticated.value = true
            return@withLock true
        }
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

    private fun decodeJwtExpiryEpochSecondsOrNull(token: String): Long? {
        return runCatching {
            val parts = token.split(".")
            if (parts.size < 2) {
                return null
            }
            val payloadJson = String(Base64.getUrlDecoder().decode(parts[1]))
            val payload = JSONObject(payloadJson)
            if (!payload.has("exp")) {
                return null
            }
            payload.optLong("exp", 0L).takeIf { it > 0L }
        }.getOrNull()
    }

    private const val UNSET_LONG_SENTINEL = -1L
}
