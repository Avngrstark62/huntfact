package com.example.android

import android.os.Bundle
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import com.example.android.hunts.HuntRepository
import kotlinx.coroutines.launch

class ResultActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_result)

        val titleText = findViewById<TextView>(R.id.titleText)
        val metaText = findViewById<TextView>(R.id.metaText)
        val resultText = findViewById<TextView>(R.id.resultText)

        val huntId = intent.getIntExtra(EXTRA_HUNT_ID, -1)
        if (huntId <= 0) {
            titleText.text = "Fact Check Result"
            metaText.text = "Missing hunt reference"
            resultText.text = "No result available."
            return
        }

        titleText.text = "Fact Check #$huntId"
        metaText.text = "Loading latest result..."
        resultText.text = "Fetching result..."

        val repository = HuntRepository(applicationContext)
        lifecycleScope.launch {
            val hunt = try {
                repository.fetchHunt(huntId)
            } catch (_: Exception) {
                repository.getCachedHunts().firstOrNull { it.id == huntId }
            }

            if (hunt == null) {
                metaText.text = "Unable to load hunt"
                resultText.text = "Please reopen from notification or refresh in app."
                return@launch
            }

            val caption = hunt.caption?.takeIf { it.isNotBlank() } ?: "No caption"
            val creator = hunt.creatorHandle?.takeIf { it.isNotBlank() } ?: "unknown creator"
            metaText.text = "Status: ${hunt.status} • @$creator\n$caption"
            resultText.text = hunt.result ?: "Still processing. Please check again shortly."
        }
    }

    companion object {
        const val EXTRA_HUNT_ID = "hunt_id"
    }
}
