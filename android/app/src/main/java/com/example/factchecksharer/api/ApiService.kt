package com.example.factchecksharer.api

import retrofit2.http.POST
import retrofit2.http.Body

data class FactCheckRequest(
    val cdn_url: String,
    val fcm_token: String
)

interface ApiService {
    @POST("/fact-check")
    suspend fun submitFactCheck(@Body request: FactCheckRequest): Unit
}
