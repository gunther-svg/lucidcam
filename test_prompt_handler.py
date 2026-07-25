import unittest
from prompt_handler import generate_prompt

class TestPromptHandler(unittest.TestCase):
    def test_with_reference_image_empty_prompt(self):
        # When reference image is present but prompt is empty
        res = generate_prompt("", has_reference_image=True)
        self.assertEqual(res, "Replace the person in the video with the subject in the reference image.")

    def test_with_reference_image_simple_subject(self):
        # When reference image is present and user provides a simple subject
        res = generate_prompt("a cartoon bear", has_reference_image=True)
        self.assertEqual(res, "Replace the person in the video with the cartoon bear from the reference image.")
        
        res = generate_prompt("an astronaut", has_reference_image=True)
        self.assertEqual(res, "Replace the person in the video with the astronaut from the reference image.")
        
        res = generate_prompt("the Statue of Liberty", has_reference_image=True)
        self.assertEqual(res, "Replace the person in the video with the Statue of Liberty from the reference image.")

    def test_with_reference_image_already_replace_trigger(self):
        # Already starts with Replace and mentions image
        res = generate_prompt("Replace the person in the video with the robot in the reference image", has_reference_image=True)
        self.assertEqual(res, "Replace the person in the video with the robot in the reference image.")
        
        # Starts with Replace but does not mention image
        res = generate_prompt("Replace the person with a cyborg", has_reference_image=True)
        self.assertEqual(res, "Replace the person with a cyborg from the reference image.")

    def test_with_reference_image_other_trigger(self):
        res = generate_prompt("Change the shirt to blue", has_reference_image=True)
        self.assertEqual(res, "Change the shirt to blue using the reference image.")

    def test_no_reference_image_empty_prompt(self):
        res = generate_prompt("", has_reference_image=False)
        self.assertEqual(res, "")

    def test_no_reference_image_already_triggered(self):
        res = generate_prompt("Replace the person with a bear", has_reference_image=False)
        self.assertEqual(res, "Replace the person with a bear.")

    def test_no_reference_image_clothing_keyword(self):
        res = generate_prompt("a bright red tuxedo", has_reference_image=False)
        self.assertEqual(res, "Change the person's clothing to a bright red tuxedo.")

    def test_no_reference_image_scene_keyword(self):
        res = generate_prompt("neon cyberpunk style", has_reference_image=False)
        self.assertEqual(res, "Transform the scene to neon cyberpunk style.")

    def test_no_reference_image_default_replace(self):
        res = generate_prompt("a robotic dog", has_reference_image=False)
        self.assertEqual(res, "Replace the person in the video with a robotic dog.")

if __name__ == "__main__":
    unittest.main()
