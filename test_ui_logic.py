"""
Mock tests for UI logic including state changes and error handling.

Tests cover:
- Image upload state management
- Reference image state changes
- Error handling and user feedback
- UI state transitions
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
import tempfile
from PIL import Image


class MockQMessageBox:
    """Mock PyQt6 QMessageBox for testing."""
    warning_calls = []
    critical_calls = []
    information_calls = []
    
    @classmethod
    def reset(cls):
        cls.warning_calls = []
        cls.critical_calls = []
        cls.information_calls = []
    
    @classmethod
    def warning(cls, parent, title, message):
        cls.warning_calls.append({"parent": parent, "title": title, "message": message})
    
    @classmethod
    def critical(cls, parent, title, message):
        cls.critical_calls.append({"parent": parent, "title": title, "message": message})
    
    @classmethod
    def information(cls, parent, title, message):
        cls.information_calls.append({"parent": parent, "title": title, "message": message})


class UIStateManager:
    """Manages UI state for image reference and prompts."""
    
    def __init__(self):
        self.reference_image_path = None
        self.reference_image_data = None
        self.prompt_text = ""
        self.is_connected = False
        self.error_messages = []
    
    def load_image(self, file_path):
        """Load and store image reference."""
        if not file_path or not Path(file_path).exists():
            self.error_messages.append("File not found")
            return False
        
        self.reference_image_path = file_path
        self.reference_image_data = "mock_base64_data"
        return True
    
    def clear_image(self):
        """Clear image reference."""
        self.reference_image_path = None
        self.reference_image_data = None
    
    def set_prompt(self, text):
        """Set prompt text."""
        if not text or not text.strip():
            self.error_messages.append("Prompt cannot be empty")
            return False
        self.prompt_text = text
        return True
    
    def apply_prompt(self):
        """Apply prompt with validation."""
        if not self.is_connected:
            self.error_messages.append("Not connected")
            return False
        
        if not self.prompt_text or not self.prompt_text.strip():
            self.error_messages.append("Prompt text required")
            return False
        
        # Mock successful application
        return True
    
    def get_status_text(self):
        """Get status text for UI display."""
        if not self.is_connected:
            return "Status: Disconnected"
        
        status = f"Status: Live (Prompt: {self.prompt_text}"
        if self.reference_image_data:
            status += " + 📷 Reference Image"
        status += ")"
        return status


class TestImageUploadStateManagement(unittest.TestCase):
    """Test image upload state changes."""
    
    def setUp(self):
        """Initialize state manager."""
        self.state = UIStateManager()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()
    
    def create_test_image(self, filename):
        """Create a test image file."""
        file_path = self.temp_path / filename
        img = Image.new("RGB", (50, 50), color="red")
        img.save(file_path)
        return str(file_path)
    
    def test_initial_state_no_image(self):
        """Test initial state has no image loaded."""
        self.assertIsNone(self.state.reference_image_path)
        self.assertIsNone(self.state.reference_image_data)
    
    def test_load_image_sets_state(self):
        """Test loading image sets state correctly."""
        image_path = self.create_test_image("test.png")
        
        result = self.state.load_image(image_path)
        
        self.assertTrue(result)
        self.assertEqual(self.state.reference_image_path, image_path)
        self.assertIsNotNone(self.state.reference_image_data)
    
    def test_load_nonexistent_image_fails(self):
        """Test loading nonexistent image returns False."""
        result = self.state.load_image("/nonexistent/path.png")
        
        self.assertFalse(result)
        self.assertIsNone(self.state.reference_image_path)
        self.assertIn("File not found", self.state.error_messages)
    
    def test_clear_image_resets_state(self):
        """Test clearing image resets state."""
        image_path = self.create_test_image("test.png")
        self.state.load_image(image_path)
        
        # Verify image is loaded
        self.assertIsNotNone(self.state.reference_image_path)
        
        # Clear image
        self.state.clear_image()
        
        self.assertIsNone(self.state.reference_image_path)
        self.assertIsNone(self.state.reference_image_data)
    
    def test_load_image_replaces_previous(self):
        """Test loading new image replaces previous one."""
        image1_path = self.create_test_image("image1.png")
        image2_path = self.create_test_image("image2.png")
        
        self.state.load_image(image1_path)
        self.assertEqual(self.state.reference_image_path, image1_path)
        
        self.state.load_image(image2_path)
        self.assertEqual(self.state.reference_image_path, image2_path)


class TestPromptStateManagement(unittest.TestCase):
    """Test prompt state changes."""
    
    def setUp(self):
        """Initialize state manager."""
        self.state = UIStateManager()
    
    def test_initial_prompt_empty(self):
        """Test initial prompt is empty."""
        self.assertEqual(self.state.prompt_text, "")
    
    def test_set_prompt_text(self):
        """Test setting prompt text."""
        result = self.state.set_prompt("Transform into oil painting")
        
        self.assertTrue(result)
        self.assertEqual(self.state.prompt_text, "Transform into oil painting")
    
    def test_set_empty_prompt_fails(self):
        """Test setting empty prompt fails."""
        result = self.state.set_prompt("")
        
        self.assertFalse(result)
        self.assertIn("Prompt cannot be empty", self.state.error_messages)
    
    def test_set_whitespace_prompt_fails(self):
        """Test setting whitespace-only prompt fails."""
        result = self.state.set_prompt("   ")
        
        self.assertFalse(result)
        self.assertIn("Prompt cannot be empty", self.state.error_messages)
    
    def test_set_prompt_overwrites_previous(self):
        """Test setting new prompt overwrites previous."""
        self.state.set_prompt("First prompt")
        self.assertEqual(self.state.prompt_text, "First prompt")
        
        self.state.set_prompt("Second prompt")
        self.assertEqual(self.state.prompt_text, "Second prompt")


class TestApplyPromptErrorHandling(unittest.TestCase):
    """Test error handling when applying prompts."""
    
    def setUp(self):
        """Initialize state manager."""
        self.state = UIStateManager()
    
    def test_apply_prompt_when_disconnected_fails(self):
        """Test applying prompt when disconnected fails."""
        self.state.is_connected = False
        self.state.set_prompt("Some text")
        
        result = self.state.apply_prompt()
        
        self.assertFalse(result)
        self.assertIn("Not connected", self.state.error_messages)
    
    def test_apply_prompt_with_empty_text_fails(self):
        """Test applying empty prompt fails."""
        self.state.is_connected = True
        
        result = self.state.apply_prompt()
        
        self.assertFalse(result)
        self.assertIn("Prompt text required", self.state.error_messages)
    
    def test_apply_prompt_succeeds_when_connected_with_text(self):
        """Test applying prompt succeeds when conditions are met."""
        self.state.is_connected = True
        self.state.set_prompt("Valid prompt")
        
        result = self.state.apply_prompt()
        
        self.assertTrue(result)
    
    def test_error_messages_accumulate(self):
        """Test error messages accumulate in list."""
        self.state.load_image("/nonexistent/path.png")
        self.state.set_prompt("")
        
        self.assertGreaterEqual(len(self.state.error_messages), 2)
    
    def test_clear_error_messages(self):
        """Test error messages can be cleared."""
        self.state.load_image("/nonexistent/path.png")
        self.assertGreater(len(self.state.error_messages), 0)
        
        self.state.error_messages = []
        self.assertEqual(len(self.state.error_messages), 0)


class TestStatusTextGeneration(unittest.TestCase):
    """Test status text generation for UI display."""
    
    def setUp(self):
        """Initialize state manager."""
        self.state = UIStateManager()
    
    def test_disconnected_status(self):
        """Test status text when disconnected."""
        self.state.is_connected = False
        
        status = self.state.get_status_text()
        
        self.assertEqual(status, "Status: Disconnected")
    
    def test_connected_status_text_only(self):
        """Test status text when connected with text prompt only."""
        self.state.is_connected = True
        self.state.prompt_text = "Oil painting style"
        
        status = self.state.get_status_text()
        
        self.assertIn("Status: Live", status)
        self.assertIn("Oil painting style", status)
        self.assertNotIn("Reference Image", status)
    
    def test_connected_status_text_and_image(self):
        """Test status text when connected with text and image."""
        self.state.is_connected = True
        self.state.prompt_text = "Transform with reference"
        self.state.reference_image_data = "some_base64_data"
        
        status = self.state.get_status_text()
        
        self.assertIn("Status: Live", status)
        self.assertIn("Transform with reference", status)
        self.assertIn("📷 Reference Image", status)


class TestConnectionStateTransitions(unittest.TestCase):
    """Test connection state transitions and validation."""
    
    def setUp(self):
        """Initialize state manager."""
        self.state = UIStateManager()
    
    def test_initial_disconnected_state(self):
        """Test initial state is disconnected."""
        self.assertFalse(self.state.is_connected)
    
    def test_connect_state_change(self):
        """Test connecting changes state."""
        self.state.is_connected = True
        self.assertTrue(self.state.is_connected)
    
    def test_disconnect_state_change(self):
        """Test disconnecting changes state."""
        self.state.is_connected = True
        self.state.is_connected = False
        self.assertFalse(self.state.is_connected)
    
    def test_cannot_apply_prompt_when_disconnected(self):
        """Test prompt application fails when disconnected."""
        self.state.is_connected = False
        self.state.prompt_text = "Valid text"
        
        result = self.state.apply_prompt()
        self.assertFalse(result)
    
    def test_can_apply_prompt_when_connected(self):
        """Test prompt application succeeds when connected."""
        self.state.is_connected = True
        self.state.prompt_text = "Valid text"
        
        result = self.state.apply_prompt()
        self.assertTrue(result)


class TestImageAndPromptCombinations(unittest.TestCase):
    """Test various combinations of image and prompt states."""
    
    def setUp(self):
        """Initialize state manager."""
        self.state = UIStateManager()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()
    
    def create_test_image(self, filename):
        """Create a test image file."""
        file_path = self.temp_path / filename
        img = Image.new("RGB", (50, 50), color="red")
        img.save(file_path)
        return str(file_path)
    
    def test_text_only_prompt(self):
        """Test text-only prompt state."""
        self.state.is_connected = True
        self.state.set_prompt("Just text")
        
        self.assertIsNone(self.state.reference_image_data)
        self.assertIsNotNone(self.state.prompt_text)
    
    def test_text_and_image_prompt(self):
        """Test text and image prompt state."""
        self.state.is_connected = True
        image_path = self.create_test_image("test.png")
        self.state.load_image(image_path)
        self.state.set_prompt("With reference image")
        
        self.assertIsNotNone(self.state.reference_image_data)
        self.assertIsNotNone(self.state.prompt_text)
    
    def test_switch_from_text_to_text_and_image(self):
        """Test switching from text-only to text+image."""
        self.state.set_prompt("Original text")
        self.assertIsNone(self.state.reference_image_data)
        
        image_path = self.create_test_image("test.png")
        self.state.load_image(image_path)
        self.assertIsNotNone(self.state.reference_image_data)
    
    def test_clear_image_keeps_prompt(self):
        """Test clearing image preserves prompt text."""
        image_path = self.create_test_image("test.png")
        self.state.load_image(image_path)
        self.state.set_prompt("Important prompt")
        
        self.state.clear_image()
        
        self.assertIsNone(self.state.reference_image_data)
        self.assertEqual(self.state.prompt_text, "Important prompt")
    
    def test_update_prompt_keeps_image(self):
        """Test updating prompt preserves image."""
        image_path = self.create_test_image("test.png")
        self.state.load_image(image_path)
        original_image = self.state.reference_image_data
        
        self.state.set_prompt("New prompt")
        
        self.assertEqual(self.state.reference_image_data, original_image)


if __name__ == "__main__":
    unittest.main()
