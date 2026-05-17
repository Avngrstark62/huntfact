package com.abhijeet.huntfact.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.abhijeet.huntfact.ui.theme.AppSpacing
import com.abhijeet.huntfact.ui.theme.ErrorRed
import com.abhijeet.huntfact.ui.theme.Neutral
import com.abhijeet.huntfact.ui.theme.OnErrorRed
import com.abhijeet.huntfact.ui.theme.OnNeutral
import com.abhijeet.huntfact.ui.theme.OnSuccess
import com.abhijeet.huntfact.ui.theme.OnWarning
import com.abhijeet.huntfact.ui.theme.Success
import com.abhijeet.huntfact.ui.theme.Warning

@Composable
fun SectionTitle(text: String, modifier: Modifier = Modifier) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleLarge,
        modifier = modifier,
    )
}

@Composable
fun InfoCard(
    title: String,
    value: String,
    subtitle: String? = null,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(AppSpacing.sm),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.xs),
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                text = value,
                style = MaterialTheme.typography.titleLarge,
            )
            if (!subtitle.isNullOrBlank()) {
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
fun StatusChip(status: String, modifier: Modifier = Modifier) {
    val label = status.replaceFirstChar { it.uppercase() }
    val colors = when (status.lowercase()) {
        "completed" -> Pair(Success, OnSuccess)
        "failed" -> Pair(ErrorRed, OnErrorRed)
        "running", "processing", "pending" -> Pair(Warning, OnWarning)
        else -> Pair(Neutral, OnNeutral)
    }
    SimpleChip(
        text = label,
        backgroundColor = colors.first,
        contentColor = colors.second,
        modifier = modifier,
    )
}

@Composable
fun VerdictChip(verdict: String, modifier: Modifier = Modifier) {
    val normalized = verdict.lowercase().trim()
    val label = when (normalized) {
        "true" -> "True"
        "false" -> "False"
        "partially true" -> "Partially True"
        else -> "No Verdict"
    }
    val colors = when (normalized) {
        "true" -> Pair(Success, OnSuccess)
        "false" -> Pair(ErrorRed, OnErrorRed)
        "partially true" -> Pair(Warning, OnWarning)
        else -> Pair(Neutral, OnNeutral)
    }
    SimpleChip(
        text = label,
        backgroundColor = colors.first,
        contentColor = colors.second,
        modifier = modifier,
    )
}

@Composable
private fun SimpleChip(
    text: String,
    backgroundColor: Color,
    contentColor: Color,
    modifier: Modifier = Modifier,
) {
    Text(
        text = text,
        color = contentColor,
        style = MaterialTheme.typography.labelMedium,
        modifier = modifier
            .background(backgroundColor, RoundedCornerShape(999.dp))
            .padding(horizontal = AppSpacing.sm, vertical = AppSpacing.xs),
    )
}

@Composable
fun EmptyStateView(
    title: String,
    subtitle: String,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        shape = RoundedCornerShape(AppSpacing.sm),
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.md),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.xs),
        ) {
            Text(text = title, style = MaterialTheme.typography.titleMedium)
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
fun KeyValueRow(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.labelLarge,
        )
    }
}
