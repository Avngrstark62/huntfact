package com.abhijeet.huntfact.ui.profile

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.abhijeet.huntfact.utils.AuthSessionManager
import com.abhijeet.huntfact.utils.SupabaseClientProvider
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
        viewModelScope.launch {
            AuthSessionManager.refreshAuthState(appContext)
        }
    }

    fun signInWithGoogle() {
        viewModelScope.launch {
            runCatching { SupabaseClientProvider.signInWithGoogle() }
                .onSuccess { _uiState.update { it.copy(message = "Google sign-in started.") } }
                .onFailure { _uiState.update { it.copy(message = "Failed to start sign-in.") } }
        }
    }

    fun signOut() {
        viewModelScope.launch {
            val signedOut = AuthSessionManager.signOut(appContext)
            _uiState.update {
                it.copy(
                    message = if (signedOut) "Signed out." else "Sign-out failed. Please try again.",
                )
            }
        }
    }

    fun clearMessage() {
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
