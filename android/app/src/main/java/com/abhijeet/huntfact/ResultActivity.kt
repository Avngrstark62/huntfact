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
import com.google.firebase.Firebase
import com.google.firebase.crashlytics.crashlytics
import com.google.gson.JsonParser
import kotlinx.coroutines.launch

class ResultActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Firebase.crashlytics.log("ResultActivity.onCreate: started")

        val huntId = intent.getIntExtra(EXTRA_HUNT_ID, -1)
        if (huntId <= 0) {
            Firebase.crashlytics.log("ResultActivity.onCreate: missing or invalid huntId=$huntId")
            Firebase.crashlytics.recordException(Exception("ResultActivity received invalid huntId"))
            setContent {
                AndroidTheme {
                    EmptyResultScreen(
                        title = "Missing hunt reference",
                        subtitle = "No result available.",
                    )
                }
            }
            Firebase.crashlytics.log("ResultActivity.onCreate: returning due to invalid hunt ID")
            return
        }

        Firebase.crashlytics.log("ResultActivity.onCreate: loading huntId=$huntId")
        val repository = HuntRepository(applicationContext)
        lifecycleScope.launch {
            val hunt = try {
                Firebase.crashlytics.log("ResultActivity.onCreate: fetching hunt from API for huntId=$huntId")
                repository.fetchHunt(huntId)
            } catch (exception: Exception) {
                Firebase.crashlytics.log("ResultActivity.onCreate: API fetch failed for huntId=$huntId, trying cache")
                Firebase.crashlytics.recordException(exception)
                repository.getCachedHunts().firstOrNull { it.id == huntId }
            }

            if (hunt == null) {
                Firebase.crashlytics.log("ResultActivity.onCreate: hunt not found for huntId=$huntId")
                Firebase.crashlytics.recordException(Exception("Hunt not found in API and cache for huntId=$huntId"))
                setContent {
                    AndroidTheme {
                        EmptyResultScreen(
                            title = "Unable to load hunt",
                            subtitle = "Please reopen from notification or refresh from the hunts screen.",
                        )
                    }
                }
                Firebase.crashlytics.log("ResultActivity.onCreate: returning due to missing hunt")
                return@launch
            }

            Firebase.crashlytics.log("ResultActivity.onCreate: rendering result screen for huntId=${hunt.id}")
            setContent {
                AndroidTheme {
                    ResultScreen(hunt = hunt)
                }
            }
            Firebase.crashlytics.log("ResultActivity.onCreate: completed")
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
private const val DEFAULT_CLAIM_CONFIDENCE_PERCENT = 50

@Composable
private fun ResultScreen(hunt: com.abhijeet.huntfact.hunts.HuntItem) {
    val huntStatus = normalizeHuntStatus(hunt.status)
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
            TrustSummaryCard(
                trustScore = hunt.trustScore,
                huntStatus = huntStatus,
            )

            if (huntStatus == HuntStatus.PROCESSING) {
                EmptyStateView(
                    title = "Result not ready",
                    subtitle = "This hunt is still processing. Please check again shortly.",
                )
                return@Column
            }
            if (huntStatus == HuntStatus.FAILED) {
                EmptyStateView(
                    title = "Hunt failed",
                    subtitle = hunt.errorMessage?.takeIf { it.isNotBlank() }
                        ?: "This hunt failed. Please retry.",
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
                        huntStatus = huntStatus,
                    )
                }
                item {
                    ClaimStatsGrid(
                        falseClaims = claimStats.falseClaims,
                        mostlyFalseClaims = claimStats.mostlyFalseClaims,
                        unverifiedClaims = claimStats.unverifiedClaims,
                        mostlyTrueClaims = claimStats.mostlyTrueClaims,
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
private fun TrustSummaryCard(
    trustScore: Int?,
    huntStatus: HuntStatus,
) {
    val normalizedScore = trustScore?.coerceIn(0, 100)
    val trustColor = if (normalizedScore != null) trustScoreColor(normalizedScore) else MaterialTheme.colorScheme.outline
    val trustBand = remember(normalizedScore, huntStatus) {
        if (huntStatus == HuntStatus.PROCESSING) {
            TrustBand(
                title = "Processing",
                description = "Trust score will appear when verification completes.",
            )
        } else if (huntStatus == HuntStatus.FAILED) {
            TrustBand(
                title = "Hunt failed",
                description = "No trust score is available for failed hunts.",
            )
        } else if (normalizedScore != null) {
            trustBandForScore(normalizedScore)
        } else {
            TrustBand(
                title = "Trust unavailable",
                description = "This hunt has no trust score yet.",
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
private fun HuntSummaryCard(
    summary: String?,
    huntStatus: HuntStatus,
) {
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
                text = summary?.takeIf { it.isNotBlank() } ?: fallbackSummaryText(huntStatus),
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
    mostlyFalseClaims: Int,
    unverifiedClaims: Int,
    mostlyTrueClaims: Int,
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
                value = mostlyFalseClaims,
                label = "mostly false",
                color = Color(0xFFFF7043),
                modifier = Modifier.weight(1f),
            )
            ClaimStatTile(
                value = mostlyTrueClaims,
                label = "mostly true",
                color = Color(0xFF66BB6A),
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
    val mostlyFalseClaims: Int,
    val unverifiedClaims: Int,
    val mostlyTrueClaims: Int,
    val trueClaims: Int,
    val totalClaims: Int,
)

private fun computeResultClaimStats(rows: List<ClaimRow>): ResultClaimStats {
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

    return ResultClaimStats(
        falseClaims = falseCount,
        mostlyFalseClaims = mostlyFalseCount,
        unverifiedClaims = unverifiedCount,
        mostlyTrueClaims = mostlyTrueCount,
        trueClaims = trueCount,
        totalClaims = rows.size,
    )
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
    val label = row.verdict.ifBlank { VERDICT_UNVERIFIED }
    val accentColor = verdictColor(label)
    val iconRes = verdictIconRes(label)

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

private fun verdictColor(verdict: String): Color {
    return when (verdict) {
        VERDICT_FALSE -> Color(0xFFE53935)
        VERDICT_MOSTLY_FALSE -> Color(0xFFFF7043)
        VERDICT_UNVERIFIED -> Color(0xFFFFB300)
        VERDICT_MOSTLY_TRUE -> Color(0xFF66BB6A)
        VERDICT_TRUE -> Color(0xFF2E7D32)
        else -> Color(0xFF9E9E9E)
    }
}

private fun verdictIconRes(verdict: String): Int {
    return when (verdict) {
        VERDICT_FALSE, VERDICT_MOSTLY_FALSE -> android.R.drawable.ic_delete
        VERDICT_UNVERIFIED -> android.R.drawable.ic_dialog_alert
        VERDICT_MOSTLY_TRUE, VERDICT_TRUE -> R.drawable.ic_verdict_true
        else -> android.R.drawable.ic_menu_help
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
    Firebase.crashlytics.log("ResultActivity.parseRows: started")
    if (raw.isNullOrBlank()) {
        Firebase.crashlytics.log("ResultActivity.parseRows: empty input, returning empty rows")
        return emptyList()
    }

    return runCatching {
        Firebase.crashlytics.log("ResultActivity.parseRows: parsing JSON payload")
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
            val verdict = obj.get("verdict").safeAsString().ifBlank { VERDICT_UNVERIFIED }
            val confidencePercent = obj.get("confidence").safeAsIntOrNull()
                ?: obj.get("confidence_percent").safeAsIntOrNull()
                ?: DEFAULT_CLAIM_CONFIDENCE_PERCENT
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
                confidencePercent = confidencePercent.coerceIn(0, 100),
                sources = sources,
                explanation = explanation.ifBlank { "No explanation provided." },
            )
        }
    }.getOrElse {
        Firebase.crashlytics.log("ResultActivity.parseRows: parse failed, falling back to plain text row")
        Firebase.crashlytics.recordException(it)
        listOf(
            ClaimRow(
                claim = "Result",
                verdict = VERDICT_UNVERIFIED,
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

private fun com.google.gson.JsonElement?.safeAsIntOrNull(): Int? {
    return runCatching {
        when {
            this == null -> null
            this.isJsonNull -> null
            this.isJsonPrimitive && this.asJsonPrimitive.isNumber -> this.asInt
            this.isJsonPrimitive && this.asJsonPrimitive.isString -> this.asString.trim().toInt()
            else -> null
        }
    }.getOrNull()
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

private fun fallbackSummaryText(status: HuntStatus): String {
    return when (status) {
        HuntStatus.PROCESSING -> "Summary will be available when processing completes."
        HuntStatus.FAILED -> "No summary is available for failed hunts."
        HuntStatus.COMPLETED, HuntStatus.OTHER -> "Summary unavailable."
    }
}

private const val VERDICT_TRUE = "true"
private const val VERDICT_MOSTLY_TRUE = "mostly true"
private const val VERDICT_UNVERIFIED = "unverified"
private const val VERDICT_MOSTLY_FALSE = "mostly false"
private const val VERDICT_FALSE = "false"
