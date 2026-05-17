package com.abhijeet.huntfact.ui.resources

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.abhijeet.huntfact.ui.components.EmptyStateView
import com.abhijeet.huntfact.ui.components.InfoCard
import com.abhijeet.huntfact.ui.components.SectionTitle
import com.abhijeet.huntfact.ui.theme.AppSpacing

@Composable
fun ResourcesScreen(
    uiState: ResourcesUiState,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = AppSpacing.md, vertical = AppSpacing.sm),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.sm),
    ) {
        SectionTitle("Resources")

        if (uiState.isLoading) {
            Text(
                text = "Loading resource summary...",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            return
        }

        val summary = uiState.summary
        if (summary != null) {
            InfoCard(
                title = "Credits left",
                value = "${summary.creditsRemaining} / ${summary.creditsTotal}",
                subtitle = summary.planName,
            )
            InfoCard(
                title = "Hunts used this month",
                value = summary.huntsUsedThisMonth.toString(),
                subtitle = summary.renewalDate,
            )
        }

        Spacer(modifier = Modifier.height(AppSpacing.xs))
        EmptyStateView(
            title = "Coming soon",
            subtitle = "Full resource management actions will be enabled once backend endpoints are available.",
        )
    }
}
