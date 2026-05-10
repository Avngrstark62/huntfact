from services.audio_extractor import extract_audio
from services.transcriber.openai import transcribe_audio
from services.translator.translator import translate_text
from services.reel_extractor import get_reel_video_url

import time
from datetime import datetime
import asyncio
from pathlib import Path

# url = "https://www.instagram.com/reel/DWwYeJkiXSO"
# url = "https://www.instagram.com/reel/DWWNjCajCcK"
# url = "https://www.instagram.com/reel/DUFL0xADGDL"
# url = "https://www.instagram.com/reel/DWBrc8Ij6si"
# url = "https://www.instagram.com/reel/DTVPPD_EtOJ"
# url = "https://www.instagram.com/reels/DVno2XZElSu"
# url = "https://www.instagram.com/reels/DWtydO4Essb"
# url = "https://www.instagram.com/reels/DXHSbajAh9j"
# url = "https://www.instagram.com/reel/DX-wL9IxoiV/"
url = "https://www.instagram.com/reel/DYGL3ueDssS"

async def main():
    start_time = time.time()

    cdn_link = get_reel_video_url(url)
    print("cdn_link:", cdn_link)
    elapsed = (time.time() - start_time) * 1000
    print(f"✓ get_reel_video_url took {elapsed:.2f}ms")

    result = await extract_audio(cdn_link)
    elapsed = (time.time() - start_time) * 1000
    print(f"✓ extract_audio took {elapsed:.2f}ms")

    if result.get("error"):
        print(f"✗ Error: {result['error']}")
    else:
        audio = result.get("audio")
        fmt = result.get("format", "mp3")
        transcript_text = await transcribe_audio(audio, fmt)
        elapsed = (time.time() - start_time) * 1000
        print(f"✓ transcribe_audio took {elapsed:.2f}ms")

        translated_text = await translate_text(transcript_text or "")
        elapsed = (time.time() - start_time) * 1000
        print(f"✓ translate_text took {elapsed:.2f}ms")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        transcriptions_dir = Path("transcriptions")
        translations_dir = Path("translations")
        transcriptions_dir.mkdir(parents=True, exist_ok=True)
        translations_dir.mkdir(parents=True, exist_ok=True)

        transcription_file = transcriptions_dir / f"transcription_{timestamp}.txt"
        translation_file = translations_dir / f"translation_{timestamp}.txt"

        with transcription_file.open("w", encoding="utf-8") as f:
            f.write(transcript_text or "")

        with translation_file.open("w", encoding="utf-8") as f:
            f.write(translated_text or "")

        print(f"✓ Saved transcription to {transcription_file}")
        print(f"✓ Saved translation to {translation_file}")

if __name__ == "__main__":
    asyncio.run(main())
