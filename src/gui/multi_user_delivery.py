"""
Multi-user Email Delivery Service.
Sends digest emails to all registered users subscribed to a persona.
Uses async operations and concurrent sending for efficiency.
"""
import asyncio
import logging
from typing import List, Dict, Optional
from email.message import EmailMessage
import aiosmtplib

from core.entities import DigestEntry
from delivery.base import DeliveryChannel
from gui.models import UserDatabase

logger = logging.getLogger(__name__)


class MultiUserEmailDelivery(DeliveryChannel):
    """
    Email delivery channel that sends to all registered users
    subscribed to the specific persona.
    """
    name = "multi_user_email"

    # Default color scheme
    DEFAULT_COLORS = {
        "primary": "#00F6FF",
        "primary_dark": "#0047FF",
        "secondary": "#B896FF",
        "background": "#060606",
        "card_bg": "#0a0a0a",
        "text_primary": "#FBFAFA",
        "text_secondary": "#7BA8FF",
        "border": "#0047FF",
        "accent": "#00FFF0",
        "why_it_matters_bg": "#060606",
        "why_it_matters_text": "#00FFF0",
    }

    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        sender: str,
        user_db_path: str = "data/gui.db",
        colors: Dict[str, str] = None,
        batch_size: int = 10,
        rate_limit_delay: float = 1.0,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender = sender
        self.user_db_path = user_db_path
        self.colors = {**self.DEFAULT_COLORS, **(colors or {})}
        self.batch_size = batch_size
        self.rate_limit_delay = rate_limit_delay

    def _build_html_template(
        self, persona: str, digest_date: str, entries: List[DigestEntry]
    ) -> str:
        """Build a visually appealing HTML email template."""
        import html as html_escape
        c = self.colors

        # Build entry cards
        entry_cards = []
        for entry in entries:
            # Build source links
            source_links = "".join(
                f'''<a href="{html_escape.escape(url)}" 
                    style="display: inline-block; margin: 4px 8px 4px 0; padding: 6px 12px; 
                           background-color: {c['background']}; color: {c['primary']}; 
                           text-decoration: none; border-radius: 6px; font-size: 13px;
                           border: 1px solid {c['border']};">
                    🔗 Source {i+1}
                </a>'''
                for i, url in enumerate(entry.source_urls)
            )

            card = f'''
            <div style="background-color: {c['card_bg']}; border-radius: 12px; 
                        padding: 24px; margin-bottom: 20px; 
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
                        border-left: 4px solid {c['primary']};">
                
                <!-- Header with title -->
                <div style="margin-bottom: 16px;">
                    <h2 style="margin: 0; color: {c['text_primary']}; font-size: 18px; 
                               font-weight: 600; line-height: 1.4;">
                        {html_escape.escape(entry.title)}
                    </h2>
                </div>
                
                <!-- Summary -->
                <p style="color: {c['text_primary']}; font-size: 15px; line-height: 1.6; 
                          margin: 0 0 16px 0;">
                    {html_escape.escape(entry.summary)}
                </p>
                
                <!-- Why it matters -->
                <div style="background-color: {c['why_it_matters_bg']}; border-radius: 8px; padding: 14px; 
                            margin-bottom: 16px; border-left: 3px solid {c['accent']};">
                    <p style="margin: 0; font-size: 14px; color: {c['why_it_matters_text']};">
                        <strong>💡 Why it matters:</strong> {html_escape.escape(entry.why_it_matters)}
                    </p>
                </div>
                
                <!-- Footer with sources -->
                <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 12px;">
                    <div>
                        {source_links}
                    </div>
                </div>
            </div>
            '''
            entry_cards.append(card)

        # Complete HTML template
        html_content = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html_escape.escape(persona)} Digest</title>
</head>
<body style="margin: 0; padding: 0; background-color: {c['background']}; 
             font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 
                          'Helvetica Neue', Arial, sans-serif;">
    
    <!-- Container -->
    <div style="max-width: 680px; margin: 0 auto; padding: 20px;">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, {c['primary']} 0%, {c['primary_dark']} 100%); 
                    border-radius: 16px 16px 0 0; padding: 32px; text-align: center;">
            <h1 style="margin: 0 0 8px 0; color: {c['background']}; font-size: 28px; font-weight: 700;">
                📰 {html_escape.escape(persona.replace('_', ' ').title())}
            </h1>
            <p style="margin: 0; color: {c['background']}; font-size: 16px; opacity: 0.9;">
                Daily Intelligence Digest
            </p>
            <p style="margin: 12px 0 0 0; color: {c['background']}; font-size: 14px; opacity: 0.75;">
                📅 {digest_date}
            </p>
        </div>
        
        <!-- Stats bar -->
        <div style="background-color: {c['card_bg']}; padding: 16px 24px; 
                    border-bottom: 1px solid {c['border']}; text-align: center;">
            <span style="color: {c['text_secondary']}; font-size: 14px;">
                🎯 <strong style="color: {c['primary']};">{len(entries)}</strong> curated items for you today
            </span>
        </div>
        
        <!-- Content area -->
        <div style="background-color: {c['background']}; padding: 24px; 
                    border-radius: 0 0 16px 16px; border: 1px solid {c['border']}; border-top: none;">
            
            {"".join(entry_cards)}
            
        </div>
        
        <!-- Footer -->
        <div style="text-align: center; padding: 24px; color: {c['text_secondary']}; 
                    font-size: 13px;">
            <p style="margin: 0 0 8px 0;">
                Generated by <strong style="color: {c['primary']};">AI Intelligence Digest</strong>
            </p>
            <p style="margin: 0; color: {c['border']};">
                ─────────────────────
            </p>
            <p style="margin: 8px 0 0 0; font-size: 12px;">
                Stay informed. Stay ahead. 🚀
            </p>
        </div>
        
    </div>
</body>
</html>
'''
        return html_content

    def _build_plain_text(
        self, persona: str, digest_date: str, entries: List[DigestEntry]
    ) -> str:
        """Build a plain text version of the digest."""
        lines = [
            f"{'='*60}",
            f"{persona.replace('_', ' ').title()} - Daily Intelligence Digest",
            f"Date: {digest_date}",
            f"{'='*60}",
            f"",
            f"{len(entries)} curated items for you today",
            f"",
        ]

        for entry in entries:
            lines.extend([
                f"{'─'*60}",
                f"{entry.title}",
                f"{'─'*60}",
                f"",
                f"{entry.summary}",
                f"",
                f"💡 Why it matters: {entry.why_it_matters}",
                f"",
                f"🔗 Sources:",
            ])
            for url in entry.source_urls:
                lines.append(f"   - {url}")
            lines.append("")

        lines.extend([
            f"{'='*60}",
            f"Generated by AI Intelligence Digest",
            f"Stay informed. Stay ahead.",
            f"{'='*60}",
        ])

        return "\n".join(lines)

    async def _send_single_email(
        self,
        recipient: str,
        subject: str,
        html_content: str,
        plain_text: str
    ) -> bool:
        """Send a single email."""
        try:
            msg = EmailMessage()
            msg["From"] = self.sender
            msg["To"] = recipient
            msg["Subject"] = subject

            msg.set_content(plain_text)
            msg.add_alternative(html_content, subtype="html")

            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                start_tls=True,
            )
            logger.info(f"Email sent successfully to {recipient}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            return False

    async def _get_subscribers(self, persona: str) -> List[str]:
        """Get all subscribers for a persona from the user database."""
        try:
            user_db = UserDatabase(self.user_db_path)
            users = await user_db.get_verified_users_with_persona(persona)
            return [user['email'] for user in users]
        except Exception as e:
            logger.error(f"Failed to get subscribers for {persona}: {e}")
            return []

    async def deliver(
        self,
        *,
        persona: str,
        digest_date: str,
        entries: List[DigestEntry],
    ) -> None:
        """Deliver digest to all subscribed users."""
        # Get subscribers for this persona
        subscribers = await self._get_subscribers(persona)

        if not subscribers:
            logger.warning(f"No subscribers found for persona {persona}")
            return

        logger.info(f"Sending {persona} digest to {len(subscribers)} subscribers")

        # Build email content once
        subject = f"📰 {persona.replace('_', ' ').title()} Digest – {digest_date}"
        html_content = self._build_html_template(persona, digest_date, entries)
        plain_text = self._build_plain_text(persona, digest_date, entries)

        # Send emails in batches with rate limiting
        successful = 0
        failed = 0

        for i in range(0, len(subscribers), self.batch_size):
            batch = subscribers[i:i + self.batch_size]

            # Send batch concurrently
            tasks = [
                self._send_single_email(recipient, subject, html_content, plain_text)
                for recipient in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if result is True:
                    successful += 1
                else:
                    failed += 1

            # Rate limiting between batches
            if i + self.batch_size < len(subscribers):
                await asyncio.sleep(self.rate_limit_delay)

        logger.info(f"Digest delivery complete: {successful} successful, {failed} failed")


class HybridEmailDelivery(DeliveryChannel):
    """
    Hybrid email delivery that sends to both:
    1. Configured recipient (legacy support)
    2. All registered users subscribed to the persona
    """
    name = "hybrid_email"

    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        sender: str,
        legacy_recipient: Optional[str] = None,
        user_db_path: str = "data/gui.db",
        colors: Dict[str, str] = None,
    ):
        self.multi_user_delivery = MultiUserEmailDelivery(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            username=username,
            password=password,
            sender=sender,
            user_db_path=user_db_path,
            colors=colors,
        )
        self.legacy_recipient = legacy_recipient

    async def deliver(
        self,
        *,
        persona: str,
        digest_date: str,
        entries: List[DigestEntry],
    ) -> None:
        """Deliver to all subscribers and optionally the legacy recipient."""
        # Send to all registered users
        await self.multi_user_delivery.deliver(
            persona=persona,
            digest_date=digest_date,
            entries=entries,
        )

        # Also send to legacy recipient if configured
        if self.legacy_recipient:
            subject = f"📰 {persona.replace('_', ' ').title()} Digest – {digest_date}"
            html_content = self.multi_user_delivery._build_html_template(persona, digest_date, entries)
            plain_text = self.multi_user_delivery._build_plain_text(persona, digest_date, entries)

            await self.multi_user_delivery._send_single_email(
                self.legacy_recipient, subject, html_content, plain_text
            )
