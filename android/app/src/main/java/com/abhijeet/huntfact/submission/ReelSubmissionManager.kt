package com.abhijeet.huntfact.submission

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.workDataOf
import com.abhijeet.huntfact.MainActivity
import com.abhijeet.huntfact.utils.DebugLogger
import com.abhijeet.huntfact.workers.ReelProcessingWorker
import java.util.concurrent.TimeUnit

object ReelSubmissionManager {
    private const val TAG = "ReelSubmissionManager"
    private const val RECEIVED_NOTIFICATION_ID = 100
    private const val UNSUPPORTED_NOTIFICATION_ID = 104
    private const val BATTERY_SAVER_NOTIFICATION_ID = 106

    data class SubmissionResult(
        val accepted: Boolean,
        val message: String,
    )

    fun submitReelUrl(context: Context, reelUrl: String): SubmissionResult {
        if (isBatterySaverEnabled(context)) {
            DebugLogger.e(TAG, "Battery Saver is enabled; skipping reel submission")
            showBatterySaverNotification(context)
            return SubmissionResult(
                accepted = false,
                message = "Battery Saver is ON. HuntFact won't work with Battery Saver. Please disable it and try again.",
            )
        }

        val normalizedUrl = normalizeReelUrl(reelUrl)
        if (!isSupportedInstagramUrl(normalizedUrl)) {
            DebugLogger.e(TAG, "Unsupported reel URL submitted: $normalizedUrl")
            showUnsupportedNotification(context)
            return SubmissionResult(
                accepted = false,
                message = "Please share a public Instagram reel link.",
            )
        }

        DebugLogger.d(TAG, "Received reel URL for processing: $normalizedUrl")
        showReceivedNotification(context)
        enqueueReelProcessingJob(context, normalizedUrl)
        return SubmissionResult(
            accepted = true,
            message = "Reel received. We started processing in the background.",
        )
    }

    private fun normalizeReelUrl(url: String): String {
        return url.trim().substringBefore('?').removeSuffix("/")
    }

    fun isSupportedInstagramUrl(url: String): Boolean {
        val normalized = url.lowercase()
        return normalized.contains("instagram.com/") &&
            (normalized.contains("/reel/") || normalized.contains("/reels/") || normalized.contains("/p/"))
    }

    private fun enqueueReelProcessingJob(context: Context, reelUrl: String) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val workRequest = OneTimeWorkRequestBuilder<ReelProcessingWorker>()
            .setInputData(workDataOf("reel_url" to reelUrl))
            .setConstraints(constraints)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.SECONDS)
            .build()

        WorkManager.getInstance(context).enqueueUniqueWork(
            uniqueWorkName(reelUrl),
            ExistingWorkPolicy.KEEP,
            workRequest,
        )
        DebugLogger.d(TAG, "Enqueued reel processing job with ID: ${workRequest.id}")
    }

    private fun uniqueWorkName(reelUrl: String): String = "reel_process:$reelUrl"

    private fun showReceivedNotification(context: Context) {
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = "reel_processing_channel"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Reel Processing",
                NotificationManager.IMPORTANCE_DEFAULT,
            )
            notificationManager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("Reel received")
            .setContentText("Preparing your fact-check request.")
            .setContentIntent(createOpenAppPendingIntent(context))
            .setGroup("huntfact_hunts")
            .setAutoCancel(true)
            .build()

        notificationManager.notify(RECEIVED_NOTIFICATION_ID, notification)
    }

    private fun showUnsupportedNotification(context: Context) {
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = "reel_error_channel"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Reel Processing Errors",
                NotificationManager.IMPORTANCE_DEFAULT,
            )
            notificationManager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("Unsupported link")
            .setContentText("Please share a public Instagram reel URL.")
            .setAutoCancel(true)
            .build()

        notificationManager.notify(UNSUPPORTED_NOTIFICATION_ID, notification)
    }

    private fun showBatterySaverNotification(context: Context) {
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = "reel_error_channel"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Reel Processing Errors",
                NotificationManager.IMPORTANCE_HIGH,
            )
            notificationManager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("Disable Battery Saver")
            .setContentText("HuntFact won't work with Battery Saver. Disable it and share the reel again.")
            .setAutoCancel(true)
            .build()

        notificationManager.notify(BATTERY_SAVER_NOTIFICATION_ID, notification)
    }

    private fun isBatterySaverEnabled(context: Context): Boolean {
        val powerManager = context.getSystemService(PowerManager::class.java)
        return powerManager?.isPowerSaveMode == true
    }

    private fun createOpenAppPendingIntent(context: Context): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        return PendingIntent.getActivity(
            context,
            2000,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }
}
