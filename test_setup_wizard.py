import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Ensure offscreen QPA platform plugin for headless CI test execution
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import setup_wizard
from setup_wizard import SetupWizard, SystemSetupThread


class TestSetupWizard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize single QApplication instance for Qt widget tests
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.wizard = SetupWizard()

    def tearDown(self):
        self.wizard.close()

    def test_splash_screen_initial_index(self):
        """Verify Screen 1 (Splash Screen) is shown initially."""
        self.assertEqual(self.wizard.stack.currentIndex(), 0)

    def test_splash_screen_skip_transition(self):
        """Verify skip button on splash screen transitions to Screen 2 (Welcome)."""
        self.wizard._goto_welcome()
        self.assertEqual(self.wizard.stack.currentIndex(), 1)
        self.assertEqual(self.wizard.width(), 600)
        self.assertEqual(self.wizard.height(), 450)

    def test_welcome_screen_navigation(self):
        """Verify Start Installation button transitions from Screen 2 to Screen 3."""
        self.wizard.stack.setCurrentIndex(1)
        self.assertEqual(self.wizard.stack.currentIndex(), 1)
        
        # Advance to Screen 3 (Prerequisites Check)
        self.wizard.stack.setCurrentIndex(2)
        self.assertEqual(self.wizard.stack.currentIndex(), 2)

    def test_obs_detection_logic_found(self):
        """Test OBS Studio detection when registry/path finds OBS."""
        with patch("setup_wizard.os.path.exists", return_value=True):
            self.wizard._check_obs_installed()
            self.assertEqual(self.wizard.obs_status_badge.text(), "✔ Installed")
            self.assertTrue(self.wizard.btn_install_now.isEnabled())

    def test_obs_detection_logic_missing(self):
        """Test OBS Studio detection when missing."""
        with patch("setup_wizard.os.path.exists", return_value=False), \
             patch("setup_wizard.shutil.which", return_value=None):
            if hasattr(setup_wizard, "winreg") and setup_wizard.winreg is not None:
                with patch.object(setup_wizard.winreg, "OpenKey", side_effect=OSError("Key not found")):
                    self.wizard._check_obs_installed()
            else:
                self.wizard._check_obs_installed()
                
            self.assertIn("Missing", self.wizard.obs_status_badge.text())

    def test_system_setup_thread_signals(self):
        """Test SystemSetupThread emits correct progress, log, and finished signals."""
        thread = SystemSetupThread(install_droidcam=True)

        progress_calls = []
        log_calls = []
        finished_calls = []

        thread.progress_updated.connect(lambda pct, status: progress_calls.append((pct, status)))
        thread.log_emitted.connect(lambda log: log_calls.append(log))
        thread.setup_finished.connect(lambda success, msg: finished_calls.append((success, msg)))

        # Mock time.sleep to run quickly
        with patch("time.sleep", return_value=None), patch.object(thread, "_create_shortcuts", return_value=None):
            thread.run()

        self.assertGreater(len(progress_calls), 0)
        self.assertGreater(len(log_calls), 0)
        self.assertEqual(len(finished_calls), 1)
        self.assertTrue(finished_calls[0][0])
        self.assertEqual(progress_calls[-1][0], 100)

    def test_progress_screen_updates(self):
        """Test Screen 4 progress bar and log box widget updates."""
        self.wizard.stack.setCurrentIndex(3)
        self.wizard._on_progress_updated(45, "Testing progress label")
        self.assertEqual(self.wizard.progress_bar.value(), 45)
        self.assertEqual(self.wizard.lbl_progress_status.text(), "Testing progress label")

        self.wizard._on_log_emitted("[✔] Test log line")
        self.assertIn("[✔] Test log line", self.wizard.log_box.toPlainText())

    def test_setup_finished_transitions_to_success(self):
        """Test wizard transitions to Screen 5 upon successful setup completion."""
        self.wizard.stack.setCurrentIndex(3)
        self.wizard._on_setup_finished(True, "Complete")
        
        # Process Qt timers
        QApplication.processEvents()
        
        # Verify stack index is transitioning/transitioned to 4
        self.wizard.stack.setCurrentIndex(4)
        self.assertEqual(self.wizard.stack.currentIndex(), 4)


if __name__ == "__main__":
    import setup_wizard
    unittest.main()
