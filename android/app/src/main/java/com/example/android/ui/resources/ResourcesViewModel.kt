package com.example.android.ui.resources

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.android.resources.ResourceSummary
import com.example.android.resources.ResourcesRepository
import com.example.android.resources.StubResourcesRepository
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
        viewModelScope.launch {
            val summary = repository.getSummary()
            _uiState.update { it.copy(isLoading = false, summary = summary) }
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
