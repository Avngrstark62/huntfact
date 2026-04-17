from services.audio_extractor import extract_audio
from services.transcriber.assemblyai import transcribe_audio
from services.reel_extractor import get_reel_video_url

import json
import time
from datetime import datetime

start_time = time.time()

# url = "https://www.instagram.com/reel/DWwYeJkiXSO"
# url = "https://www.instagram.com/reel/DWWNjCajCcK"
# url = "https://www.instagram.com/reel/DUFL0xADGDL"
# url = "https://www.instagram.com/reel/DWBrc8Ij6si"
# url = "https://www.instagram.com/reel/DTVPPD_EtOJ"
url = "https://www.instagram.com/reel/DXHQ-DLE5Ye"

cdn_link = get_reel_video_url(url)
print("cdn_link:", cdn_link)
elapsed = (time.time() - start_time) * 1000
print(f"✓ get_reel_video_url took {elapsed:.2f}ms")

result = extract_audio(cdn_link)
elapsed = (time.time() - start_time) * 1000
print(f"✓ extract_audio took {elapsed:.2f}ms")

if result.get("error"):
    print(f"✗ Error: {result['error']}")
else:
    audio = result.get("audio")
    fmt = result.get("format", "mp3")
    final_result = transcribe_audio(audio, fmt)
    elapsed = (time.time() - start_time) * 1000
    print(f"✓ transcribe_audio took {elapsed:.2f}ms")

    # Create filename (timestamped to avoid overwrite)
    filename = f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Save JSON (pretty formatted)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(final_result, f, ensure_ascii=False, indent=2)

    print(f"✓ Saved transcription to {filename}")
    # print(text)
