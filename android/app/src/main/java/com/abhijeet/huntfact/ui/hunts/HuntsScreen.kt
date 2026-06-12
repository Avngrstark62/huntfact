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
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.animation.core.tween
import com.abhijeet.huntfact.ui.components.HeroHeaderCard
import com.abhijeet.huntfact.hunts.HuntItem
import com.abhijeet.huntfact.ui.components.EmptyStateView
import com.abhijeet.huntfact.ui.components.InfoCard
import com.abhijeet.huntfact.ui.components.SectionTitle
import com.abhijeet.huntfact.ui.components.StatusChip
import com.google.gson.JsonParser
import coil.compose.AsyncImage
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
    val claimStats = remember(hunt.result) { calculateClaimStats(hunt.result) }
    val cardHeight = 104.dp
    val thumbnailSize = 72.dp

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
                .padding(horizontal = AppSpacing.md, vertical = AppSpacing.sm),
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.sm),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            HuntThumbnail(
                url = hunt.thumbnailUrl,
                modifier = Modifier
                    .size(thumbnailSize)
                    .clip(RoundedCornerShape(12.dp)),
            )

            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Text(
                    text = hunt.title?.takeIf { it.isNotBlank() } ?: "Claim verification report",
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = claimStats.summaryLabel(),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }

            TrustScoreBadge(score = hunt.trustScore)
        }
    }
}

@Composable
private fun HuntThumbnail(
    url: String?,
    modifier: Modifier = Modifier,
) {
    val shape = RoundedCornerShape(12.dp)
    val placeholderPainter = painterResource(id = android.R.drawable.ic_media_play)
    if (url.isNullOrBlank()) {
        ThumbnailPlaceholder(
            modifier = modifier
                .clip(shape)
        )
        return
    }

    AsyncImage(
        model = url,
        contentDescription = "Hunt thumbnail",
        modifier = modifier
            .clip(shape),
        placeholder = placeholderPainter,
        error = placeholderPainter,
        contentScale = ContentScale.Crop,
    )
}

@Composable
private fun ThumbnailPlaceholder(modifier: Modifier = Modifier) {
    Box(
        modifier = modifier.background(MaterialTheme.colorScheme.surfaceVariant),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            painter = painterResource(id = android.R.drawable.ic_media_play),
            contentDescription = "Video thumbnail placeholder",
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.size(28.dp),
        )
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
    val unverifiedClaims: Int,
)

private fun HuntClaimStats.summaryLabel(): String {
    return when {
        falseClaims > 0 -> "$totalClaims claims . $falseClaims false"
        unverifiedClaims > 0 -> "$totalClaims claims . $unverifiedClaims unverified"
        else -> "$totalClaims claims . all accurate"
    }
}

private fun calculateClaimStats(rawResult: String?): HuntClaimStats {
    if (rawResult.isNullOrBlank()) {
        return HuntClaimStats(totalClaims = 0, falseClaims = 0, unverifiedClaims = 0)
    }

    return runCatching {
        val root = JsonParser.parseString(rawResult)
        val rowsElement = when {
            root.isJsonObject && root.asJsonObject.has("rows") -> root.asJsonObject.get("rows")
            root.isJsonArray -> root
            else -> null
        } ?: return@runCatching HuntClaimStats(totalClaims = 0, falseClaims = 0, unverifiedClaims = 0)

        if (!rowsElement.isJsonArray) {
            return@runCatching HuntClaimStats(totalClaims = 0, falseClaims = 0, unverifiedClaims = 0)
        }

        var total = 0
        var falseCount = 0
        var unverifiedCount = 0

        rowsElement.asJsonArray.forEach { rowElement ->
            if (!rowElement.isJsonObject) return@forEach
            total += 1
            val verdictRaw = rowElement.asJsonObject.get("verdict")?.safeAsString().orEmpty()
            when (parseVerdictBucket(verdictRaw)) {
                VerdictBucket.FALSE -> falseCount += 1
                VerdictBucket.UNVERIFIED -> unverifiedCount += 1
                VerdictBucket.TRUE -> Unit
            }
        }

        HuntClaimStats(
            totalClaims = total,
            falseClaims = falseCount,
            unverifiedClaims = unverifiedCount,
        )
    }.getOrDefault(HuntClaimStats(totalClaims = 0, falseClaims = 0, unverifiedClaims = 0))
}

private enum class VerdictBucket {
    TRUE,
    FALSE,
    UNVERIFIED,
}

private fun parseVerdictBucket(verdict: String): VerdictBucket {
    val normalized = verdict.trim().lowercase()
    return when {
        "false" in normalized -> VerdictBucket.FALSE
        normalized == "true" -> VerdictBucket.TRUE
        else -> VerdictBucket.UNVERIFIED
    }
}

private fun trustScoreColor(score: Int): Color {
    return when (score) {
        in 0..40 -> Color(0xFFE53935)
        in 41..69 -> Color(0xFFFFB300)
        else -> Color(0xFF2E7D32)
    }
}

private fun com.google.gson.JsonElement?.safeAsString(): String {
    return runCatching { this?.asString?.trim().orEmpty() }.getOrDefault("")
}
