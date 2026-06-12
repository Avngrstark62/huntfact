package com.abhijeet.huntfact.hunts

import com.abhijeet.huntfact.network.HuntDto

private const val DEFAULT_TRUST_SCORE = 47
private const val DEFAULT_SUMMARY = "This government is resonsible for increasing the price of petrol by 10 rupees overnight. This government is resonsible for increasing the price of petrol by 10 rupees overnight. This government is resonsible for increasing the price of petrol by 10 rupees overnight. This government is resonsible for increasing the price of petrol by 10 rupees overnight. This government is resonsible for increasing the price of petrol by 10 rupees overnight."
private const val DEFAULT_TITLE = "This government is resonsible for increasing the price of petrol by 10 rupees overnight."

data class HuntItem(
    val id: Int,
    val videoLink: String,
    val title: String? = DEFAULT_TITLE,
    val status: String,
    val result: String?,
    val thumbnailUrl: String?,
    val caption: String?,
    val creatorHandle: String?,
    val platform: String,
    val errorMessage: String?,
    val createdAt: String?,
    val updatedAt: String?,
    val completedAt: String?,
    val trustScore: Int = DEFAULT_TRUST_SCORE,
    val summary: String? = DEFAULT_SUMMARY,
)

fun HuntDto.toHuntItem(): HuntItem {
    return HuntItem(
        id = id,
        videoLink = video_link,
        title = DEFAULT_TITLE,
        status = status,
        result = result,
        thumbnailUrl = thumbnail_url,
        caption = caption,
        creatorHandle = creator_handle,
        platform = platform,
        errorMessage = error_message,
        createdAt = createdAt,
        updatedAt = updatedAt,
        completedAt = completedAt,
        trustScore = DEFAULT_TRUST_SCORE,
        summary = DEFAULT_SUMMARY,
    )
}
