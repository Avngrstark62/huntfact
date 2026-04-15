package com.example.android.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import com.example.android.R
import com.example.android.ResultActivity
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class FactCheckMessagingService : FirebaseMessagingService() {

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        Log.d(TAG, "Message received from: ${remoteMessage.from}")

        val title = remoteMessage.notification?.title ?: "Fact Check Ready"
        val body = remoteMessage.notification?.body ?: "Your fact check is ready"
        
        val verdict = remoteMessage.data["verdict"] ?: ""
        val confidence = remoteMessage.data["confidence"] ?: ""
        val explanation = remoteMessage.data["explanation"] ?: ""
        val sources = remoteMessage.data["sources"] ?: "[]"

        showNotification(title, body, verdict, confidence, explanation, sources)
    }

    override fun onNewToken(token: String) {
        Log.d(TAG, "New FCM token: $token")
        saveFcmToken(token)
    }

    private fun saveFcmToken(token: String) {
        val sharedPref = getSharedPreferences(SHARED_PREF_NAME, Context.MODE_PRIVATE)
        sharedPref.edit().putString(FCM_TOKEN_KEY, token).apply()
        Log.d(TAG, "FCM token saved: $token")
    }

    private fun showNotification(
        title: String,
        body: String,
        verdict: String,
        confidence: String,
        explanation: String,
        sources: String
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
            putExtra("verdict", verdict)
            putExtra("confidence", confidence)
            putExtra("explanation", explanation)
            putExtra("sources", sources)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            resultIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(title)
            .setContentText(body)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(NOTIFICATION_ID, notification)
    }

    companion object {
        private const val TAG = "FactCheckMessagingService"
        private const val CHANNEL_ID = "fact_check_channel"
        private const val NOTIFICATION_ID = 1
        private const val SHARED_PREF_NAME = "fact_check_prefs"
        private const val FCM_TOKEN_KEY = "fcm_token"
    }
}

