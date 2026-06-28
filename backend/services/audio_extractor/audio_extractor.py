import asyncio
import logging
from typing import Dict, Optional
from urllib.parse import urlparse

from logging_config import get_logger, log_event, sanitize_url

logger = get_logger("services.audio_extractor.audio_extractor")


def _validate_url(url: str) -> bool:
    """Validate URL format."""
    if not url or not isinstance(url, str):
        return False
    try:
        result = urlparse(url)
        return bool(result.scheme and result.netloc)
    except Exception:
        return False


async def extract_audio(
    url: str,
    timeout: int = 60,
    bitrate: str = "128k"
) -> Dict[str, Optional[bytes | str]]:
    """
    Extract audio from URL and convert to MP3.

    Tries fast path (copy AAC) -> converts to MP3 in-memory.
    Falls back to direct MP3 encode if needed.

    Args:
        url: URL to extract audio from
        timeout: Timeout in seconds for each ffmpeg process
        bitrate: MP3 bitrate (default: 128k)

    Returns:
        Dictionary with keys:
        - audio: bytes of MP3 audio (None if failed)
        - format: "mp3"
        - error: error message if failed (None if successful)
    """

    # Validate URL
    if not _validate_url(url):
        error_msg = f"Invalid URL format: {url}"
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Invalid CDN URL format for audio extraction",
            component="services.audio_extractor",
            cdn_link=sanitize_url(url),
            error_message=error_msg,
        )
        return {"audio": None, "format": "mp3", "error": error_msg}

    # ---------- FAST PATH (copy AAC) ----------
    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-loglevel", "error",
            "-i", url,
            "-vn",
            "-acodec", "copy",
            "-f", "adts",
            "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            aac_audio, err = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            log_event(
                logger,
                level=logging.WARNING,
                event="task.timed_out",
                status="timed_out",
                message="Fast path ffmpeg timeout; falling back",
                component="services.audio_extractor",
                timeout_seconds=timeout,
                cdn_link=sanitize_url(url),
            )
            aac_audio = None

        if aac_audio:
            # Convert AAC -> MP3 in-memory
            try:
                convert = await asyncio.create_subprocess_exec(
                    "ffmpeg",
                    "-loglevel", "error",
                    "-f", "aac",
                    "-i", "pipe:0",
                    "-f", "mp3",
                    "-ab", bitrate,
                    "pipe:1",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                try:
                    mp3_audio, err = await asyncio.wait_for(
                        convert.communicate(input=aac_audio),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    convert.kill()
                    await convert.wait()
                    log_event(
                        logger,
                        level=logging.WARNING,
                        event="task.timed_out",
                        status="timed_out",
                        message="AAC to MP3 conversion timeout; falling back",
                        component="services.audio_extractor",
                        timeout_seconds=timeout,
                        cdn_link=sanitize_url(url),
                    )
                    mp3_audio = None

                if mp3_audio:
                    log_event(
                        logger,
                        level=logging.INFO,
                        event="task.succeeded",
                        status="succeeded",
                        message="Audio extracted via fast path",
                        component="services.audio_extractor",
                        cdn_link=sanitize_url(url),
                        result_summary={"audio_bytes": len(mp3_audio)},
                    )
                    return {"audio": mp3_audio, "format": "mp3", "error": None}
            except Exception as e:
                log_event(
                    logger,
                    level=logging.WARNING,
                    event="task.failed",
                    status="retrying",
                    message="AAC to MP3 conversion failed; falling back",
                    component="services.audio_extractor",
                    cdn_link=sanitize_url(url),
                    error_type=type(e).__name__,
                    error_message=str(e),
                )

    except FileNotFoundError as e:
        error_msg = f"FFmpeg not found: {e}"
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="FFmpeg not found",
            component="services.audio_extractor",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        return {"audio": None, "format": "mp3", "error": error_msg}
    except Exception as e:
        log_event(
            logger,
            level=logging.WARNING,
            event="task.failed",
            status="retrying",
            message="Fast path failed; falling back",
            component="services.audio_extractor",
            cdn_link=sanitize_url(url),
            error_type=type(e).__name__,
            error_message=str(e),
        )

    log_event(
        logger,
        level=logging.INFO,
        event="task.retrying",
        status="retrying",
        message="Fast path failed, using direct MP3 fallback",
        component="services.audio_extractor",
        cdn_link=sanitize_url(url),
    )

    # ---------- FALLBACK (direct MP3 encode) ----------
    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-loglevel", "error",
            "-i", url,
            "-vn",
            "-f", "mp3",
            "-ab", bitrate,
            "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            mp3_audio, err = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            error_msg = f"Audio extraction timeout after {timeout}s"
            log_event(
                logger,
                level=logging.ERROR,
                event="task.timed_out",
                status="timed_out",
                message="Fallback audio extraction timeout",
                component="services.audio_extractor",
                timeout_seconds=timeout,
                cdn_link=sanitize_url(url),
                error_message=error_msg,
            )
            return {"audio": None, "format": "mp3", "error": error_msg}

        if process.returncode != 0:
            stderr_text = err.decode("utf-8", errors="ignore")
            error_msg = f"FFmpeg failed: {stderr_text}"
            log_event(
                logger,
                level=logging.ERROR,
                event="task.failed",
                status="failed",
                message="Fallback ffmpeg returned non-zero exit",
                component="services.audio_extractor",
                cdn_link=sanitize_url(url),
                return_code=process.returncode,
                error_message=error_msg,
            )
            return {"audio": None, "format": "mp3", "error": error_msg}

        if not mp3_audio:
            error_msg = "FFmpeg produced no output"
            log_event(
                logger,
                level=logging.ERROR,
                event="task.failed",
                status="failed",
                message="Fallback ffmpeg produced no output",
                component="services.audio_extractor",
                cdn_link=sanitize_url(url),
                return_code=process.returncode,
                error_message=error_msg,
            )
            return {"audio": None, "format": "mp3", "error": error_msg}

        log_event(
            logger,
            level=logging.INFO,
            event="task.succeeded",
            status="succeeded",
            message="Audio extracted via fallback",
            component="services.audio_extractor",
            cdn_link=sanitize_url(url),
            result_summary={"audio_bytes": len(mp3_audio)},
        )
        return {"audio": mp3_audio, "format": "mp3", "error": None}

    except FileNotFoundError as e:
        error_msg = f"FFmpeg not found: {e}"
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="FFmpeg not found in fallback",
            component="services.audio_extractor",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        return {"audio": None, "format": "mp3", "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error during audio extraction: {e}"
        log_event(
            logger,
            level=logging.ERROR,
            event="task.failed",
            status="failed",
            message="Unexpected fallback audio extraction error",
            component="services.audio_extractor",
            cdn_link=sanitize_url(url),
            error_type=type(e).__name__,
            error_message=error_msg,
            exc_info=True,
        )
        return {"audio": None, "format": "mp3", "error": error_msg}
