package com.example.factchecksharer.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.example.factchecksharer.api.ApiClient
import com.example.factchecksharer.api.FactCheckRequest
import com.example.factchecksharer.extractor.ReelExtractor
import com.example.factchecksharer.fcm.FcmTokenManager

class ReelProcessingWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            val reelUrl = inputData.getString("reel_url") ?: return Result.failure()

            // Extract CDN URL
            val cdnUrl = ReelExtractor.extractCdnUrl(reelUrl)
                ?: return Result.retry()

            // Get FCM token
            val fcmToken = FcmTokenManager.getToken()
                ?: return Result.retry()

            // Send to backend
            val request = FactCheckRequest(cdn_url = cdnUrl, fcm_token = fcmToken)
            ApiClient.apiService.submitFactCheck(request)

            Result.success()
        } catch (e: Exception) {
            e.printStackTrace()
            Result.retry()
        }
    }
}
