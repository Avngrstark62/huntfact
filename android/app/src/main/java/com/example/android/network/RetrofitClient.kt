package com.example.android.network

import com.example.android.utils.AuthSessionManager
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {
    private var apiService: ApiService? = null

    fun getApiService(baseUrl: String = "http://172.23.6.89:8000"): ApiService {
        if (apiService == null) {
            val okHttpClient = OkHttpClient.Builder()
                .addInterceptor { chain ->
                    val token = AuthSessionManager.getAccessToken()
                    val requestBuilder = chain.request().newBuilder()
                    if (!token.isNullOrBlank()) {
                        requestBuilder.addHeader("Authorization", "Bearer $token")
                    }
                    chain.proceed(requestBuilder.build())
                }
                .build()

            val retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
            apiService = retrofit.create(ApiService::class.java)
        }
        return apiService!!
    }
}
