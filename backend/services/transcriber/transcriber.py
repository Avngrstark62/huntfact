import io
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI()

def transcribe_audio(audio_bytes: bytes, fmt: str) -> str:
    """
    audio_bytes: raw bytes from extract_audio
    fmt: "aac" or "mp3"
    returns: transcript string
    """

    # Map extension properly
    ext = "aac" if fmt == "aac" else "mp3"

    # Wrap bytes as file-like object
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = f"audio.{ext}"  # IMPORTANT for OpenAI

    transcript = client.audio.transcriptions.create(
        model="gpt-4o-transcribe",  # best current model
        file=audio_file
    )

    return transcript.text
