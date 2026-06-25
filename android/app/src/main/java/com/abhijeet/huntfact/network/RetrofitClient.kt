package com.abhijeet.huntfact.network

import android.content.Context
import com.abhijeet.huntfact.BuildConfig
import com.abhijeet.huntfact.utils.AuthSessionManager
import com.google.firebase.Firebase
import com.google.firebase.crashlytics.crashlytics
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
        Firebase.crashlytics.log("RetrofitClient.getApiService: started")
        if (context != null) {
            appContext = context.applicationContext
        }
        if (apiService == null) {
            Firebase.crashlytics.log("RetrofitClient.getApiService: creating new ApiService for baseUrl=$baseUrl")
            val okHttpClient = OkHttpClient.Builder()
                .addInterceptor { chain ->
                    val request = chain.request()
                    Firebase.crashlytics.log(
                        "RetrofitClient.interceptor: request ${request.method} ${request.url.encodedPath}"
                    )
                    val token = AuthSessionManager.getAccessToken(appContext)
                    val requestBuilder = request.newBuilder()
                    if (!token.isNullOrBlank()) {
                        requestBuilder.addHeader("Authorization", "Bearer $token")
                    }
                    val response = chain.proceed(requestBuilder.build())
                    Firebase.crashlytics.log(
                        "RetrofitClient.interceptor: response status=${response.code} for ${request.method} ${request.url.encodedPath}"
                    )
                    if (response.code == 401 || response.code == 403) {
                        Firebase.crashlytics.log("RetrofitClient.interceptor: auth rejected, invalidating local session")
                        Firebase.crashlytics.recordException(
                            Exception("Auth rejected by API with status=${response.code}")
                        )
                        AuthSessionManager.invalidateLocalSession(appContext)
                    }
                    response
                }
                .build()

            val retrofit = Retrofit.Builder()
                .baseUrl(if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/")
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
            apiService = retrofit.create(ApiService::class.java)
            Firebase.crashlytics.log("RetrofitClient.getApiService: ApiService created successfully")
        }
        Firebase.crashlytics.log("RetrofitClient.getApiService: returning ApiService instance")
        return apiService!!
    }
}
