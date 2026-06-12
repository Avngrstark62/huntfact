package com.abhijeet.huntfact.ui.hunts

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.abhijeet.huntfact.hunts.HuntItem
import com.abhijeet.huntfact.ui.components.EmptyStateView
import com.abhijeet.huntfact.ui.components.InfoCard
import com.abhijeet.huntfact.ui.components.SectionTitle
import com.abhijeet.huntfact.ui.components.StatusChip
import com.abhijeet.huntfact.ui.theme.AppSpacing

@Composable
fun HuntsScreen(
    uiState: HuntsUiState,
    onRefresh: () -> Unit,
    onSignIn: () -> Unit,
    onSignOut: () -> Unit,
    onOpenHunt: (HuntItem) -> Unit,
    showSectionTitle: Boolean = true,
    showSummary: Boolean = true,
    showActionButtons: Boolean = true,
    showMessage: Boolean = true,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = AppSpacing.md, vertical = AppSpacing.sm),
    ) {
        if (showSectionTitle) {
            SectionTitle("Hunts")
            Spacer(modifier = Modifier.height(AppSpacing.sm))
        }

        if (!uiState.isAuthenticated) {
            EmptyStateView(
                title = "Sign in required",
                subtitle = "Sign in with Google to view your hunts and verification results.",
            )
            Spacer(modifier = Modifier.height(AppSpacing.md))
            Button(onClick = onSignIn, modifier = Modifier.fillMaxWidth()) {
                Text("Sign in with Google")
            }
            return
        }

        if (showSummary) {
            HuntsSummaryRow(
                hunts = uiState.hunts,
                isRefreshing = uiState.isRefreshing,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(AppSpacing.sm))
        }

        if (showActionButtons) {
            Row(horizontalArrangement = Arrangement.spacedBy(AppSpacing.xs)) {
                Button(
                    onClick = onRefresh,
                    modifier = Modifier.weight(1f),
                    enabled = !uiState.isRefreshing,
                ) {
                    Text(if (uiState.isRefreshing) "Refreshing..." else "Refresh hunts")
                }
                Button(onClick = onSignOut, modifier = Modifier.weight(1f)) {
                    Text("Sign out")
                }
            }
        }

        if (showMessage && !uiState.message.isNullOrBlank()) {
            Spacer(modifier = Modifier.height(AppSpacing.xs))
            Text(
                text = uiState.message,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        Spacer(modifier = Modifier.height(AppSpacing.md))

        if (uiState.hunts.isEmpty()) {
            EmptyStateView(
                title = "No hunts yet",
                subtitle = "Share an Instagram reel to HuntFact and your hunt will appear here.",
            )
            return
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(AppSpacing.sm)) {
            items(uiState.hunts, key = { it.id }) { hunt ->
                HuntCard(hunt = hunt, onClick = { onOpenHunt(hunt) })
            }
        }
    }
}

@Composable
private fun HuntsSummaryRow(
    hunts: List<HuntItem>,
    isRefreshing: Boolean,
    modifier: Modifier = Modifier,
) {
    val completed = hunts.count { it.status.equals("completed", ignoreCase = true) }
    val running = hunts.count {
        it.status.equals("running", ignoreCase = true) ||
            it.status.equals("processing", ignoreCase = true) ||
            it.status.equals("pending", ignoreCase = true)
    }

    Row(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.sm),
    ) {
        InfoCard(
            title = "Total hunts",
            value = hunts.size.toString(),
            subtitle = if (isRefreshing) "Updating now" else null,
            modifier = Modifier.weight(1f),
        )
        InfoCard(
            title = "Completed",
            value = completed.toString(),
            subtitle = "Running: $running",
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun HuntCard(
    hunt: HuntItem,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.xs),
        ) {
            Text(
                text = hunt.caption?.takeIf { it.isNotBlank() } ?: hunt.videoLink,
                style = MaterialTheme.typography.titleMedium,
                maxLines = 2,
            )
            StatusChip(status = hunt.status)
            hunt.creatorHandle?.takeIf { it.isNotBlank() }?.let {
                Text(
                    text = "Creator: @$it",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            hunt.updatedAt?.takeIf { it.isNotBlank() }?.let {
                Text(
                    text = "Updated: $it",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (hunt.status.equals("failed", ignoreCase = true) && !hunt.errorMessage.isNullOrBlank()) {
                Text(
                    text = "Error: ${hunt.errorMessage}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}
