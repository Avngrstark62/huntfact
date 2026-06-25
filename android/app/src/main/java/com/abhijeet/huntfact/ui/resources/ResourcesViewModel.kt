package com.abhijeet.huntfact.ui.resources

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.abhijeet.huntfact.resources.ResourceSummary
import com.abhijeet.huntfact.resources.ResourcesRepository
import com.abhijeet.huntfact.resources.StubResourcesRepository
import com.google.firebase.Firebase
import com.google.firebase.crashlytics.crashlytics
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ResourcesUiState(
    val isLoading: Boolean = true,
    val summary: ResourceSummary? = null,
    val comingSoon: Boolean = true,
)

class ResourcesViewModel(
    private val repository: ResourcesRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(ResourcesUiState())
    val uiState: StateFlow<ResourcesUiState> = _uiState.asStateFlow()

    init {
        loadSummary()
    }

    private fun loadSummary() {
        Firebase.crashlytics.log("ResourcesViewModel.loadSummary: started")
        viewModelScope.launch {
            Firebase.crashlytics.log("ResourcesViewModel.loadSummary: requesting resource summary")
            val summary = repository.getSummary()
            _uiState.update { it.copy(isLoading = false, summary = summary) }
            Firebase.crashlytics.log("ResourcesViewModel.loadSummary: completed")
        }
    }

    companion object {
        fun factory(
            repository: ResourcesRepository = StubResourcesRepository(),
        ): ViewModelProvider.Factory {
            return object : ViewModelProvider.Factory {
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    if (modelClass.isAssignableFrom(ResourcesViewModel::class.java)) {
                        @Suppress("UNCHECKED_CAST")
                        return ResourcesViewModel(repository) as T
                    }
                    throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
                }
            }
        }
    }
}
