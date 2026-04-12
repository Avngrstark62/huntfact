import time
import asyncio
import json
from agents.ClaimExtractor import extract_claims

transcribed_text = """
Creator: Today I want to talk about something really important. Did you know that drinking 8 glasses of water a day is actually a myth? 
Other Person: Really? I thought that was real.
Creator: Yeah, most people don't need that much. The actual amount depends on your body weight and activity level. 
Creator: Also, I've been doing research and found that eating eggs for breakfast actually increases your metabolism by 30%.
Other Person: That's interesting!
Creator: And one more thing - sleeping more than 9 hours a day can actually make you more tired, not less.
"""

if __name__ == "__main__":
    start_time = time.perf_counter()
    
    result = asyncio.run(extract_claims(transcribed_text))
    
    end_time = time.perf_counter()
    execution_time_ms = (end_time - start_time) * 1000
    
    print(f"\nClaim Extraction Result (took {execution_time_ms:.2f}ms):")
    print("-" * 50)
    print(json.dumps(result.model_dump(), indent=2))
