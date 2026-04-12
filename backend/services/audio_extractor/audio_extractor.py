import subprocess


def extract_audio(url: str, timeout: int = 15):
    """
    Always returns MP3 bytes.
    Tries fast path (copy AAC) → converts to MP3 in-memory.
    Falls back to direct MP3 encode if needed.
    """

    # ---------- FAST PATH (copy AAC) ----------
    try:
        process = subprocess.Popen(
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
        )

        aac_audio, err = process.communicate(timeout=timeout)

        if process.returncode == 0 and aac_audio:
            # 🔥 Convert AAC → MP3 in-memory
            convert = subprocess.Popen(
                [
                    "ffmpeg",
                    "-loglevel", "error",
                    "-f", "aac",
                    "-i", "pipe:0",
                    "-f", "mp3",
                    "-ab", "128k",
                    "pipe:1"
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            mp3_audio, err = convert.communicate(input=aac_audio)

            if convert.returncode == 0 and mp3_audio:
                return mp3_audio, "mp3"

    except Exception:
        pass

    print("Fast path failed, falling back to direct MP3 encode...")

    # ---------- FALLBACK (direct MP3 encode) ----------
    process = subprocess.Popen(
        [
            "ffmpeg",
            "-loglevel", "error",
            "-i", url,
            "-vn",
            "-f", "mp3",
            "-ab", "128k",
            "pipe:1"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    mp3_audio, err = process.communicate(timeout=timeout)

    if process.returncode != 0:
        raise Exception(f"FFmpeg failed: {err.decode()}")

    return mp3_audio, "mp3"
