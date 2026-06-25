package com.abhijeet.huntfact.utils

import android.content.Context
import com.google.firebase.Firebase
import com.google.firebase.crashlytics.crashlytics
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
        Firebase.crashlytics.log("AuthSessionManager.readCachedToken: started")
        if (context == null) {
            Firebase.crashlytics.log("AuthSessionManager.readCachedToken: context is null")
            return null
        }
        val cached = context.applicationContext
            .getSharedPreferences(AUTH_PREFS, Context.MODE_PRIVATE)
            .getString(ACCESS_TOKEN_KEY, null)
        Firebase.crashlytics.log("AuthSessionManager.readCachedToken: completed hasToken=${!cached.isNullOrBlank()}")
        return cached?.takeIf { it.isNotBlank() }
    }

    private fun writeCachedToken(context: Context?, token: String?) {
        Firebase.crashlytics.log("AuthSessionManager.writeCachedToken: started hasToken=${!token.isNullOrBlank()}")
        if (context == null) {
            Firebase.crashlytics.log("AuthSessionManager.writeCachedToken: context is null, skipping write")
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
        Firebase.crashlytics.log("AuthSessionManager.writeCachedToken: completed")
    }

    fun invalidateLocalSession(context: Context? = null) {
        Firebase.crashlytics.log("AuthSessionManager.invalidateLocalSession: started")
        writeCachedToken(context, null)
        _isAuthenticated.value = false
        Firebase.crashlytics.log("AuthSessionManager.invalidateLocalSession: completed")
    }

    fun getAccessToken(context: Context? = null): String? {
        Firebase.crashlytics.log("AuthSessionManager.getAccessToken: started")
        val liveToken = try {
            SupabaseClientProvider.client.auth.currentSessionOrNull()?.accessToken
        } catch (exception: Exception) {
            Firebase.crashlytics.log("AuthSessionManager.getAccessToken: failed to read live session token")
            Firebase.crashlytics.recordException(exception)
            null
        }
        if (!liveToken.isNullOrBlank()) {
            Firebase.crashlytics.log("AuthSessionManager.getAccessToken: using live token")
            writeCachedToken(context, liveToken)
            return liveToken
        }
        Firebase.crashlytics.log("AuthSessionManager.getAccessToken: using cached token fallback")
        return readCachedToken(context)
    }

    suspend fun refreshAuthState(context: Context? = null): Boolean {
        Firebase.crashlytics.log("AuthSessionManager.refreshAuthState: started")
        val hasSession = !getAccessToken(context).isNullOrBlank()
        _isAuthenticated.value = hasSession
        Firebase.crashlytics.log("AuthSessionManager.refreshAuthState: completed isAuthenticated=$hasSession")
        return hasSession
    }

    suspend fun hasValidSession(context: Context? = null): Boolean {
        return refreshAuthState(context)
    }

    suspend fun signOut(context: Context? = null): Boolean {
        Firebase.crashlytics.log("AuthSessionManager.signOut: started")
        return try {
            SupabaseClientProvider.client.auth.signOut()
            invalidateLocalSession(context)
            Firebase.crashlytics.log("AuthSessionManager.signOut: completed success=true")
            true
        } catch (exception: Exception) {
            Firebase.crashlytics.log("AuthSessionManager.signOut: failed")
            Firebase.crashlytics.recordException(exception)
            false
        }
    }
}
