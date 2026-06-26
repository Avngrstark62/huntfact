package com.abhijeet.huntfact

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AddCircle
import androidx.compose.material.icons.rounded.Home
import androidx.compose.material3.Button
import androidx.compose.material3.Scaffold
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.lifecycleScope
import com.abhijeet.huntfact.ui.theme.AndroidTheme
import com.abhijeet.huntfact.ui.hunts.HuntsScreen
import com.abhijeet.huntfact.ui.hunts.HuntsViewModel
import com.abhijeet.huntfact.ui.theme.AppSpacing
import com.abhijeet.huntfact.ui.profile.ProfileViewModel
import com.abhijeet.huntfact.ui.resources.ResourcesViewModel
import com.abhijeet.huntfact.utils.AuthSessionManager
import com.abhijeet.huntfact.utils.DebugLogger
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
                    onExportDebugLogs = { exportDebugLogs() },
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

    private fun exportDebugLogs() {
        val logFile = DebugLogger.getLogFile(this)
        if (!logFile.exists()) {
            Toast.makeText(this, getString(R.string.debug_logs_not_found), Toast.LENGTH_SHORT).show()
            return
        }

        try {
            val authority = "${packageName}.fileprovider"
            val fileUri = FileProvider.getUriForFile(this, authority, logFile)
            val shareIntent = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_STREAM, fileUri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            startActivity(Intent.createChooser(shareIntent, getString(R.string.export_debug_logs)))
        } catch (_: Exception) {
            Toast.makeText(this, getString(R.string.debug_logs_share_error), Toast.LENGTH_SHORT).show()
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
    onExportDebugLogs: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val huntsUiState by huntsViewModel.uiState.collectAsState()
    val resourcesUiState by resourcesViewModel.uiState.collectAsState()
    val profileUiState by profileViewModel.uiState.collectAsState()
    val context = LocalContext.current
    val selectedTab = remember { mutableStateOf(AppTab.Home) }
    val lifecycleOwner = LocalLifecycleOwner.current
    val selectedBlend = lerp(
        MaterialTheme.colorScheme.primary,
        MaterialTheme.colorScheme.secondary,
        0.35f,
    )

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
            NavigationBar(
                containerColor = MaterialTheme.colorScheme.surface,
            ) {
                AppTab.entries.forEach { tab ->
                    val selected = selectedTab.value == tab
                    NavigationBarItem(
                        selected = selected,
                        onClick = { selectedTab.value = tab },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = selectedBlend,
                            selectedTextColor = selectedBlend,
                            unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                            unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant,
                            indicatorColor = MaterialTheme.colorScheme.surface,
                        ),
                        icon = {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(AppSpacing.xs),
                                modifier = Modifier
                                    .then(
                                        if (selected) {
                                            Modifier
                                                .clip(RoundedCornerShape(999.dp))
                                                .background(selectedBlend.copy(alpha = 0.14f))
                                                .padding(horizontal = AppSpacing.sm, vertical = AppSpacing.xs)
                                        } else {
                                            Modifier.padding(horizontal = AppSpacing.sm, vertical = AppSpacing.xs)
                                        },
                                    ),
                            ) {
                                when (tab) {
                                    AppTab.Home -> Icon(
                                        imageVector = Icons.Rounded.Home,
                                        contentDescription = tab.label,
                                        tint = if (selected) selectedBlend else MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                    AppTab.Analyze -> Icon(
                                        imageVector = Icons.Rounded.AddCircle,
                                        contentDescription = tab.label,
                                        tint = if (selected) selectedBlend else MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                    AppTab.History -> Icon(
                                        painter = painterResource(id = R.drawable.ic_tab_history_clock),
                                        contentDescription = tab.label,
                                        tint = if (selected) selectedBlend else MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                                Text(
                                    text = tab.label,
                                    style = MaterialTheme.typography.labelMedium,
                                    color = if (selected) selectedBlend else MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        },
                        label = null,
                        alwaysShowLabel = false,
                    )
                }
            }
        },
    ) { innerPadding ->
        AnimatedContent(
            targetState = selectedTab.value,
            transitionSpec = { fadeIn(tween(180)) togetherWith fadeOut(tween(180)) },
            modifier = Modifier.padding(innerPadding),
            label = "tab-switch",
        ) { tab ->
            when (tab) {
                AppTab.Home -> HuntsScreen(
                    uiState = huntsUiState,
                    onRefresh = { huntsViewModel.refreshHunts() },
                    onSignIn = { huntsViewModel.signInWithGoogle() },
                    onSignOut = { huntsViewModel.signOut() },
                    onExportDebugLogs = onExportDebugLogs,
                    onOpenHunt = { hunt ->
                        context.startActivity(
                            Intent(context, ResultActivity::class.java).apply {
                                putExtra(ResultActivity.EXTRA_HUNT_ID, hunt.id)
                                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            }
                        )
                    },
                    modifier = Modifier,
                )
                AppTab.Analyze -> AnalyzeScreen(modifier = Modifier)
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
                    modifier = Modifier,
                )
            }
        }
    }
}

@Composable
private fun AnalyzeScreen(modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(AppSpacing.md),
        verticalArrangement = Arrangement.Center,
    ) {
        Card(
            shape = RoundedCornerShape(20.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        ) {
            Column(
                verticalArrangement = Arrangement.spacedBy(AppSpacing.sm),
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.padding(AppSpacing.lg),
            ) {
                Icon(
                    imageVector = Icons.Rounded.Home,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                )
                Text(
                    text = "Analyze",
                    style = MaterialTheme.typography.headlineMedium,
                )
                Text(
                    text = "Deeper claim analysis tools are coming soon.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Button(
                    onClick = {},
                    enabled = false,
                    shape = RoundedCornerShape(999.dp),
                ) {
                    Text("Enable when ready")
                }
            }
        }
    }
}

