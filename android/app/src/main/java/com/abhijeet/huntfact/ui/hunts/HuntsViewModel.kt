package com.abhijeet.huntfact.ui.hunts

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.abhijeet.huntfact.hunts.HuntItem
import com.abhijeet.huntfact.hunts.HuntRepository
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
        Firebase.crashlytics.log("HuntsViewModel.refreshAuthState: started")
        viewModelScope.launch {
            AuthSessionManager.refreshAuthState(appContext)
            Firebase.crashlytics.log("HuntsViewModel.refreshAuthState: completed")
        }
    }

    private fun observeAuthState() {
        viewModelScope.launch {
            AuthSessionManager.isAuthenticated.collectLatest { isAuthenticated ->
                Firebase.crashlytics.log("HuntsViewModel.observeAuthState: authState=$isAuthenticated")
                _uiState.update { current ->
                    current.copy(
                        isAuthenticated = isAuthenticated,
                        hunts = if (isAuthenticated) current.hunts else emptyList(),
                    )
                }
                if (isAuthenticated) {
                    Firebase.crashlytics.log("HuntsViewModel.observeAuthState: authenticated, refreshing hunts")
                    refreshHunts()
                }
            }
        }
    }

    fun onResume() {
        Firebase.crashlytics.log("HuntsViewModel.onResume: started")
        if (_uiState.value.isAuthenticated) {
            Firebase.crashlytics.log("HuntsViewModel.onResume: authenticated, running silent refresh")
            refreshHunts(silent = true)
        }
    }

    fun refreshHunts(silent: Boolean = false) {
        Firebase.crashlytics.log("HuntsViewModel.refreshHunts: started silent=$silent")
        if (!_uiState.value.isAuthenticated || _uiState.value.isRefreshing) {
            Firebase.crashlytics.log("HuntsViewModel.refreshHunts: skipped due to auth/refresh guard")
            return
        }
        viewModelScope.launch {
            if (!silent) {
                Firebase.crashlytics.log("HuntsViewModel.refreshHunts: setting loading state")
                _uiState.update { it.copy(isRefreshing = true, message = null) }
            }
            runCatching {
                Firebase.crashlytics.log("HuntsViewModel.refreshHunts: syncing hunts from repository")
                repository.syncHunts()
            }
                .onSuccess { hunts ->
                    Firebase.crashlytics.log("HuntsViewModel.refreshHunts: success huntCount=${hunts.size}")
                    _uiState.update {
                        it.copy(
                            hunts = hunts,
                            isRefreshing = false,
                            message = if (silent) it.message else null,
                        )
                    }
                }
                .onFailure { exception ->
                    Firebase.crashlytics.log("HuntsViewModel.refreshHunts: failed to sync hunts")
                    Firebase.crashlytics.recordException(exception)
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
        Firebase.crashlytics.log("HuntsViewModel.signInWithGoogle: started")
        viewModelScope.launch {
            runCatching { SupabaseClientProvider.signInWithGoogle() }
                .onSuccess {
                    Firebase.crashlytics.log("HuntsViewModel.signInWithGoogle: sign-in flow started")
                    _uiState.update { it.copy(message = "Google sign-in started.") }
                }
                .onFailure { exception ->
                    Firebase.crashlytics.log("HuntsViewModel.signInWithGoogle: sign-in flow failed")
                    Firebase.crashlytics.recordException(exception)
                    _uiState.update { it.copy(message = "Sign-in failed. Please try again.") }
                }
        }
    }

    fun signOut() {
        Firebase.crashlytics.log("HuntsViewModel.signOut: started")
        viewModelScope.launch {
            val signedOut = AuthSessionManager.signOut(appContext)
            if (!signedOut) {
                Firebase.crashlytics.log("HuntsViewModel.signOut: sign-out failed")
                Firebase.crashlytics.recordException(Exception("HuntsViewModel signOut returned false"))
            }
            _uiState.update {
                it.copy(
                    hunts = emptyList(),
                    message = if (signedOut) "Signed out." else "Sign-out failed. Please try again.",
                )
            }
        }
    }

    fun clearMessage() {
        Firebase.crashlytics.log("HuntsViewModel.clearMessage: clearing UI message")
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
