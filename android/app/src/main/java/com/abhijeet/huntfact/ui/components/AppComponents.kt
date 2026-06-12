package com.abhijeet.huntfact.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.abhijeet.huntfact.ui.theme.AccentGradientEnd
import com.abhijeet.huntfact.ui.theme.AccentGradientStart
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
fun HeroHeaderCard(
    title: String,
    subtitle: String,
    modifier: Modifier = Modifier,
    statsContent: (@Composable RowScope.() -> Unit)? = null,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
    ) {
        Column(
            modifier = Modifier
                .background(
                    brush = Brush.linearGradient(
                        listOf(AccentGradientStart, AccentGradientEnd),
                    ),
                )
                .padding(AppSpacing.lg),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.sm),
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.displaySmall,
                color = MaterialTheme.colorScheme.onPrimary,
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.92f),
            )
            if (statsContent != null) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(AppSpacing.sm),
                    content = statsContent,
                )
            }
        }
    }
}

@Composable
fun InfoCard(
    title: String,
    value: String,
    subtitle: String? = null,
    modifier: Modifier = Modifier,
    accentStripColor: Color? = null,
    gradientBorder: Boolean = false,
) {
    val shape = RoundedCornerShape(14.dp)
    Card(
        modifier = modifier
            .then(
                if (gradientBorder) {
                    Modifier.border(
                        width = 1.dp,
                        brush = Brush.linearGradient(
                            listOf(AccentGradientStart.copy(alpha = 0.9f), AccentGradientEnd.copy(alpha = 0.8f)),
                        ),
                        shape = shape,
                    )
                } else {
                    Modifier
                },
            ),
        shape = shape,
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface,
        ),
    ) {
        Row {
            if (accentStripColor != null) {
                Box(
                    modifier = Modifier
                        .width(AppSpacing.xs)
                        .height(96.dp)
                        .background(accentStripColor),
                )
            }
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
                    style = MaterialTheme.typography.titleMedium,
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
}

@Composable
fun StatusChip(status: String, modifier: Modifier = Modifier) {
    val label = status.replaceFirstChar { it.uppercase() }
    val colors = when (status.lowercase()) {
        "completed" -> Pair(Success, OnSuccess)
        "failed" -> Pair(ErrorRed, OnErrorRed)
        "running", "processing", "pending" -> Pair(Warning.copy(alpha = 0.25f), Warning)
        else -> Pair(Neutral.copy(alpha = 0.2f), Neutral)
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
        "true" -> Pair(Success.copy(alpha = 0.18f), Success)
        "false" -> Pair(ErrorRed.copy(alpha = 0.16f), ErrorRed)
        "partially true" -> Pair(Warning.copy(alpha = 0.22f), Warning)
        else -> Pair(Neutral.copy(alpha = 0.2f), Neutral)
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
            .heightIn(min = 32.dp)
            .background(backgroundColor, RoundedCornerShape(999.dp))
            .padding(horizontal = AppSpacing.sm, vertical = AppSpacing.xs),
    )
}

@Composable
fun IconMetaRow(
    icon: ImageVector,
    text: String,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.xs),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            text = text,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
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
        shape = RoundedCornerShape(14.dp),
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
