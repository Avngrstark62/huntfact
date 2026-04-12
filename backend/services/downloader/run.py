from downloader import extract_audio
from transcriber import transcribe_audio
import time
from reel_extractor import get_reel_video_url

start_time = time.time()

# url = "https://www.instagram.com/reel/DWwYeJkiXSO"
# url = "https://www.instagram.com/reel/DWWNjCajCcK"
# url = "https://www.instagram.com/reel/DUFL0xADGDL"
# url = "https://www.instagram.com/reel/DWBrc8Ij6si"
url = "https://www.instagram.com/reel/DTVPPD_EtOJ"

cdn_link = get_reel_video_url(url)
elapsed = (time.time() - start_time) * 1000
print(f"✓ get_reel_video_url took {elapsed:.2f}ms")

audio, fmt = extract_audio(cdn_link)
elapsed = (time.time() - start_time) * 1000
print(f"✓ extract_audio took {elapsed:.2f}ms")

text = transcribe_audio(audio, fmt)
elapsed = (time.time() - start_time) * 1000
print(f"✓ transcribe_audio took {elapsed:.2f}ms")

print(text)
