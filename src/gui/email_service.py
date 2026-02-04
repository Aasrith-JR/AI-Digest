"""
Email service for sending OTP codes and notifications.
Uses async SMTP for non-blocking email operations.
"""
import aiosmtplib
from email.message import EmailMessage
from typing import Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound operations
_executor = ThreadPoolExecutor(max_workers=4)


class EmailService:
    """Async email service for OTP and notifications."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        sender: str
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender = sender

    async def send_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """Send an email asynchronously."""
        try:
            msg = EmailMessage()
            msg["From"] = self.sender
            msg["To"] = to
            msg["Subject"] = subject

            if plain_content:
                msg.set_content(plain_content)
            else:
                msg.set_content(html_content.replace('<br>', '\n').replace('</p>', '\n'))

            msg.add_alternative(html_content, subtype="html")

            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                start_tls=True,
            )
            logger.info(f"Email sent successfully to {to}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False

    async def send_otp_email(self, to: str, otp: str, purpose: str = "registration") -> bool:
        """Send OTP verification email."""
        if purpose == "registration":
            subject = "🔐 AI-Digest - Verify Your Email"
            title = "Welcome to AI-Digest!"
            message = "Thank you for registering. Please use the following OTP to verify your email address:"
        elif purpose == "password_reset":
            subject = "🔐 AI-Digest - Password Reset"
            title = "Password Reset Request"
            message = "You requested a password reset. Use the following OTP to proceed:"
        else:
            subject = "🔐 AI-Digest - Verification Code"
            title = "Verification Required"
            message = "Please use the following OTP to complete your action:"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #060606; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="background: linear-gradient(135deg, #00F6FF 0%, #0047FF 100%); border-radius: 16px 16px 0 0; padding: 32px; text-align: center;">
            <h1 style="margin: 0; color: #060606; font-size: 28px; font-weight: 700;">
                📧 {title}
            </h1>
        </div>
        
        <div style="background-color: #0a0a0a; padding: 32px; border-radius: 0 0 16px 16px; border: 1px solid #0047FF; border-top: none;">
            <p style="color: #FBFAFA; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                {message}
            </p>
            
            <div style="background-color: #060606; border-radius: 12px; padding: 24px; text-align: center; border: 2px solid #00F6FF;">
                <span style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #00F6FF;">
                    {otp}
                </span>
            </div>
            
            <p style="color: #7BA8FF; font-size: 14px; margin: 24px 0 0 0; text-align: center;">
                This code expires in 10 minutes.
            </p>
            
            <p style="color: #7BA8FF; font-size: 13px; margin: 16px 0 0 0; text-align: center;">
                If you didn't request this code, please ignore this email.
            </p>
        </div>
        
        <div style="text-align: center; padding: 24px; color: #7BA8FF; font-size: 12px;">
            <p style="margin: 0;">AI Intelligence Digest</p>
        </div>
    </div>
</body>
</html>
"""
        plain_content = f"""
{title}

{message}

Your OTP code: {otp}

This code expires in 10 minutes.

If you didn't request this code, please ignore this email.

AI Intelligence Digest
"""
        return await self.send_email(to, subject, html_content, plain_content)

    async def send_welcome_email(self, to: str) -> bool:
        """Send welcome email after successful registration."""
        subject = "🎉 Welcome to AI-Digest!"
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #060606; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="background: linear-gradient(135deg, #00F6FF 0%, #0047FF 100%); border-radius: 16px 16px 0 0; padding: 32px; text-align: center;">
            <h1 style="margin: 0; color: #060606; font-size: 28px; font-weight: 700;">
                🎉 Welcome to AI-Digest!
            </h1>
        </div>
        
        <div style="background-color: #0a0a0a; padding: 32px; border-radius: 0 0 16px 16px; border: 1px solid #0047FF; border-top: none;">
            <p style="color: #FBFAFA; font-size: 16px; line-height: 1.6; margin: 0 0 16px 0;">
                Your account has been successfully verified! 🚀
            </p>
            
            <p style="color: #FBFAFA; font-size: 16px; line-height: 1.6; margin: 0 0 16px 0;">
                You can now:
            </p>
            
            <ul style="color: #00F6FF; font-size: 15px; line-height: 2; margin: 0 0 24px 0; padding-left: 24px;">
                <li>Select personas to receive curated digests</li>
                <li>Manage your subscription preferences</li>
                <li>Access your personalized dashboard</li>
            </ul>
            
            <p style="color: #7BA8FF; font-size: 14px; margin: 0;">
                Log in to your account to get started!
            </p>
        </div>
        
        <div style="text-align: center; padding: 24px; color: #7BA8FF; font-size: 12px;">
            <p style="margin: 0;">Stay informed. Stay ahead. 🚀</p>
        </div>
    </div>
</body>
</html>
"""
        return await self.send_email(to, subject, html_content)


async def send_otp_async(email_service: EmailService, to: str, otp: str, purpose: str) -> bool:
    """Wrapper function for sending OTP asynchronously."""
    return await email_service.send_otp_email(to, otp, purpose)


async def send_bulk_emails(
    email_service: EmailService,
    recipients: list,
    subject: str,
    html_content: str,
    plain_content: Optional[str] = None
) -> dict:
    """Send emails to multiple recipients concurrently."""
    results = {}

    async def send_single(to: str):
        success = await email_service.send_email(to, subject, html_content, plain_content)
        results[to] = success

    # Use asyncio.gather for concurrent sending with rate limiting
    batch_size = 10
    for i in range(0, len(recipients), batch_size):
        batch = recipients[i:i + batch_size]
        await asyncio.gather(*[send_single(r) for r in batch])
        if i + batch_size < len(recipients):
            await asyncio.sleep(1)  # Rate limiting between batches

    return results
