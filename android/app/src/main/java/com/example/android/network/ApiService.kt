package com.example.android.network

import retrofit2.http.Body
import retrofit2.http.POST

data class StartHuntRequest(
    val video_link: String,
    val cdn_link: String,
    val fcm_token: String
)

data class StartHuntResponse(
    val success: Boolean,
    val message: String? = null,
    val result: String? = null
)

interface ApiService {
    @POST("/start-hunt")
    suspend fun startHunt(@Body request: StartHuntRequest): StartHuntResponse
}

