"""
Email to DingTalk Notification Script
"""
import argparse
import logging
import sys
import time
from typing import Optional

from src.config_manager import ConfigManager
from src.email_fetcher import EmailFetcher, EmailFetcherError, AuthenticationError, ConnectionError
from src.dingtalk_notifier import DingTalkNotifier


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_emails(email_fetcher: EmailFetcher, dingtalk_notifier: DingTalkNotifier) -> int:
    """Process unread emails and send to DingTalk."""
    try:
        emails = email_fetcher.fetch_unread_emails()
        
        if not emails:
            return 0
        
        logger.info(f"Found {len(emails)} unread email(s)")
        
        success_count = 0
        for email in emails:
            logger.info(f"Processing email: {email.subject}")
            
            if dingtalk_notifier.send(email):
                if email_fetcher.mark_as_read(email.id):
                    success_count += 1
                else:
                    logger.warning(f"Failed to mark email as read: {email.subject}")
            else:
                logger.warning(f"Failed to send to DingTalk: {email.subject}")
        
        if success_count > 0:
            logger.info(f"Processed {success_count}/{len(emails)} emails")
        return success_count
        
    except EmailFetcherError as e:
        logger.error(f"Error fetching emails: {e}")
        return 0


def run_daemon(config_path: Optional[str], interval: int) -> int:
    """Run as daemon, continuously monitoring for new emails."""
    logger.info(f"Starting daemon mode, checking every {interval} seconds")
    
    try:
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    
    dingtalk_notifier = DingTalkNotifier(
        webhook_url=config.dingtalk_webhook,
        secret=config.dingtalk_secret
    )
    
    while True:
        email_fetcher = EmailFetcher(
            host=config.email_host,
            user=config.email_user,
            password=config.email_password
        )
        
        try:
            email_fetcher.connect()
            process_emails(email_fetcher, dingtalk_notifier)
        except (AuthenticationError, ConnectionError) as e:
            logger.error(f"Connection error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            try:
                email_fetcher.disconnect()
            except:
                pass
        
        time.sleep(interval)


def main(config_path: Optional[str] = None) -> int:
    """Main entry point - single run mode."""
    logger.info("Starting email-to-dingtalk notification script")
    
    try:
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        logger.info("Configuration loaded successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    
    email_fetcher = EmailFetcher(
        host=config.email_host,
        user=config.email_user,
        password=config.email_password
    )
    
    dingtalk_notifier = DingTalkNotifier(
        webhook_url=config.dingtalk_webhook,
        secret=config.dingtalk_secret
    )
    
    try:
        email_fetcher.connect()
    except AuthenticationError as e:
        logger.error(f"Email authentication failed: {e}")
        return 2
    except ConnectionError as e:
        logger.error(f"Email connection failed: {e}")
        return 3
    
    try:
        count = process_emails(email_fetcher, dingtalk_notifier)
        if count == 0:
            logger.info("No unread emails found")
        return 0
    finally:
        email_fetcher.disconnect()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch emails and send to DingTalk')
    parser.add_argument('-c', '--config', help='Path to JSON config file', default=None)
    parser.add_argument('-d', '--daemon', help='Run in daemon mode', action='store_true')
    parser.add_argument('-i', '--interval', help='Check interval in seconds', type=int, default=60)
    
    args = parser.parse_args()
    
    try:
        if args.daemon:
            sys.exit(run_daemon(args.config, args.interval))
        else:
            sys.exit(main(args.config))
    except KeyboardInterrupt:
        logger.info("Stopped by user")
        sys.exit(0)
