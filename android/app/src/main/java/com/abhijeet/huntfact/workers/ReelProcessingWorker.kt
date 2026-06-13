package com.abhijeet.huntfact.workers

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.abhijeet.huntfact.MainActivity
import com.abhijeet.huntfact.ResultActivity
import com.abhijeet.huntfact.extraction.ReelExtractor
import com.abhijeet.huntfact.hunts.HuntItem
import com.abhijeet.huntfact.hunts.HuntRepository
import com.abhijeet.huntfact.network.RetrofitClient
import com.abhijeet.huntfact.network.StartHuntRequest
import com.abhijeet.huntfact.utils.AuthSessionManager
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.tasks.await
import retrofit2.HttpException

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

            Log.d(TAG, "📹 Extracting CDN URL from Instagram...")
            val cdnUrl = ReelExtractor.extractCdnUrl(reelUrl)
            if (cdnUrl.isNullOrEmpty()) {
                Log.e(TAG, "❌ Failed to extract CDN URL from shared URL")
                showErrorNotification()
                return Result.failure()
            }

            Log.d(TAG, "✅ Successfully extracted CDN URL")
            Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            Log.d(TAG, "🎬 CDN VIDEO URL: $cdnUrl")
            Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            val accessToken = AuthSessionManager.getAccessToken(applicationContext)
            if (accessToken.isNullOrBlank()) {
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
                return Result.failure()
            }
            Log.d(TAG, "✅ FCM token obtained: ${fcmToken.take(20)}...")

            // Call backend API
            Log.d(TAG, "📤 Sending reel to HuntFact backend...")
            val apiService = RetrofitClient.getApiService(context = applicationContext)
            val cleanedReelUrl = ReelExtractor.cleanInstagramUrl(reelUrl)
            val request = StartHuntRequest(
                video_link = cleanedReelUrl,
                cdn_link = cdnUrl,
                fcm_token = fcmToken,
                thumbnail_url = cleanedReelUrl,
                caption = cleanedReelUrl,
                creator_handle = "unknown_creator",
                platform = "instagram",
            )

            return try {
                val response = apiService.startHunt(request)
                if (response.success) {
                    val huntItem = HuntItem(
                        id = response.hunt_id,
                        videoLink = cleanedReelUrl,
                        title = response.title,
                        status = response.status,
                        result = response.result,
                        thumbnailUrl = cleanedReelUrl,
                        caption = cleanedReelUrl,
                        creatorHandle = "unknown_creator",
                        platform = "instagram",
                        errorMessage = null,
                        createdAt = null,
                        updatedAt = null,
                        completedAt = null,
                        trustScore = response.trust_score?.coerceIn(0, 100),
                        summary = response.summary,
                    )
                    HuntRepository(applicationContext).upsertLocal(huntItem)
                    Log.d(TAG, "✅ Successfully sent to HuntFact backend!")
                    Log.d(TAG, "📨 Response: ${response.message}")
                    showSuccessNotification(
                        title = "Claim check started",
                        message = "We received your reel and started fact-checking.",
                        huntId = response.hunt_id,
                    )
                    Result.success()
                } else {
                    Log.e(TAG, "❌ Backend API returned error: ${response.message}")
                    showErrorNotification()
                    Result.failure()
                }
            } catch (e: Exception) {
                if (e is HttpException && (e.code() == 401 || e.code() == 403)) {
                    Log.e(TAG, "❌ Backend rejected auth token: HTTP ${e.code()}")
                    showSignInRequiredNotification()
                    return Result.failure()
                }
                Log.e(TAG, "❌ API request failed: ${e.message}", e)
                showErrorNotification()
                Result.failure()
            }
        } catch (e: Exception) {
            Log.e(TAG, "❌ Unexpected error in worker: ${e.message}", e)
            showErrorNotification()
            Result.failure()
        }
    }

    private fun showSuccessNotification(title: String, message: String, huntId: Int) {
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

        val openIntent = Intent(applicationContext, ResultActivity::class.java).apply {
            putExtra(ResultActivity.EXTRA_HUNT_ID, huntId)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val openPendingIntent = PendingIntent.getActivity(
            applicationContext,
            huntId,
            openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val viewStatusIntent = Intent(applicationContext, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val viewStatusPendingIntent = PendingIntent.getActivity(
            applicationContext,
            5000 + huntId,
            viewStatusIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(applicationContext, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(message)
            .setContentIntent(openPendingIntent)
            .addAction(android.R.drawable.ic_menu_view, "View status", viewStatusPendingIntent)
            .setGroup("huntfact_hunts")
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
