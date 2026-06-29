package com.abhijeet.huntfact

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.abhijeet.huntfact.submission.ReelSubmissionManager
import com.abhijeet.huntfact.utils.DebugLogger

class ShareReceiverActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val intent = intent
        if (intent?.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            val reelUrl = intent.getStringExtra(Intent.EXTRA_TEXT)
            if (!reelUrl.isNullOrEmpty()) {
                val result = ReelSubmissionManager.submitReelUrl(this, reelUrl)
                if (result.accepted) {
                    DebugLogger.d(TAG, "✅ Accepted shared reel URL from Instagram")
                } else {
                    DebugLogger.e(TAG, "❌ Rejected shared URL: $reelUrl")
                }
            } else {
                DebugLogger.e(TAG, "❌ No text content found in share intent")
            }
        }
        
        finish()
    }

    companion object {
        private const val TAG = "ShareReceiverActivity"
    }
}
