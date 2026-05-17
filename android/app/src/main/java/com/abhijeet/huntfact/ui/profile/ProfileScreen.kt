package com.abhijeet.huntfact.ui.profile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.abhijeet.huntfact.ui.components.InfoCard
import com.abhijeet.huntfact.ui.components.SectionTitle
import com.abhijeet.huntfact.ui.theme.AppSpacing

@Composable
fun ProfileScreen(
    uiState: ProfileUiState,
    onSignIn: () -> Unit,
    onSignOut: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = AppSpacing.md, vertical = AppSpacing.sm),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.sm),
    ) {
        SectionTitle("Profile")
        InfoCard(
            title = "Account",
            value = uiState.userLabel,
            subtitle = if (uiState.isAuthenticated) "Authenticated with Google" else "Not signed in",
        )
        InfoCard(
            title = "Preferences",
            value = "App settings",
            subtitle = "Theme and notifications controls will be expanded in upcoming updates.",
        )

        if (uiState.isAuthenticated) {
            Button(onClick = onSignOut, modifier = Modifier.fillMaxWidth()) {
                Text("Sign out")
            }
        } else {
            Button(onClick = onSignIn, modifier = Modifier.fillMaxWidth()) {
                Text("Sign in with Google")
            }
        }

        if (!uiState.message.isNullOrBlank()) {
            Text(
                text = uiState.message,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
