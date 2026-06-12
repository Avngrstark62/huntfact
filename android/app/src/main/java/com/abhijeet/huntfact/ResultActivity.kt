package com.abhijeet.huntfact

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.ComponentActivity
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.clickable
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.FilterList
import androidx.compose.material.icons.rounded.Link
import androidx.compose.material.icons.rounded.ManageSearch
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.style.TextOverflow
import androidx.lifecycle.lifecycleScope
import com.abhijeet.huntfact.hunts.HuntRepository
import com.abhijeet.huntfact.ui.components.EmptyStateView
import com.abhijeet.huntfact.ui.components.HeroHeaderCard
import com.abhijeet.huntfact.ui.components.IconMetaRow
import com.abhijeet.huntfact.ui.components.SectionTitle
import com.abhijeet.huntfact.ui.components.StatusChip
import com.abhijeet.huntfact.ui.components.VerdictChip
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
    val sources: List<String>,
    val explanation: String,
)

@Composable
private fun ResultScreen(hunt: com.abhijeet.huntfact.hunts.HuntItem) {
    val allRows = remember(hunt.result) { parseRows(hunt.result) }
    var selectedVerdict by remember { mutableStateOf("all") }
    var searchTerm by remember { mutableStateOf("") }

    val filteredRows = remember(allRows, selectedVerdict, searchTerm) {
        allRows.filter { row ->
            val verdictMatch = selectedVerdict == "all" || row.verdict.equals(selectedVerdict, ignoreCase = true)
            val searchMatch = searchTerm.isBlank() || row.claim.contains(searchTerm, ignoreCase = true)
            verdictMatch && searchMatch
        }
    }

    Scaffold { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(AppSpacing.md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.sm),
        ) {
            HeroHeaderCard(
                title = "Result",
                subtitle = "Hunt #${hunt.id}",
                statsContent = {
                    StatusChip(status = hunt.status)
                },
            )
            IconMetaRow(
                icon = Icons.Rounded.Link,
                text = hunt.caption?.takeIf { it.isNotBlank() } ?: hunt.videoLink,
            )

            if (hunt.result.isNullOrBlank()) {
                EmptyStateView(
                    title = "Result not ready",
                    subtitle = "This hunt is still processing. Please check again shortly.",
                )
                return@Column
            }

            Card(
                shape = RoundedCornerShape(14.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            ) {
                Column(
                    modifier = Modifier.padding(AppSpacing.md),
                    verticalArrangement = Arrangement.spacedBy(AppSpacing.sm),
                ) {
                    Row(horizontalArrangement = Arrangement.spacedBy(AppSpacing.xs)) {
                        Icon(
                            imageVector = Icons.Rounded.ManageSearch,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                        )
                        Text("Search and filters", style = MaterialTheme.typography.titleMedium)
                    }
                    OutlinedTextField(
                        value = searchTerm,
                        onValueChange = { searchTerm = it },
                        label = { Text("Search claims") },
                        modifier = Modifier.fillMaxWidth(),
                    )

                    VerdictFilterRow(
                        selected = selectedVerdict,
                        onSelect = { selectedVerdict = it },
                    )
                }
            }

            if (filteredRows.isEmpty()) {
                EmptyStateView(
                    title = "No matching results",
                    subtitle = "Try changing filters or search text.",
                )
                return@Column
            }

            LazyColumn(verticalArrangement = Arrangement.spacedBy(AppSpacing.sm)) {
                items(filteredRows) { row ->
                    ClaimRowCard(row = row)
                }
            }
        }
    }
}

@Composable
private fun VerdictFilterRow(
    selected: String,
    onSelect: (String) -> Unit,
) {
    val values = listOf("all", "true", "false", "partially true", "no verdict")
    Row(horizontalArrangement = Arrangement.spacedBy(AppSpacing.xs)) {
        values.forEach { verdict ->
            val label = if (verdict == "all") "All" else verdict.replaceFirstChar { it.uppercase() }
            val isSelected = selected == verdict
            val containerColor by animateColorAsState(
                targetValue = if (isSelected) {
                    MaterialTheme.colorScheme.primaryContainer
                } else {
                    MaterialTheme.colorScheme.surfaceVariant
                },
                animationSpec = tween(durationMillis = 120),
                label = "filter-chip-bg",
            )
            Card(
                modifier = Modifier.clickable { onSelect(verdict) },
                colors = CardDefaults.cardColors(
                    containerColor = containerColor
                ),
                shape = RoundedCornerShape(999.dp),
            ) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(AppSpacing.xs),
                    modifier = Modifier.padding(horizontal = AppSpacing.sm, vertical = AppSpacing.xs),
                ) {
                    if (isSelected) {
                        Icon(
                            imageVector = Icons.Rounded.FilterList,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                        )
                    }
                    Text(
                        text = label,
                        style = MaterialTheme.typography.labelMedium,
                    )
                }
            }
        }
    }
}

@Composable
private fun ClaimRowCard(row: ClaimRow) {
    val uriHandler = LocalUriHandler.current
    var expanded by remember { mutableStateOf(false) }

    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.xs),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = row.claim,
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.weight(1f),
                )
                Spacer(modifier = Modifier.width(AppSpacing.xs))
                VerdictChip(verdict = row.verdict)
            }

            Box(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = row.explanation,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = if (expanded) Int.MAX_VALUE else 3,
                    overflow = TextOverflow.Ellipsis,
                )
                if (!expanded && row.explanation.length > 140) {
                    Spacer(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(36.dp)
                            .align(androidx.compose.ui.Alignment.BottomCenter)
                            .background(
                                brush = Brush.verticalGradient(
                                    colors = listOf(
                                        MaterialTheme.colorScheme.surface.copy(alpha = 0f),
                                        MaterialTheme.colorScheme.surface,
                                    ),
                                ),
                            ),
                    )
                }
            }
            if (row.explanation.length > 140) {
                Text(
                    text = if (expanded) "Show less" else "Read more",
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.clickable { expanded = !expanded },
                )
            }

            if (row.sources.isNotEmpty()) {
                Text("Sources", style = MaterialTheme.typography.labelLarge)
                row.sources.forEach { source ->
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(AppSpacing.xs),
                        modifier = Modifier.clickable {
                            runCatching { uriHandler.openUri(source) }
                        },
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.Link,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                        )
                        Text(
                            text = source,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.primary,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }
        }
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
                sources = sources,
                explanation = explanation.ifBlank { "No explanation provided." },
            )
        }
    }.getOrElse {
        listOf(
            ClaimRow(
                claim = "Result",
                verdict = "no verdict",
                sources = emptyList(),
                explanation = raw.trim(),
            )
        )
    }
}

private fun com.google.gson.JsonElement?.safeAsString(): String {
    return runCatching { this?.asString?.trim().orEmpty() }.getOrDefault("")
}
