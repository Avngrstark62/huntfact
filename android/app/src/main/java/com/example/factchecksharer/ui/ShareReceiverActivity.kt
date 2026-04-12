package com.example.factchecksharer.ui

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.workDataOf
import com.example.factchecksharer.worker.ReelProcessingWorker

class ShareReceiverActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val reelUrl = intent.getStringExtra(Intent.EXTRA_TEXT)

        if (!reelUrl.isNullOrEmpty()) {
            // Enqueue background job
            val workRequest = OneTimeWorkRequestBuilder<ReelProcessingWorker>()
                .setInputData(workDataOf("reel_url" to reelUrl))
                .build()

            WorkManager.getInstance(this).enqueue(workRequest)
        }

        // Finish immediately without showing UI
        finish()
    }
}
