import subprocess
import logging
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _validate_url(url: str) -> bool:
    """Validate URL format."""
    if not url or not isinstance(url, str):
        return False
    try:
        result = urlparse(url)
        return bool(result.scheme and result.netloc)
    except Exception:
        return False


def extract_audio(
    url: str,
    timeout: int = 15,
    bitrate: str = "128k"
) -> Dict[str, Optional[bytes | str]]:
    """
    Extract audio from URL and convert to MP3.
    
    Tries fast path (copy AAC) → converts to MP3 in-memory.
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
        logger.error(error_msg)
        return {"audio": None, "format": "mp3", "error": error_msg}
    
    # ---------- FAST PATH (copy AAC) ----------
    try:
        with subprocess.Popen(
            [
                "ffmpeg",
                "-loglevel", "error",
                "-i", url,
                "-vn",
                "-acodec", "copy",
                "-f", "adts",
                "pipe:1"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        ) as process:
            aac_audio, err = process.communicate(timeout=timeout)
        
        if process.returncode == 0 and aac_audio:
            # Convert AAC → MP3 in-memory
            try:
                with subprocess.Popen(
                    [
                        "ffmpeg",
                        "-loglevel", "error",
                        "-f", "aac",
                        "-i", "pipe:0",
                        "-f", "mp3",
                        "-ab", bitrate,
                        "pipe:1"
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                ) as convert:
                    mp3_audio, err = convert.communicate(input=aac_audio, timeout=timeout)
                
                if convert.returncode == 0 and mp3_audio:
                    logger.info(f"Successfully extracted audio via fast path: {url}")
                    return {"audio": mp3_audio, "format": "mp3", "error": None}
            except subprocess.TimeoutExpired as e:
                logger.warning(f"AAC→MP3 conversion timeout, falling back: {e}")
            except Exception as e:
                logger.warning(f"AAC→MP3 conversion failed, falling back: {e}")
    
    except subprocess.TimeoutExpired as e:
        logger.warning(f"Fast path ffmpeg timeout, falling back: {e}")
    except FileNotFoundError as e:
        error_msg = f"FFmpeg not found: {e}"
        logger.error(error_msg)
        return {"audio": None, "format": "mp3", "error": error_msg}
    except Exception as e:
        logger.warning(f"Fast path failed, falling back: {e}")
    
    logger.info("Fast path failed, falling back to direct MP3 encode...")
    
    # ---------- FALLBACK (direct MP3 encode) ----------
    try:
        with subprocess.Popen(
            [
                "ffmpeg",
                "-loglevel", "error",
                "-i", url,
                "-vn",
                "-f", "mp3",
                "-ab", bitrate,
                "pipe:1"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        ) as process:
            mp3_audio, err = process.communicate(timeout=timeout)
        
        if process.returncode != 0:
            error_msg = f"FFmpeg failed: {err.decode('utf-8', errors='ignore')}"
            logger.error(error_msg)
            return {"audio": None, "format": "mp3", "error": error_msg}
        
        if not mp3_audio:
            error_msg = "FFmpeg produced no output"
            logger.error(error_msg)
            return {"audio": None, "format": "mp3", "error": error_msg}
        
        logger.info(f"Successfully extracted audio via fallback: {url}")
        return {"audio": mp3_audio, "format": "mp3", "error": None}
    
    except subprocess.TimeoutExpired as e:
        error_msg = f"Audio extraction timeout after {timeout}s: {e}"
        logger.error(error_msg)
        return {"audio": None, "format": "mp3", "error": error_msg}
    except FileNotFoundError as e:
        error_msg = f"FFmpeg not found: {e}"
        logger.error(error_msg)
        return {"audio": None, "format": "mp3", "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error during audio extraction: {e}"
        logger.error(error_msg, exc_info=True)
        return {"audio": None, "format": "mp3", "error": error_msg}
