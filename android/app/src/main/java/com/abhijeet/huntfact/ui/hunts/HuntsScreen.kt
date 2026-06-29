package com.abhijeet.huntfact.ui.hunts

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
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
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.animation.core.tween
import com.abhijeet.huntfact.ui.components.HeroHeaderCard
import com.abhijeet.huntfact.hunts.HuntClaimRow
import com.abhijeet.huntfact.hunts.HuntItem
import com.abhijeet.huntfact.ui.components.EmptyStateView
import com.abhijeet.huntfact.ui.components.InfoCard
import com.abhijeet.huntfact.ui.components.SectionTitle
import com.abhijeet.huntfact.ui.components.StatusChip
import com.abhijeet.huntfact.ui.theme.AppSpacing
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun HuntsScreen(
    uiState: HuntsUiState,
    onRefresh: () -> Unit,
    onSignIn: () -> Unit,
    onSignOut: () -> Unit,
    notificationPermissionHint: String? = null,
    onViewNewHunts: () -> Unit = {},
    onOpenHunt: (HuntItem) -> Unit,
    showSectionTitle: Boolean = true,
    showSummary: Boolean = true,
    showActionButtons: Boolean = true,
    showMessage: Boolean = true,
    modifier: Modifier = Modifier,
) {
    val isHistoryMode = !showSectionTitle && !showSummary && !showActionButtons
    val listState = rememberLazyListState()
    val coroutineScope = rememberCoroutineScope()

    LaunchedEffect(uiState.scrollToTopSignal) {
        if (uiState.scrollToTopSignal > 0) {
            listState.animateScrollToItem(0)
        }
    }

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

        if (!notificationPermissionHint.isNullOrBlank()) {
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    text = notificationPermissionHint,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(AppSpacing.md),
                )
            }
            Spacer(modifier = Modifier.height(AppSpacing.sm))
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
                Column(modifier = Modifier.padding(AppSpacing.xs)) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(AppSpacing.xs),
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

        if (uiState.newHuntsAvailable) {
            Spacer(modifier = Modifier.height(AppSpacing.xs))
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Row(
                    modifier = Modifier.padding(AppSpacing.sm),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(AppSpacing.sm),
                ) {
                    Text(
                        text = "New hunt available",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.weight(1f),
                    )
                    Button(
                        onClick = {
                            coroutineScope.launch {
                                listState.animateScrollToItem(0)
                            }
                            onViewNewHunts()
                        },
                        shape = RoundedCornerShape(999.dp),
                    ) {
                        Text("View")
                    }
                }
            }
            Spacer(modifier = Modifier.height(AppSpacing.xs))
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

        LazyColumn(
            state = listState,
            verticalArrangement = Arrangement.spacedBy(AppSpacing.sm),
        ) {
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
    val claimStats = remember(hunt.result) { calculateClaimStats(hunt.result) }
    val normalizedStatus = normalizeHuntStatus(hunt.status)
    val cardHeight = 88.dp

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .height(cardHeight)
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(14.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = AppSpacing.md, vertical = AppSpacing.xs),
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.sm),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Text(
                    text = hunt.title?.takeIf { it.isNotBlank() } ?: fallbackTitleForStatus(normalizedStatus),
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = subtitleForHunt(hunt, normalizedStatus, claimStats),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }

            hunt.trustScore?.let { score ->
                TrustScoreBadge(score = score)
            } ?: StatusChip(status = hunt.status)
        }
    }
}

@Composable
private fun TrustScoreBadge(
    score: Int,
    modifier: Modifier = Modifier,
) {
    val normalizedScore = score.coerceIn(0, 100)
    val trustColor = trustScoreColor(normalizedScore)
    Box(
        modifier = modifier
            .size(42.dp)
            .background(trustColor.copy(alpha = 0.16f), CircleShape)
            .border(width = 1.dp, color = trustColor.copy(alpha = 0.55f), shape = CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = normalizedScore.toString(),
            style = MaterialTheme.typography.labelLarge,
            color = trustColor,
        )
    }
}

private data class HuntClaimStats(
    val totalClaims: Int,
    val falseClaims: Int,
    val mostlyFalseClaims: Int,
    val unverifiedClaims: Int,
    val mostlyTrueClaims: Int,
    val trueClaims: Int,
)

private fun HuntClaimStats.summaryLabel(): String {
    return when {
        falseClaims > 0 -> "$totalClaims claims . $falseClaims false"
        mostlyFalseClaims > 0 -> "$totalClaims claims . $mostlyFalseClaims mostly false"
        unverifiedClaims > 0 -> "$totalClaims claims . $unverifiedClaims unverified"
        mostlyTrueClaims > 0 -> "$totalClaims claims . $mostlyTrueClaims mostly true"
        trueClaims > 0 -> "$totalClaims claims . all true"
        else -> "$totalClaims claims"
    }
}

private fun calculateClaimStats(rows: List<HuntClaimRow>?): HuntClaimStats {
    if (rows.isNullOrEmpty()) {
        return HuntClaimStats(
            totalClaims = 0,
            falseClaims = 0,
            mostlyFalseClaims = 0,
            unverifiedClaims = 0,
            mostlyTrueClaims = 0,
            trueClaims = 0,
        )
    }

    var falseCount = 0
    var mostlyFalseCount = 0
    var unverifiedCount = 0
    var mostlyTrueCount = 0
    var trueCount = 0

    rows.forEach { row ->
        when (row.verdict.ifBlank { VERDICT_UNVERIFIED }) {
            VERDICT_FALSE -> falseCount += 1
            VERDICT_MOSTLY_FALSE -> mostlyFalseCount += 1
            VERDICT_UNVERIFIED -> unverifiedCount += 1
            VERDICT_MOSTLY_TRUE -> mostlyTrueCount += 1
            VERDICT_TRUE -> trueCount += 1
        }
    }

    return HuntClaimStats(
        totalClaims = rows.size,
        falseClaims = falseCount,
        mostlyFalseClaims = mostlyFalseCount,
        unverifiedClaims = unverifiedCount,
        mostlyTrueClaims = mostlyTrueCount,
        trueClaims = trueCount,
    )
}

private fun trustScoreColor(score: Int): Color {
    return when (score) {
        in 0..40 -> Color(0xFFE53935)
        in 41..69 -> Color(0xFFFFB300)
        else -> Color(0xFF2E7D32)
    }
}

private enum class HuntStatus {
    PROCESSING,
    COMPLETED,
    FAILED,
    OTHER,
}

private fun normalizeHuntStatus(status: String): HuntStatus {
    return when (status.trim().lowercase()) {
        "queued", "running", "processing", "pending" -> HuntStatus.PROCESSING
        "completed" -> HuntStatus.COMPLETED
        "failed" -> HuntStatus.FAILED
        else -> HuntStatus.OTHER
    }
}

private fun fallbackTitleForStatus(status: HuntStatus): String {
    return when (status) {
        HuntStatus.PROCESSING -> "Processing..."
        HuntStatus.FAILED -> "Hunt failed"
        HuntStatus.COMPLETED, HuntStatus.OTHER -> "Untitled hunt"
    }
}

private fun subtitleForHunt(
    hunt: HuntItem,
    status: HuntStatus,
    claimStats: HuntClaimStats,
): String {
    return when (status) {
        HuntStatus.PROCESSING -> "Processing"
        HuntStatus.FAILED -> hunt.errorMessage?.takeIf { it.isNotBlank() } ?: "Failed"
        HuntStatus.COMPLETED -> {
            if (claimStats.totalClaims == 0) "No claims found" else claimStats.summaryLabel()
        }
        HuntStatus.OTHER -> hunt.status.ifBlank { "Unknown" }
    }
}

private const val VERDICT_TRUE = "true"
private const val VERDICT_MOSTLY_TRUE = "mostly true"
private const val VERDICT_UNVERIFIED = "unverified"
private const val VERDICT_MOSTLY_FALSE = "mostly false"
private const val VERDICT_FALSE = "false"
