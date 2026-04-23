package com.example.android.workers

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.example.android.extraction.ReelExtractor
import com.example.android.network.RetrofitClient
import com.example.android.network.StartHuntRequest
import com.example.android.utils.AuthSessionManager
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
                Log.e(TAG, "❌ Invalid reel URL provided")
                showErrorNotification()
                return Result.failure()
            }

            Log.d(TAG, "🔍 Starting to process reel: $reelUrl")

            // Extract CDN URL
            Log.d(TAG, "📹 Extracting CDN URL from Instagram...")
            val cdnUrl = ReelExtractor.extractCdnUrl(reelUrl)
            if (cdnUrl.isNullOrEmpty()) {
                Log.e(TAG, "❌ Failed to extract CDN URL from reel")
                showErrorNotification()
                return Result.retry()
            }

            Log.d(TAG, "✅ Successfully extracted CDN URL")
            Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            Log.d(TAG, "🎬 CDN VIDEO URL: $cdnUrl")
            Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            if (!AuthSessionManager.hasValidSession()) {
                Log.e(TAG, "❌ Missing Supabase session, user needs to sign in again")
                showSignInRequiredNotification()
                return Result.failure()
            }

            // Get FCM token
            Log.d(TAG, "🔐 Fetching FCM token...")
            val fcmToken = try {
                FirebaseMessaging.getInstance().token.await()
            } catch (e: Exception) {
                Log.e(TAG, "❌ Failed to get FCM token: ${e.message}")
                showErrorNotification()
                return Result.retry()
            }
            Log.d(TAG, "✅ FCM token obtained: ${fcmToken.take(20)}...")

            // Call backend API
            Log.d(TAG, "📤 Sending reel to HuntFact backend...")
            val apiService = RetrofitClient.getApiService()
            val cleanedReelUrl = ReelExtractor.cleanInstagramUrl(reelUrl)
            val request = StartHuntRequest(
                video_link = cleanedReelUrl,
                cdn_link = cdnUrl,
                fcm_token = fcmToken
            )

            return try {
                val response = apiService.startHunt(request)
                if (response.success) {
                    Log.d(TAG, "✅ Successfully sent to HuntFact backend!")
                    Log.d(TAG, "📨 Response: ${response.message}")
                    showSuccessNotification("Sent to HuntFact", "Your reel is being fact-checked!")
                    Result.success()
                } else {
                    Log.e(TAG, "❌ Backend API returned error: ${response.message}")
                    showErrorNotification()
                    Result.retry()
                }
            } catch (e: Exception) {
                Log.e(TAG, "❌ API request failed: ${e.message}", e)
                showErrorNotification()
                Result.retry()
            }
        } catch (e: Exception) {
            Log.e(TAG, "❌ Unexpected error in worker: ${e.message}", e)
            showErrorNotification()
            Result.retry()
        }
    }

    private fun showSuccessNotification(title: String, message: String) {
        val notificationManager = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = "reel_success_channel"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Reel Processing Success",
                NotificationManager.IMPORTANCE_DEFAULT
            )
            notificationManager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(applicationContext, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(message)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(SUCCESS_NOTIFICATION_ID, notification)
        Log.d(TAG, "📲 Success notification shown: $title - $message")
    }

    private fun showErrorNotification() {
        val notificationManager = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = "reel_error_channel"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Reel Processing Error",
                NotificationManager.IMPORTANCE_HIGH
            )
            notificationManager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(applicationContext, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("Error Processing Reel")
            .setContentText("An error occurred while processing your reel. Please try again.")
            .setAutoCancel(true)
            .build()

        notificationManager.notify(ERROR_NOTIFICATION_ID, notification)
        Log.e(TAG, "📲 Error notification shown: Generic error message")
    }

    private fun showSignInRequiredNotification() {
        val notificationManager = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = "reel_auth_channel"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Authentication Required",
                NotificationManager.IMPORTANCE_HIGH
            )
            notificationManager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(applicationContext, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("Sign in required")
            .setContentText("Please sign in with Google again to continue fact-checking reels.")
            .setAutoCancel(true)
            .build()

        notificationManager.notify(SIGN_IN_REQUIRED_NOTIFICATION_ID, notification)
        Log.e(TAG, "📲 Error notification shown: Sign-in required")
    }

    companion object {
        private const val TAG = "ReelProcessingWorker"
        private const val SUCCESS_NOTIFICATION_ID = 101
        private const val ERROR_NOTIFICATION_ID = 102
        private const val SIGN_IN_REQUIRED_NOTIFICATION_ID = 103
    }
}
