package com.abhijeet.huntfact.network

import android.content.Context
import com.abhijeet.huntfact.BuildConfig
import com.abhijeet.huntfact.utils.AuthSessionManager
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {
    private var apiService: ApiService? = null
    private var appContext: Context? = null

    fun getApiService(
        baseUrl: String = BuildConfig.BACKEND_BASE_URL,
        context: Context? = null,
    ): ApiService {
        if (context != null) {
            appContext = context.applicationContext
        }
        if (apiService == null) {
            val okHttpClient = OkHttpClient.Builder()
                .addInterceptor { chain ->
                    val token = AuthSessionManager.getAccessToken(appContext)
                    val requestBuilder = chain.request().newBuilder()
                    if (!token.isNullOrBlank()) {
                        requestBuilder.addHeader("Authorization", "Bearer $token")
                    }
                    chain.proceed(requestBuilder.build())
                }
                .build()

            val retrofit = Retrofit.Builder()
                .baseUrl(if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/")
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
            apiService = retrofit.create(ApiService::class.java)
        }
        return apiService!!
    }
}
