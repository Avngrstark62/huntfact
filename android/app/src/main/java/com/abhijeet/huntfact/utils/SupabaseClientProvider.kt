package com.abhijeet.huntfact.utils

import android.content.Intent
import com.abhijeet.huntfact.BuildConfig
import com.google.firebase.Firebase
import com.google.firebase.crashlytics.crashlytics
import io.github.jan.supabase.auth.Auth
import io.github.jan.supabase.auth.FlowType
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
            flowType = FlowType.PKCE
            scheme = DEEPLINK_SCHEME
            host = DEEPLINK_HOST
        }
    }

    suspend fun signInWithGoogle() {
        Firebase.crashlytics.log("SupabaseClientProvider.signInWithGoogle: started")
        client.auth.signInWith(
            provider = Google,
            redirectUrl = "$DEEPLINK_SCHEME://$DEEPLINK_HOST"
        )
        Firebase.crashlytics.log("SupabaseClientProvider.signInWithGoogle: sign-in request sent")
    }

    fun handleAuthDeeplink(intent: Intent?, onSessionImported: (() -> Unit)? = null) {
        Firebase.crashlytics.log("SupabaseClientProvider.handleAuthDeeplink: started")
        if (intent == null) {
            Firebase.crashlytics.log("SupabaseClientProvider.handleAuthDeeplink: intent is null, returning")
            return
        }
        Firebase.crashlytics.log("SupabaseClientProvider.handleAuthDeeplink: processing deeplink intent")
        client.handleDeeplinks(intent) {
            Firebase.crashlytics.log("SupabaseClientProvider.handleAuthDeeplink: session imported callback invoked")
            onSessionImported?.invoke()
        }
    }
}
