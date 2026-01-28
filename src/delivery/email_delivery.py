"""
Email Delivery channel
"""
from typing import List
from email.message import EmailMessage
import aiosmtplib

from core.entities import DigestEntry
from delivery.base import DeliveryChannel


class EmailDelivery(DeliveryChannel):
    name = "email"

    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        sender: str,
        recipient: str,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender = sender
        self.recipient = recipient

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
        msg["Subject"] = f"{persona} Digest – {digest_date}"

        html = ["<html><body>"]
        html.append(f"<h1>{persona} Digest</h1>")

        for entry in entries:
            html.append(f"<h2>{entry.title}</h2>")
            html.append(f"<p>{entry.summary}</p>")
            html.append(
                f"<p><b>Why it matters:</b> {entry.why_it_matters}</p>")
            html.append(f"<p><b>Audience:</b> {entry.audience}</p>")
            html.append("<ul>")
            for url in entry.source_urls:
                html.append(f"<li><a href='{url}'>{url}</a></li>")
            html.append("</ul>")

        html.append("</body></html>")

        msg.set_content("Your email client does not support HTML.")
        msg.add_alternative("\n".join(html), subtype="html")

        await aiosmtplib.send(
            msg,
            hostname=self.smtp_host,
            port=self.smtp_port,
            username=self.username,
            password=self.password,
            start_tls=True,
        )
