"""
Email Delivery channel
"""
from typing import List, Dict
from email.message import EmailMessage
import aiosmtplib
import html as html_escape

from core.entities import DigestEntry
from delivery.base import DeliveryChannel


class EmailDelivery(DeliveryChannel):
    name = "email"

    # Default color scheme (used if no colors provided)
    DEFAULT_COLORS = {
        "primary": "#6366f1",
        "primary_dark": "#4f46e5",
        "secondary": "#10b981",
        "background": "#f8fafc",
        "card_bg": "#ffffff",
        "text_primary": "#1e293b",
        "text_secondary": "#64748b",
        "border": "#e2e8f0",
        "accent": "#f59e0b",
        "why_it_matters_bg": "#fef3c7",
        "why_it_matters_text": "#92400e",
    }

    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        sender: str,
        recipient: str,
        colors: Dict[str, str] = None,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender = sender
        self.recipient = recipient
        # Merge provided colors with defaults
        self.colors = {**self.DEFAULT_COLORS, **(colors or {})}

    def _build_html_template(
        self, persona: str, digest_date: str, entries: List[DigestEntry]
    ) -> str:
        """Build a visually appealing HTML email template."""
        c = self.colors

        # Build entry cards
        entry_cards = []
        for idx, entry in enumerate(entries, 1):

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
                
                <!-- Header with number and title -->
                <div style="display: flex; align-items: flex-start; margin-bottom: 16px;">
                    <span style="background-color: {c['primary']}; color: white; 
                                 font-weight: bold; font-size: 14px; 
                                 width: 28px; height: 28px; border-radius: 50%; 
                                 display: inline-block; text-align: center; 
                                 line-height: 28px; margin-right: 12px; flex-shrink: 0;">
                        {idx}
                    </span>
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
            <h1 style="margin: 0 0 8px 0; color: white; font-size: 28px; font-weight: 700;">
                📰 {html_escape.escape(persona)}
            </h1>
            <p style="margin: 0; color: rgba(255,255,255,0.9); font-size: 16px;">
                Daily Intelligence Digest
            </p>
            <p style="margin: 12px 0 0 0; color: rgba(255,255,255,0.75); font-size: 14px;">
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
                    border-radius: 0 0 16px 16px;">
            
            {"".join(entry_cards)}
            
        </div>
        
        <!-- Footer -->
        <div style="text-align: center; padding: 24px; color: {c['text_secondary']}; 
                    font-size: 13px;">
            <p style="margin: 0 0 8px 0;">
                Generated by <strong>AI Intelligence Digest</strong>
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
            f"{persona} - Daily Intelligence Digest",
            f"Date: {digest_date}",
            f"{'='*60}",
            f"",
            f"{len(entries)} curated items for you today",
            f"",
        ]

        for idx, entry in enumerate(entries, 1):
            lines.extend([
                f"{'─'*60}",
                f"[{idx}] {entry.title}",
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

    async def deliver(
        self,
        *,
        persona: str,
        digest_date: str,
        entries: List[DigestEntry],
    ) -> None:
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = self.recipient
        msg["Subject"] = f"📰 {persona} Digest – {digest_date}"

        # Set plain text content as fallback
        plain_text = self._build_plain_text(persona, digest_date, entries)
        msg.set_content(plain_text)

        # Add HTML as the preferred alternative
        html_content = self._build_html_template(persona, digest_date, entries)
        msg.add_alternative(html_content, subtype="html")

        await aiosmtplib.send(
            msg,
            hostname=self.smtp_host,
            port=self.smtp_port,
            username=self.username,
            password=self.password,
            start_tls=True,
        )
