package com.abhijeet.huntfact.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.abhijeet.huntfact.R
import com.abhijeet.huntfact.ResultActivity
import com.abhijeet.huntfact.hunts.HuntRepository
import com.abhijeet.huntfact.hunts.toHuntItem
import com.abhijeet.huntfact.network.RetrofitClient
import com.abhijeet.huntfact.utils.DebugLogger
import com.abhijeet.huntfact.utils.FcmTokenManager
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class FactCheckMessagingService : FirebaseMessagingService() {

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        DebugLogger.d(TAG, "Message received from: ${remoteMessage.from}")

        val title = remoteMessage.notification?.title ?: remoteMessage.data["title"] ?: "Fact check ready"
        val body = remoteMessage.notification?.body ?: remoteMessage.data["body"] ?: "Your reel has been fact-checked."
        val huntId = remoteMessage.data["hunt_id"]?.toIntOrNull()

        if (huntId == null) {
            DebugLogger.e(TAG, "Missing hunt_id in push payload")
            return
        }

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val hunt = RetrofitClient.getApiService(context = applicationContext).getHunt(huntId).toHuntItem()
                HuntRepository(applicationContext).upsertLocal(hunt)
            } catch (e: Exception) {
                DebugLogger.e(TAG, "Failed to prefetch hunt result: ${e.message}", e)
            }
        }

        showNotification(title, body, huntId)
    }

    override fun onNewToken(token: String) {
        DebugLogger.d(TAG, "New FCM token: $token")
        saveFcmToken(token)
    }

    private fun saveFcmToken(token: String) {
        FcmTokenManager.saveToken(this, token)
        DebugLogger.d(TAG, "FCM token saved: $token")
    }

    private fun showNotification(
        title: String,
        body: String,
        huntId: Int
    ) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = CHANNEL_ID

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Fact Check Notifications",
                NotificationManager.IMPORTANCE_DEFAULT
            )
            notificationManager.createNotificationChannel(channel)
        }

        val resultIntent = Intent(this, ResultActivity::class.java).apply {
            putExtra(ResultActivity.EXTRA_HUNT_ID, huntId)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val pendingIntent = PendingIntent.getActivity(
            this,
            huntId,
            resultIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(title)
            .setContentText(body)
            .setContentIntent(pendingIntent)
            .setGroup("huntfact_hunts")
            .setAutoCancel(true)
            .build()

        notificationManager.notify(huntId, notification)
    }

    companion object {
        private const val TAG = "FactCheckMessagingService"
        private const val CHANNEL_ID = "fact_check_channel"
    }
}

