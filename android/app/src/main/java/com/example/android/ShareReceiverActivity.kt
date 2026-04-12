package com.example.android

import android.app.NotificationChannel
import android.app.NotificationManager
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
                Log.d(TAG, "✅ Received reel URL from Instagram: $reelUrl")
                showReceivedNotification()
                enqueueReelProcessingJob(reelUrl)
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
            .setContentTitle("Reel Sent Successfully")
            .setContentText("You will get your response in a few moments")
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

    companion object {
        private const val TAG = "ShareReceiverActivity"
        private const val RECEIVED_NOTIFICATION_ID = 100
    }
}
