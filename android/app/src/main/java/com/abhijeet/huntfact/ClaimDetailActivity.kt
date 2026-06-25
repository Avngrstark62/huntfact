package com.abhijeet.huntfact

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.abhijeet.huntfact.ui.theme.AndroidTheme
import com.abhijeet.huntfact.ui.theme.AppSpacing

class ClaimDetailActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val claimIndex = intent.getIntExtra(EXTRA_CLAIM_INDEX, 1)
        val totalClaims = intent.getIntExtra(EXTRA_TOTAL_CLAIMS, 1)
        val claimText = intent.getStringExtra(EXTRA_CLAIM_TEXT).orEmpty()
        val verdict = intent.getStringExtra(EXTRA_VERDICT).orEmpty()
        val confidence = intent.getIntExtra(EXTRA_CONFIDENCE_PERCENT, 0)
        val explanation = intent.getStringExtra(EXTRA_EXPLANATION).orEmpty()
        val sources = intent.getStringArrayListExtra(EXTRA_SOURCES).orEmpty()

        setContent {
            AndroidTheme {
                ClaimDetailScreen(
                    claimIndex = claimIndex,
                    totalClaims = totalClaims,
                    claimText = claimText,
                    verdictRaw = verdict,
                    confidencePercent = confidence,
                    explanation = explanation,
                    sources = sources,
                    onBack = { finish() },
                )
            }
        }
    }

    companion object {
        private const val EXTRA_CLAIM_INDEX = "claim_index"
        private const val EXTRA_TOTAL_CLAIMS = "total_claims"
        private const val EXTRA_CLAIM_TEXT = "claim_text"
        private const val EXTRA_VERDICT = "claim_verdict"
        private const val EXTRA_CONFIDENCE_PERCENT = "claim_confidence_percent"
        private const val EXTRA_EXPLANATION = "claim_explanation"
        private const val EXTRA_SOURCES = "claim_sources"

        fun createIntent(
            context: Context,
            claimText: String,
            verdict: String,
            confidencePercent: Int,
            explanation: String,
            sources: List<String>,
            claimIndex: Int,
            totalClaims: Int,
        ): Intent {
            return Intent(context, ClaimDetailActivity::class.java).apply {
                putExtra(EXTRA_CLAIM_INDEX, claimIndex)
                putExtra(EXTRA_TOTAL_CLAIMS, totalClaims)
                putExtra(EXTRA_CLAIM_TEXT, claimText)
                putExtra(EXTRA_VERDICT, verdict)
                putExtra(EXTRA_CONFIDENCE_PERCENT, confidencePercent)
                putExtra(EXTRA_EXPLANATION, explanation)
                putStringArrayListExtra(EXTRA_SOURCES, ArrayList(sources))
            }
        }
    }
}

@Composable
private fun ClaimDetailScreen(
    claimIndex: Int,
    totalClaims: Int,
    claimText: String,
    verdictRaw: String,
    confidencePercent: Int,
    explanation: String,
    sources: List<String>,
    onBack: () -> Unit,
) {
    val verdictLabel = verdictRaw.ifBlank { VERDICT_UNVERIFIED }
    val verdictColor = detailVerdictColor(verdictLabel)

    Scaffold { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(AppSpacing.md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.sm),
        ) {
            item {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(AppSpacing.xs),
                ) {
                    IconButton(onClick = onBack) {
                        Icon(
                            painter = painterResource(id = R.drawable.ic_back_arrow_thin),
                            contentDescription = "Back",
                        )
                    }
                    Text(
                        text = "Claim $claimIndex of $totalClaims",
                        style = MaterialTheme.typography.headlineMedium,
                    )
                }
            }

            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 84.dp, max = 220.dp),
                    shape = RoundedCornerShape(18.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                ) {
                    Text(
                        text = claimText,
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.padding(AppSpacing.md),
                    )
                }
            }

            item {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(AppSpacing.sm),
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Card(
                        modifier = Modifier,
                        shape = RoundedCornerShape(999.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = verdictColor.copy(alpha = 0.16f),
                        ),
                    ) {
                        Text(
                            text = verdictLabel,
                            color = verdictColor,
                            style = MaterialTheme.typography.labelLarge,
                            modifier = Modifier.padding(horizontal = AppSpacing.md, vertical = AppSpacing.xs),
                        )
                    }

                    Card(
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    ) {
                        Column(
                            modifier = Modifier.padding(AppSpacing.sm),
                            verticalArrangement = Arrangement.spacedBy(AppSpacing.xs),
                        ) {
                            Text(
                                text = "${confidencePercent.coerceIn(0, 100)}% confidence",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            LinearProgressIndicator(
                                progress = { confidencePercent.coerceIn(0, 100) / 100f },
                                modifier = Modifier.fillMaxWidth(),
                                color = verdictColor,
                                trackColor = verdictColor.copy(alpha = 0.2f),
                            )
                        }
                    }
                }
            }

            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 84.dp, max = 220.dp),
                    shape = RoundedCornerShape(18.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                ) {
                    Column(
                        modifier = Modifier.padding(AppSpacing.md),
                        verticalArrangement = Arrangement.spacedBy(AppSpacing.xs),
                    ) {
                        Text(
                            text = "Explanation",
                            style = MaterialTheme.typography.titleMedium,
                        )
                        Text(
                            text = explanation.ifBlank { "No explanation available." },
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 10,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }

            item {
                Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.xs)) {
                    Text(
                        text = "Sources",
                        style = MaterialTheme.typography.titleLarge,
                    )
                    Text(
                        text = "Tap the given link to read the source yourself",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            if (sources.isEmpty()) {
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(14.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    ) {
                        Text(
                            text = "No sources provided.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(AppSpacing.md),
                        )
                    }
                }
            } else {
                items(sources) { source ->
                    SourceLinkCard(source = source)
                }
            }
        }
    }
}

@Composable
private fun SourceLinkCard(source: String) {
    val uriHandler = LocalUriHandler.current
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { runCatching { uriHandler.openUri(source) } },
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(AppSpacing.md),
            horizontalArrangement = Arrangement.spacedBy(AppSpacing.sm),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                painter = painterResource(id = android.R.drawable.ic_menu_view),
                contentDescription = "Open source",
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(20.dp),
            )
            Text(
                text = source,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.primary,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

private fun detailVerdictColor(verdict: String): Color {
    return when (verdict) {
        VERDICT_FALSE -> Color(0xFFE53935)
        VERDICT_MOSTLY_FALSE -> Color(0xFFFF7043)
        VERDICT_UNVERIFIED -> Color(0xFFFFB300)
        VERDICT_MOSTLY_TRUE -> Color(0xFF66BB6A)
        VERDICT_TRUE -> Color(0xFF2E7D32)
        else -> Color(0xFF9E9E9E)
    }
}

private const val VERDICT_TRUE = "true"
private const val VERDICT_MOSTLY_TRUE = "mostly true"
private const val VERDICT_UNVERIFIED = "unverified"
private const val VERDICT_MOSTLY_FALSE = "mostly false"
private const val VERDICT_FALSE = "false"
