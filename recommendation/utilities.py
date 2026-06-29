import re

CATEGORIES = {
    'Cricket': ['cricket', 'ipl', 'dhoni', 'kohli', 'batsman', 'bowler', 't20', 'odi', 'match', 'wicket', 'world cup'],
    'Tech': ['tech', 'python', 'coding', 'ai', 'django', 'react', 'software', 'programming', 'developer', 'gadget', 'phone', 'computer', 'machine learning', 'data'],
    'Travel': ['travel', 'trip', 'journey', 'wanderlust', 'mountain', 'beach', 'hotel', 'flight', 'explore', 'nature', 'adventure', 'vacation'],
    'Food': ['food', 'recipe', 'cooking', 'delicious', 'yummy', 'dinner', 'lunch', 'breakfast', 'restaurant', 'cafe', 'paneer', 'biryani', 'masala'],
    'Entertainment': ['movie', 'song', 'music', 'dance', 'cinema', 'actor', 'actress', 'bollywood', 'hollywood', 'celebrity', 'drama', 'theatre'],
    'Fashion': ['fashion', 'style', 'dress', 'makeup', 'outfit', 'design', 'trend', 'wear', 'look', 'shopping', 'clothing'],
    'Finance': ['money', 'finance', 'stock', 'investment', 'market', 'crypto', 'bitcoin', 'saving', 'budget', 'business', 'wealth', 'economy'],
}

def detect_language(text):
    if not text:
        return 'en'
    # Hindi unicode range: 0900-097F
    if re.search(r'[\u0900-\u097F]', text):
        return 'hi'
    
    # Common Hinglish/transliterated words
    hinglish_words = {'kya', 'hai', 'bhai', 'yaar', 'aur', 'nhi', 'nahi', 'hua', 'tha', 'acha', 'theek', 'kam', 'log', 'ghar', 'chahiye', 'kar', 'karna'}
    words = re.findall(r'\b\w+\b', text.lower())
    if not words:
        return 'en'
    hinglish_count = sum(1 for w in words if w in hinglish_words)
    if hinglish_count > 1 or (hinglish_count / len(words) > 0.15):
        return 'hi'
        
    return 'en'

def classify_category(text):
    if not text:
        return 'General'
        
    text_lower = text.lower()
    best_category = 'General'
    max_matches = 0
    
    for category, keywords in CATEGORIES.items():
        matches = sum(len(re.findall(r'\b' + re.escape(kw) + r'\b', text_lower)) for kw in keywords)
        if matches > max_matches:
            max_matches = matches
            best_category = category
            
    return best_category

def analyze_sentiment(text):
    """
    Analyzes text and returns a float sentiment score between -1.0 (negative) and +1.0 (positive).
    If no text is provided, returns 0.0 (neutral).
    Uses a lexicon-based analysis containing common emotional keywords in English, Hindi, and Hinglish.
    """
    if not text:
        return 0.0
        
    text_lower = text.lower()
    
    # Positive words list (English, Hindi, Hinglish)
    positive_words = {
        'love', 'great', 'awesome', 'wonderful', 'beautiful', 'happy', 'good', 'best', 'cool',
        'perfect', 'amazing', 'nice', 'delicious', 'yummy', 'excellent', 'success', 'proud',
        'प्यार', 'सुंदर', 'अच्छा', 'बढ़िया', 'खूबसूरत', 'अद्भुत', 'शानदार', 'खुश', 'शुभ',
        'khubsurat', 'acha', 'badhiya', 'mast', 'gazab', 'sundar', 'dil khush', 'lajawab'
    }
    
    # Negative words list
    negative_words = {
        'hate', 'bad', 'worst', 'sad', 'terrible', 'awful', 'ugly', 'boring', 'fail', 'loss',
        'angry', 'pain', 'scam', 'fake', 'abusive', 'useless',
        'नफ़रत', 'बुरा', 'खराब', 'दुखी', 'गुस्सा', 'फेक', 'बकवास', 'आलसी',
        'nafrat', 'bura', 'kharab', 'bakwaas', 'useless', 'terrible', 'scam'
    }
    
    words = re.findall(r'\b\w+\b', text_lower)
    if not words:
        pos_emojis = ['❤️', '💖', '✨', '🔥', '🥰', '😍', '👍', '😊', '🥳', '🌟']
        neg_emojis = ['😭', '😡', '😠', '👎', '💔', '😞', '😟', '🤮', '🤬']
        
        pos_count = sum(text.count(e) for e in pos_emojis)
        neg_count = sum(text.count(e) for e in neg_emojis)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        return float(pos_count - neg_count) / total
        
    pos_count = sum(1 for w in words if w in positive_words)
    neg_count = sum(1 for w in words if w in negative_words)
    
    # Add emoji sentiment boost
    pos_emojis = ['❤️', '💖', '✨', '🔥', '🥰', '😍', '👍', '😊', '🥳', '🌟']
    neg_emojis = ['😭', '😡', '😠', '👎', '💔', '😞', '😟', '🤮', '🤬']
    pos_count += sum(text.count(e) for e in pos_emojis)
    neg_count += sum(text.count(e) for e in neg_emojis)
    
    total = pos_count + neg_count
    if total == 0:
        return 0.0
        
    return float(pos_count - neg_count) / total
