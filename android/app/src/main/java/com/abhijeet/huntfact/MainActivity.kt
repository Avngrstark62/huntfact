package com.abhijeet.huntfact

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.lifecycleScope
import com.abhijeet.huntfact.ui.theme.AndroidTheme
import com.abhijeet.huntfact.ui.hunts.HuntsScreen
import com.abhijeet.huntfact.ui.hunts.HuntsViewModel
import com.abhijeet.huntfact.ui.profile.ProfileViewModel
import com.abhijeet.huntfact.ui.resources.ResourcesViewModel
import com.abhijeet.huntfact.utils.AuthSessionManager
import com.abhijeet.huntfact.utils.FcmTokenManager
import com.abhijeet.huntfact.utils.SupabaseClientProvider
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private val huntsViewModel: HuntsViewModel by viewModels {
        HuntsViewModel.factory(applicationContext)
    }
    private val resourcesViewModel: ResourcesViewModel by viewModels {
        ResourcesViewModel.factory()
    }
    private val profileViewModel: ProfileViewModel by viewModels {
        ProfileViewModel.factory(applicationContext)
    }

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            initializeFcm()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        SupabaseClientProvider.handleAuthDeeplink(intent) {
            lifecycleScope.launch {
                AuthSessionManager.refreshAuthState(applicationContext)
            }
        }
        lifecycleScope.launch {
            AuthSessionManager.refreshAuthState(applicationContext)
        }
        
        requestNotificationPermission()
        
        setContent {
            AndroidTheme {
                MainScreen(
                    huntsViewModel = huntsViewModel,
                    resourcesViewModel = resourcesViewModel,
                    profileViewModel = profileViewModel,
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        SupabaseClientProvider.handleAuthDeeplink(intent) {
            lifecycleScope.launch {
                huntsViewModel.refreshAuthState()
                profileViewModel.refreshAuthState()
            }
        }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            when {
                ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) == PackageManager.PERMISSION_GRANTED -> {
                    initializeFcm()
                }
                else -> {
                    notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                }
            }
        } else {
            initializeFcm()
        }
    }

    private fun initializeFcm() {
        lifecycleScope.launch {
            val token = FcmTokenManager.getFcmToken()
            FcmTokenManager.saveToken(applicationContext, token)
        }
    }
}

private enum class AppTab(val label: String) {
    Home("Home"),
    Analyze("Analyze"),
    History("History"),
}

@Composable
fun MainScreen(
    huntsViewModel: HuntsViewModel,
    resourcesViewModel: ResourcesViewModel,
    profileViewModel: ProfileViewModel,
    modifier: Modifier = Modifier,
) {
    val huntsUiState by huntsViewModel.uiState.collectAsState()
    val resourcesUiState by resourcesViewModel.uiState.collectAsState()
    val profileUiState by profileViewModel.uiState.collectAsState()
    val context = LocalContext.current
    val selectedTab = remember { mutableStateOf(AppTab.Home) }
    val lifecycleOwner = LocalLifecycleOwner.current

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                huntsViewModel.onResume()
                huntsViewModel.refreshAuthState()
                profileViewModel.refreshAuthState()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        bottomBar = {
            NavigationBar {
                AppTab.entries.forEach { tab ->
                    NavigationBarItem(
                        selected = selectedTab.value == tab,
                        onClick = { selectedTab.value = tab },
                        icon = { Text(tab.label.take(1)) },
                        label = { Text(tab.label) },
                    )
                }
            }
        },
    ) { innerPadding ->
        when (selectedTab.value) {
            AppTab.Home -> HuntsScreen(
                uiState = huntsUiState,
                onRefresh = { huntsViewModel.refreshHunts() },
                onSignIn = { huntsViewModel.signInWithGoogle() },
                onSignOut = { huntsViewModel.signOut() },
                onOpenHunt = { hunt ->
                    context.startActivity(
                        Intent(context, ResultActivity::class.java).apply {
                            putExtra(ResultActivity.EXTRA_HUNT_ID, hunt.id)
                            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        }
                    )
                },
                modifier = Modifier.padding(innerPadding),
            )
            AppTab.Analyze -> AnalyzeScreen(modifier = Modifier.padding(innerPadding))
            AppTab.History -> HuntsScreen(
                uiState = huntsUiState,
                onRefresh = {},
                onSignIn = { huntsViewModel.signInWithGoogle() },
                onSignOut = {},
                onOpenHunt = { hunt ->
                    context.startActivity(
                        Intent(context, ResultActivity::class.java).apply {
                            putExtra(ResultActivity.EXTRA_HUNT_ID, hunt.id)
                            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        }
                    )
                },
                showSectionTitle = false,
                showSummary = false,
                showActionButtons = false,
                showMessage = false,
                modifier = Modifier.padding(innerPadding),
            )
        }
    }
}

@Composable
private fun AnalyzeScreen(modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = com.abhijeet.huntfact.ui.theme.AppSpacing.md),
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "Analyze",
            style = MaterialTheme.typography.headlineSmall,
        )
        Text(
            text = "Analyze page template coming soon.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

