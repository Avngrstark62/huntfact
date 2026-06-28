package com.abhijeet.huntfact.extraction

import com.abhijeet.huntfact.utils.DebugLogger
import com.google.gson.JsonArray
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.Headers
import okhttp3.OkHttpClient
import okhttp3.Request
import org.w3c.dom.Element
import org.xml.sax.InputSource
import java.io.StringReader
import java.net.URI
import java.net.URL
import java.util.concurrent.TimeUnit
import javax.xml.parsers.DocumentBuilderFactory

object ReelExtractor {
    private const val TAG = "ReelExtractor"
    private const val MPD_NS = "urn:mpeg:dash:schema:mpd:2011"

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    data class ReelInfo(
        val cdnUrl: String,
        val caption: String?,
        val thumbnailUrl: String?,
        val creatorHandle: String?,
    )

    private data class CdnRecord(
        val url: String,
        val source: String?,
        val contentType: String?,
        val mimeType: String?,
        val representationId: String?,
        val bandwidth: String?,
        val width: String?,
        val height: String?,
        val codecs: String?,
    )

    suspend fun extractCdnUrl(reelUrl: String): String? = withContext(Dispatchers.IO) {
        extractReelInfo(reelUrl)?.cdnUrl
    }

    suspend fun extractReelInfo(reelUrl: String): ReelInfo? = withContext(Dispatchers.IO) {
        try {
            val cleanedUrl = cleanInstagramUrl(reelUrl)
            val shortcode = extractShortcodeFromUrl(cleanedUrl)
            if (shortcode == null) {
                DebugLogger.e(TAG, "Could not extract shortcode from URL: $cleanedUrl")
                return@withContext null
            }

            val reelPageUrl = "https://www.instagram.com/reel/$shortcode/?l=1"
            val htmlText = fetchReelHtml(reelPageUrl) ?: return@withContext null
            val audioCdnUrl = extractAudioCdnLinkFromHtml(htmlText)

            if (audioCdnUrl.isNullOrBlank()) {
                DebugLogger.e(TAG, "Audio CDN link not found in HTML")
                return@withContext null
            }

            ReelInfo(
                cdnUrl = audioCdnUrl,
                caption = null,
                thumbnailUrl = null,
                creatorHandle = null,
            )
        } catch (e: Exception) {
            DebugLogger.e(TAG, "Unexpected error while extracting CDN URL: ${e.message}", e)
            null
        }
    }

    fun cleanInstagramUrl(url: String): String {
        return url.substringBefore('?').removeSuffix("/")
    }

    private fun fetchReelHtml(reelPageUrl: String): String? {
        val request = Request.Builder()
            .url(reelPageUrl)
            .headers(getReelPageHeaders())
            .build()

        return try {
            httpClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    DebugLogger.e(TAG, "Failed to fetch reel HTML (status: ${response.code})")
                    return null
                }
                val htmlText = response.body?.string().orEmpty()
                if (htmlText.isBlank()) {
                    DebugLogger.e(TAG, "Received empty HTML response")
                    return null
                }
                htmlText
            }
        } catch (e: Exception) {
            DebugLogger.e(TAG, "Failed to fetch reel HTML: ${e.message}", e)
            null
        }
    }

    private fun extractShortcodeFromUrl(url: String): String? {
        return try {
            val path = URL(url).path.trim('/')
            Regex("^(?:reels?|p)/([a-zA-Z0-9_-]+)").find(path)?.groupValues?.getOrNull(1)
        } catch (e: Exception) {
            DebugLogger.e(TAG, "Error extracting shortcode from URL: ${e.message}", e)
            null
        }
    }

    private fun getReelPageHeaders(): Headers {
        return Headers.Builder()
            .add(
                "accept",
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            )
            .add("accept-language", "en-US,en;q=0.9,hi;q=0.8,ja;q=0.7")
            .add("sec-fetch-dest", "document")
            .add("sec-fetch-mode", "navigate")
            .add("sec-fetch-site", "same-origin")
            .add("sec-fetch-user", "?1")
            .add(
                "user-agent",
                "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
            )
            .build()
    }

    private fun extractAudioCdnLinkFromHtml(htmlText: String): String? {
        val links = extractCdnLinksFromHtml(htmlText)
        return links.firstOrNull { isAudioRecord(it) }?.url
    }

    private fun isAudioRecord(record: CdnRecord): Boolean {
        val contentType = record.contentType.orEmpty().lowercase()
        val mimeType = record.mimeType.orEmpty().lowercase()
        val codecs = record.codecs.orEmpty().lowercase()

        return contentType == "audio" ||
            mimeType.startsWith("audio/") ||
            codecs.startsWith("mp4a") ||
            codecs.startsWith("opus") ||
            codecs.startsWith("vorbis") ||
            codecs.startsWith("ec-3") ||
            codecs.startsWith("ac-3")
    }

    private fun extractCdnLinksFromHtml(htmlText: String): List<CdnRecord> {
        val records = mutableListOf<CdnRecord>()
        val jsonBlocks = extractSjsJsonBlocks(htmlText)

        for (block in jsonBlocks) {
            val payload = try {
                JsonParser.parseString(block)
            } catch (_: Exception) {
                null
            } ?: continue
            walkPayload(payload, records, "")
        }

        val deduped = mutableListOf<CdnRecord>()
        val seen = mutableSetOf<String>()
        for (record in records) {
            if (seen.add(record.url)) {
                deduped.add(record)
            }
        }
        return deduped
    }

    private fun extractSjsJsonBlocks(htmlText: String): List<String> {
        val scriptRegex = Regex(
            pattern = """<script\b(?=[^>]*\btype=["']application/json["'])(?=[^>]*\bdata-sjs(?:[=\s>]|$))[^>]*>(.*?)</script>""",
            options = setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL),
        )
        return scriptRegex.findAll(htmlText)
            .mapNotNull { match -> match.groupValues.getOrNull(1)?.trim() }
            .filter { it.isNotEmpty() }
            .toList()
    }

    private fun walkPayload(node: JsonElement, records: MutableList<CdnRecord>, path: String) {
        when {
            node.isJsonObject -> walkObject(node.asJsonObject, records, path)
            node.isJsonArray -> walkArray(node.asJsonArray, records, path)
        }
    }

    private fun walkObject(obj: JsonObject, records: MutableList<CdnRecord>, path: String) {
        for ((key, value) in obj.entrySet()) {
            val nextPath = if (path.isEmpty()) key else "$path.$key"

            if (key == "video_dash_manifest" && value.isJsonPrimitive && value.asJsonPrimitive.isString) {
                records += extractFromMpd(value.asString)
            }

            if (key in setOf("manifest_url", "progressive_url", "hls_playlist_url", "videoDashUrl") &&
                value.isJsonPrimitive && value.asJsonPrimitive.isString
            ) {
                addIfValid(
                    records,
                    CdnRecord(
                        url = value.asString,
                        source = nextPath,
                        contentType = null,
                        mimeType = null,
                        representationId = null,
                        bandwidth = null,
                        width = null,
                        height = null,
                        codecs = null,
                    ),
                )
            }

            if (key == "video_versions" && value.isJsonArray) {
                value.asJsonArray.forEachIndexed { index, item ->
                    if (!item.isJsonObject) return@forEachIndexed
                    val entry = item.asJsonObject
                    val url = entry.getAsJsonPrimitiveOrNull("url")?.asString ?: return@forEachIndexed

                    addIfValid(
                        records,
                        CdnRecord(
                            url = url,
                            source = "$nextPath[$index].url",
                            contentType = entry.getAsJsonPrimitiveOrNull("content_type")?.asString,
                            mimeType = entry.getAsJsonPrimitiveOrNull("mime_type")?.asString,
                            representationId = null,
                            bandwidth = null,
                            width = entry.getAsJsonPrimitiveOrNull("width")?.asString,
                            height = entry.getAsJsonPrimitiveOrNull("height")?.asString,
                            codecs = entry.getAsJsonPrimitiveOrNull("codecs")?.asString,
                        ),
                    )
                }
            }

            walkPayload(value, records, nextPath)
        }
    }

    private fun walkArray(array: JsonArray, records: MutableList<CdnRecord>, path: String) {
        array.forEachIndexed { index, item ->
            walkPayload(item, records, "$path[$index]")
        }
    }

    private fun extractFromMpd(manifestXml: String): List<CdnRecord> {
        val records = mutableListOf<CdnRecord>()
        val document = try {
            val factory = DocumentBuilderFactory.newInstance()
            factory.isNamespaceAware = true
            val builder = factory.newDocumentBuilder()
            builder.parse(InputSource(StringReader(manifestXml)))
        } catch (_: Exception) {
            return records
        }

        val adaptations = document.getElementsByTagNameNS(MPD_NS, "AdaptationSet")
        for (i in 0 until adaptations.length) {
            val adaptation = adaptations.item(i) as? Element ?: continue
            val adaptationContentType = adaptation.getAttributeOrNull("contentType")
            val representations = adaptation.getElementsByTagNameNS(MPD_NS, "Representation")

            for (j in 0 until representations.length) {
                val rep = representations.item(j) as? Element ?: continue
                val baseUrls = rep.getElementsByTagNameNS(MPD_NS, "BaseURL")
                if (baseUrls.length == 0) continue
                val baseUrlText = baseUrls.item(0)?.textContent?.trim().orEmpty()
                if (baseUrlText.isEmpty()) continue

                addIfValid(
                    records,
                    CdnRecord(
                        url = baseUrlText,
                        source = "video_dash_manifest.BaseURL",
                        contentType = adaptationContentType ?: rep.getAttributeOrNull("mimeType"),
                        mimeType = rep.getAttributeOrNull("mimeType"),
                        representationId = rep.getAttributeOrNull("id"),
                        bandwidth = rep.getAttributeOrNull("bandwidth"),
                        width = rep.getAttributeOrNull("width"),
                        height = rep.getAttributeOrNull("height"),
                        codecs = rep.getAttributeOrNull("codecs"),
                    ),
                )
            }
        }
        return records
    }

    private fun addIfValid(records: MutableList<CdnRecord>, record: CdnRecord) {
        val candidate = record.url.trim().replace("&amp;", "&")
        if (!isHttpUrl(candidate)) return
        records.add(record.copy(url = candidate))
    }

    private fun isHttpUrl(url: String): Boolean {
        return try {
            val uri = URI(url)
            (uri.scheme == "http" || uri.scheme == "https") && !uri.host.isNullOrBlank()
        } catch (_: Exception) {
            false
        }
    }

    private fun JsonObject.getAsJsonPrimitiveOrNull(key: String) =
        this.get(key)?.takeIf { it.isJsonPrimitive }

    private fun Element.getAttributeOrNull(name: String): String? {
        val value = getAttribute(name).trim()
        return value.ifEmpty { null }
    }
}
