package com.example.android

import android.content.Intent
import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
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
                Log.d(TAG, "Received reel URL: $reelUrl")
                enqueueReelProcessingJob(reelUrl)
            } else {
                Log.e(TAG, "No text content found")
            }
        }
        
        finish()
    }

    private fun enqueueReelProcessingJob(reelUrl: String) {
        val workRequest = OneTimeWorkRequestBuilder<ReelProcessingWorker>()
            .setInputData(workDataOf("reel_url" to reelUrl))
            .build()

        WorkManager.getInstance(this).enqueue(workRequest)
        Log.d(TAG, "Enqueued reel processing job")
    }

    companion object {
        private const val TAG = "ShareReceiverActivity"
    }
}
