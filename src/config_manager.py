"""Configuration management module."""
import json
import os
import re
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class Config:
    """Configuration data model."""
    email_host: str
    email_user: str
    email_password: str
    dingtalk_webhook: str
    dingtalk_secret: str


class ConfigManager:
    """Configuration manager for loading and validating config."""
    
    REQUIRED_FIELDS = [
        'email_host', 'email_user', 'email_password',
        'dingtalk_webhook', 'dingtalk_secret'
    ]
    
    ENV_MAPPING = {
        'email_host': 'EMAIL_HOST',
        'email_user': 'EMAIL_USER',
        'email_password': 'EMAIL_PASSWORD',
        'dingtalk_webhook': 'DINGTALK_WEBHOOK',
        'dingtalk_secret': 'DINGTALK_SECRET'
    }
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
    
    def load_config(self) -> Config:
        """Load configuration from environment variables or config file."""
        config_dict = {}
        
        if self.config_path and os.path.exists(self.config_path):
            config_dict = self._load_from_file()
        
        env_config = self._load_from_env()
        config_dict.update(env_config)
        
        missing = self.get_missing_fields(config_dict)
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return Config(
            email_host=config_dict['email_host'],
            email_user=config_dict['email_user'],
            email_password=config_dict['email_password'],
            dingtalk_webhook=config_dict['dingtalk_webhook'],
            dingtalk_secret=config_dict['dingtalk_secret']
        )
    
    def _load_from_file(self) -> dict:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Failed to load config file: {e}")
    
    def _load_from_env(self) -> dict:
        config = {}
        for field, env_var in self.ENV_MAPPING.items():
            value = os.environ.get(env_var)
            if value:
                config[field] = value
        return config
    
    def get_missing_fields(self, config: dict) -> List[str]:
        return [f for f in self.REQUIRED_FIELDS if f not in config or not config[f]]
