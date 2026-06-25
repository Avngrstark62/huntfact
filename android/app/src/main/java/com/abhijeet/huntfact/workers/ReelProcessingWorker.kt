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
import com.google.firebase.Firebase
import com.google.firebase.crashlytics.crashlytics
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.tasks.await
import retrofit2.HttpException

class ReelProcessingWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        Firebase.crashlytics.log("ReelProcessingWorker.doWork: started jobId=$id")
        return try {
            val reelUrl = inputData.getString("reel_url")
            
            if (reelUrl.isNullOrEmpty()) {
                Log.e(TAG, "❌ Invalid reel URL provided")
                Firebase.crashlytics.log("ReelProcessingWorker.doWork: missing reel_url input")
                Firebase.crashlytics.recordException(Exception("ReelProcessingWorker input reel_url is empty"))
                showErrorNotification()
                Firebase.crashlytics.log("ReelProcessingWorker.doWork: returning failure due to invalid input")
                return Result.failure()
            }

            Log.d(TAG, "🔍 Starting to process reel: $reelUrl")
            Firebase.crashlytics.log("ReelProcessingWorker.doWork: processing reel URL")

            Log.d(TAG, "📹 Extracting CDN URL from Instagram...")
            Firebase.crashlytics.log("ReelProcessingWorker.doWork: extracting CDN URL")
            val cdnUrl = ReelExtractor.extractCdnUrl(reelUrl)
            if (cdnUrl.isNullOrEmpty()) {
                Log.e(TAG, "❌ Failed to extract CDN URL from shared URL")
                Firebase.crashlytics.log("ReelProcessingWorker.doWork: CDN extraction failed")
                Firebase.crashlytics.recordException(Exception("CDN extraction failed for shared reel URL"))
                showErrorNotification()
                Firebase.crashlytics.log("ReelProcessingWorker.doWork: returning failure due to CDN extraction")
                return Result.failure()
            }

            Log.d(TAG, "✅ Successfully extracted CDN URL")
            Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            Log.d(TAG, "🎬 CDN VIDEO URL: $cdnUrl")
            Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            val accessToken = AuthSessionManager.getAccessToken(applicationContext)
            if (accessToken.isNullOrBlank()) {
                Log.e(TAG, "❌ Missing Supabase session, user needs to sign in again")
                Firebase.crashlytics.log("ReelProcessingWorker.doWork: missing auth session")
                Firebase.crashlytics.recordException(Exception("Missing auth session in ReelProcessingWorker"))
                showSignInRequiredNotification()
                Firebase.crashlytics.log("ReelProcessingWorker.doWork: returning failure due to missing auth")
                return Result.failure()
            }

            // Get FCM token
            Log.d(TAG, "🔐 Fetching FCM token...")
            Firebase.crashlytics.log("ReelProcessingWorker.doWork: requesting FCM token")
            val fcmToken = try {
                FirebaseMessaging.getInstance().token.await()
            } catch (exception: Exception) {
                Log.e(TAG, "❌ Failed to get FCM token: ${exception.message}")
                Firebase.crashlytics.log("ReelProcessingWorker.doWork: failed to fetch FCM token")
                Firebase.crashlytics.recordException(exception)
                showErrorNotification()
                Firebase.crashlytics.log("ReelProcessingWorker.doWork: returning failure due to FCM token error")
                return Result.failure()
            }
            Log.d(TAG, "✅ FCM token obtained: ${fcmToken.take(20)}...")
            Firebase.crashlytics.log("ReelProcessingWorker.doWork: FCM token fetched successfully")

            // Call backend API
            Log.d(TAG, "📤 Sending reel to HuntFact backend...")
            Firebase.crashlytics.log("ReelProcessingWorker.doWork: preparing start-hunt request")
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
                Firebase.crashlytics.log("ReelProcessingWorker.doWork: calling POST /start-hunt")
                val response = apiService.startHunt(request)
                Firebase.crashlytics.log(
                    "ReelProcessingWorker.doWork: start-hunt response success=${response.success} huntId=${response.hunt_id}"
                )
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
                    Firebase.crashlytics.log("ReelProcessingWorker.doWork: persisting huntId=${response.hunt_id}")
                    HuntRepository(applicationContext).upsertLocal(huntItem)
                    Log.d(TAG, "✅ Successfully sent to HuntFact backend!")
                    Log.d(TAG, "📨 Response: ${response.message}")
                    showSuccessNotification(
                        title = "Claim check started",
                        message = "We received your reel and started fact-checking.",
                        huntId = response.hunt_id,
                    )
                    Firebase.crashlytics.log("ReelProcessingWorker.doWork: completed successfully")
                    Result.success()
                } else {
                    Log.e(TAG, "❌ Backend API returned error: ${response.message}")
                    Firebase.crashlytics.log("ReelProcessingWorker.doWork: backend returned non-success response")
                    Firebase.crashlytics.recordException(
                        Exception("Backend start-hunt returned success=false for jobId=$id")
                    )
                    showErrorNotification()
                    Result.failure()
                }
            } catch (exception: Exception) {
                if (exception is HttpException && (exception.code() == 401 || exception.code() == 403)) {
                    Log.e(TAG, "❌ Backend rejected auth token: HTTP ${exception.code()}")
                    Firebase.crashlytics.log(
                        "ReelProcessingWorker.doWork: auth rejected by backend status=${exception.code()}"
                    )
                    Firebase.crashlytics.recordException(exception)
                    showSignInRequiredNotification()
                    Firebase.crashlytics.log("ReelProcessingWorker.doWork: returning failure due to auth rejection")
                    return Result.failure()
                }
                Log.e(TAG, "❌ API request failed: ${exception.message}", exception)
                Firebase.crashlytics.log("ReelProcessingWorker.doWork: backend request failed")
                Firebase.crashlytics.recordException(exception)
                showErrorNotification()
                Result.failure()
            }
        } catch (exception: Exception) {
            Log.e(TAG, "❌ Unexpected error in worker: ${exception.message}", exception)
            Firebase.crashlytics.log("ReelProcessingWorker.doWork: unexpected top-level exception")
            Firebase.crashlytics.recordException(exception)
            showErrorNotification()
            Result.failure()
        }
    }

    private fun showSuccessNotification(title: String, message: String, huntId: Int) {
        Firebase.crashlytics.log("ReelProcessingWorker.showSuccessNotification: started huntId=$huntId")
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
        Firebase.crashlytics.log("ReelProcessingWorker.showSuccessNotification: completed")
    }

    private fun showErrorNotification() {
        Firebase.crashlytics.log("ReelProcessingWorker.showErrorNotification: started")
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
        Firebase.crashlytics.log("ReelProcessingWorker.showErrorNotification: completed")
    }

    private fun showSignInRequiredNotification() {
        Firebase.crashlytics.log("ReelProcessingWorker.showSignInRequiredNotification: started")
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
        Firebase.crashlytics.log("ReelProcessingWorker.showSignInRequiredNotification: completed")
    }

    companion object {
        private const val TAG = "ReelProcessingWorker"
        private const val SUCCESS_NOTIFICATION_ID = 101
        private const val ERROR_NOTIFICATION_ID = 102
        private const val SIGN_IN_REQUIRED_NOTIFICATION_ID = 103
    }
}
