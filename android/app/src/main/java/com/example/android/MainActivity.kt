package com.example.android

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.example.android.ui.theme.AndroidTheme
import com.example.android.utils.FcmTokenManager
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
    val videoLink = remember { mutableStateOf("") }
    val cdnLink = remember { mutableStateOf("") }
    val isLoading = remember { mutableStateOf(false) }
    val resultMessage = remember { mutableStateOf("") }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Text("Fact Check - HuntFact")
        
        Spacer(modifier = Modifier.height(16.dp))
        
        TextField(
            value = videoLink.value,
            onValueChange = { videoLink.value = it },
            label = { Text("Video Link") },
            modifier = Modifier.fillMaxWidth()
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        TextField(
            value = cdnLink.value,
            onValueChange = { cdnLink.value = it },
            label = { Text("CDN Link") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(16.dp))

        Button(
            onClick = {
                if (videoLink.value.isNotEmpty() && cdnLink.value.isNotEmpty()) {
                    isLoading.value = true
                }
            },
            enabled = !isLoading.value,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (isLoading.value) "Checking..." else "Start Fact Check")
        }

        if (resultMessage.value.isNotEmpty()) {
            Spacer(modifier = Modifier.height(16.dp))
            Text(resultMessage.value)
        }
    }
}

@Preview(showBackground = true)
@Composable
fun MainScreenPreview() {
    AndroidTheme {
        MainScreen()
    }
}
