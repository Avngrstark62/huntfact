package com.abhijeet.huntfact.workers

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.abhijeet.huntfact.MainActivity
import com.abhijeet.huntfact.ResultActivity
import com.abhijeet.huntfact.extraction.ReelExtractor
import com.abhijeet.huntfact.hunts.HuntItem
import com.abhijeet.huntfact.hunts.HuntRepository
import com.abhijeet.huntfact.hunts.toHuntItem
import com.abhijeet.huntfact.network.RetrofitClient
import com.abhijeet.huntfact.network.StartHuntRequest
import com.abhijeet.huntfact.utils.AuthSessionManager
import com.abhijeet.huntfact.utils.DebugLogger
import com.abhijeet.huntfact.utils.FcmTokenManager
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.tasks.await
import retrofit2.HttpException
import java.io.IOException
import java.net.InetAddress
import java.net.UnknownHostException

class ReelProcessingWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            val reelUrl = inputData.getString("reel_url")
            
            if (reelUrl.isNullOrEmpty()) {
                DebugLogger.e(TAG, "❌ Invalid reel URL provided")
                showFailureNotification(
                    title = "Unsupported link",
                    message = "Please share a public Instagram reel link.",
                )
                return Result.failure()
            }

            DebugLogger.d(TAG, "🔍 Starting to process reel: $reelUrl")

            DebugLogger.d(TAG, "📹 Extracting CDN URL from Instagram...")
            val cdnUrl = ReelExtractor.extractCdnUrl(reelUrl)
            if (cdnUrl.isNullOrEmpty()) {
                if (isLikelyInstagramNetworkIssue()) {
                    if (runAttemptCount < MAX_NETWORK_RETRY_ATTEMPTS) {
                        DebugLogger.e(
                            TAG,
                            "🌐 Failed to reach Instagram (attempt ${runAttemptCount + 1}/$MAX_NETWORK_RETRY_ATTEMPTS). Retrying.",
                        )
                        showNetworkIssueNotification(isRetrying = true)
                        return Result.retry()
                    }
                    DebugLogger.e(TAG, "🌐 Failed to reach Instagram after retries.")
                    showNetworkIssueNotification(isRetrying = false)
                    return Result.failure()
                }
                DebugLogger.e(TAG, "❌ Failed to extract CDN URL from shared URL")
                showFailureNotification(
                    title = "Reel not accessible",
                    message = "We couldn't access this reel. Check that it is public and still available.",
                )
                return Result.failure()
            }

            DebugLogger.d(TAG, "✅ Successfully extracted CDN URL")
            DebugLogger.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            DebugLogger.d(TAG, "🎬 CDN VIDEO URL: $cdnUrl")
            DebugLogger.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            val accessToken = AuthSessionManager.getAccessToken(applicationContext)
            if (accessToken.isNullOrBlank()) {
                DebugLogger.e(TAG, "❌ Missing Supabase session, user needs to sign in again")
                showSignInRequiredNotification()
                return Result.failure()
            }

            // Get FCM token
            DebugLogger.d(TAG, "🔐 Fetching FCM token...")
            val freshFcmToken = try {
                FirebaseMessaging.getInstance().token.await()
            } catch (e: Exception) {
                DebugLogger.e(TAG, "⚠️ Failed to get fresh FCM token: ${e.message}")
                null
            }
            if (!freshFcmToken.isNullOrBlank()) {
                FcmTokenManager.saveToken(applicationContext, freshFcmToken)
            }
            val savedFcmToken = FcmTokenManager.getSavedToken(applicationContext)
            val effectiveFcmToken = when {
                !freshFcmToken.isNullOrBlank() -> freshFcmToken
                !savedFcmToken.isNullOrBlank() -> {
                    DebugLogger.d(TAG, "ℹ️ Using cached FCM token fallback")
                    savedFcmToken
                }
                else -> {
                    DebugLogger.e(
                        TAG,
                        "⚠️ No FCM token available; continuing hunt creation without push notification token",
                    )
                    ""
                }
            }
            if (effectiveFcmToken.isBlank()) {
                DebugLogger.d(TAG, "ℹ️ Push notification may not be delivered for this hunt")
            } else {
                DebugLogger.d(TAG, "✅ FCM token ready: ${effectiveFcmToken.take(20)}...")
            }

            // Call backend API
            DebugLogger.d(TAG, "📤 Sending reel to HuntFact backend...")
            val apiService = RetrofitClient.getApiService(context = applicationContext)
            val cleanedReelUrl = ReelExtractor.cleanInstagramUrl(reelUrl)
            val request = StartHuntRequest(
                video_link = cleanedReelUrl,
                cdn_link = cdnUrl,
                fcm_token = effectiveFcmToken,
                thumbnail_url = cleanedReelUrl,
                caption = cleanedReelUrl,
                creator_handle = "unknown_creator",
                platform = "instagram",
            )

            return try {
                val response = apiService.startHunt(request)
                if (response.success) {
                    val huntRepository = HuntRepository(applicationContext)
                    val huntItem = runCatching {
                        apiService.getHunt(response.hunt_id).toHuntItem()
                    }.getOrElse {
                        // start-hunt only guarantees hunt_id/message/success; use safe local fallback.
                        HuntItem(
                            id = response.hunt_id,
                            videoLink = cleanedReelUrl,
                            title = null,
                            status = "processing",
                            result = null,
                            thumbnailUrl = cleanedReelUrl,
                            caption = cleanedReelUrl,
                            creatorHandle = "unknown_creator",
                            platform = "instagram",
                            errorMessage = null,
                            createdAt = null,
                            updatedAt = null,
                            completedAt = null,
                            trustScore = null,
                            summary = null,
                        )
                    }
                    huntRepository.upsertLocal(huntItem)
                    DebugLogger.d(TAG, "✅ Successfully sent to HuntFact backend!")
                    DebugLogger.d(TAG, "📨 Response: ${response.message}")
                    showSuccessNotification(
                        title = if (effectiveFcmToken.isBlank()) "Processing started" else "Claim check started",
                        message = if (effectiveFcmToken.isBlank()) {
                            "Fact-check started. Notifications may be delayed; check History for updates."
                        } else {
                            "We received your reel and started fact-checking."
                        },
                        huntId = response.hunt_id,
                    )
                    Result.success()
                } else {
                    DebugLogger.e(TAG, "❌ Backend API returned error: ${response.message}")
                    showFailureNotification(
                        title = "Unable to start fact-check",
                        message = "We couldn't start processing this reel right now. Please try again shortly.",
                    )
                    Result.failure()
                }
            } catch (e: Exception) {
                if (e is HttpException && (e.code() == 401 || e.code() == 403)) {
                    DebugLogger.e(TAG, "❌ Backend rejected auth token: HTTP ${e.code()}")
                    showSignInRequiredNotification()
                    return Result.failure()
                }
                DebugLogger.e(TAG, "❌ API request failed: ${e.message}", e)
                showBackendAwareFailureNotification(e)
                Result.failure()
            }
        } catch (e: Exception) {
            DebugLogger.e(TAG, "❌ Unexpected error in worker: ${e.message}", e)
            showBackendAwareFailureNotification(e)
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
        DebugLogger.d(TAG, "📲 Success notification shown: $title - $message")
    }

    private fun showErrorNotification() {
        showFailureNotification(
            title = "Error processing reel",
            message = "Something went wrong while processing your reel. Please try again.",
        )
    }

    private fun showFailureNotification(title: String, message: String) {
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
            .setContentTitle(title)
            .setContentText(message)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(ERROR_NOTIFICATION_ID, notification)
        DebugLogger.e(TAG, "📲 Error notification shown: $title - $message")
    }

    private fun showBackendAwareFailureNotification(error: Exception) {
        if (error is HttpException) {
            when (error.code()) {
                401, 403 -> {
                    showSignInRequiredNotification()
                    return
                }
                429 -> {
                    showFailureNotification(
                        title = "Too many requests",
                        message = "Please wait a minute and try sharing the reel again.",
                    )
                    return
                }
                503 -> {
                    showFailureNotification(
                        title = "Service temporarily unavailable",
                        message = "Our servers are busy right now. Please try again shortly.",
                    )
                    return
                }
            }

            if (error.code() in 400..499) {
                showFailureNotification(
                    title = "Unable to process this reel",
                    message = "Please share a public Instagram reel link and try again.",
                )
                return
            }

            if (error.code() >= 500) {
                showFailureNotification(
                    title = "Server issue",
                    message = "HuntFact is having trouble right now. Please try again later.",
                )
                return
            }
        }

        if (error is UnknownHostException || error is IOException) {
            showFailureNotification(
                title = "Network issue",
                message = "Please check your internet connection and try again.",
            )
            return
        }

        showErrorNotification()
    }

    private fun showNetworkIssueNotification(isRetrying: Boolean) {
        val notificationManager = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = "reel_network_channel"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Network Issues",
                NotificationManager.IMPORTANCE_HIGH,
            )
            notificationManager.createNotificationChannel(channel)
        }

        val contentText = if (isRetrying) {
            "Instagram is temporarily unreachable. We'll retry automatically."
        } else {
            "Unable to reach Instagram. Check internet, DNS, VPN, or ad blocker and try again."
        }

        val notification = NotificationCompat.Builder(applicationContext, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("Network issue while processing reel")
            .setContentText(contentText)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(NETWORK_ISSUE_NOTIFICATION_ID, notification)
        DebugLogger.e(TAG, "📲 Network issue notification shown: $contentText")
    }

    private fun isLikelyInstagramNetworkIssue(): Boolean {
        if (!isNetworkConnected()) {
            return true
        }

        return try {
            InetAddress.getAllByName("www.instagram.com")
            false
        } catch (_: UnknownHostException) {
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun isNetworkConnected(): Boolean {
        val connectivityManager = applicationContext.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return false
        val activeNetwork = connectivityManager.activeNetwork ?: return false
        val capabilities = connectivityManager.getNetworkCapabilities(activeNetwork) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
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
        DebugLogger.e(TAG, "📲 Error notification shown: Sign-in required")
    }

    companion object {
        private const val TAG = "ReelProcessingWorker"
        private const val SUCCESS_NOTIFICATION_ID = 101
        private const val ERROR_NOTIFICATION_ID = 102
        private const val SIGN_IN_REQUIRED_NOTIFICATION_ID = 103
        private const val NETWORK_ISSUE_NOTIFICATION_ID = 105
        private const val MAX_NETWORK_RETRY_ATTEMPTS = 3
    }
}
