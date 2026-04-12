package com.example.factchecksharer.ui

import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.example.factchecksharer.R

class ResultActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_result)

        val titleText = findViewById<TextView>(R.id.titleText)
        val resultText = findViewById<TextView>(R.id.resultText)

        val result = intent.getStringExtra("result_text") ?: "No result available"
        resultText.text = result
    }
}
