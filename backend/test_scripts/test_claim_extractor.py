import time
import asyncio
from agents.ClaimExtractor import extract_claims

transcribed_text = """
Creator: Today I want to talk about something really important. Did you know that drinking 8 glasses of water a day is actually a myth? 
Other Person: Really? I thought that was real.
Creator: Yeah, most people don't need that much. The actual amount depends on your body weight and activity level. 
Creator: Also, I've been doing research and found that eating eggs for breakfast actually increases your metabolism by 30%.
Other Person: That's interesting!
Creator: And one more thing - sleeping more than 9 hours a day can actually make you more tired, not less.
"""

# transcribed_text = """
# Here’s the same text, clearly separating **[Cleric/Other Person]** vs **[Creator]**:
#
# ---
#
# **[Cleric/Other Person]**
# “The solution to these conditions does not lie with any political party. The solution lies in obedience to religion. The solution lies in establishing religion.”
#
# ---
#
# **[Creator]**
# A big media house like Lallantop gave such a foolish person a huge platform on debate shows. He went on to say even more nonsense.
#
# **[Creator → quoting the cleric’s claim]**
# Now what did he say? He said that apart from religious faith, no one has a solution to these problems.
#
# ---
#
# **[Creator]**
# A similar statement was made by another cleric from their group earlier, and this is what I had replied:
#
# You people see how much God has helped the Muslim population in India. Around the 1990s, the fertility rate in the Muslim community was approximately 4.5. At the same time, there was around a 40% chance that a child would not survive until the age of 5.
#
# But the problem was not just child mortality. According to a WHO report, in 1990 in India, out of every 100,000 women giving birth, about 570 women died. This is called the maternal mortality ratio.
#
# By 2015–16, both child mortality and maternal mortality saw roughly a 50% decline. And this did not happen because of God. The entire credit goes to Anganwadi workers who went into villages, streets, and neighborhoods, and educated people about family planning, primary healthcare, and various welfare schemes.
#
# So tell me—did your Allah give the solution to these conditions? Did your religion give the solution? Or did we ourselves create policies and solve these problems?
#
# We kept saying that our nation is more sacred than our religion. We accepted that a secular system is more valuable than our own system. And yes, it is—secular systems are better. Even Akbar understood this. What is the stature of this cleric compared to Jalaluddin Muhammad Akbar?
#
# If you want a country based on religious law, then look at Saudi Arabia—where Muslims go for pilgrimage. That country itself depends on a secular nation for its security—because America understood that progress comes through secularism. Europe understood this as well.
#
# Secularism is not a moral obligation, but if you want to move your society forward and empower it, then it becomes necessary.
#
# ---
#
# **[Creator → hypothetical question to audience]**
# If a religious authority issues a ruling under Sharia, will you accept it?
#
# **[Creator answering]**
# You will have to—because under the Constitution, you and your entire community must bow your heads.
#
# ---
#
# **[Creator]**
# If someone is homosexual, you cannot stone them. If someone leaves your religion and becomes an atheist like me, you cannot kill them.
#
# The courts have already ruled against triple talaq—you will have to follow it quietly and respectfully.
#
# Take child marriage—under Muslim Personal Law, child marriages still get legal protection in India. Even in 2022, the Punjab High Court upheld this, and in 2025, the Indian Supreme Court also validated that justification. This is their Muslim Personal Law, which is inspired by their religion.
#
# Leaders like Asaduddin Owaisi and others—have you ever heard any of them talk about this issue? How difficult is it to introduce an amendment stating that under Muslim Personal Law, marriages of minor girls will no longer be allowed? Is that such a big thing?
#
# ---
#
# **[Creator → concluding message to audience]**
# And to my Muslim brothers and sisters watching this: people like these clerics cannot be touched. They will live luxurious lives, move abroad if needed, and nothing will happen to them. But if you follow their words, your life and your family’s life will become miserable.
#
# ---
# """

if __name__ == "__main__":
    # 1. Record the start time (in fractional seconds)
    start_time = time.perf_counter()

    # 2. Run the async function
    claims = asyncio.run(extract_claims(transcribed_text))

    # 3. Record the end time
    end_time = time.perf_counter()

    # 4. Calculate the difference and convert to milliseconds
    # (seconds * 1000 = milliseconds)
    execution_time_ms = (end_time - start_time) * 1000

    print(f"\nExtracted Claims (took {execution_time_ms:.2f}ms):")
    print("-" * 30)
    
    if not claims:
        print("No claims found.")
    else:
        for i, claim in enumerate(claims, 1):
            print(f"{i}. {claim}")

# if __name__ == "__main__":
#     claims = asyncio.run(extract_claims(transcribed_text)) # extract_claims(transcribed_text)
#     print("Extracted Claims:")
#     for i, claim in enumerate(claims, 1):
#         print(f"{i}. {claim}")
