package com.example.android.ui.hunts

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.android.hunts.HuntItem
import com.example.android.hunts.HuntRepository
import com.example.android.utils.AuthSessionManager
import com.example.android.utils.SupabaseClientProvider
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class HuntsUiState(
    val hunts: List<HuntItem> = emptyList(),
    val isAuthenticated: Boolean = false,
    val isRefreshing: Boolean = false,
    val message: String? = null,
)

class HuntsViewModel(
    private val repository: HuntRepository,
    private val appContext: Context,
) : ViewModel() {
    private val _uiState = MutableStateFlow(
        HuntsUiState(hunts = repository.getCachedHunts()),
    )
    val uiState: StateFlow<HuntsUiState> = _uiState.asStateFlow()

    init {
        observeAuthState()
        refreshAuthState()
    }

    fun refreshAuthState() {
        viewModelScope.launch {
            AuthSessionManager.refreshAuthState(appContext)
        }
    }

    private fun observeAuthState() {
        viewModelScope.launch {
            AuthSessionManager.isAuthenticated.collectLatest { isAuthenticated ->
                _uiState.update { current ->
                    current.copy(
                        isAuthenticated = isAuthenticated,
                        hunts = if (isAuthenticated) current.hunts else emptyList(),
                    )
                }
                if (isAuthenticated) {
                    refreshHunts()
                }
            }
        }
    }

    fun onResume() {
        if (_uiState.value.isAuthenticated) {
            refreshHunts(silent = true)
        }
    }

    fun refreshHunts(silent: Boolean = false) {
        if (!_uiState.value.isAuthenticated || _uiState.value.isRefreshing) {
            return
        }
        viewModelScope.launch {
            if (!silent) {
                _uiState.update { it.copy(isRefreshing = true, message = null) }
            }
            runCatching { repository.syncHunts() }
                .onSuccess { hunts ->
                    _uiState.update {
                        it.copy(
                            hunts = hunts,
                            isRefreshing = false,
                            message = if (silent) it.message else null,
                        )
                    }
                }
                .onFailure {
                    _uiState.update {
                        it.copy(
                            isRefreshing = false,
                            message = "Failed to refresh hunts. Please try again.",
                        )
                    }
                }
        }
    }

    fun signInWithGoogle() {
        viewModelScope.launch {
            runCatching { SupabaseClientProvider.signInWithGoogle() }
                .onSuccess {
                    _uiState.update { it.copy(message = "Google sign-in started.") }
                }
                .onFailure {
                    _uiState.update { it.copy(message = "Sign-in failed. Please try again.") }
                }
        }
    }

    fun signOut() {
        viewModelScope.launch {
            val signedOut = AuthSessionManager.signOut(appContext)
            _uiState.update {
                it.copy(
                    hunts = emptyList(),
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
            val repository = HuntRepository(context.applicationContext)
            val appContext = context.applicationContext
            return object : ViewModelProvider.Factory {
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    if (modelClass.isAssignableFrom(HuntsViewModel::class.java)) {
                        @Suppress("UNCHECKED_CAST")
                        return HuntsViewModel(repository, appContext) as T
                    }
                    throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
                }
            }
        }
    }
}
