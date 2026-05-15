package com.example.android.network

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.POST

data class StartHuntRequest(
    val video_link: String,
    val cdn_link: String,
    val fcm_token: String,
    val thumbnail_url: String? = null,
    val caption: String? = null,
    val creator_handle: String? = null,
    val platform: String = "instagram",
)

data class StartHuntResponse(
    val success: Boolean,
    val message: String? = null,
    val hunt_id: Int,
    val status: String,
    val result: String? = null,
)

data class HuntDto(
    val id: Int,
    val video_link: String,
    val status: String,
    val result: String? = null,
    val thumbnail_url: String? = null,
    val caption: String? = null,
    val creator_handle: String? = null,
    val platform: String = "instagram",
    val error_message: String? = null,
    @SerializedName("created_at") val createdAt: String? = null,
    @SerializedName("updated_at") val updatedAt: String? = null,
    @SerializedName("completed_at") val completedAt: String? = null,
)

interface ApiService {
    @POST("/start-hunt")
    suspend fun startHunt(@Body request: StartHuntRequest): StartHuntResponse

    @GET("/hunts")
    suspend fun getHunts(): List<HuntDto>

    @GET("/hunts/{hunt_id}")
    suspend fun getHunt(@Path("hunt_id") huntId: Int): HuntDto
}

