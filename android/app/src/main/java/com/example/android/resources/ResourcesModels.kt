package com.example.android.resources

data class ResourceSummary(
    val creditsRemaining: Int,
    val creditsTotal: Int,
    val huntsUsedThisMonth: Int,
    val planName: String,
    val renewalDate: String,
)
