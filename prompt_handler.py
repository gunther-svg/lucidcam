import re

# Vague quality words deprecated in Lucy 2.5 prompting guide ("Common prompt mistakes")
VAGUE_QUALITY_WORDS = {
    "realistic", "photorealistic", "cinematic", "seamless", "beautiful", 
    "high quality", "ultra high quality", "4k", "8k", "hd", "hyperrealistic",
    "natural", "perfect"
}

# Specific clothing-only keywords
CLOTHING_SPECIFIC_KEYWORDS = {
    "shirt", "pants", "suit", "dress", "tuxedo", "wear", "wearing", "outfit", 
    "tshirt", "t-shirt", "jeans", "coat", "sweater", "blouse", "skirt", 
    "tie", "glasses", "sunglasses", "scarf", "cloak", "uniform", "vest"
}

# Subject / Character keywords
CHARACTER_KEYWORDS = {
    "person", "man", "woman", "boy", "girl", "character", "chef", "bear", "dog", 
    "cat", "robot", "cyborg", "knight", "astronaut", "explorer", "statue", "capybara"
}

SCENE_KEYWORDS = {
    "aesthetic", "painting", "style", "scene", "background", "neon", "cyberpunk", 
    "drawing", "sketch", "art", "oil painting", "watercolor", "illustration",
    "lighting", "environment", "anime", "charcoal"
}

REMOVE_KEYWORDS = {"remove", "delete", "erase", "take away", "clear"}
ADD_KEYWORDS = {"add", "attach", "put", "place", "insert", "give"}
BACKGROUND_KEYWORDS = {"background", "environment", "scenery", "setting", "room", "location"}

# Feature indicators for character replacer identification features
FEATURE_INDICATORS = {
    "keeping", "features", "details", "hair", "eyes", "face", "outfit", 
    "beard", "glasses", "smile", "earrings", "skin", "jacket", "mustache"
}

def clean_vague_words(text: str) -> str:
    """
    Strip process language and vague quality buzzwords deprecated in the Lucy 2.5 guide.
    Words like 'realistic', 'cinematic', 'seamless', 'high quality' add no detail and make output unpredictable.
    """
    pattern = re.compile(r'\b(' + '|'.join(re.escape(w) for w in VAGUE_QUALITY_WORDS) + r')\b', re.IGNORECASE)
    cleaned = pattern.sub('', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = re.sub(r',\s*,', ',', cleaned).strip(', ')
    return cleaned

def is_feature_list(text: str) -> bool:
    """
    Detect if user prompt is describing identification features for character replacement.
    E.g., 'short curly black hair, gold earrings, green jacket, warm smile'
    """
    text_lower = text.lower()
    if any(text_lower.startswith(prefix) for prefix in ["keeping", "features:", "details:", "with features:", "with details:"]):
        return True
    
    # Check if multiple comma-separated features are listed with feature keywords
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if len(parts) >= 2:
        words = set(re.findall(r'\b\w+\b', text_lower))
        if len(words.intersection(FEATURE_INDICATORS)) >= 1:
            return True
            
    return False

def clean_feature_text(text: str) -> str:
    """Clean feature list for incorporation into Lucy 2.5 character replacement template."""
    clean = re.sub(r'^(features|with features|details|with details|keeping|keeping their|their|with)\s*:\s*', '', text, flags=re.IGNORECASE).strip()
    if clean.lower().startswith("keeping their "):
        clean = clean[14:].strip()
    elif clean.lower().startswith("keeping "):
        clean = clean[8:].strip()
    elif clean.lower().startswith("their "):
        clean = clean[6:].strip()
    return clean

def capitalize_first(text: str) -> str:
    """Ensure first character of text is capitalized."""
    if not text:
        return text
    return text[0].upper() + text[1:]

def generate_prompt(user_text: str, has_reference_image: bool) -> str:
    """
    Format raw user input text into an optimized prompt following Decart Lucy 2.5 guidelines.
    Works seamlessly alongside Lucy 2.5 prompt enhancer (`enhance=True`).
    
    Lucy 2.5 Prompt Templates:
    - Character transformation: 'Replace the character in the video with <description>.'
    - Reference image character replacement matching identification features:
      'Replace the character in the video with the person in the reference image, keeping their <features>.'
    - Add object: 'Add <object> to <placement>.'
    - Replace object/feature: 'Replace <thing in the video> with <new thing>.'
    - Change attribute: 'Change <object or feature> to <new color, material, texture, or style>.'
    - Remove object: 'Remove <object>, leaving <what should appear in its place>.'
    - Change background: 'Change the background to <scene with visible activity>.'
    - Restyle whole video: 'Transform the entire scene into <style>, while preserving the original subjects, layout, and motion.'
    """
    clean_text = clean_vague_words(user_text.strip())
    
    # Strip any trailing period for consistent sentence construction
    if clean_text.endswith('.'):
        clean_text = clean_text[:-1].strip()

    if has_reference_image:
        if not clean_text:
            return "Replace the character in the video with the subject in the reference image."
            
        clean_lower = clean_text.lower()
        
        # Check if user already uses standard trigger words
        if clean_lower.startswith("replace"):
            # Normalize "replace the person" to "replace the character" per Lucy 2.5 standard
            res = clean_text
            if clean_lower.startswith("replace the person"):
                res = "Replace the character" + clean_text[18:]
            res = capitalize_first(res)
            
            # Check if reference image is already mentioned
            if "reference" in res.lower() or "image" in res.lower():
                return f"{res}." if not res.endswith('.') else res
            else:
                if "with" in res.lower():
                    return f"{res} from the reference image."
                return f"{res} using the reference image."
                
        elif (clean_lower.startswith("change") or 
              clean_lower.startswith("add") or 
              clean_lower.startswith("transform") or 
              clean_lower.startswith("remove")):
            res = capitalize_first(clean_text)
            if "reference" in clean_lower or "image" in clean_lower:
                return f"{res}."
            return f"{res} using the reference image."
            
        # Character replacement with explicit identification features matching uploaded image
        elif is_feature_list(clean_text):
            features = clean_feature_text(clean_text)
            return f"Replace the character in the video with the person in the reference image, keeping their {features}."
            
        else:
            # Subject description (e.g., "a cartoon bear", "an astronaut")
            natural_text = clean_text
            words = clean_text.split()
            if words:
                first_word = words[0].lower()
                if first_word in ("a", "an", "the") and len(words) > 1:
                    natural_text = " ".join(words[1:])
            
            return f"Replace the character in the video with the {natural_text} from the reference image."

    else:
        # No reference image attached
        if not clean_text:
            return ""
            
        clean_lower = clean_text.lower()
        
        # Check if user already prefix-triggered the prompt with explicit action
        if clean_lower.startswith("replace the person"):
            # Normalize to Lucy 2.5 "Replace the character" template
            res = "Replace the character" + clean_text[18:]
            res = capitalize_first(res)
            return f"{res}."
        elif clean_lower.startswith("remove"):
            res = capitalize_first(clean_text)
            if "leaving" not in clean_lower:
                return f"{res}, leaving clean background in its place."
            return f"{res}."
        elif (clean_lower.startswith("replace") or 
              clean_lower.startswith("change") or 
              clean_lower.startswith("add") or 
              clean_lower.startswith("transform")):
            res = capitalize_first(clean_text)
            return f"{res}."
            
        # Detect intent based on keywords for non-triggered prompts
        words_found = set(re.findall(r'\b\w+\b', clean_lower))
        
        # 1. Remove object
        if any(keyword in words_found for keyword in REMOVE_KEYWORDS):
            return f"Remove {clean_text}, leaving clean background in its place."
            
        # 2. Add object
        if any(keyword in words_found for keyword in ADD_KEYWORDS):
            return f"{capitalize_first(clean_text)}."
            
        # 3. Change background
        if any(keyword in words_found for keyword in BACKGROUND_KEYWORDS):
            return f"Change the background to {clean_text}."
            
        # 4. Restyle entire scene
        if any(keyword in words_found for keyword in SCENE_KEYWORDS) and not any(keyword in words_found for keyword in CHARACTER_KEYWORDS):
            return f"Transform the entire scene into {clean_text}, while preserving the original subjects, layout, and motion."

        # 5. Clothing change (only if specific clothing words exist and no character subject word)
        if any(keyword in words_found for keyword in CLOTHING_SPECIFIC_KEYWORDS) and not any(keyword in words_found for keyword in CHARACTER_KEYWORDS):
            return f"Change the person's clothing to {clean_text}."
            
        # 6. Default character transformation (Character replacer per Lucy 2.5 guide)
        subject = clean_text
        words = clean_text.split()
        if words and words[0].lower() in ("a", "an"):
            return f"Replace the character in the video with {subject}."
        elif words and words[0].lower() == "the":
            return f"Replace the character in the video with {subject}."
        else:
            return f"Replace the character in the video with {clean_text}."
