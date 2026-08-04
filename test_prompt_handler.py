import unittest
from prompt_handler import generate_prompt, clean_vague_words, is_feature_list, clean_feature_text

class TestPromptHandlerLucy25(unittest.TestCase):

    def test_vague_words_removal(self):
        # Verify vague/process quality buzzwords prohibited in Lucy 2.5 guide are removed
        text = "a realistic photorealistic cinematic ultra high quality cartoon bear"
        cleaned = clean_vague_words(text)
        self.assertEqual(cleaned, "a cartoon bear")

    def test_with_reference_image_empty_prompt(self):
        # When reference image is present but prompt is empty
        res = generate_prompt("", has_reference_image=True)
        self.assertEqual(res, "Replace the character in the video with the subject in the reference image.")

    def test_with_reference_image_simple_subject(self):
        # When reference image is present and user provides a simple subject
        res = generate_prompt("a cartoon bear", has_reference_image=True)
        self.assertEqual(res, "Replace the character in the video with the cartoon bear from the reference image.")
        
        res = generate_prompt("an astronaut", has_reference_image=True)
        self.assertEqual(res, "Replace the character in the video with the astronaut from the reference image.")

    def test_with_reference_image_identification_features(self):
        # Character replacer with identification features matching user uploaded reference image
        res = generate_prompt("short curly black hair, gold earrings, green jacket, warm smile", has_reference_image=True)
        self.assertEqual(
            res, 
            "Replace the character in the video with the person in the reference image, keeping their short curly black hair, gold earrings, green jacket, warm smile."
        )

        # Feature list explicitly prefixed with keeping/details/features
        res = generate_prompt("features: short curly black hair, gold earrings, green jacket", has_reference_image=True)
        self.assertEqual(
            res,
            "Replace the character in the video with the person in the reference image, keeping their short curly black hair, gold earrings, green jacket."
        )

    def test_with_reference_image_already_replace_trigger(self):
        # Already starts with Replace and mentions image
        res = generate_prompt("Replace the character in the video with the robot in the reference image", has_reference_image=True)
        self.assertEqual(res, "Replace the character in the video with the robot in the reference image.")
        
        # Starts with Replace but does not mention image
        res = generate_prompt("Replace the person with a cyborg", has_reference_image=True)
        self.assertEqual(res, "Replace the character with a cyborg from the reference image.")

    def test_with_reference_image_other_trigger(self):
        res = generate_prompt("Change the shirt to blue", has_reference_image=True)
        self.assertEqual(res, "Change the shirt to blue using the reference image.")

    def test_no_reference_image_empty_prompt(self):
        res = generate_prompt("", has_reference_image=False)
        self.assertEqual(res, "")

    def test_no_reference_image_character_replacer_default(self):
        res = generate_prompt("a robotic dog", has_reference_image=False)
        self.assertEqual(res, "Replace the character in the video with a robotic dog.")

        res = generate_prompt("a cheerful cartoon chef with a tall white hat", has_reference_image=False)
        self.assertEqual(res, "Replace the character in the video with a cheerful cartoon chef with a tall white hat.")

    def test_no_reference_image_clothing_keyword(self):
        res = generate_prompt("a bright red tuxedo", has_reference_image=False)
        self.assertEqual(res, "Change the person's clothing to a bright red tuxedo.")

    def test_no_reference_image_scene_keyword(self):
        res = generate_prompt("neon cyberpunk style", has_reference_image=False)
        self.assertEqual(res, "Transform the entire scene into neon cyberpunk style, while preserving the original subjects, layout, and motion.")

    def test_no_reference_image_add_remove_background(self):
        # Add object template
        res = generate_prompt("add a glowing silver crown floating above the head", has_reference_image=False)
        self.assertEqual(res, "Add a glowing silver crown floating above the head.")

        # Remove object template
        res = generate_prompt("remove the coffee mug from the desk", has_reference_image=False)
        self.assertEqual(res, "Remove the coffee mug from the desk, leaving clean background in its place.")

        # Change background template
        res = generate_prompt("background with yellow taxis and afternoon sun", has_reference_image=False)
        self.assertEqual(res, "Change the background to background with yellow taxis and afternoon sun.")

if __name__ == "__main__":
    unittest.main()
