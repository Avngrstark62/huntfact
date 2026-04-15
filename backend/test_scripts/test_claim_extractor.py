import time
import asyncio
import json
from agents.ClaimExtractor import extract_claims, Utterance
from agents.TranslationAgent import translate_text
from agents.ClaimVerifier import verify_claim

from datetime import datetime

# transcribed_text = """Hello, Today I want to talk about something really important. Did you know that drinking 8 glasses of water a day is actually a myth? Really? I thought that was real. Yeah, most people don't need that much. The actual amount depends on your body weight and activity level. Also, I've been doing research and found that eating eggs for breakfast actually increases your metabolism by 30%. That's interesting! And one more thing - sleeping more than 9 hours a day can actually make you more tired, not less.
# """

# transcribed_text = """
# تو حالات کا حل کسی سیاسی پارٹی کے پاس نہیں ہے حالات کا حل اطاعت دین میں ہے حالات کا حل اقامت دین میں ہے لاللن ٹاپ جیسے بڑی میڈیا ہاؤس نے اس جاہل آدمی کو بناتا ڈیبیٹ پر اتنا بڑا پلیٹ فارم دے دیا اسے آگے اس نے اور بھی گھڑیا باتیں کرئی ہیں پر اب اس نے کیا بولا کہ بھائی مذہبی دین کے علاوہ اور کسی کا پاس حالات کا سلوشن نہیں ہے ایسی بکواس انہیں کے جماعت کے ایک اور مولانا نے کری تھی تب میں نے کیا جواب دیا تھا دیکھ لیجی آپ لوگ تو دیکھتے ہیں کہ خدا نے انڈیا کے مسلم پوبلیشن کی کتنی مدد کری ہے نائنٹین نائنٹیز کے راوند مسلم کمیونٹی کی فرٹیلٹی ریٹ تھی گریبن 4.5 اور اسی دوران مسلم سمدائے میں گریبن 40% چانس تھی کہ بچہ 5 سال کی عمر تک زندہ نہیں رہے گا پر پرابلم صرف بچوں کے موت کی نہیں تھی WHO کی ریپورٹ کے اگارڈنگ 1990 کے انڈیا میں اگر ایک لاکھ عورتیں بچوں کو جنم دے رہی ہیں تو ان میں سے 570 عورتوں کی موت ہو جاتی تھی اس سے میٹرنل مورٹالیٹی ریشو کہا جاتا ہے دوزار پندرہ سولہ آتے آتے چائل مورٹالیٹی اور میٹرنل مورٹالیٹی دونوں میں گریبن 50% کی گرابت دیکھی گئی اور یہ کسی خدا کی وجہ سے نہیں ہوا ہے اس کا پورا کرائیڈٹ جاتا ہے آنگن باڑی ورکرز کو جنہوں نے دیش کے گاؤں میں گلی محلو میں جا کر لوگوں کو فیملی پلیننگ پرائیمری ہیلتھ کے اور الگ الگ ویل فیر اسکیمنز کے بارے میں بتایا ہے تو بتاؤ بھائی حالات کا سولیوشن آپ کے اللہ نے دیا آپ کے مذہبی دین نے دیا یا پھر ہم لوگوں نے ہی خود پولیسی بنا کے حالات کا سولیوشن نکالا ہم یہ کہتے پھرتے رہے کہ ہمارا وطن ہمارے دین سے زیادہ مقدس ہے ہم نے یہ اعتراف کیا کہ سیکیلر نظام ہمارے نظام سے زیادہ مقدس ہے ہاں تو بھی ہے سیکیلر نظام زیادہ بہتر ہے یہ بات تو اکبر بھی سمجھ گئے تھے اس مفتی کی کیا عقاد جلال الدین محمد اکبر کے سامنے مذہبی دین والا دیش لو آپ سعودی عربیا جہاں میں سارے مسلمان جاتے ہیں متھا ٹیکنے وہ دیش خود ایک سیکیلر دیش پر ڈیپنڈ کرتا ہے اپنی سیکیورٹی کے لیے کیونکہ امریکہ یہ بات سمجھ گیا تھا کہ بھائی سیکیلرزم فالو کر کے ہی ہم آگے بڑھ سکتے ہیں یورپ یہ بات سمجھ گیا تھا کہ بھائی سیکیلرزم فالو کر کے ہی ہم آگے بڑھ سکتے ہیں سیکیلرزم کوئی مورل اوبلیگیشن نہیں ہے اگر آپ کو اپنی سماج کو آگے لے کے جانا ہے اور سشکت بنانا ہے کیا فلان دربار اگر شریعت کے قلعہ حکم دے کیا تم تسلیم کرو گے کیا تم تسلیم کرو گے کرنا پڑے گا میرے کنٹنجنسی کاشک کرنا پڑے گا سممیدان کے سامنے آپ کو اور آپ کے پورے جماعت کو سر جھکانا پڑے گا اگر کوئی سملینگی ہے تو آپ اس کو پتھر نہیں مار سکتے آپ کا دھرم چھوڑ کر کوئی میری طرح ناستک بن جائے تو اس کی حتیہ نہیں کر سکتے اور دربار نے تو ٹرپل طلاق کے خلاف حکمت دے دیا فالو کرنا پڑے گا سر جھکا کے چپچا فالو کرنا پڑے گا چائل میریج دے لو آپ مسلم پرسنل لاو کے انترکت ہوئی چائل میریج کو انڈیا میں لیگل پروٹیکشن مل جاتی ہے آج بھی دوہزار بائیس میں پنجاب ہائی کوٹ نے دی اور دوہزار پچیس میں انڈین سپریم کوٹ نے اس جسٹیفیکیشن کو صحیح ٹھہرا دیا یہ ہے ان کا مسلم پرسنل لاو جو کی ان کے مذہبی دین سے انسپائرڈ ہے اسد الدین وویسی وغیرہ کتنے ہی مسلم لیڈر ہیں کسی کو آپ نے سنا ہے جو اس بار میں بات کرنا چاہتا ہو کتنا مشکل ہے بھائی ایک امنمنٹ پیش کرو کہ بھائیہ مسلم پرسنل لاو کے تحت اب سے بچیوں کی شادی نہیں ہوگی یہ کوئی بہت بڑی بات ہے کیا اور جو مسلم بھائی بہن میری ویڈیو دیکھ رہے ہیں ان سے میں یہی کہنا چاہوں گا کہ اس طرح کے جو مفتی ہوتے ہیں ان کو کوئی ٹچ نہیں کر سکتا یہ بہت آلی شان زندگی چییں گے یہاں سے بھکر دوبائی چلا جائے گا یہ کچھ کر لے گا کوئی اریسٹ نہیں کرے گا پر ان کی باتیں سن کر زندگی حرام ہوگی آپ کی اور آپ کے پریوار والوں کی
# """

transcribed_text = {
  "utterances": [
    {
      "speaker": "A",
      "text": "तो हालात का हल किसी सियासी पार्टी के पास नहीं है। हालात का हल त दिन में है, हालात का हल दिन में है।",
      "start": 260,
      "end": 6460,
      "confidence": 0.9218128
    },
    {
      "speaker": "B",
      "text": "लल्लनटॉप जैसी बड़ी मीडिया हाउस ने इस जाहिल बुलाते इतना बड़ा प्लैटफार्म दे दिया। आगे इसमें और भी घटिया बात करी है। पर इसे क्या बोला की भाई बी के लावा किसी के पास हालात का सॉलूशन नहीं है। ऐसी बकवास जमा मैंने क्या जवाब दिया था। देख लीजिये। आप लोग तो देखते है की खुदा ने इंडिया के मुस्लिम पोपुलेशन की कितनी मदद की है। नाइनटीनइनीसकेराउंड मुस्लिम कम्यनिटी फर्टी रेट थी, करीबन फोर, प्वाइंट फाइव और उसी दौरान मुसलिम समुदाय में करीबन 40 परसेंट चांस दे बच्चा 5 साल की उम्र तक जिंदा नहीं रहेगा, पर प्रॉब्लम सिर्फ बच्चों की मौत की नहीं थी। डब्लूएचओ की रिपोर्ट के अकॉर्डिंग नाइनटी नाइनटी की इंडिया में अगर 1 लाख औरतें बच्चों को जन्म दे रही हैं तो उनमें से 570 औरतों की मौत हो जाती थी जिसे मेटरनल मोटेलिटी रेश्यो कहा जाता है। 2000 पंद्रह 16 आते आते चाइल्ड मोटेलिटी और मेटरनल मोटेलिटी दोनो में करीबन 50 पर्सेंट की गिरावट देखी गई। और यह किसी खुदा की वजह से नहीं हुआ है। इसका पूरा क्रेडिट ज्यादा है आंगनबाड़ी वर्कर्स को जिन्होंने देश के गाँव में, गली मोहल्लों में जाकर लोगों को फैमिली प्लानिंग, प्राइमरी, हेल्थ केयर और अलग अलग वेलफेयर स्कीम्स के बारे में बताया तो बताओ भाई हालात का सॉलूशन आपके ने दिया, आपको मजा भी दी ने दिया या फिर हम लोगो ने ही खुद पॉलिसी बना कर हालात का सॉल्यूशन निकाला।",
      "start": 6780,
      "end": 64070,
      "confidence": 0.9089281
    },
    {
      "speaker": "A",
      "text": "हम ये कहते फिरते रहे की हमारा वतन हमारे दिन ऐसे ज्यादा मुकद्दस है। हमने ये तारा किया की सेक्युलर निज़ाम हमारे निजाम से ज्यादा मुकद्दस है। हाँ तो",
      "start": 64269,
      "end": 70650,
      "confidence": 0.9154623
    },
    {
      "speaker": "B",
      "text": "भई है सेक्युलर निज़ाम ज्यादा बेहतर ये बात तो अकबर भी समझ गए थे, इस मुफ्त की, क्या होगा जलालुदीन मोहम्मद अकबर के सामने मजहबी दीन वाला देश लो साधु अरेबिया जहाँ पर सारे मुसलमान वो देश खुद 1 सेक्युलर देश पर अपनी सिक्योरिटी के लिए अमेरिका क्यूंकी अमेरिका ये बात समझ गया था की भाई सेकुलरिज्म फॉलो करके ही हम आगे बढ़ सकते है। यूरोप यह बात समझ गया था की भाई सेकुलरिज्म फॉलो करके ही हम आगे बढ़ सकते हैं। सेकुलरिज्म को मोरल ऑपलिकेशन नहीं है। वेरी प्रैक्टिकल चॉइस अगर आपको अपने समाज को आगे ले के जाना है और सशक्त बनाना है।",
      "start": 70690,
      "end": 96710,
      "confidence": 0.9095743
    },
    {
      "speaker": "A",
      "text": "क्या खुला दरबार अगर शरियत के खिलाफ हुकम दे, क्या तुम तसलीम करोगे, क्या तुम तसलीम करोगे",
      "start": 96920,
      "end": 101720,
      "confidence": 0.946485
    },
    {
      "speaker": "B",
      "text": "करना पड़ेगा, मेरे केस करना पड़ेगा, संविधान के सामने आपको और आपके पूरे जमात को सिर झुकाना पड़ेगा। अगर कोई समलैंगिक है तो आप कुसको पत्थर नहीं मार सकते, आपका धर्म छोड़ कर कोई मेरी तरह नास्तिक बन जाए तो उसकी हत्या नहीं कर सकते। और दरबार ने तो ट्रिपल तलाक के खिलाफ हुक्म दे दिया, फॉलो करना पड़ेगा, सर झुका के चुपचाप फॉलो करना पड़ेगा, चाइल्ड मैरेज डे ला मुस्लिम पर्सनल लॉ के अंतर्गत हुई चाइल्ड मैरेज को इंडिया में लीगल प्रोटेक्शन मिल जाती है। आज भी 2022 में पंजाब हाई कोर्ट ने दी और 2025 में इंडियन सुप्रीम कोर्ट ने उस जस्टिफिकेशन को सही ठहरा दिया। ये है उनका मुस्लिम पर्सनल लॉ जो की इनके मसबीदीनसेइंस्पायर्ड है अस दिन वैसी वगैरह कितने ही मुस्लिम लीडर है किसी को आपने सुना है जो इस बारे में बात करना चाहता हूँ कितना मुश्किल है भाई 1 अमेंडमेंट पेश करो की भैया मुस्लिम पर्सनल लॉ के तहत अब से बच्चियों की शादी नहीं होगी यह कोई बहुत बड़ी बात है क्या और जो मुस्लिम भाई बहन मेरी वीडियो देख रहे हैं उनसे मैं यही कहना चाहूंगा कि इस तरह के जो मुफ्ति होते हैं इनको कोई टच नहीं कर सकता ये बहुत आलिशान जिंदगी जिएंगे यहाँ से भर कर दुबई चला जाएगा, ये कुछ कर लेगा, कोई रस नहीं करेगा पर इनकी बातें सुनकर जिंदगी हराम होंगी आपकी और आपके परिवार वालों की।",
      "start": 102280,
      "end": 160150,
      "confidence": 0.9441397
    }
  ],
  "language_code": "hi",
  "confidence": 0.9235752,
  "audio_duration": 161
}

utterances = {
  "utterances": [
    {
      "speaker": "A",
      "text": "So, no political party has a solution to the situation. The solution to the situation is in the day, the solution to the situation is in the day.",
      "start": 260,
      "end": 6460,
      "confidence": 0.9218128
    },
    {
      "speaker": "B",
      "text": "A big media house like Lallantop has given such an ignorant person such a big platform. They have said even worse things in this. But what can be said is that apart from B, no one has a solution to the situation. What nonsense I had to respond to. Just look. You all see how much God has helped the Muslim population in India. Around nineteen ninety, the Muslim community's fertility rate was about four point five, and during that time, there was about a forty percent chance that a child in the Muslim community would not survive to the age of five, but the problem was not just the death of children. According to the WHO report, in nineteen ninety, if one hundred thousand women were giving birth to children in India, then five hundred seventy of those women would die, which is called the maternal mortality ratio. By two thousand fifteen and sixteen, a nearly fifty percent decline was observed in both child mortality and maternal mortality. And this did not happen because of any God. The entire credit goes to the Anganwadi workers who went into the villages, streets, and neighborhoods of the country to inform people about family planning, primary healthcare, and various welfare schemes. So tell me, brother, the solution to the situation was given by you, you were also given enjoyment, or did we ourselves create policies and find the solution to the situation?",
      "start": 6780,
      "end": 64070,
      "confidence": 0.9089281
    },
    {
      "speaker": "A",
      "text": "We kept saying that our homeland is more sacred than our religion. We made it clear that a secular system is more sacred than our system. Yes, so",
      "start": 64269,
      "end": 70650,
      "confidence": 0.9154623
    },
    {
      "speaker": "B",
      "text": "Well, the secular system is better, even Akbar understood this, what will happen in front of Jalaluddin Muhammad Akbar in a religious country like Saudi Arabia where all Muslims themselves rely on a secular country for their security because America understood that by following secularism, we can move forward. Europe understood that by following secularism, we can move forward. Secularism has no moral obligation. It is a very practical choice if you want to advance and empower your society.",
      "start": 70690,
      "end": 96710,
      "confidence": 0.9095743
    },
    {
      "speaker": "A",
      "text": "What if an open court gives a ruling against Sharia, will you accept it, will you accept it?",
      "start": 96920,
      "end": 101720,
      "confidence": 0.946485
    },
    {
      "speaker": "B",
      "text": "You will have to, in my case you will have to, you and your entire community will have to bow your heads before the constitution. If someone is homosexual, you cannot stone them, if someone leaves their religion and becomes an atheist like me, you cannot kill them. And the court has already given a ruling against triple talaq, you will have to follow it, bow your head and quietly follow it. Child marriage is legally protected in India under the Muslim Personal Law. Even today, in 2022, the Punjab High Court has given this, and in 2025, the Indian Supreme Court justified that. This is their Muslim Personal Law which is inspired by their religious leaders. How many Muslim leaders have you heard who want to talk about this? How difficult is it, brother, to present an amendment that says that under the Muslim Personal Law, from now on, girls will not be married? Is this a very big deal? And to the Muslim brothers and sisters watching my video, I would like to say that these kinds of muftis cannot be touched, they will live a very luxurious life, they will go to Dubai from here, they will do something, no one will do anything, but listening to their words will make your life miserable and that of your family.",
      "start": 102280,
      "end": 160150,
      "confidence": 0.9441397
    }
  ],
  "language_code": "hi",
  "confidence": 0.9235752,
  "audio_duration": 161
}


if __name__ == "__main__":
    start_time = time.perf_counter()
    
    # utterance_objects = [Utterance(**u) for u in utterances["utterances"]]
    # result = asyncio.run(extract_claims(utterance_objects))

    # result = asyncio.run(translate_text(transcribed_text))

    claim_to_verify = """In 1990, the Muslim community's fertility rate was about 4.5
, and there was a 40% chance that a child in the Muslim community would not survive to the age of five."""
    result = asyncio.run(verify_claim(claim_to_verify))

    end_time = time.perf_counter()
    execution_time_ms = (end_time - start_time) * 1000

    # filename = f"translation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    # with open(filename, "w", encoding="utf-8") as f:
        # json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)

    # print("claims_list:", result.claims_list)
    # print("opinions_list:", result.opinions_list)

    print(result)
