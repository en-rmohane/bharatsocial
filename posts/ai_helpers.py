import random
import re
import json
import urllib.request
import urllib.error
from django.conf import settings
from .fallback_composer import FALLBACK_COMPOSER

class AIPlatformConnector:
    """
    Modular Connector to interface with LLMs (Gemini, OpenAI, Claude, or Local Models).
    Integrates the Groq API for live generation, falling back gracefully to advanced
    semantic simulation templates on failure.
    """
    
    CAPTION_TEMPLATES = {
        'Travel': {
            'Short': {'en': "Lost in the right direction. 🏔️", 'hi': "सफ़र का मज़ा रास्तों में है। ✨", 'hinglish': "Safar khubsurat hai. 🌄"},
            'Medium': {'en': "Exploring the untouched corners of India. 🌄", 'hi': "भारत के खूबसूरत कोने। ⛰️", 'hinglish': "Exploring hidden gems. 💚"},
            'Long': {'en': "Wandering without a map. 🇮🇳", 'hi': "बिना किसी नक्शे के घूमना। ✨", 'hinglish': "Bina kisi plan ke bas nikal gaya. 🇮🇳"}
        },
        'Food': {
            'Short': {'en': "First we eat, then we do everything else. 🥘", 'hi': "स्वाद का असली धमाका! 😋", 'hinglish': "Khana pehle, baaki sab baad me! 🍕"},
            'Medium': {'en': "Indulging in authentic Indian flavours today. 🌶️", 'hi': "स्वादिष्ट खाने का आनंद लिया। 😍", 'hinglish': "Authentic Indian flavors at their best. 🥘✨"},
            'Long': {'en': "Food is an emotion. 🥘❤️", 'hi': "भोजन केवल पेट भरना नहीं, एक अहसास है। 🍽️❤️", 'hinglish': "Khana sirf pet bharne ke liye nahi, emotion hai. 🥘❤️"}
        },
        'Fashion': {
            'Short': {'en': "Confidence is the best outfit. 💅", 'hi': "सादगी में ही सबसे बड़ा स्टाइल है। ✨", 'hinglish': "Desi vibes, modern style! 🌟"},
            'Medium': {'en': "Blending traditional wear with a modern touch. 💃🌟", 'hi': "परंपरा और आधुनिकता का सुंदर मेल। 👑", 'hinglish': "Traditional dress me modern styling touch. 💫"},
            'Long': {'en': "Style is a way to say who you are without speaking. 👗✨", 'hi': "स्टाइल आपके व्यक्तित्व की गवाही देता है। 👑🇮🇳", 'hinglish': "Style wahi hai jo ap bina bole sab keh de. 👗✨"}
        },
        'Tech': {
            'Short': {'en': "Building the future, line by line. 💻", 'hi': "तकनीक से बदलती दुनिया। 🚀", 'hinglish': "Debugging my life and code... ☕"},
            'Medium': {'en': "Converting coffee into clean code. 🚀💻", 'hi': "चाय की चुस्कियों के साथ कोडिंग का मज़ा। ☕🖥️", 'hinglish': "Coding mode: ON. 💻🚀"},
            'Long': {'en': "Technology is best when it brings people together. 🖥️✨", 'hi': "तकनीक का असली महत्व तब है जब यह लोगों को जोड़े। 🚀💻", 'hinglish': "Technology jab logo ko connect kare, wahi sabse badi win hai. 🖥️💡"}
        },
        'Fitness': {
            'Short': {'en': "No excuses. Only results. 💪", 'hi': "स्वस्थ शरीर, प्रसन्न मन। 🧘‍♂️", 'hinglish': "Sweat now, shine later! 🔥"},
            'Medium': {'en': "Sweat is just fat crying. 🏋️‍♂️🔥", 'hi': "कठिन परिश्रम का कोई विकल्प नहीं। 🧘‍♂️💪", 'hinglish': "Consistency hi key hai dosto. 🏋️‍♂️🔥"},
            'Long': {'en': "It is you versus you. 🧘‍♂️💪", 'hi': "यह मुकाबला आपका खुद से है। 🧘‍♂️✨", 'hinglish': "Apki fight sirf khud se hai. 💪🧘‍♂️"}
        },
        'General': {
            'Short': {'en': "Just living life. ✨", 'hi': "ज़िंदगी एक खूबसूरत सफ़र है। ❤️", 'hinglish': "Good vibes and positive energy only! ✌️"},
            'Medium': {'en': "Cherishing little moments. ✨☀️", 'hi': "छोटी-छोटी खुशियों को समेटना। 🌻✨", 'hinglish': "Chhoti khushiyan, bade khwab. ❤️☀️"},
            'Long': {'en': "Life is like a camera: focus on what is important. ✨💖", 'hi': "ज़िंदगी एक कैमरे की तरह है। ✨💖", 'hinglish': "Zindagi bilkul camera jaisi hai. ✨💖"}
        }
    }

    TRENDING_HASHTAGS = {
        'Local': ['#ExploreIndia', '#VocalForLocal', '#MakeInIndia', '#DesiVibes', '#BharatSocial', '#SwachhBharat', '#MonsoonDiaries', '#ChaiTime', '#IndianTravel', '#LocalArtisans'],
        'Global': ['#Trending', '#ExplorePage', '#InstaGood', '#PhotoOfTheDay', '#Vibes', '#Innovate', '#CreatorEconomy', '#TechBreakthrough', '#FitnessMotivation', '#GlobalVibe']
    }

    HASHTAG_POOL = {
        'Travel': ['travelgram', 'wanderlust', 'safar', 'exploreindia', 'traveldiaries', 'indiatravel', 'beautifuldestinations', 'naturelovers', 'lonelyplanet', 'indiatourism'],
        'Food': ['foodie', 'instafood', 'desikhana', 'foodlove', 'delhifoodie', 'mumbaifoodie', 'indiancuisine', 'delicious', 'streetfoodindia', 'gharkakhana'],
        'Fashion': ['style', 'ootd', 'fashionblogger', 'desivibes', 'ethnicwear', 'instafashion', 'lookbook', 'streetstyle', 'sareelove', 'kurtaoutfit'],
        'Tech': ['technews', 'gadgets', 'coding', 'developer', 'startup', 'innovation', 'futuretech', 'geek', 'programmer', 'softwareengineer'],
        'Fitness': ['workout', 'gymlife', 'fitnessmotivation', 'healthyindia', 'yoga', 'fitfam', 'discipline', 'healthylifestyle', 'fitindia', 'pranayama'],
        'General': ['bharatsocial', 'trending', 'picoftheday', 'mood', 'dost', 'zindagi', 'goodvibes', 'foryou', 'hindustani', 'inspiration']
    }

    TRANSLATIONS = {
        'hi': {'text': "यह आज बहुत ही शानदार अनुभव रहा।", 'lang_name': "Hindi (हिंदी)"},
        'pa': {'text': "ਇਹ ਅੱਜ ਬਹੁਤ ਹੀ ਵਧੀਆ ਅਨੁਭਵ ਰਿਹਾ।", 'lang_name': "Punjabi (ਪੰਜਾਬੀ)"},
        'mr': {'text': "आजचा अनुभव खरोखरच अप्रतिम होता.", 'lang_name': "Marathi (मराठी)"},
        'bn': {'text': "আজকের অভিজ্ঞতা সত্যিই দারুণ ছিল।", 'lang_name': "Bengali (বাংলা)"},
        'ta': {'text': "இன்றைய அனுபவம் மிகவும் அற்புதம்.", 'lang_name': "Tamil (தமிழ்)"},
        'te': {'text': "ఈరోజు అనుభవం నిజంగా అద్భుతం.", 'lang_name': "Telugu (తెలుగు)"},
        'kn': {'text': "ಇಂದಿನ ಅನುಭವ ನಿಜಕ್ಕೂ ಅದ್ಭುತವಾಗಿತ್ತು.", 'lang_name': "Kannada (ಕನ್ನಡ)"}
    }

    @classmethod
    def call_groq_api(cls, prompt, system_prompt=None, max_tokens=1000):
        api_key = getattr(settings, 'GROQ_API_KEY', '')
        if not api_key:
            print("[AIPlatformConnector] GROQ_API_KEY is not set.")
            return None
            
        url = "https://api.groq.com/openai/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": "llama3-8b-8192",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5.0) as response:
                res_body = response.read().decode('utf-8')
                res_json = json.loads(res_body)
                content = res_json['choices'][0]['message']['content']
                return content.strip()
        except Exception as e:
            print(f"[AIPlatformConnector] Groq API call failed: {e}")
            return None

    _selected_ollama_model = None

    @classmethod
    def get_ollama_model(cls):
        if cls._selected_ollama_model:
            return cls._selected_ollama_model
        default_model = getattr(settings, 'OLLAMA_MODEL', 'llama3:latest')
        url = getattr(settings, 'OLLAMA_API_URL', 'http://localhost:11434/v1/chat/completions')
        if "localhost" not in url and "127.0.0.1" not in url:
            cls._selected_ollama_model = default_model
            return default_model
            
        try:
            base_url = url.split('/v1/')[0]
            tags_url = f"{base_url}/api/tags"
            req = urllib.request.Request(tags_url, method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as response:
                data = json.loads(response.read().decode('utf-8'))
                models = [m['name'] for m in data.get('models', [])]
                if models:
                    preferences = ['llama3.2:1b', 'llama3.2:latest', 'llama3:latest']
                    for pref in preferences:
                        for m in models:
                            if m == pref or m.startswith(pref + ":") or pref.startswith(m + ":"):
                                cls._selected_ollama_model = m
                                return m
                    cls._selected_ollama_model = models[0]
                    return models[0]
        except Exception as e:
            print(f"[AIPlatformConnector] Error querying local Ollama models: {e}")
        cls._selected_ollama_model = default_model
        return default_model

    @classmethod
    def call_ollama_api(cls, prompt, system_prompt=None, max_tokens=1000):
        url = getattr(settings, 'OLLAMA_API_URL', 'http://localhost:11434/v1/chat/completions')
        model = cls.get_ollama_model()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60.0) as response:
                res_body = response.read().decode('utf-8')
                res_json = json.loads(res_body)
                content = res_json['choices'][0]['message']['content']
                return content.strip()
        except Exception as e:
            print(f"[AIPlatformConnector] Ollama API call failed: {e}")
            return None

    @classmethod
    def format_fallback_keywords(cls, keywords, lang):
        if not keywords:
            return ""
        words = [w.strip() for w in keywords.replace(',', ' ').split() if w.strip()]
        if not words:
            return ""
        if len(words) == 1:
            return words[0]
        elif len(words) == 2:
            connective = " और " if lang == 'hi' else " and "
            return f"{words[0]}{connective}{words[1]}"
        else:
            connective = " और " if lang == 'hi' else " and "
            return ", ".join(words[:-1]) + f"{connective}{words[-1]}"

    @classmethod
    def generate_captions(cls, category, keywords, length, language):
        lang_instruction = "English"
        if language == 'hi':
            lang_instruction = "Hindi (pure Devanagari script or mixed as appropriate)"
        elif language == 'hinglish':
            lang_instruction = "Hinglish (Hindi written using Latin/English alphabet script)"
            
        # Randomly select a tone to guarantee that the LLM generates a completely unique style each time
        tones = ['aesthetic', 'poetic', 'witty', 'bold', 'inspirational', 'casual', 'minimalist', 'vibrant', 'storytelling', 'thoughtful']
        selected_tone = random.choice(tones)
        
        prompt = (
            f"Generate a single premium social media caption in {lang_instruction} for a post. "
            f"Category of the post: {category}. "
            f"The style and tone should be '{selected_tone}'. "
            f"Relevant keywords: {keywords or 'none'}. "
            f"The length should be '{length}' (Short: 1 quick punchy line/sentence; Medium: 2-3 engaging sentences; Long: a detailed paragraph with paragraphs/bullets). "
            f"Add appropriate emojis to make it look active and premium. "
            f"CRITICAL: Always generate a completely new, unique, and highly creative caption. Never reuse or repeat previous typical templates or sentences. Ensure the phrasing, structure, vocabulary, and emojis are fresh, varied, and unique every time. "
            f"Return ONLY the final caption text. Do not put quotes around it. Do not include introductory or concluding words."
        )
        
        # Tailor the system prompt based on requested length to enforce strict limits
        if length == 'Short':
            system_prompt = (
                "You are an expert social media creator. Generate a highly punchy, SINGLE sentence caption. "
                "CRITICAL: Always generate a completely new, unique, and creative caption. Never output more than 1 sentence or 20 words. "
                "Return ONLY the caption text. Do not add introductions, explanations, or quotes."
            )
        elif length == 'Medium':
            system_prompt = (
                "You are an expert social media creator. Generate a concise 2-3 sentence caption. "
                "CRITICAL: Always generate a completely new, unique, and creative caption. Never output more than 3 sentences or 45 words. "
                "Return ONLY the caption text. Do not add introductions, explanations, or quotes."
            )
        else:
            system_prompt = (
                "You are an expert social media creator. Generate a detailed paragraph with bullet points. "
                "CRITICAL: Always generate a completely new, unique, and creative caption. Maximum 100 words. "
                "Return ONLY the caption text. Do not add introductions, explanations, or quotes."
            )
        
        # Fetch positive and negative user feedback for in-context learning
        try:
            from .models import AICaptionFeedback
            pos_feedbacks = AICaptionFeedback.objects.filter(category=category, rating__gt=0).order_by('-created_at')[:3]
            neg_feedbacks = AICaptionFeedback.objects.filter(category=category, rating__lt=0).order_by('-created_at')[:3]
            
            feedback_instructions = []
            if pos_feedbacks.exists():
                feedback_instructions.append("Here are some examples of captions that users LIKED for this category. Learn from their style, tone, length, and emoji placements:")
                for fb in pos_feedbacks:
                    feedback_instructions.append(f"- \"{fb.generated_caption}\"")
                    
            if neg_feedbacks.exists():
                feedback_instructions.append("Here are some examples of captions that users DISLIKED/REJECTED for this category. Do NOT generate anything similar to these in phrasing, style, length, or structure:")
                for fb in neg_feedbacks:
                    feedback_instructions.append(f"- \"{fb.generated_caption}\"")
                    
            if feedback_instructions:
                feedback_context = "\n".join(feedback_instructions)
            else:
                feedback_context = ""
        except Exception as ex:
            print(f"[AIPlatformConnector] Error loading caption feedback: {ex}")
            feedback_context = ""

        if feedback_context:
            system_prompt = f"{system_prompt}\n\n{feedback_context}"

        # Try Groq first, then Ollama
        res = cls.call_groq_api(prompt, system_prompt=system_prompt)
        if not res:
            res = cls.call_ollama_api(prompt, system_prompt=system_prompt)
            
        if res:
            if (res.startswith('"') and res.endswith('"')) or (res.startswith("'") and res.endswith("'")):
                res = res[1:-1].strip()
            
            # Post-processing: Enforce strict length limits
            if length == 'Short':
                lines = [line.strip() for line in res.split('\n') if line.strip()]
                if lines:
                    first_line = lines[0]
                    sentences = re.split(r'(?<=[.!?])\s+', first_line)
                    res = sentences[0]
            elif length == 'Medium':
                sentences = re.split(r'(?<=[.!?])\s+', res.replace('\n', ' '))
                res = " ".join([s.strip() for s in sentences[:3] if s.strip()])
            return res
            
        # Sophisticated Dynamic Fallback Composition Engine
        composer = FALLBACK_COMPOSER.get(category, FALLBACK_COMPOSER['General'])
        lang_composer = composer.get(language, composer['en'])
        
        words_formatted = cls.format_fallback_keywords(keywords, language)
        opening = random.choice(lang_composer['openings'])
        closing = random.choice(lang_composer['closings'])
        
        # Inject randomized minor variants to ensure the combinatorial fallback doesn't repeat
        variations = {
            'en': [" Truly unforgettable.", " Loved every bit of it.", " Living the dream.", " Pure joy.", " Highly recommend."],
            'hi': [" सच में लाजवाब अनुभव।", " बहुत ही सुंदर दिन रहा।", " जीवन का एक हसीन पल।", " अद्भुत और शानदार।"],
            'hinglish': [" Sach me bahut hi mazedar tha.", " Super exciting experience raha.", " Dil khush ho gaya dekh kar.", " Full power energy."]
        }
        var_pool = variations.get(language, variations['en'])
        random_suffix = random.choice(var_pool)
        
        if length == 'Short':
            if words_formatted:
                middle = random.choice(lang_composer['middles']).format(words_comma=words_formatted)
                clean_opening = opening.rstrip('.!?')
                base_text = random.choice([middle, f"{clean_opening} ({words_formatted})"])
            else:
                base_text = opening
            base_text = base_text.rstrip('.!?') + "." + random_suffix
            sentences = re.split(r'(?<=[.!?])\s+', base_text)
            res_sentence = sentences[0]
            if words_formatted and words_formatted.lower() not in res_sentence.lower():
                res_sentence = f"{res_sentence.rstrip('.!?')} ({words_formatted})."
            return res_sentence
            
        elif length == 'Medium':
            if words_formatted:
                middle = random.choice(lang_composer['middles']).format(words_comma=words_formatted)
                base_text = f"{opening} {middle}{random_suffix} {closing}"
            else:
                base_text = f"{opening}{random_suffix} {closing}"
            return base_text
            
        else: # Long
            if words_formatted:
                middle = random.choice(lang_composer['middles']).format(words_comma=words_formatted)
            else:
                middle_str = {
                    'en': f"Enjoying the present moment and embracing life's journey.{random_suffix}",
                    'hi': f"वर्तमान पल का आनंद लेते हुए और जीवन की यात्रा को गले लगाते हुए।{random_suffix}",
                    'hinglish': f"Present moment ko enjoy karte hue aur life ki journey ko embrace karte hue.{random_suffix}"
                }
                middle = middle_str.get(language, middle_str['en'])
                
            bullets_dict = {
                'en': [
                    "✨ Focus on consistency and positive growth.",
                    "📍 Appreciating every single step of this process.",
                    "💫 Supporting local vibes and community love."
                ],
                'hi': [
                    "✨ निरंतरता और सकारात्मक बदलाव पर ध्यान दें।",
                    "📍 इस सफ़र के हर एक छोटे पड़ाव का आनंद लें।",
                    "💫 स्थानीय संस्कृति और कला को बढ़ावा दें।"
                ],
                'hinglish': [
                    "✨ Consistency aur positive growth par focus rakhein.",
                    "📍 Safar ke har ek step ko appreciate karna seekhein.",
                    "💫 Local community aur positive connections ko support karein."
                ]
            }
            bullets = bullets_dict.get(language, bullets_dict['en']).copy()
            random.shuffle(bullets)
            bullets_text = "\n".join(bullets)
            
            base_text = f"{opening}\n\n📍 {middle}\n\n{bullets_text}\n\n{closing}"
            return base_text

    @classmethod
    def generate_hashtags(cls, caption, category, keywords):
        prompt = (
            f"Generate a list of 5 to 8 highly relevant social media hashtags based on: \n"
            f"Caption: '{caption}'\n"
            f"Category: '{category}'\n"
            f"Keywords: '{keywords or 'none'}'\n"
            f"Format the output strictly as a space-separated list of hashtags (e.g., '#tag1 #tag2 #tag3'). "
            f"CRITICAL: Always generate a completely new, unique, and creative set of hashtags. Never reuse or repeat previous typical sets. "
            f"Do not include any other text."
        )
        system_prompt = "You are a professional social media optimizer. You only return a space-separated string of hashtags."
        
        res = cls.call_groq_api(prompt, system_prompt=system_prompt)
        if not res:
            res = cls.call_ollama_api(prompt, system_prompt=system_prompt)
            
        if res:
            tags = [t.strip() for t in res.split() if t.strip().startswith('#')]
            if tags:
                return tags[:8]
                
        # Fallback to local templates and keyword conversion
        derived_tags = []
        if keywords:
            # Clean and parse keywords
            raw_words = [w.strip().lower() for w in keywords.replace(',', ' ').split() if w.strip()]
            for word in raw_words:
                cleaned_word = re.sub(r'[^\w]', '', word)
                if cleaned_word:
                    derived_tags.append(f"#{cleaned_word}")
                    
        pool = cls.HASHTAG_POOL.get(category, cls.HASHTAG_POOL['General']).copy()
        random.shuffle(pool)
        
        # Merge derived tags from keywords first, then fill from the pool
        final_tags = []
        for t in derived_tags:
            if t not in final_tags:
                final_tags.append(t)
                
        for p in pool:
            formatted = f"#{p}" if not p.startswith('#') else p
            if formatted not in final_tags:
                final_tags.append(formatted)
                
        return final_tags[:8]

    @classmethod
    def get_trending_suggestions(cls, category):
        # Return highly dynamic suggestions with localized flair
        trends = {
            'Travel': ["Exploring ancient forts in Rajasthan", "Hidden beaches of South Goa", "Monsoon trekking in Western Ghats"],
            'Food': ["Chasing the best street food in Old Delhi", "Making direct single-estate filter coffee", "Styling traditional Gujarati thali"],
            'Fashion': ["Styling handloom sarees with modern jackets", "Minimalist kurtas for summer office wear", "Traditional silver jewellery look"],
            'Tech': ["Building robust local-first web applications", "Scaling databases with PgBouncer", "Designing active real-time push engines"],
            'Fitness': ["Early morning Yoga routines", "Pranayama techniques for stress relief", "Desi home-cooked high-protein diet charts"]
        }
        return trends.get(category, ["Daily mindfulness & positive mindset routines", "Exploring creative arts & design spaces"])

    @classmethod
    def improve_content(cls, text, tone='Friendly'):
        prompt = (
            f"Rewrite the following social media text to improve its engagement. Make it look premium. "
            f"Adopt the requested tone: '{tone}'. Keep all original emojis and hashtags unless you can add more appropriate ones. \n"
            f"Original text: '{text}'\n"
            f"Return ONLY the improved text."
        )
        system_prompt = "You are a copywriter assistant specializing in content improvement."
        res = cls.call_groq_api(prompt, system_prompt=system_prompt)
        if res:
            return res
        return f"{text} ✨"

    @classmethod
    def calculate_preview_score(cls, text, hashtags=None):
        cleaned = text.strip()
        word_count = len(cleaned.split())
        emoji_count = len(re.findall(r'[\u2600-\u27BF]|[\u1F300-\u1F6FF]|[\u1F900-\u1F9FF]', cleaned))
        tag_count = len(re.findall(r'#\w+', cleaned))
        
        # Readability
        readability = 90
        if word_count > 60: readability -= 15
        if word_count < 10: readability -= 10
        
        # Engagement
        engagement = 65
        if emoji_count >= 1 and emoji_count <= 4: engagement += 15
        else: engagement -= 5
        if tag_count >= 3 and tag_count <= 8: engagement += 15
        else: engagement -= 5
        engagement = min(max(engagement, 40), 99)
        
        # Hashtag score
        hashtag_score = 50
        if tag_count > 0:
            hashtag_score += min(tag_count * 8, 40)
        
        total_score = (readability + engagement + hashtag_score) / 3
        if total_score >= 82:
            reach = "High (उच्च)"
        elif total_score >= 65:
            reach = "Medium (मध्यम)"
        else:
            reach = "Low (कम)"
            
        return {
            'engagement_score': int(engagement),
            'readability_score': int(readability),
            'hashtag_score': int(hashtag_score),
            'reach_prediction': reach
        }

    @classmethod
    def translate_caption(cls, caption, target_lang):
        lang_names = {
            'hi': 'Hindi (हिंदी)',
            'pa': 'Punjabi (ਪੰਜਾਬੀ)',
            'mr': 'Marathi (मराठी)',
            'bn': 'Bengali (বাংলা)',
            'ta': 'Tamil (தமிழ்)',
            'te': 'Telugu (తెలుగు)',
            'kn': 'Kannada (ಕನ್ನಡ)'
        }
        lang_name = lang_names.get(target_lang, 'Original (मूल)')
        prompt = (
            f"Translate this social media caption into {lang_name}. "
            f"Preserve all emojis and hashtags exactly. Keep the tone natural and engaging. \n"
            f"Caption: '{caption}'\n"
            f"Return ONLY the translated caption."
        )
        system_prompt = "You are a translation assistant specializing in social media. You only output the translation."
        res = cls.call_groq_api(prompt, system_prompt=system_prompt)
        if res:
            return {
                'translated_text': res,
                'language_name': lang_name
            }
            
        trans_map = cls.TRANSLATIONS.get(target_lang)
        if trans_map:
            emojis = "".join(re.findall(r'[\u2600-\u27BF]|[\u1F300-\u1F6FF]|[\u1F900-\u1F9FF]', caption))
            tags = " ".join(re.findall(r'#\w+', caption))
            translated = f"{trans_map['text']}"
            if emojis: translated += f" {emojis}"
            if tags: translated += f"\n\n{tags}"
            return {
                'translated_text': translated,
                'language_name': trans_map['lang_name']
            }
        return {
            'translated_text': caption,
            'language_name': 'Original (मूल)'
        }

    @classmethod
    def suggest_comments(cls, caption, tone):
        comments = {
            'Friendly': [
                "This is absolutely beautiful! Keep shining! ✨❤️",
                "Such an amazing share, love the vibe! 🙌",
                "Superb post! Thanks for sharing this with us."
            ],
            'Professional': [
                "Excellent framing and composition. Great insights shared! 📈",
                "A highly professional presentation. Very engaging.",
                "Well articulated. Looking forward to your next release."
            ],
            'Humorous': [
                "This post deserves a national award and free samosas! 🏆😂",
                "I was having a boring day until I saw this masterclass. Haha!",
                "Who gave you permission to look this awesome? Call the police! 🚨"
            ]
        }
        return comments.get(tone, comments['Friendly'])

    @classmethod
    def generate_bio(cls, interests, style):
        prompt = (
            f"Generate a premium social media bio based on: \n"
            f"Interests: '{interests or 'general coding, travel, style'}'\n"
            f"Style: '{style}' (e.g., Professional, Creator, Student, Business)\n"
            f"Include appropriate emojis and structure it with line breaks. Keep it under 150 characters. "
            f"Return ONLY the generated bio text."
        )
        system_prompt = "You are a bio generator assistant. You write punchy, brief social media bios."
        res = cls.call_ollama_api(prompt, system_prompt=system_prompt)
        if res:
            if len(res) > 150:
                res = res[:147] + "..."
            return res
            
        bios = {
            'Professional': f"💼 Professional | Focus: {interests or 'Software & Tech'}\n🇮🇳 Proud Indian | Building scalable solutions.\n📬 DM for collaborations.",
            'Creator': f"✨ Digital Creator | Exploring {interests or 'Art, Travel & Food'}\n📸 Sharing snippets of my zindagi.\n👇 Check out my latest link!",
            'Student': f"🎓 Student Life | Exploring {interests or 'Coding & Finance'}\n📚 Learner | Dream big, work hard.\n📍 Bengaluru, India",
            'Business': f"🚀 Business | {interests or 'Premium Products & Handlooms'}\n📦 Delivering value across India.\n🌐 Visit our website to order!"
        }
        return bios.get(style, bios['Creator'])

    @classmethod
    def get_trend_discovery(cls, user_niche='General'):
        ideas = {
            'Travel': [
                {"title": "Hidden Waterfalls in Western Ghats", "concept": "Shoot a 15-second vertical transition reel with slow-mo water splashes.", "tags": ["#HiddenGems", "#MonsoonIndia"]},
                {"title": "Weekend Gateway from Mumbai/Delhi", "concept": "Create a carousel listing 5 budget stays with pricing cards.", "tags": ["#WeekendTrip", "#BudgetTravel"]}
            ],
            'Food': [
                {"title": "Local Street Food vs Premium restaurant taste", "concept": "Short video comparing filter coffee/cutting chai taste and atmosphere.", "tags": ["#ChaiLove", "#StreetFood"]},
                {"title": "5-Minute Quick Evening Desi Snacks", "concept": "Quick jump-cut editing showing preparation of bhel or bread-pakoda.", "tags": ["#QuickRecipes", "#SnackTime"]}
            ],
            'Fashion': [
                {"title": "Styling Khadi / Handlooms for office wear", "concept": "Transition reel swapping from casual styling to premium formal ethnic looks.", "tags": ["#VocalForLocal", "#OfficeWear"]},
                {"title": "Styling a single dupatta in 3 different styles", "concept": "Step-by-step styling guide with upbeat Indian background music.", "tags": ["#DesiLook", "#FashionHacks"]}
            ],
            'Tech': [
                {"title": "Why distributed sharding is hard but critical", "concept": "Draw a database architecture whiteboard overview showing Citus shard routers.", "tags": ["#CodingLife", "#SystemDesign"]},
                {"title": "Top AI developer extensions in 2026", "concept": "Fast-paced screen recording displaying autocomplete features.", "tags": ["#DeveloperTools", "#AIAssist"]}
            ],
            'Fitness': [
                {"title": "Yoga postures for desk workers", "concept": "Demonstrate 4 simple stretches that can be executed directly on a chair.", "tags": ["#YogaAtWork", "#FitIndia"]},
                {"title": "Healthy high-protein Indian breakfast options", "concept": "Infographic image listing sprouts, paneer, and sattu metrics.", "tags": ["#HealthyBreakfast", "#ProteinDiet"]}
            ],
            'General': [
                {"title": "My morning routine in summer", "concept": "A aesthetic slow-paced cinematic montage with relaxing sounds.", "tags": ["#MorningVibes", "#Aesthetic"]},
                {"title": "Review of the month's trending reads", "concept": "Overlay text containing favorite quotes from a selected book.", "tags": ["#Bookstagram", "#Inspiration"]}
            ]
        }
        return ideas.get(user_niche, ideas['General'])

    @classmethod
    def safety_filter(cls, text):
        prompt = (
            f"Analyze the following text for safety. Check if it contains spam phrases, offensive/abusive language, or scams/unverified financial offers. "
            f"Output the result strictly in JSON format with the following keys:\n"
            f"- 'is_safe': boolean\n"
            f"- 'warnings': array of strings (explaining why it is unsafe, or empty array if safe)\n"
            f"- 'flagged_phrases': array of strings (containing the offending substrings)\n"
            f"Text to analyze: '{text}'\n"
            f"Return ONLY the JSON object."
        )
        system_prompt = "You are a content moderation assistant. You output strictly JSON."
        res = cls.call_groq_api(prompt, system_prompt=system_prompt, max_tokens=200)
        if res:
            try:
                cleaned_res = res.strip()
                if cleaned_res.startswith("```"):
                    start = cleaned_res.find("{")
                    end = cleaned_res.rfind("}")
                    if start != -1 and end != -1:
                        cleaned_res = cleaned_res[start:end+1]
                data = json.loads(cleaned_res)
                if 'is_safe' in data:
                    return {
                        'is_safe': bool(data.get('is_safe', True)),
                        'warnings': list(data.get('warnings', [])),
                        'flagged_phrases': list(data.get('flagged_phrases', []))
                    }
            except Exception as e:
                print(f"[AIPlatformConnector] safety JSON parse failed: {e}")
                
        warnings = []
        is_safe = True
        flagged = []
        spam_patterns = [
            r'free gift card', r'claim your money', r'double your (cash|money|wealth)', 
            r'click here to win', r'guaranteed income', r'earn \$\d+ daily',
            r'घर बैठे पैसे कमाएं', r'फ्री उपहार'
        ]
        abuse_patterns = [
            r'\bbastard\b', r'\bidiot\b', r'\bchutiya\b', r'\bsaala\b', r'\bkamina\b', r'\bbhadwa\b'
        ]
        scam_patterns = [
            r'whatsapp me at \+\d+', r'dm to buy crypto', r'send money to start',
            r'secret mining trick'
        ]
        for p in spam_patterns:
            if re.search(p, text, re.IGNORECASE):
                warnings.append("Spam phrases detected. Try avoiding click-bait claims.")
                is_safe = False
                flagged.append(re.search(p, text, re.IGNORECASE).group())
        for p in abuse_patterns:
            if re.search(p, text, re.IGNORECASE):
                warnings.append("Offensive or abusive language detected. Maintain social guidelines.")
                is_safe = False
                flagged.append(re.search(p, text, re.IGNORECASE).group())
        for p in scam_patterns:
            if re.search(p, text, re.IGNORECASE):
                warnings.append("Scam or unverified financial offer patterns detected.")
                is_safe = False
                flagged.append(re.search(p, text, re.IGNORECASE).group())
                
        return {
            'is_safe': is_safe,
            'warnings': warnings,
            'flagged_phrases': flagged
        }
