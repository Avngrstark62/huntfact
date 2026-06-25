package com.abhijeet.huntfact.utils

import android.content.Context
import io.github.jan.supabase.auth.auth
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

object AuthSessionManager {
    private const val AUTH_PREFS = "huntfact_auth"
    private const val ACCESS_TOKEN_KEY = "access_token"

    private val _isAuthenticated = MutableStateFlow(false)
    val isAuthenticated: StateFlow<Boolean> = _isAuthenticated.asStateFlow()

    private fun readCachedToken(context: Context?): String? {
        if (context == null) {
            return null
        }
        val cached = context.applicationContext
            .getSharedPreferences(AUTH_PREFS, Context.MODE_PRIVATE)
            .getString(ACCESS_TOKEN_KEY, null)
        return cached?.takeIf { it.isNotBlank() }
    }

    private fun writeCachedToken(context: Context?, token: String?) {
        if (context == null) {
            return
        }
        context.applicationContext
            .getSharedPreferences(AUTH_PREFS, Context.MODE_PRIVATE)
            .edit()
            .apply {
                if (token.isNullOrBlank()) {
                    remove(ACCESS_TOKEN_KEY)
                } else {
                    putString(ACCESS_TOKEN_KEY, token)
                }
            }
            .apply()
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
