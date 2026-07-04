package com.abhijeet.huntfact.network

import android.content.Context
import com.abhijeet.huntfact.BuildConfig
import com.abhijeet.huntfact.utils.AuthSessionManager
import okhttp3.OkHttpClient
import kotlinx.coroutines.runBlocking
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {
    private var apiService: ApiService? = null
    private var appContext: Context? = null
    private const val AUTH_RETRY_HEADER = "X-HuntFact-Auth-Retry"

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
                    val originalRequest = chain.request()
                    val token = AuthSessionManager.getAccessToken(appContext)
                    val requestBuilder = originalRequest.newBuilder()
                    if (!token.isNullOrBlank()) {
                        requestBuilder.addHeader("Authorization", "Bearer $token")
                    }
                    val response = chain.proceed(requestBuilder.build())
                    if (response.code == 401 || response.code == 403) {
                        val alreadyRetried = originalRequest.header(AUTH_RETRY_HEADER) == "1"
                        if (alreadyRetried) {
                            AuthSessionManager.invalidateLocalSession(appContext)
                            response
                        } else {
                            val refreshed = runBlocking {
                                AuthSessionManager.attemptSessionRefresh(appContext)
                            }
                            if (!refreshed) {
                                AuthSessionManager.invalidateLocalSession(appContext)
                                response
                            } else {
                                response.close()
                                val refreshedToken = AuthSessionManager.getAccessToken(appContext)
                                val retryRequestBuilder = originalRequest.newBuilder()
                                    .header(AUTH_RETRY_HEADER, "1")
                                    .removeHeader("Authorization")
                                if (!refreshedToken.isNullOrBlank()) {
                                    retryRequestBuilder.addHeader("Authorization", "Bearer $refreshedToken")
                                }
                                val retryResponse = chain.proceed(retryRequestBuilder.build())
                                if (retryResponse.code == 401 || retryResponse.code == 403) {
                                    AuthSessionManager.invalidateLocalSession(appContext)
                                }
                                retryResponse
                            }
                        }
                    } else {
                        response
                    }
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
