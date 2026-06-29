package com.abhijeet.huntfact.ui.hunts

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.abhijeet.huntfact.hunts.HuntItem
import com.abhijeet.huntfact.hunts.HuntRepository
import com.abhijeet.huntfact.utils.AuthSessionManager
import com.abhijeet.huntfact.utils.SupabaseClientProvider
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import retrofit2.HttpException
import java.io.IOException
import java.net.UnknownHostException

data class HuntsUiState(
    val hunts: List<HuntItem> = emptyList(),
    val isAuthenticated: Boolean = false,
    val isRefreshing: Boolean = false,
    val message: String? = null,
    val newHuntsAvailable: Boolean = false,
    val scrollToTopSignal: Int = 0,
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
            val previousTopHuntId = _uiState.value.hunts.firstOrNull()?.id
            if (!silent) {
                _uiState.update { it.copy(isRefreshing = true, message = null) }
            }
            runCatching { repository.syncHunts() }
                .onSuccess { hunts ->
                    val latestTopHuntId = hunts.firstOrNull()?.id
                    val hasNewTopHunt = latestTopHuntId != null && latestTopHuntId != previousTopHuntId
                    _uiState.update {
                        it.copy(
                            hunts = hunts,
                            isRefreshing = false,
                            message = if (silent) it.message else null,
                            newHuntsAvailable = if (silent) it.newHuntsAvailable || hasNewTopHunt else false,
                            scrollToTopSignal = if (!silent && hasNewTopHunt) it.scrollToTopSignal + 1 else it.scrollToTopSignal,
                        )
                    }
                }
                .onFailure { error ->
                    _uiState.update {
                        it.copy(
                            isRefreshing = false,
                            message = refreshErrorMessage(error),
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

    fun clearNewHuntsIndicator() {
        _uiState.update { it.copy(newHuntsAvailable = false) }
    }

    private fun refreshErrorMessage(error: Throwable): String {
        if (error is HttpException) {
            return when (error.code()) {
                401, 403 -> "Your session expired. Please sign in again."
                429 -> "You are refreshing too quickly. Please wait and try again."
                503 -> "Service is temporarily unavailable. Please try again shortly."
                in 400..499 -> "Unable to load hunts right now. Please try again."
                else -> "Server issue while loading hunts. Please try again later."
            }
        }
        if (error is UnknownHostException || error is IOException) {
            return "No internet connection. Please check your network and try again."
        }
        return "Failed to refresh hunts. Please try again."
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
