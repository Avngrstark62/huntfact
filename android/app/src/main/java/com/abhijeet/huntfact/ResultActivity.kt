package com.abhijeet.huntfact

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.ComponentActivity
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
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import com.abhijeet.huntfact.hunts.HuntRepository
import com.abhijeet.huntfact.ui.components.EmptyStateView
import com.abhijeet.huntfact.ui.components.SectionTitle
import com.abhijeet.huntfact.ui.theme.AndroidTheme
import com.abhijeet.huntfact.ui.theme.AppSpacing
import com.google.gson.JsonParser
import kotlinx.coroutines.launch

class ResultActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val huntId = intent.getIntExtra(EXTRA_HUNT_ID, -1)
        if (huntId <= 0) {
            setContent {
                AndroidTheme {
                    EmptyResultScreen(
                        title = "Missing hunt reference",
                        subtitle = "No result available.",
                    )
                }
            }
            return
        }

        val repository = HuntRepository(applicationContext)
        lifecycleScope.launch {
            val hunt = try {
                repository.fetchHunt(huntId)
            } catch (_: Exception) {
                repository.getCachedHunts().firstOrNull { it.id == huntId }
            }

            if (hunt == null) {
                setContent {
                    AndroidTheme {
                        EmptyResultScreen(
                            title = "Unable to load hunt",
                            subtitle = "Please reopen from notification or refresh from the hunts screen.",
                        )
                    }
                }
                return@launch
            }

            setContent {
                AndroidTheme {
                    ResultScreen(hunt = hunt)
                }
            }
        }
    }

    companion object {
        const val EXTRA_HUNT_ID = "hunt_id"
    }
}

private data class ClaimRow(
    val claim: String,
    val verdict: String,
    val confidencePercent: Int,
    val sources: List<String>,
    val explanation: String,
)

private val TrustSummaryCardHeight = 124.dp
private const val DEFAULT_CLAIM_CONFIDENCE_PERCENT = 78

@Composable
private fun ResultScreen(hunt: com.abhijeet.huntfact.hunts.HuntItem) {
    val allRows = remember(hunt.result) { parseRows(hunt.result) }
    val claimCountLabel = "${allRows.size} claims"
    val claimStats = remember(allRows) { computeResultClaimStats(allRows) }
    val context = LocalContext.current

    Scaffold { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(AppSpacing.md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.sm),
        ) {
            Text(
                text = "Can I trust this?",
                style = MaterialTheme.typography.headlineMedium,
            )
            Text(
                text = claimCountLabel,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            TrustSummaryCard(trustScore = hunt.trustScore)

            if (hunt.result.isNullOrBlank()) {
                EmptyStateView(
                    title = "Result not ready",
                    subtitle = "This hunt is still processing. Please check again shortly.",
                )
                return@Column
            }

            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(AppSpacing.sm),
            ) {
                item {
                    HuntSummaryCard(
                        summary = hunt.summary,
                    )
                }
                item {
                    ClaimStatsGrid(
                        falseClaims = claimStats.falseClaims,
                        unverifiedClaims = claimStats.unverifiedClaims,
                        trueClaims = claimStats.trueClaims,
                        totalClaims = claimStats.totalClaims,
                    )
                }
                if (allRows.isEmpty()) {
                    item {
                        EmptyStateView(
                            title = "No claims found",
                            subtitle = "This result has no claim rows yet.",
                        )
                    }
                } else {
                    item {
                        Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.xs)) {
                            Text(
                                text = "Claims",
                                style = MaterialTheme.typography.titleLarge,
                            )
                            Text(
                                text = "Tap any claim for full evidence",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                    itemsIndexed(allRows) { index, row ->
                        ClaimRowCard(
                            row = row,
                            onClick = {
                                context.startActivity(
                                    ClaimDetailActivity.createIntent(
                                        context = context,
                                        claimText = row.claim,
                                        verdict = row.verdict,
                                        confidencePercent = row.confidencePercent,
                                        explanation = row.explanation,
                                        sources = row.sources,
                                        claimIndex = index + 1,
                                        totalClaims = allRows.size,
                                    ),
                                )
                            },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun TrustSummaryCard(trustScore: Int?) {
    val normalizedScore = trustScore?.coerceIn(0, 100)
    val trustColor = if (normalizedScore != null) trustScoreColor(normalizedScore) else MaterialTheme.colorScheme.outline
    val trustBand = remember(normalizedScore) {
        if (normalizedScore != null) {
            trustBandForScore(normalizedScore)
        } else {
            TrustBand(
                title = "Processing",
                description = "Trust score will appear when verification completes.",
            )
        }
    }
    val cardShape = RoundedCornerShape(18.dp)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .height(TrustSummaryCardHeight),
        shape = cardShape,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = AppSpacing.md, vertical = AppSpacing.sm),
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.md),
            verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(88.dp)
                    .background(trustColor.copy(alpha = 0.16f), CircleShape)
                    .border(width = 1.4.dp, color = trustColor.copy(alpha = 0.58f), shape = CircleShape),
                contentAlignment = androidx.compose.ui.Alignment.Center,
            ) {
                Text(
                    text = normalizedScore?.toString() ?: "--",
                    style = MaterialTheme.typography.headlineSmall,
                    color = trustColor,
                )
            }
            Column(
                verticalArrangement = Arrangement.spacedBy(AppSpacing.xs),
            ) {
                Text(
                    text = trustBand.title,
                    style = MaterialTheme.typography.titleLarge,
                )
                Text(
                    text = trustBand.description,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun HuntSummaryCard(summary: String?) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 84.dp, max = 220.dp),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(AppSpacing.md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.xs),
        ) {
            Text(
                text = "Summary",
                style = MaterialTheme.typography.titleMedium,
            )
            Text(
                text = summary?.takeIf { it.isNotBlank() } ?: "Summary will be available when processing completes.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 10,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun ClaimStatsGrid(
    falseClaims: Int,
    unverifiedClaims: Int,
    trueClaims: Int,
    totalClaims: Int,
) {
    Column(
        verticalArrangement = Arrangement.spacedBy(AppSpacing.sm),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(AppSpacing.sm)) {
            ClaimStatTile(
                value = falseClaims,
                label = "false",
                color = Color(0xFFE53935),
                modifier = Modifier.weight(1f),
            )
            ClaimStatTile(
                value = unverifiedClaims,
                label = "unverified",
                color = Color(0xFFFFB300),
                modifier = Modifier.weight(1f),
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(AppSpacing.sm)) {
            ClaimStatTile(
                value = trueClaims,
                label = "true",
                color = Color(0xFF2E7D32),
                modifier = Modifier.weight(1f),
            )
            ClaimStatTile(
                value = totalClaims,
                label = "total claims",
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun ClaimStatTile(
    value: Int,
    label: String,
    color: Color,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier
            .height(88.dp),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(AppSpacing.md),
            verticalArrangement = Arrangement.Center,
        ) {
            Text(
                text = value.toString(),
                style = MaterialTheme.typography.headlineSmall,
                color = color,
            )
            Text(
                text = label,
                style = MaterialTheme.typography.titleSmall,
                color = color,
            )
        }
    }
}

private data class TrustBand(val title: String, val description: String)
private data class ResultClaimStats(
    val falseClaims: Int,
    val unverifiedClaims: Int,
    val trueClaims: Int,
    val totalClaims: Int,
)

private fun computeResultClaimStats(rows: List<ClaimRow>): ResultClaimStats {
    var falseCount = 0
    var unverifiedCount = 0
    var trueCount = 0

    rows.forEach { row ->
        when (normalizeResultVerdict(row.verdict)) {
            ResultVerdict.FALSE -> falseCount += 1
            ResultVerdict.UNVERIFIED -> unverifiedCount += 1
            ResultVerdict.TRUE -> trueCount += 1
        }
    }

    return ResultClaimStats(
        falseClaims = falseCount,
        unverifiedClaims = unverifiedCount,
        trueClaims = trueCount,
        totalClaims = rows.size,
    )
}

private enum class ResultVerdict {
    TRUE,
    FALSE,
    UNVERIFIED,
}

private fun normalizeResultVerdict(rawVerdict: String): ResultVerdict {
    val normalized = rawVerdict.trim().lowercase()
    return when {
        "false" in normalized -> ResultVerdict.FALSE
        normalized == "true" -> ResultVerdict.TRUE
        else -> ResultVerdict.UNVERIFIED
    }
}

private fun trustBandForScore(score: Int): TrustBand {
    return when (score) {
        in 0..40 -> TrustBand(
            title = "Low trust",
            description = "Multiple false claims detected. Use caution sharing.",
        )
        in 41..69 -> TrustBand(
            title = "Moderate trust",
            description = "Some claims are uncertain. Verify key points before sharing.",
        )
        else -> TrustBand(
            title = "High trust",
            description = "Most claims appear accurate based on available evidence.",
        )
    }
}

private fun trustScoreColor(score: Int): Color {
    return when (score) {
        in 0..40 -> Color(0xFFE53935)
        in 41..69 -> Color(0xFFFFB300)
        else -> Color(0xFF2E7D32)
    }
}

@Composable
private fun ClaimRowCard(
    row: ClaimRow,
    onClick: () -> Unit,
) {
    val verdict = normalizeResultVerdict(row.verdict)
    val accentColor = verdictColor(verdict)
    val iconRes = verdictIconRes(verdict)
    val label = when (verdict) {
        ResultVerdict.FALSE -> "false"
        ResultVerdict.TRUE -> "true"
        ResultVerdict.UNVERIFIED -> "unverified"
    }

    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier
            .fillMaxWidth()
            .height(96.dp)
            .clickable(onClick = onClick),
    ) {
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = AppSpacing.md, vertical = AppSpacing.sm),
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.sm),
            verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
        ) {
            Icon(
                painter = painterResource(id = iconRes),
                contentDescription = label,
                tint = accentColor,
                modifier = Modifier.size(26.dp),
            )
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(AppSpacing.xs),
            ) {
                Text(
                    text = row.claim,
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = "$label . ${row.confidencePercent}% confidence",
                    style = MaterialTheme.typography.bodyMedium,
                    color = accentColor,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

private fun verdictColor(verdict: ResultVerdict): Color {
    return when (verdict) {
        ResultVerdict.FALSE -> Color(0xFFE53935)
        ResultVerdict.UNVERIFIED -> Color(0xFFFFB300)
        ResultVerdict.TRUE -> Color(0xFF2E7D32)
    }
}

private fun verdictIconRes(verdict: ResultVerdict): Int {
    return when (verdict) {
        ResultVerdict.FALSE -> android.R.drawable.ic_delete
        ResultVerdict.UNVERIFIED -> android.R.drawable.ic_dialog_alert
        ResultVerdict.TRUE -> R.drawable.ic_verdict_true
    }
}

@Composable
private fun EmptyResultScreen(title: String, subtitle: String) {
    Scaffold { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(AppSpacing.md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.sm),
        ) {
            SectionTitle("Fact Check Result")
            EmptyStateView(title = title, subtitle = subtitle)
        }
    }
}

private fun parseRows(raw: String?): List<ClaimRow> {
    if (raw.isNullOrBlank()) {
        return emptyList()
    }

    return runCatching {
        val root = JsonParser.parseString(raw)
        val rowsElement = when {
            root.isJsonObject && root.asJsonObject.has("rows") -> root.asJsonObject.get("rows")
            root.isJsonArray -> root
            else -> null
        } ?: return@runCatching emptyList()

        if (!rowsElement.isJsonArray) {
            return@runCatching emptyList()
        }

        rowsElement.asJsonArray.mapNotNull { rowElement ->
            if (!rowElement.isJsonObject) {
                return@mapNotNull null
            }
            val obj = rowElement.asJsonObject
            val claim = obj.get("claim").safeAsString()
            if (claim.isBlank()) {
                return@mapNotNull null
            }
            val verdict = obj.get("verdict").safeAsString().ifBlank { "no verdict" }
            val explanation = obj.get("explanation").safeAsString()
            val sources = obj.get("sources")
                ?.takeIf { it.isJsonArray }
                ?.asJsonArray
                ?.mapNotNull { sourceElement ->
                    runCatching { sourceElement.asString.trim() }.getOrNull()?.takeIf { it.isNotBlank() }
                }
                .orEmpty()
            ClaimRow(
                claim = claim,
                verdict = verdict,
                confidencePercent = DEFAULT_CLAIM_CONFIDENCE_PERCENT,
                sources = sources,
                explanation = explanation.ifBlank { "No explanation provided." },
            )
        }
    }.getOrElse {
        listOf(
            ClaimRow(
                claim = "Result",
                verdict = "no verdict",
                confidencePercent = DEFAULT_CLAIM_CONFIDENCE_PERCENT,
                sources = emptyList(),
                explanation = raw.trim(),
            )
        )
    }
}

private fun com.google.gson.JsonElement?.safeAsString(): String {
    return runCatching { this?.asString?.trim().orEmpty() }.getOrDefault("")
}
