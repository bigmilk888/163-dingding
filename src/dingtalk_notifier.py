"""DingTalk notification module."""
import base64
import hashlib
import hmac
import time
import urllib.parse
from typing import Optional
import logging

import requests

from src.models import Email


logger = logging.getLogger(__name__)


class DingTalkNotifier:
    """DingTalk webhook notifier with signature authentication."""
    
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1
    
    def __init__(self, webhook_url: str, secret: str):
        self.webhook_url = webhook_url
        self.secret = secret
    
    def generate_sign(self, timestamp: int) -> str:
        """Generate HMAC-SHA256 signature for DingTalk authentication."""
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode('utf-8'))
        return sign
    
    def build_webhook_url(self, timestamp: Optional[int] = None) -> str:
        """Build webhook URL with timestamp and signature parameters."""
        if timestamp is None:
            timestamp = int(time.time() * 1000)
        
        sign = self.generate_sign(timestamp)
        separator = '&' if '?' in self.webhook_url else '?'
        return f"{self.webhook_url}{separator}timestamp={timestamp}&sign={sign}"
    
    def format_message(self, email: Email) -> dict:
        """Format email as DingTalk markdown message."""
        body = email.body
        if len(body) > 2000:
            body = body[:2000] + "...(内容已截断)"
        
        markdown_text = f"""### 📧 新邮件通知

**主题:** {email.subject}

**发件人:** {email.sender}

**时间:** {email.date}

---

**内容:**

{body}"""
        
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": "新邮件通知",
                "text": markdown_text
            }
        }
    
    def send(self, email: Email) -> bool:
        """Send email notification to DingTalk with retry logic."""
        message = self.format_message(email)
        backoff = self.INITIAL_BACKOFF
        
        for attempt in range(self.MAX_RETRIES):
            try:
                url = self.build_webhook_url()
                response = requests.post(
                    url,
                    json=message,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                result = response.json()
                
                if result.get('errcode') == 0:
                    logger.info(f"Successfully sent email notification: {email.subject}")
                    return True
                else:
                    logger.warning(
                        f"DingTalk API error (attempt {attempt + 1}): "
                        f"errcode={result.get('errcode')}, errmsg={result.get('errmsg')}"
                    )
            except requests.RequestException as e:
                logger.warning(f"Network error (attempt {attempt + 1}): {e}")
            
            if attempt < self.MAX_RETRIES - 1:
                time.sleep(backoff)
                backoff *= 2
        
        logger.error(f"Failed to send email notification after {self.MAX_RETRIES} attempts: {email.subject}")
        return False
