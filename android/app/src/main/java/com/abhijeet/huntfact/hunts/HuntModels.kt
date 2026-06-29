package com.abhijeet.huntfact.hunts

import com.abhijeet.huntfact.network.HuntDto

data class HuntClaimRow(
    val claim: String,
    val verdict: String,
    val confidence: Int,
    val sources: List<String>,
    val explanation: String,
)

data class HuntItem(
    val id: Int,
    val videoLink: String,
    val title: String?,
    val status: String,
    val result: List<HuntClaimRow>?,
    val thumbnailUrl: String?,
    val caption: String?,
    val creatorHandle: String?,
    val platform: String,
    val errorMessage: String?,
    val createdAt: String?,
    val updatedAt: String?,
    val completedAt: String?,
    val trustScore: Int?,
    val summary: String?,
)

fun HuntDto.toHuntItem(): HuntItem {
    return HuntItem(
        id = id,
        videoLink = video_link,
        title = title,
        status = status,
        result = result?.map { row ->
            HuntClaimRow(
                claim = row.claim,
                verdict = row.verdict,
                confidence = row.confidence.coerceIn(0, 100),
                sources = row.sources,
                explanation = row.explanation,
            )
        },
        thumbnailUrl = thumbnail_url,
        caption = caption,
        creatorHandle = creator_handle,
        platform = platform,
        errorMessage = error_message,
        createdAt = createdAt,
        updatedAt = updatedAt,
        completedAt = completedAt,
        trustScore = trust_score?.coerceIn(0, 100),
        summary = summary,
    )
}
