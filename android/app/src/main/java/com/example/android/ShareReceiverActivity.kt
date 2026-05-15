package com.example.android

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.NotificationCompat
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.workDataOf
import com.example.android.workers.ReelProcessingWorker

class ShareReceiverActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val intent = intent
        if (intent?.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            val reelUrl = intent.getStringExtra(Intent.EXTRA_TEXT)
            if (!reelUrl.isNullOrEmpty()) {
                if (isSupportedInstagramUrl(reelUrl)) {
                    Log.d(TAG, "✅ Received reel URL from Instagram: $reelUrl")
                    showReceivedNotification()
                    enqueueReelProcessingJob(reelUrl)
                } else {
                    Log.e(TAG, "❌ Unsupported shared URL: $reelUrl")
                    showUnsupportedNotification()
                }
            } else {
                Log.e(TAG, "❌ No text content found in share intent")
            }
        }
        
        finish()
    }

    private fun showReceivedNotification() {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = "reel_processing_channel"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Reel Processing",
                NotificationManager.IMPORTANCE_DEFAULT
            )
            notificationManager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("Claim check in progress")
            .setContentText("We received your reel and started fact-checking.")
            .setContentIntent(createOpenAppPendingIntent())
            .setGroup("huntfact_hunts")
            .setAutoCancel(true)
            .build()

        notificationManager.notify(RECEIVED_NOTIFICATION_ID, notification)
        Log.d(TAG, "📲 Notification shown: Reel sent successfully")
    }

    private fun enqueueReelProcessingJob(reelUrl: String) {
        val workRequest = OneTimeWorkRequestBuilder<ReelProcessingWorker>()
            .setInputData(workDataOf("reel_url" to reelUrl))
            .build()

        WorkManager.getInstance(this).enqueue(workRequest)
        Log.d(TAG, "📋 Enqueued reel processing job with ID: ${workRequest.id}")
    }

    private fun isSupportedInstagramUrl(url: String): Boolean {
        val normalized = url.lowercase()
        return normalized.contains("instagram.com/")
            && (normalized.contains("/reel/") || normalized.contains("/reels/") || normalized.contains("/p/"))
    }

    private fun showUnsupportedNotification() {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = "reel_error_channel"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Reel Processing Errors",
                NotificationManager.IMPORTANCE_DEFAULT
            )
            notificationManager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("Unsupported link")
            .setContentText("Please share a public Instagram reel URL.")
            .setAutoCancel(true)
            .build()

        notificationManager.notify(UNSUPPORTED_NOTIFICATION_ID, notification)
    }

    private fun createOpenAppPendingIntent(): PendingIntent {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        return PendingIntent.getActivity(
            this,
            2000,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    companion object {
        private const val TAG = "ShareReceiverActivity"
        private const val RECEIVED_NOTIFICATION_ID = 100
        private const val UNSUPPORTED_NOTIFICATION_ID = 104
    }
}
