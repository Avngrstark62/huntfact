package com.abhijeet.huntfact.utils

import android.content.Context
import android.util.Log
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object DebugLogger {
    private const val LOG_FILE_NAME = "debug_logs.txt"
    private val fileLock = Any()
    private val timestampFormatter = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US)

    private val keyValueSensitivePattern =
        Regex("(?i)(password|passwd|api[_-]?key|token|secret|cookie|authorization)\\s*[:=]\\s*[^\\s,;]+")
    private val bearerSensitivePattern = Regex("(?i)bearer\\s+[a-z0-9\\-._~+/]+=*")

    fun d(tag: String, message: String, throwable: Throwable? = null) {
        log("D", tag, message, throwable)
    }

    fun i(tag: String, message: String, throwable: Throwable? = null) {
        log("I", tag, message, throwable)
    }

    fun w(tag: String, message: String, throwable: Throwable? = null) {
        log("W", tag, message, throwable)
    }

    fun e(tag: String, message: String, throwable: Throwable? = null) {
        log("E", tag, message, throwable)
    }

    fun getLogFile(context: Context): File = File(context.filesDir, LOG_FILE_NAME)

    private fun log(level: String, tag: String, message: String, throwable: Throwable?) {
        val safeMessage = sanitize(message)
        val safeStackTrace = throwable?.let { sanitize(Log.getStackTraceString(it)) }

        val logcatMessage = if (safeStackTrace.isNullOrBlank()) {
            safeMessage
        } else {
            "$safeMessage\n$safeStackTrace"
        }

        when (level) {
            "D" -> Log.d(tag, logcatMessage)
            "I" -> Log.i(tag, logcatMessage)
            "W" -> Log.w(tag, logcatMessage)
            else -> Log.e(tag, logcatMessage)
        }

        appendToFile(level, tag, safeMessage, safeStackTrace)
    }

    private fun appendToFile(level: String, tag: String, message: String, stackTrace: String?) {
        val appContext = HuntFactApp.getAppContextOrNull() ?: return
        try {
            synchronized(fileLock) {
                val timestamp = timestampFormatter.format(Date())
                val line = buildString {
                    append(timestamp)
                    append(" [")
                    append(level)
                    append("] ")
                    append(tag)
                    append(": ")
                    append(message)
                    if (!stackTrace.isNullOrBlank()) {
                        append('\n')
                        append(stackTrace)
                    }
                    append('\n')
                }
                getLogFile(appContext).appendText(line)
            }
        } catch (e: Exception) {
            Log.e("DebugLogger", "Failed to append debug log file: ${e.message}")
        }
    }

    private fun sanitize(input: String): String {
        val redactedKeyValues = input.replace(keyValueSensitivePattern) { match ->
            val key = match.value.substringBefore(':').substringBefore('=').trim()
            "$key=<redacted>"
        }
        return redactedKeyValues.replace(bearerSensitivePattern, "Bearer <redacted>")
    }
}
