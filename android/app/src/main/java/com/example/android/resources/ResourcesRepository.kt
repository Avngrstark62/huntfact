package com.example.android.resources

interface ResourcesRepository {
    suspend fun getSummary(): ResourceSummary
}

class StubResourcesRepository : ResourcesRepository {
    override suspend fun getSummary(): ResourceSummary {
        return ResourceSummary(
            creditsRemaining = 12,
            creditsTotal = 20,
            huntsUsedThisMonth = 8,
            planName = "Starter",
            renewalDate = "Next renewal: Coming soon",
        )
    }
}
