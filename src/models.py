"""Data models for email-to-dingtalk module."""
import json
from dataclasses import dataclass, asdict


@dataclass
class Email:
    """Email data model."""
    id: str           # 邮件唯一标识
    subject: str      # 邮件主题
    sender: str       # 发件人
    date: str         # 发送日期
    body: str         # 邮件正文
    
    def serialize(self) -> str:
        """Serialize Email to JSON string."""
        return json.dumps(asdict(self), ensure_ascii=False)
    
    @classmethod
    def deserialize(cls, json_str: str) -> 'Email':
        """Deserialize JSON string to Email object."""
        try:
            data = json.loads(json_str)
            return cls(
                id=data['id'],
                subject=data['subject'],
                sender=data['sender'],
                date=data['date'],
                body=data['body']
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Failed to deserialize Email: {e}")


@dataclass
class Config:
    """Configuration data model."""
    email_host: str       # IMAP服务器地址
    email_user: str       # 邮箱账号
    email_password: str   # 邮箱授权码
    dingtalk_webhook: str # 钉钉Webhook URL
    dingtalk_secret: str  # 钉钉加签密钥
