"""Email fetching module."""
import imaplib
import logging
import socket
from typing import List, Optional

from src.models import Email
from src.email_parser import EmailParser


logger = logging.getLogger(__name__)


class EmailFetcherError(Exception):
    """Base exception for EmailFetcher errors."""
    pass


class AuthenticationError(EmailFetcherError):
    """Raised when authentication fails."""
    pass


class ConnectionError(EmailFetcherError):
    """Raised when connection fails."""
    pass


class EmailFetcher:
    """Fetcher for retrieving emails from IMAP server."""
    
    CONNECTION_TIMEOUT = 30
    
    IMAP_ID_PARAMS = (
        '"name" "Python IMAP Client" '
        '"contact" "your@email.com" '
        '"version" "1.0.0" '
        '"vendor" "Python"'
    )
    
    def __init__(self, host: str, user: str, password: str):
        self.host = host
        self.user = user
        self.password = password
        self.connection: Optional[imaplib.IMAP4_SSL] = None
    
    def connect(self) -> bool:
        """Connect to IMAP server and authenticate."""
        try:
            socket.setdefaulttimeout(self.CONNECTION_TIMEOUT)
            self.connection = imaplib.IMAP4_SSL(self.host)
            self._send_id_command()
            self.connection.login(self.user, self.password)
            
            inbox_names = ['INBOX', 'inbox', 'Inbox']
            selected = False
            
            for inbox_name in inbox_names:
                status, data = self.connection.select(inbox_name)
                if status == 'OK':
                    selected = True
                    break
            
            if not selected:
                try:
                    _, folders = self.connection.list()
                    logger.error(f"Available folders: {folders}")
                    if data:
                        logger.error(f"Server response: {data}")
                except:
                    pass
                raise EmailFetcherError(
                    f"Failed to select INBOX folder: {status}. "
                    "请确认: 1) 163邮箱已开启IMAP服务 2) 使用的是授权码而非登录密码 "
                    "3) 在163邮箱设置中允许第三方客户端访问"
                )
            
            logger.info(f"Successfully connected to {self.host}")
            return True
            
        except imaplib.IMAP4.error as e:
            raise AuthenticationError(f"Authentication failed: {e}")
        except socket.timeout:
            raise ConnectionError(f"Connection timeout after {self.CONNECTION_TIMEOUT} seconds")
        except (socket.error, OSError) as e:
            raise ConnectionError(f"Connection failed: {e}")
    
    def _send_id_command(self) -> None:
        """Send IMAP ID command for 163/126/yeah mail servers."""
        if not self.connection:
            return
        try:
            tag = self.connection._new_tag()
            cmd = f'{tag.decode()} ID ({self.IMAP_ID_PARAMS})\r\n'
            self.connection.send(cmd.encode())
            self.connection.readline()
            logger.debug("ID command sent successfully")
        except Exception as e:
            logger.debug(f"ID command failed: {e}")
    
    def disconnect(self) -> None:
        """Disconnect from IMAP server."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.connection = None
            logger.info("Disconnected from IMAP server")
    
    def fetch_unread_emails(self) -> List[Email]:
        """Fetch all unread emails from inbox."""
        if not self.connection:
            raise EmailFetcherError("Not connected to IMAP server")
        
        emails = []
        
        try:
            status, message_ids = self.connection.search(None, 'UNSEEN')
            
            if status != 'OK':
                logger.warning("Failed to search for unread emails")
                return emails
            
            email_ids = message_ids[0].split()
            
            for email_id in email_ids:
                try:
                    status, data = self.connection.fetch(email_id, '(RFC822)')
                    
                    if status != 'OK' or not data or not data[0]:
                        continue
                    
                    raw_email = data[0][1]
                    email_id_str = email_id.decode('utf-8')
                    email_obj = EmailParser.parse(raw_email, email_id_str)
                    emails.append(email_obj)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse email {email_id}: {e}")
                    continue
            
            logger.info(f"Fetched {len(emails)} unread emails")
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            raise EmailFetcherError(f"Failed to fetch emails: {e}")
    
    def mark_as_read(self, email_id: str) -> bool:
        """Mark an email as read."""
        if not self.connection:
            logger.error("Not connected to IMAP server")
            return False
        
        try:
            status, _ = self.connection.store(email_id.encode(), '+FLAGS', '\\Seen')
            
            if status == 'OK':
                logger.info(f"Marked email {email_id} as read")
                return True
            else:
                logger.warning(f"Failed to mark email {email_id} as read")
                return False
                
        except Exception as e:
            logger.error(f"Error marking email {email_id} as read: {e}")
            return False
