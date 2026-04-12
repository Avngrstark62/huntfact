package com.example.factchecksharer.extractor

import com.google.gson.JsonParser
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.FormBody
import java.util.regex.Pattern

object ReelExtractor {

    private val httpClient = OkHttpClient()

    suspend fun extractCdnUrl(reelUrl: String): String? = withContext(Dispatchers.IO) {
        try {
            // Step 1: Extract shortcode from URL
            val shortcode = extractShortcodeFromUrl(reelUrl) ?: return@withContext null

            // Step 2: Fetch reel page to get CSRF token
            val (csrfToken, cookies) = fetchReelPageAndToken(shortcode) ?: return@withContext null

            // Step 3: Perform GraphQL query
            val videoUrl = graphqlQuery(shortcode, csrfToken, cookies)
            videoUrl
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    private fun extractShortcodeFromUrl(url: String): String? {
        val pattern = Pattern.compile("(?:reels?|p)/([a-zA-Z0-9_-]+)")
        val matcher = pattern.matcher(url)
        return if (matcher.find()) matcher.group(1) else null
    }

    private fun fetchReelPageAndToken(shortcode: String): Pair<String, Map<String, String>>? {
        val pageUrl = "https://www.instagram.com/reel/$shortcode/"
        val headers = getBrowserHeaders()

        return try {
            val request = Request.Builder()
                .url(pageUrl)
                .get()
                .apply {
                    headers.forEach { (key, value) -> addHeader(key, value) }
                }
                .build()

            val response = httpClient.newCall(request).execute()
            if (!response.isSuccessful) return null

            val htmlBody = response.body?.string() ?: return null

            // Extract CSRF token
            val csrfToken = extractCsrfToken(htmlBody) ?: return null

            // Extract cookies from response
            val cookies = extractCookies(response.headers)

            Pair(csrfToken, cookies)
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    private fun graphqlQuery(
        shortcode: String,
        csrfToken: String,
        cookies: Map<String, String>
    ): String? {
        val pageUrl = "https://www.instagram.com/reel/$shortcode/"
        val graphqlUrl = "https://www.instagram.com/graphql/query"
        val headers = getBrowserHeaders().toMutableMap()

        headers.apply {
            put("authority", "www.instagram.com")
            put("scheme", "https")
            put("accept", "*/*")
            put("X-CSRFToken", csrfToken)
            put("Referer", pageUrl)
            remove("Content-Length")
            remove("Connection")
        }

        return try {
            val variables = """{"shortcode":"$shortcode"}"""
            val docId = "8845758582119845"

            val formBody = FormBody.Builder()
                .add("variables", variables)
                .add("doc_id", docId)
                .add("server_timestamps", "true")
                .build()

            val request = Request.Builder()
                .url(graphqlUrl)
                .post(formBody)
                .apply {
                    headers.forEach { (key, value) -> addHeader(key, value) }
                    cookies.forEach { (key, value) -> addHeader("Cookie", "$key=$value") }
                }
                .build()

            val response = httpClient.newCall(request).execute()
            if (!response.isSuccessful) return null

            val jsonBody = response.body?.string() ?: return null
            parseVideoUrl(jsonBody)
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    private fun extractCsrfToken(html: String): String? {
        // Try to find in script content: {"csrf_token":"..."}
        val pattern1 = Pattern.compile("\"csrf_token\":\"([a-zA-Z0-9]+)\"")
        var matcher = pattern1.matcher(html)
        if (matcher.find()) return matcher.group(1)

        // Try meta tag: <meta name="csrf-token" content="...">
        val pattern2 = Pattern.compile("<meta[^>]*name=\"csrf-token\"[^>]*content=\"([^\"]*)\"")
        matcher = pattern2.matcher(html)
        return if (matcher.find()) matcher.group(1) else null
    }

    private fun extractCookies(headers: okhttp3.Headers): Map<String, String> {
        val cookies = mutableMapOf<String, String>()
        headers.values("set-cookie").forEach { cookie ->
            val parts = cookie.split(";")[0].split("=")
            if (parts.size == 2) {
                cookies[parts[0].trim()] = parts[1].trim()
            }
        }
        return cookies
    }

    private fun parseVideoUrl(jsonBody: String): String? {
        return try {
            val jsonObject = JsonParser.parseString(jsonBody).asJsonObject
            val dataField = jsonObject.getAsJsonObject("data") ?: return null
            val mediaData = dataField.getAsJsonObject("xdt_shortcode_media") ?: return null
            mediaData.get("video_url")?.asString
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    private fun getBrowserHeaders(): Map<String, String> {
        return mapOf(
            "Accept-Encoding" to "gzip, deflate",
            "Accept-Language" to "en-US,en;q=0.8",
            "Content-Length" to "0",
            "Host" to "www.instagram.com",
            "Origin" to "https://www.instagram.com",
            "Referer" to "https://www.instagram.com/",
            "User-Agent" to "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "X-Instagram-AJAX" to "1",
            "X-Requested-With" to "XMLHttpRequest"
        )
    }
}
