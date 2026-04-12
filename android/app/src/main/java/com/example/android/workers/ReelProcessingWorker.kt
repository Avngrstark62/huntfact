package com.example.android.workers

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.example.android.extraction.ReelExtractor
import com.example.android.network.FactCheckRequest
import com.example.android.network.RetrofitClient
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.tasks.await

class ReelProcessingWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            val reelUrl = inputData.getString("reel_url")
            
            if (reelUrl.isNullOrEmpty()) {
                Log.e(TAG, "Invalid reel URL")
                return Result.failure()
            }

            Log.d(TAG, "Processing reel: $reelUrl")

            // Extract CDN URL
            val cdnUrl = ReelExtractor.extractCdnUrl(reelUrl)
            if (cdnUrl.isNullOrEmpty()) {
                Log.e(TAG, "Failed to extract CDN URL")
                return Result.retry()
            }

            Log.d(TAG, "Extracted CDN URL: $cdnUrl")

            // Get FCM token
            val fcmToken = try {
                FirebaseMessaging.getInstance().token.await()
            } catch (e: Exception) {
                Log.e(TAG, "Failed to get FCM token: ${e.message}")
                return Result.retry()
            }

            // Call backend API
            val apiService = RetrofitClient.getApiService()
            val request = FactCheckRequest(
                cdn_url = cdnUrl,
                fcm_token = fcmToken
            )

            return try {
                val response = apiService.submitFactCheck(request)
                if (response.success) {
                    Log.d(TAG, "Successfully submitted fact check request")
                    Result.success()
                } else {
                    Log.e(TAG, "API returned error: ${response.message}")
                    Result.retry()
                }
            } catch (e: Exception) {
                Log.e(TAG, "API request failed: ${e.message}")
                Result.retry()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Unexpected error in worker: ${e.message}", e)
            Result.retry()
        }
    }

    companion object {
        private const val TAG = "ReelProcessingWorker"
    }
}
