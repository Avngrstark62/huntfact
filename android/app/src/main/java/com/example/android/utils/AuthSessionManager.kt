package com.example.android.utils

import io.github.jan.supabase.auth.auth

object AuthSessionManager {
    fun getAccessToken(): String? {
        return try {
            SupabaseClientProvider.client.auth.currentSessionOrNull()?.accessToken
        } catch (_: Exception) {
            null
        }
    }

    fun hasValidSession(): Boolean {
        return !getAccessToken().isNullOrBlank()
    }
}
