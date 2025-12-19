"""Email parsing module."""
import email
import email.message
import re
from email.header import decode_header
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Optional

from src.models import Email


class HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML, removing scripts and styles."""
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_data = False
        self.skip_tags = {'script', 'style', 'head', 'meta', 'link'}
    
    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.skip_tags:
            self.skip_data = True
        elif tag.lower() in ('br', 'p', 'div', 'tr', 'li'):
            self.text_parts.append('\n')
    
    def handle_endtag(self, tag):
        if tag.lower() in self.skip_tags:
            self.skip_data = False
        elif tag.lower() in ('p', 'div', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.text_parts.append('\n')
    
    def handle_data(self, data):
        if not self.skip_data:
            self.text_parts.append(data)
    
    def get_text(self) -> str:
        text = ''.join(self.text_parts)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()


class EmailParser:
    """Parser for raw email data."""
    
    SUPPORTED_ENCODINGS = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'iso-8859-1', 'ascii']
    
    @classmethod
    def parse(cls, raw_email: bytes, email_id: str) -> Email:
        """Parse raw email data into Email object."""
        msg = email.message_from_bytes(raw_email)
        
        subject = cls._decode_header(msg.get('Subject', ''))
        sender = cls._decode_header(msg.get('From', ''))
        
        date_str = msg.get('Date', '')
        try:
            date_obj = parsedate_to_datetime(date_str)
            date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            date = date_str
        
        body = cls._extract_body(msg)
        
        return Email(id=email_id, subject=subject, sender=sender, date=date, body=body)
    
    @classmethod
    def _decode_header(cls, header_value: str) -> str:
        """Decode email header value."""
        if not header_value:
            return ''
        
        decoded_parts = []
        for part, charset in decode_header(header_value):
            if isinstance(part, bytes):
                decoded_parts.append(cls.decode_content(part, charset or 'utf-8'))
            else:
                decoded_parts.append(part)
        
        return ''.join(decoded_parts)
    
    @classmethod
    def _extract_body(cls, msg: email.message.Message) -> str:
        """Extract plain text body from email message."""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))
                
                if 'attachment' in content_disposition:
                    continue
                
                if content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        return cls.decode_content(payload, charset)
            
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/html':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        html_content = cls.decode_content(payload, charset)
                        return cls._html_to_text(html_content)
            
            return ''
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                return cls.decode_content(payload, charset)
            return ''
    
    @classmethod
    def _html_to_text(cls, html: str) -> str:
        """Convert HTML to plain text, removing scripts and styles."""
        try:
            extractor = HTMLTextExtractor()
            extractor.feed(html)
            return extractor.get_text()
        except Exception:
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
    
    @classmethod
    def decode_content(cls, content: bytes, charset: Optional[str] = None) -> str:
        """Decode email content to UTF-8 string."""
        if not content:
            return ''
        
        if charset:
            try:
                return content.decode(charset)
            except (UnicodeDecodeError, LookupError):
                pass
        
        for encoding in cls.SUPPORTED_ENCODINGS:
            try:
                return content.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        
        return content.decode('utf-8', errors='replace')
