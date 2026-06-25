package com.abhijeet.huntfact.ui.profile

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.abhijeet.huntfact.utils.AuthSessionManager
import com.abhijeet.huntfact.utils.SupabaseClientProvider
import com.google.firebase.Firebase
import com.google.firebase.crashlytics.crashlytics
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ProfileUiState(
    val isAuthenticated: Boolean = false,
    val userLabel: String = "Guest",
    val message: String? = null,
)

class ProfileViewModel(
    private val appContext: Context,
) : ViewModel() {
    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()

    init {
        observeAuthState()
        refreshAuthState()
    }

    private fun observeAuthState() {
        viewModelScope.launch {
            AuthSessionManager.isAuthenticated.collectLatest { isAuthenticated ->
                Firebase.crashlytics.log("ProfileViewModel.observeAuthState: authState=$isAuthenticated")
                _uiState.update {
                    it.copy(
                        isAuthenticated = isAuthenticated,
                        userLabel = if (isAuthenticated) "Signed-in user" else "Guest",
                    )
                }
            }
        }
    }

    fun refreshAuthState() {
        Firebase.crashlytics.log("ProfileViewModel.refreshAuthState: started")
        viewModelScope.launch {
            AuthSessionManager.refreshAuthState(appContext)
            Firebase.crashlytics.log("ProfileViewModel.refreshAuthState: completed")
        }
    }

    fun signInWithGoogle() {
        Firebase.crashlytics.log("ProfileViewModel.signInWithGoogle: started")
        viewModelScope.launch {
            runCatching { SupabaseClientProvider.signInWithGoogle() }
                .onSuccess {
                    Firebase.crashlytics.log("ProfileViewModel.signInWithGoogle: sign-in flow started")
                    _uiState.update { it.copy(message = "Google sign-in started.") }
                }
                .onFailure { exception ->
                    Firebase.crashlytics.log("ProfileViewModel.signInWithGoogle: sign-in flow failed")
                    Firebase.crashlytics.recordException(exception)
                    _uiState.update { it.copy(message = "Failed to start sign-in.") }
                }
        }
    }

    fun signOut() {
        Firebase.crashlytics.log("ProfileViewModel.signOut: started")
        viewModelScope.launch {
            val signedOut = AuthSessionManager.signOut(appContext)
            if (!signedOut) {
                Firebase.crashlytics.log("ProfileViewModel.signOut: sign-out failed")
                Firebase.crashlytics.recordException(Exception("ProfileViewModel signOut returned false"))
            }
            _uiState.update {
                it.copy(
                    message = if (signedOut) "Signed out." else "Sign-out failed. Please try again.",
                )
            }
        }
    }

    fun clearMessage() {
        Firebase.crashlytics.log("ProfileViewModel.clearMessage: clearing UI message")
        _uiState.update { it.copy(message = null) }
    }

    companion object {
        fun factory(context: Context): ViewModelProvider.Factory {
            val appContext = context.applicationContext
            return object : ViewModelProvider.Factory {
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    if (modelClass.isAssignableFrom(ProfileViewModel::class.java)) {
                        @Suppress("UNCHECKED_CAST")
                        return ProfileViewModel(appContext) as T
                    }
                    throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
                }
            }
        }
    }
}
