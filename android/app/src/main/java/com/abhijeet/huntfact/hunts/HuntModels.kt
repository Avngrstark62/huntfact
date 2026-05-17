package com.abhijeet.huntfact.hunts

import com.abhijeet.huntfact.network.HuntDto

data class HuntItem(
    val id: Int,
    val videoLink: String,
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
)

fun HuntDto.toHuntItem(): HuntItem {
    return HuntItem(
        id = id,
        videoLink = video_link,
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
    )
}
