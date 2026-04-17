from logging_config import setup_logging
setup_logging()

import asyncio
import json
import time
from config import settings
from services.extract_questions_queries.extract_questions_queries import extract_questions_queries

async def test_extract_questions():
    print(f"LLM Debug enabled: {settings.llm_debug}")
    
    utterances = [
 {
    "speaker": "A",
    "text": "Then, there is no solution to the situation from any political party. The solution to the situation is in the day, the solution is in the day.",
    "start": 260,
    "end": 6460,
    "confidence": 0.9218128
  },
  {
    "speaker": "B",
    "text": """Lallantop, a big media house like this, gave such a big platform to this illiterate man. He has spoken even more disgraceful things on it. But what was called to him, brother, a
part from B, no one has a solution to the situation. Such nonsense I have never heard; see for yourself. You all can see how much God has helped India's Muslim population. In 1990, the Musli
m community was 40 percent, roughly around 4.5 and at that time, there was about a 40 percent chance that a child would not survive past the age of 5. But the problem was not just about chil
dren dying. According to WHO reports, in 1999-2000, in India, if 100,000 women give birth to children, 570 of them die, which is called the maternal mortality ratio. By 2015-16, both child m
ortality and maternal mortality saw about a 50 percent decline. And this was not due to any divine reason. All credit goes to Anganwadi workers who went into villages and neighborhoods, info
rming people about family planning, primary health care, and various welfare schemes. So tell me, brother, who gave the solution to the situation? Did you enjoy it, or did we ourselves creat
e policies to find the solution?""",
    "start": 6780,
    "end": 64070,
    "confidence": 0.9089281
  },
  {
    "speaker": "A",
    "text": "We keep saying that our homeland is more sacred to us. We have vowed that the secular system is more sacred than our own system. So,",
    "start": 64269,
    "end": 70650,
    "confidence": 0.9154623
  },
  {
    "speaker": "B",
    "text": """The secular system is better, even Akbar understood this. This free, what will happen, Jalaluddin Muhammad Akbar’s time, you consider the country of religion, go to Arabia where
 all Muslims themselves, that country, are in a secular nation, for their security Americans, because America understood that brother, by following secularism alone, we can progress. Europe
understood that brother, by following secularism, we can progress. Secularism is not a moral obligation. It's a very practical choice if you want to move your society forward and empower it.
""",
    "start": 70690,
    "end": 96710,
    "confidence": 0.9095743
  },
  {
    "speaker": "A",
    "text": "If an open court orders against Sharia, will you accept it? Will you accept it? Will you accept it?",
    "start": 96920,
    "end": 101720,
    "confidence": 0.946485
  },
    {
    "speaker": "B",
    "text": """It will have to be done, I will have to file a case, you and your entire group will have to bow your heads before the Constitution. If someone is gay, you cannot stone them, if
your religion is abandoned and someone becomes an atheist like me, you cannot kill him. And the court has already ordered against triple talaq, you will have to follow it, bow your head and
silently follow it. Child marriage under Muslim personal law is legally protected in India. Even today, in 2022, the Punjab High Court issued such a verdict, and in 2025, the Indian Supreme
Court upheld that justification. This is their Muslim personal law, inspired by their religious books. How many Muslim leaders are there today who want to talk about this? How difficult is i
t, brother? Introduce an amendment that from now on, under Muslim personal law, child marriages will not happen. Is this not a big deal? And to the Muslim brothers and sisters watching my vi
deos, I want to say that these kinds of muftis cannot be touched. They will live a very luxurious life, fill themselves up and go to Dubai, they will do something, nobody will touch them. Bu
t by listening to their words, your life and your family's lives will be ruined.""",
    "start": 102280,
    "end": 160150,
    "confidence": 0.9441397
  }
]
    
    print("Input utterances:")
    print(json.dumps(utterances, indent=2, ensure_ascii=False))
    
    print("\n" + "="*50)
    print("Extracting questions and queries...")
    print("="*50 + "\n")
    
    start_time = time.time()
    try:
        items = await extract_questions_queries(utterances)
        elapsed = time.time() - start_time
        print(f"Latency: {elapsed:.2f}s\n")
        print(f"Extracted {len(items)} question/query items:")
        print(json.dumps(items, indent=2, ensure_ascii=False))
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Latency: {elapsed:.2f}s")
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_extract_questions())
