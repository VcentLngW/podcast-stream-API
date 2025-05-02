import logging
from pathlib import Path
from typing import Dict, List

from fastapi import BackgroundTasks
from fastapi.templating import Jinja2Templates
from jinja2 import Template
from pydantic import EmailStr

from app.core.config import settings

# Set up templates directory
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Import aiosmtplib for async email sending
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


async def send_email(
    email_to: str,
    subject: str,
    html_content: str,
):
    """
    Send an email with the provided HTML content
    """
    # Create message
    message = MIMEMultipart()
    message["From"] = settings.MAIL_FROM
    message["To"] = email_to
    message["Subject"] = subject
    
    # Add HTML body
    message.attach(MIMEText(html_content, "html"))
    
    # Connect and send
    try:
        smtp = aiosmtplib.SMTP(
            hostname=settings.MAIL_SERVER,
            port=settings.MAIL_PORT,
            use_tls=settings.MAIL_TLS,
            start_tls=False
        )
        await smtp.connect()
        await smtp.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        await smtp.send_message(message)
        await smtp.quit()
        logging.info(f"Email sent successfully to {email_to}")
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return {"status": "error", "message": str(e)}


def get_verification_email_template(username: str, verification_url: str) -> str:
    """
    Generate the HTML content for a verification email
    """
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Verify Your Email</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            .header {
                background-color: #f5f5f5;
                padding: 15px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }
            .content {
                padding: 20px;
            }
            .button {
                display: inline-block;
                padding: 10px 20px;
                background-color: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                margin: 20px 0;
            }
            .footer {
                font-size: 12px;
                color: #777;
                text-align: center;
                margin-top: 30px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Email Verification</h2>
            </div>
            <div class="content">
                <p>Hello {{ username }},</p>
                <p>Thank you for registering! Please click the button below to verify your email address:</p>
                <div style="text-align: center;">
                    <a href="{{ verification_url }}" class="button">Verify Email</a>
                </div>
                <p>Or copy and paste the following link into your browser:</p>
                <p>{{ verification_url }}</p>
                <p>This link will expire in 24 hours.</p>
                <p>If you didn't create an account, you can safely ignore this email.</p>
                <p>Best regards,<br>{{ app_name }} Team</p>
            </div>
            <div class="footer">
                <p>This is an automated email. Please do not reply to this message.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    template = Template(email_template)
    return template.render(
        username=username,
        verification_url=verification_url,
        app_name=settings.APP_NAME
    )


async def send_verification_email(
    background_tasks: BackgroundTasks, 
    username: str,  # This is now actually the user's name, not username
    email_to: EmailStr, 
    token: str
):
    """
    Send a verification email with a link to confirm the user's email address
    """
    # Create a verification URL that points to the frontend, not directly to the API
    verification_url = f"{settings.FRONTEND_URL}/auth/verify?token={token}"
    subject = f"Verify your email for {settings.APP_NAME}"
    
    html_content = get_verification_email_template(username, verification_url)
    
    # Send email asynchronously
    return await send_email(
        email_to=email_to,
        subject=subject,
        html_content=html_content,
    ) 