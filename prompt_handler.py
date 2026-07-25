import re

# Keywords for intent detection
CLOTHING_KEYWORDS = {
    "clothing", "shirt", "pants", "jacket", "suit", "dress", "hat", "tuxedo", 
    "wear", "wearing", "outfit", "tshirt", "jeans", "coat", "sweater", "blouse",
    "skirt", "tie", "glasses", "sunglasses"
}

# Scene keywords (ignoring substrings like "part" in "art" by matching exact words)
SCENE_KEYWORDS = {
    "aesthetic", "painting", "style", "scene", "background", "neon", "cyberpunk", 
    "drawing", "sketch", "art", "oil painting", "watercolor", "illustration",
    "lighting", "view", "environment"
}

def generate_prompt(user_text: str, has_reference_image: bool) -> str:
    """
    Format a raw user input text prompt into an optimized prompt following Decart Lucy 2.1 guidelines.
    Specialize prompting behavior when an image is attached.
    """
    # Clean up input text
    clean_text = user_text.strip()
    
    # Strip any trailing periods to handle punctuation consistently
    if clean_text.endswith('.'):
        clean_text = clean_text[:-1].strip()

    if has_reference_image:
        if not clean_text:
            return "Replace the person in the video with the subject in the reference image."
            
        clean_lower = clean_text.lower()
        
        # Check if user already uses standard trigger words
        if clean_lower.startswith("replace"):
            # Check if it already mentions "reference image" or "image"
            if "image" in clean_lower:
                return f"{clean_text}."
            else:
                # E.g. "Replace the person in the video with a cartoon bear" -> "Replace the person in the video with the cartoon bear from the reference image."
                if "with" in clean_lower:
                    return f"{clean_text} from the reference image."
                return f"{clean_text} using the reference image."
                
        elif clean_lower.startswith("change") or clean_lower.startswith("add") or clean_lower.startswith("transform"):
            if "image" in clean_lower:
                return f"{clean_text}."
            return f"{clean_text} using the reference image."
            
        else:
            # Simple subject replacement description (e.g., "a futuristic knight")
            # Strip initial "a", "an", or "the" so it sounds more natural when we prepend "the"
            natural_text = clean_text
            words = clean_text.split()
            if words:
                first_word = words[0].lower()
                if first_word in ("a", "an", "the") and len(words) > 1:
                    natural_text = " ".join(words[1:])
            
            return f"Replace the person in the video with the {natural_text} from the reference image."
            
    else:
        # No reference image attached
        if not clean_text:
            return ""
            
        clean_lower = clean_text.lower()
        
        # Check if user already prefix-triggered the prompt
        if (clean_lower.startswith("replace") or 
            clean_lower.startswith("change") or 
            clean_lower.startswith("add") or 
            clean_lower.startswith("transform")):
            return f"{clean_text}."
            
        # Detect intent based on keywords
        words_found = set(re.findall(r'\b\w+\b', clean_lower))
        
        # 1. Clothing change
        if any(keyword in words_found for keyword in CLOTHING_KEYWORDS):
            return f"Change the person's clothing to {clean_text}."
            
        # 2. Scene/Art Style transform
        if any(keyword in words_found for keyword in SCENE_KEYWORDS):
            return f"Transform the scene to {clean_text}."
            
        # 3. Default to character replacement
        return f"Replace the person in the video with {clean_text}."
