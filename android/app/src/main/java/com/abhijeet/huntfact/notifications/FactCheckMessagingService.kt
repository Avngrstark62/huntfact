package com.abhijeet.huntfact.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import com.abhijeet.huntfact.R
import com.abhijeet.huntfact.ResultActivity
import com.abhijeet.huntfact.hunts.HuntRepository
import com.abhijeet.huntfact.hunts.toHuntItem
import com.abhijeet.huntfact.network.RetrofitClient
import com.google.firebase.Firebase
import com.google.firebase.crashlytics.crashlytics
import com.abhijeet.huntfact.utils.FcmTokenManager
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class FactCheckMessagingService : FirebaseMessagingService() {

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        Firebase.crashlytics.log("FactCheckMessagingService.onMessageReceived: started")
        Log.d(TAG, "Message received from: ${remoteMessage.from}")

        val title = remoteMessage.notification?.title ?: remoteMessage.data["title"] ?: "Fact check ready"
        val body = remoteMessage.notification?.body ?: remoteMessage.data["body"] ?: "Your reel has been fact-checked."
        val huntId = remoteMessage.data["hunt_id"]?.toIntOrNull()
        Firebase.crashlytics.log("FactCheckMessagingService.onMessageReceived: parsed huntId=${huntId ?: -1}")

        if (huntId == null) {
            Log.e(TAG, "Missing hunt_id in push payload")
            Firebase.crashlytics.log("FactCheckMessagingService.onMessageReceived: missing hunt_id, returning")
            Firebase.crashlytics.recordException(Exception("Push payload missing hunt_id"))
            return
        }

        CoroutineScope(Dispatchers.IO).launch {
            try {
                Firebase.crashlytics.log("FactCheckMessagingService.prefetch: requesting huntId=$huntId")
                val hunt = RetrofitClient.getApiService(context = applicationContext).getHunt(huntId).toHuntItem()
                HuntRepository(applicationContext).upsertLocal(hunt)
                Firebase.crashlytics.log("FactCheckMessagingService.prefetch: completed huntId=$huntId")
            } catch (exception: Exception) {
                Log.e(TAG, "Failed to prefetch hunt result: ${exception.message}", exception)
                Firebase.crashlytics.log("FactCheckMessagingService.prefetch: failed huntId=$huntId")
                Firebase.crashlytics.recordException(exception)
            }
        }

        showNotification(title, body, huntId)
        Firebase.crashlytics.log("FactCheckMessagingService.onMessageReceived: completed")
    }

    override fun onNewToken(token: String) {
        Log.d(TAG, "New FCM token: $token")
        Firebase.crashlytics.log("FactCheckMessagingService.onNewToken: received new token")
        saveFcmToken(token)
    }

    private fun saveFcmToken(token: String) {
        Firebase.crashlytics.log("FactCheckMessagingService.saveFcmToken: saving token")
        FcmTokenManager.saveToken(this, token)
        Log.d(TAG, "FCM token saved: $token")
        Firebase.crashlytics.log("FactCheckMessagingService.saveFcmToken: completed")
    }

    private fun showNotification(
        title: String,
        body: String,
        huntId: Int
    ) {
        Firebase.crashlytics.log("FactCheckMessagingService.showNotification: started huntId=$huntId")
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
        Firebase.crashlytics.log("FactCheckMessagingService.showNotification: notification posted huntId=$huntId")
    }

    companion object {
        private const val TAG = "FactCheckMessagingService"
        private const val CHANNEL_ID = "fact_check_channel"
    }
}

