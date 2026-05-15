package com.example.android

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.lifecycleScope
import com.example.android.hunts.HuntItem
import com.example.android.hunts.HuntRepository
import com.example.android.ui.theme.AndroidTheme
import com.example.android.utils.AuthSessionManager
import com.example.android.utils.FcmTokenManager
import com.example.android.utils.SupabaseClientProvider
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    
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
                AuthSessionManager.refreshAuthState()
            }
        }
        lifecycleScope.launch {
            AuthSessionManager.refreshAuthState()
        }
        
        requestNotificationPermission()
        
        setContent {
            AndroidTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    MainScreen(
                        modifier = Modifier.padding(innerPadding)
                    )
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        SupabaseClientProvider.handleAuthDeeplink(intent) {
            lifecycleScope.launch {
                AuthSessionManager.refreshAuthState()
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

@Composable
fun MainScreen(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val huntRepository = remember { HuntRepository(context.applicationContext) }
    val hunts = remember { mutableStateOf<List<HuntItem>>(huntRepository.getCachedHunts()) }
    val isRefreshing = remember { mutableStateOf(false) }
    val authMessage = remember { mutableStateOf("") }
    val authScope = rememberCoroutineScope()
    val isAuthenticated by AuthSessionManager.isAuthenticated.collectAsState()

    LaunchedEffect(Unit) {
        AuthSessionManager.refreshAuthState()
    }
    LaunchedEffect(isAuthenticated) {
        if (isAuthenticated) {
            authScope.launch {
                isRefreshing.value = true
                runCatching { huntRepository.syncHunts() }
                    .onSuccess { hunts.value = it }
                    .onFailure { authMessage.value = "Unable to sync hunts." }
                isRefreshing.value = false
            }
        }
    }
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner, isAuthenticated) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME && isAuthenticated) {
                authScope.launch {
                    runCatching { huntRepository.syncHunts() }
                        .onSuccess { hunts.value = it }
                }
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Text("HuntFact")
        Spacer(modifier = Modifier.height(16.dp))

        if (!isAuthenticated) {
            Button(
                onClick = {
                    authScope.launch {
                        try {
                            SupabaseClientProvider.signInWithGoogle()
                            authMessage.value = "Google sign-in started"
                        } catch (e: Exception) {
                            Log.e("MainScreen", "Google sign-in failed", e)
                            authMessage.value = "Sign-in failed. Please try again."
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Sign in with Google")
            }
        }

        if (isAuthenticated) {
            Spacer(modifier = Modifier.height(8.dp))
            Text("Signed in. Shared reels appear here.")
            Spacer(modifier = Modifier.height(8.dp))
            Row(modifier = Modifier.fillMaxWidth()) {
                Button(
                    onClick = {
                        authScope.launch {
                            isRefreshing.value = true
                            runCatching { huntRepository.syncHunts() }
                                .onSuccess { hunts.value = it }
                                .onFailure { authMessage.value = "Failed to refresh hunts." }
                            isRefreshing.value = false
                        }
                    },
                    modifier = Modifier.weight(1f)
                ) {
                    Text(if (isRefreshing.value) "Refreshing..." else "Refresh")
                }

                Spacer(modifier = Modifier.width(6.dp))

                Button(
                    onClick = {
                        authScope.launch {
                            val signedOut = AuthSessionManager.signOut()
                            authMessage.value = if (signedOut) {
                                "Signed out"
                            } else {
                                "Sign-out failed. Please try again."
                            }
                        }
                    },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Sign out")
                }
            }
        }

        if (authMessage.value.isNotEmpty()) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(authMessage.value)
        }
        Spacer(modifier = Modifier.height(16.dp))
        if (isAuthenticated && isRefreshing.value) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(modifier = Modifier.height(18.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text("Syncing hunts...")
            }
            Spacer(modifier = Modifier.height(16.dp))
        }

        if (!isAuthenticated) {
            Text("Sign in to view your hunt history.")
            return@Column
        }

        if (hunts.value.isEmpty()) {
            Text("No reels yet. Share an Instagram reel to HuntFact and it will appear here.")
            return@Column
        }

        LazyColumn(modifier = Modifier.fillMaxSize()) {
            items(hunts.value) { hunt ->
                HuntCard(
                    hunt = hunt,
                    onOpen = {
                        context.startActivity(
                            Intent(context, ResultActivity::class.java).apply {
                                putExtra(ResultActivity.EXTRA_HUNT_ID, hunt.id)
                                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            }
                        )
                    },
                )
                Spacer(modifier = Modifier.height(10.dp))
            }
        }
    }
}

@Composable
private fun HuntCard(hunt: HuntItem, onOpen: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onOpen() }
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            val caption = hunt.caption?.takeIf { it.isNotBlank() } ?: hunt.videoLink
            Text(caption)
            Spacer(modifier = Modifier.height(8.dp))
            AssistChip(
                onClick = onOpen,
                label = { Text(hunt.status.replaceFirstChar { it.uppercase() }) },
            )
            hunt.creatorHandle?.let {
                if (it.isNotBlank()) {
                    Text("Creator: @$it")
                }
            }
            hunt.thumbnailUrl?.let {
                if (it.isNotBlank()) {
                    Text("Thumbnail saved")
                }
            }
            if (hunt.status == "completed" && !hunt.result.isNullOrBlank()) {
                Text(resultPreview(hunt.result))
            }
            if (hunt.status == "failed" && !hunt.errorMessage.isNullOrBlank()) {
                Text("Error: ${hunt.errorMessage}")
            }
        }
    }
}

private fun resultPreview(rawResult: String): String {
    val compact = rawResult.replace("\n", " ").trim()
    return if (compact.length > 120) {
        "Result: ${compact.take(120)}..."
    } else {
        "Result: $compact"
    }
}

@Preview(showBackground = true)
@Composable
fun MainScreenPreview() {
    AndroidTheme {
        MainScreen()
    }
}
