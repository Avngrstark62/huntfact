package com.example.android.utils

import android.content.Intent
import com.example.android.BuildConfig
import io.github.jan.supabase.auth.Auth
import io.github.jan.supabase.auth.auth
import io.github.jan.supabase.auth.providers.Google
import io.github.jan.supabase.auth.handleDeeplinks
import io.github.jan.supabase.createSupabaseClient

object SupabaseClientProvider {
    private const val DEEPLINK_SCHEME = "huntfact"
    private const val DEEPLINK_HOST = "auth"

    val client = createSupabaseClient(
        supabaseUrl = BuildConfig.SUPABASE_URL,
        supabaseKey = BuildConfig.SUPABASE_ANON_KEY
    ) {
        install(Auth) {
            scheme = DEEPLINK_SCHEME
            host = DEEPLINK_HOST
        }
    }

    suspend fun signInWithGoogle() {
        client.auth.signInWith(Google)
    }

    fun handleAuthDeeplink(intent: Intent?) {
        if (intent == null) {
            return
        }
        client.handleDeeplinks(intent)
    }
}
