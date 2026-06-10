"""
Configuration management for LucidCam.
Loads settings from lucidcam.ini with fallback defaults.
"""

import configparser
import logging
from pathlib import Path
from typing import Optional


class Config:
    """Singleton configuration manager for LucidCam."""
    
    _instance: Optional['Config'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.config = configparser.ConfigParser()
        self.config_path = Path(__file__).parent / "lucidcam.ini"
        
        if self.config_path.exists():
            self.config.read(self.config_path)
        else:
            self._load_defaults()
    
    def _load_defaults(self):
        """Load default configuration values."""
        self.config['camera'] = {
            'width': '1280',
            'height': '720',
            'fps': '24',
        }
        self.config['video'] = {
            'device_name': 'pyvirtualcam',
        }
        self.config['model'] = {
            'model_id': 'lucy-2.1',
            'initial_prompt': 'A cinematic portrait',
        }
        self.config['ui'] = {
            'theme': 'dark',
            'min_width': '1000',
            'min_height': '800',
            'default_font': 'Segoe UI',
        }
        self.config['logging'] = {
            'level': 'INFO',
            'log_file': 'logs/lucidcam.log',
            'max_file_size': '10485760',
            'backup_count': '5',
        }
        self.config['presets'] = {
            'preset_1': 'Transform the video into Albert Stylestein style',
            'preset_2': 'Transform the video into Capybara style',
            'preset_3': 'Transform the video into Statue of Liberty style',
            'preset_4': 'Transform the video into Cyberpunk style',
            'preset_5': 'Transform the video into Oil Painting style',
        }
        self.config['performance'] = {
            'frame_strategy': 'drop_oldest',
            'frame_buffer_size': '2',
        }
    
    def get(self, section: str, key: str, fallback: Optional[str] = None) -> str:
        """Get a configuration value."""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return fallback
            raise
    
    def get_int(self, section: str, key: str, fallback: Optional[int] = None) -> int:
        """Get a configuration value as integer."""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return fallback
            raise
    
    def get_bool(self, section: str, key: str, fallback: Optional[bool] = None) -> bool:
        """Get a configuration value as boolean."""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return fallback
            raise
    
    def get_presets(self) -> list:
        """Get all preset styles."""
        presets = []
        for key in sorted(self.config['presets'].keys()):
            preset_value = self.config['presets'][key]
            if "into " in preset_value and " style" in preset_value:
                name = preset_value.split("into ")[1].replace(" style", "")
                presets.append(name)
        return presets
    
    def save(self):
        """Save current configuration to file."""
        with open(self.config_path, 'w') as f:
            self.config.write(f)


config = Config()
