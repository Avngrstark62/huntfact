package com.example.android.extraction

import android.util.Log
import com.google.gson.JsonParser
import com.google.gson.stream.JsonReader
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.FormBody
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import java.io.StringReader
import java.net.URL
import java.util.concurrent.TimeUnit
import java.util.regex.Pattern
import java.util.zip.GZIPInputStream

object ReelExtractor {
    private const val TAG = "ReelExtractor"
    
    private val httpClient = OkHttpClient.Builder()
        .addInterceptor(GzipDecompressionInterceptor())
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    private class GzipDecompressionInterceptor : Interceptor {
        override fun intercept(chain: Interceptor.Chain): Response {
            val response = chain.proceed(chain.request())
            
            val encoding = response.header("Content-Encoding")
            if (encoding != null && (encoding.contains("gzip") || encoding.contains("deflate"))) {
                val decompressedBody = response.body?.let { body ->
                    val inputStream = GZIPInputStream(body.byteStream())
                    val decompressedString = inputStream.bufferedReader().use { it.readText() }
                    okhttp3.ResponseBody.create(body.contentType(), decompressedString)
                } ?: response.body
                
                return response.newBuilder()
                    .body(decompressedBody)
                    .removeHeader("Content-Encoding")
                    .build()
            }
            
            return response
        }
    }

    suspend fun extractCdnUrl(reelUrl: String): String? = withContext(Dispatchers.IO) {
        try {
            // Clean the URL first (remove query parameters)
            val cleanedUrl = cleanInstagramUrl(reelUrl)
            
            // Step 1: Extract shortcode
            val shortcode = extractShortcodeFromUrl(cleanedUrl)
            if (shortcode == null) {
                Log.e(TAG, "Failed to extract shortcode from URL: $cleanedUrl")
                return@withContext null
            }
            Log.d(TAG, "Extracted shortcode: $shortcode")

            // Step 2: Fetch reel page to get CSRF token
            val pageUrl = "https://www.instagram.com/reel/$shortcode/"
            val pageResponse = try {
                val request = Request.Builder()
                    .url(pageUrl)
                    .headers(getBrowserHeaders())
                    .build()
                httpClient.newCall(request).execute()
            } catch (e: Exception) {
                Log.e(TAG, "Failed to fetch reel page: ${e.message}")
                return@withContext null
            }

            if (!pageResponse.isSuccessful) {
                Log.e(TAG, "Failed to fetch reel page (status: ${pageResponse.code})")
                return@withContext null
            }

            val pageHtml = pageResponse.body?.string() ?: ""
            Log.d(TAG, "Fetched reel page (status: ${pageResponse.code})")

            // Extract CSRF token
            var csrfToken = extractCsrfToken(pageHtml)
            if (csrfToken == null) {
                // Try to get from cookies
                val setCookieHeaders = pageResponse.headers("set-cookie")
                for (cookie in setCookieHeaders) {
                    if (cookie.contains("csrftoken=")) {
                        val parts = cookie.split(";")[0].split("=")
                        if (parts.size == 2) {
                            csrfToken = parts[1]
                            break
                        }
                    }
                }
            }

            if (csrfToken == null) {
                Log.e(TAG, "Failed to extract CSRF token")
                return@withContext null
            }
            Log.d(TAG, "Extracted CSRF token")

            // Step 3: Small delay (anti-bot)
            Thread.sleep(200)

            // Step 4: GraphQL query
            val graphqlHeaders: MutableMap<String, String> = mutableMapOf<String, String>().apply {
                getBrowserHeaders().forEach { (key, value) ->
                    put(key, value)
                }
                remove("Content-Length")
                put("authority", "www.instagram.com")
                put("scheme", "https")
                put("accept", "*/*")
                put("X-CSRFToken", csrfToken)
                put("Referer", pageUrl)
            }

            val variables = """{"shortcode":"$shortcode"}"""
            val docId = "8845758582119845"

            val graphqlUrl = "https://www.instagram.com/graphql/query"
            val formBody = FormBody.Builder()
                .add("variables", variables)
                .add("doc_id", docId)
                .add("server_timestamps", "true")
                .build()

            val graphqlResponse = try {
                val request = Request.Builder()
                    .url(graphqlUrl)
                    .post(formBody)
                    .apply {
                        graphqlHeaders.forEach { (key: String, value: String) ->
                            header(key, value)
                        }
                    }
                    .build()
                httpClient.newCall(request).execute()
            } catch (e: Exception) {
                Log.e(TAG, "GraphQL request failed: ${e.message}")
                return@withContext null
            }

            if (!graphqlResponse.isSuccessful) {
                Log.e(TAG, "GraphQL request failed (status: ${graphqlResponse.code})")
                return@withContext null
            }

            Log.d(TAG, "GraphQL query successful (status: ${graphqlResponse.code})")

            // Step 5: Parse response
            val responseBody = graphqlResponse.body?.string() ?: ""
            val jsonObject = try {
                val jsonReader = JsonReader(StringReader(responseBody))
                jsonReader.isLenient = true
                JsonParser.parseReader(jsonReader).asJsonObject
            } catch (e: Exception) {
                Log.e(TAG, "Failed to parse GraphQL response as JSON: ${e.message}")
                return@withContext null
            }

            val dataField = jsonObject.get("data")
            if (dataField == null || dataField.isJsonNull) {
                Log.e(TAG, "'data' field is null in response")
                return@withContext null
            }

            if (!dataField.isJsonObject) {
                Log.e(TAG, "'data' field is not a JSON object")
                return@withContext null
            }

            val mediaData = dataField.asJsonObject.get("xdt_shortcode_media")
            if (mediaData == null || mediaData.isJsonNull) {
                Log.e(TAG, "'xdt_shortcode_media' is null or unavailable")
                return@withContext null
            }

            if (!mediaData.isJsonObject) {
                Log.e(TAG, "'xdt_shortcode_media' is not a JSON object")
                return@withContext null
            }

            val mediaObj = mediaData.asJsonObject
            val videoUrl = mediaObj.get("video_url")
            
            if (videoUrl != null && !videoUrl.isJsonNull) {
                Log.d(TAG, "Extracted video URL")
                return@withContext videoUrl.asString
            }

            if (mediaObj.get("is_video")?.asBoolean == true) {
                Log.e(TAG, "Media is video but video_url field is missing")
                return@withContext null
            }

            Log.e(TAG, "Media is not a video")
            null
        } catch (e: Exception) {
            Log.e(TAG, "Unexpected error: ${e.message}", e)
            null
        }
    }

    fun cleanInstagramUrl(url: String): String {
        // Remove query parameters and trailing slash from Instagram URL
        // Example: https://www.instagram.com/p/DXJaD4sEdWZ/?igsh=... → https://www.instagram.com/p/DXJaD4sEdWZ
        return url.substringBefore('?').removeSuffix("/")
    }

    private fun extractShortcodeFromUrl(url: String): String? {
        try {
            val parsedUrl = URL(url)
            val path = parsedUrl.path.trim('/')
            
            val pattern = Pattern.compile("^(?:reels?|p)/([a-zA-Z0-9_-]+)")
            val matcher = pattern.matcher(path)
            
            return if (matcher.find()) {
                matcher.group(1)
            } else {
                null
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error extracting shortcode: ${e.message}")
            return null
        }
    }

    private fun extractCsrfToken(html: String): String? {
        // Try to find in script content: {"csrf_token":"..."}
        val scriptPattern = Pattern.compile("\"csrf_token\":\"([a-zA-Z0-9]+)\"")
        var matcher = scriptPattern.matcher(html)
        if (matcher.find()) {
            return matcher.group(1)
        }

        // Try meta tag: <meta name="csrf-token" content="...">
        val metaPattern = Pattern.compile("""<meta[^>]*name="csrf-token"[^>]*content="([^"]*)"""")
        matcher = metaPattern.matcher(html)
        if (matcher.find()) {
            return matcher.group(1)
        }

        return null
    }

    private fun getBrowserHeaders(): okhttp3.Headers {
        return okhttp3.Headers.Builder()
            .add("Accept-Encoding", "gzip, deflate")
            .add("Accept-Language", "en-US,en;q=0.8")
            .add("Host", "www.instagram.com")
            .add("Origin", "https://www.instagram.com")
            .add("Referer", "https://www.instagram.com/")
            .add("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36")
            .add("X-Instagram-AJAX", "1")
            .add("X-Requested-With", "XMLHttpRequest")
            .build()
    }
}
