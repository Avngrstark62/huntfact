package com.example.android

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
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
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
import com.example.android.ui.theme.AndroidTheme
import com.example.android.ui.hunts.HuntsScreen
import com.example.android.ui.hunts.HuntsViewModel
import com.example.android.ui.profile.ProfileScreen
import com.example.android.ui.profile.ProfileViewModel
import com.example.android.ui.resources.ResourcesScreen
import com.example.android.ui.resources.ResourcesViewModel
import com.example.android.utils.AuthSessionManager
import com.example.android.utils.FcmTokenManager
import com.example.android.utils.SupabaseClientProvider
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
    Hunts("Hunts"),
    Resources("Resources"),
    Profile("Profile"),
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
    val selectedTab = remember { mutableStateOf(AppTab.Hunts) }
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
            AppTab.Hunts -> HuntsScreen(
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
            AppTab.Resources -> ResourcesScreen(
                uiState = resourcesUiState,
                modifier = Modifier.padding(innerPadding),
            )
            AppTab.Profile -> ProfileScreen(
                uiState = profileUiState,
                onSignIn = { profileViewModel.signInWithGoogle() },
                onSignOut = { profileViewModel.signOut() },
                modifier = Modifier.padding(innerPadding),
            )
        }
    }
}

