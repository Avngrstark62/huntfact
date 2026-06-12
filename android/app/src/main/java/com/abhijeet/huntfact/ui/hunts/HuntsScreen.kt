package com.abhijeet.huntfact.ui.hunts

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
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
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.animation.core.tween
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Home
import com.abhijeet.huntfact.ui.components.HeroHeaderCard
import com.abhijeet.huntfact.ui.components.IconMetaRow
import com.abhijeet.huntfact.hunts.HuntItem
import com.abhijeet.huntfact.ui.components.EmptyStateView
import com.abhijeet.huntfact.ui.components.InfoCard
import com.abhijeet.huntfact.ui.components.SectionTitle
import com.abhijeet.huntfact.ui.components.StatusChip
import com.abhijeet.huntfact.ui.theme.AppSpacing
import kotlinx.coroutines.delay

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
    val isHistoryMode = !showSectionTitle && !showSummary && !showActionButtons

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = AppSpacing.md, vertical = AppSpacing.sm),
    ) {
        if (isHistoryMode) {
            HeroHeaderCard(
                title = "History",
                subtitle = "All your completed and in-progress hunts",
            )
            Spacer(modifier = Modifier.height(AppSpacing.sm))
        } else {
            HeroHeaderCard(
                title = "Home",
                subtitle = "Check, track, and verify quickly",
                statsContent = {
                    InfoCard(
                        title = "Total",
                        value = uiState.hunts.size.toString(),
                        modifier = Modifier.weight(1f),
                        accentStripColor = MaterialTheme.colorScheme.tertiary,
                    )
                    val completed = uiState.hunts.count { it.status.equals("completed", ignoreCase = true) }
                    InfoCard(
                        title = "Completed",
                        value = completed.toString(),
                        modifier = Modifier.weight(1f),
                        accentStripColor = MaterialTheme.colorScheme.secondary,
                    )
                },
            )
            Spacer(modifier = Modifier.height(AppSpacing.md))
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

        if (showSummary && isHistoryMode) {
            HuntsSummaryRow(
                hunts = uiState.hunts,
                isRefreshing = uiState.isRefreshing,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(AppSpacing.sm))
        }

        if (showActionButtons) {
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(AppSpacing.xs),
                    modifier = Modifier.padding(AppSpacing.xs),
                ) {
                Button(
                    onClick = onRefresh,
                    modifier = Modifier.weight(1f),
                    enabled = !uiState.isRefreshing,
                    shape = RoundedCornerShape(999.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary,
                    ),
                ) {
                    Text(if (uiState.isRefreshing) "Refreshing..." else "Refresh hunts")
                }
                    Button(
                        onClick = onSignOut,
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(999.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.surface,
                            contentColor = MaterialTheme.colorScheme.onSurface,
                        ),
                    ) {
                    Text("Sign out")
                }
                }
            }
            Spacer(modifier = Modifier.height(AppSpacing.sm))
        }

        if (showMessage && !uiState.message.isNullOrBlank()) {
            Spacer(modifier = Modifier.height(AppSpacing.xs))
            Text(
                text = uiState.message,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        if (!isHistoryMode) {
            SectionTitle("Recent hunts")
            Spacer(modifier = Modifier.height(AppSpacing.sm))
        }

        if (uiState.hunts.isEmpty()) {
            EmptyStateView(
                title = "No hunts yet",
                subtitle = "Share an Instagram reel to HuntFact and your hunt will appear here.",
            )
            return
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(AppSpacing.sm)) {
            itemsIndexed(uiState.hunts, key = { _, hunt -> hunt.id }) { index, hunt ->
                var visible by remember(hunt.id) { mutableStateOf(false) }
                LaunchedEffect(hunt.id) {
                    delay((index * 40L).coerceAtMost(220L))
                    visible = true
                }
                AnimatedVisibility(
                    visible = visible,
                    enter = fadeIn(animationSpec = tween(durationMillis = 150)) +
                        slideInVertically(
                            initialOffsetY = { it / 6 },
                            animationSpec = tween(durationMillis = 150),
                        ),
                ) {
                    HuntCard(hunt = hunt, onClick = { onOpenHunt(hunt) })
                }
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
        shape = RoundedCornerShape(14.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.xs),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(AppSpacing.xs),
            ) {
                Text(
                    text = hunt.caption?.takeIf { it.isNotBlank() } ?: hunt.videoLink,
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
                StatusChip(status = hunt.status)
            }
            hunt.creatorHandle?.takeIf { it.isNotBlank() }?.let {
                IconMetaRow(
                    icon = Icons.Rounded.Home,
                    text = it,
                )
            }
            hunt.updatedAt?.takeIf { it.isNotBlank() }?.let {
                IconMetaRow(
                    icon = Icons.Rounded.Home,
                    text = it,
                )
            }
            if (hunt.status.equals("failed", ignoreCase = true) && !hunt.errorMessage.isNullOrBlank()) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(AppSpacing.xs),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Icon(
                        imageVector = Icons.Rounded.Home,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.error,
                    )
                    Text(
                        text = "Error: ${hunt.errorMessage}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }
        }
    }
}
