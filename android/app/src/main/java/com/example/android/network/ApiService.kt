package com.example.android.network

import retrofit2.http.Body
import retrofit2.http.POST

data class FactCheckRequest(
    val cdn_url: String,
    val fcm_token: String
)

data class FactCheckResponse(
    val success: Boolean,
    val message: String? = null
)

interface ApiService {
    @POST("/fact-check")
    suspend fun submitFactCheck(@Body request: FactCheckRequest): FactCheckResponse
}
