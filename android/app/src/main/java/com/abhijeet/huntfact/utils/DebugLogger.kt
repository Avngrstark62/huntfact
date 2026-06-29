package com.abhijeet.huntfact.utils

import android.util.Log

object DebugLogger {
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
    }

    private fun sanitize(input: String): String {
        val redactedKeyValues = input.replace(keyValueSensitivePattern) { match ->
            val key = match.value.substringBefore(':').substringBefore('=').trim()
            "$key=<redacted>"
        }
        return redactedKeyValues.replace(bearerSensitivePattern, "Bearer <redacted>")
    }
}
