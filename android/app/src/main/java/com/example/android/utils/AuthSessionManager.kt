package com.example.android.utils

import io.github.jan.supabase.auth.auth
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withTimeoutOrNull

object AuthSessionManager {
    private val _isAuthenticated = MutableStateFlow(false)
    val isAuthenticated: StateFlow<Boolean> = _isAuthenticated.asStateFlow()

    fun getAccessToken(): String? {
        return try {
            SupabaseClientProvider.client.auth.currentSessionOrNull()?.accessToken
        } catch (_: Exception) {
            null
        }
    }

    suspend fun refreshAuthState(): Boolean {
        withTimeoutOrNull(5_000) {
            SupabaseClientProvider.client.auth.awaitInitialization()
            true
        }

        val hasSession = !getAccessToken().isNullOrBlank()
        _isAuthenticated.value = hasSession
        return hasSession
    }

    suspend fun hasValidSession(): Boolean {
        return refreshAuthState()
    }

    suspend fun signOut(): Boolean {
        return try {
            SupabaseClientProvider.client.auth.signOut()
            _isAuthenticated.value = false
            true
        } catch (_: Exception) {
            false
        }
    }
}
