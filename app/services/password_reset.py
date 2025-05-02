from jinja2 import Template
from pydantic import EmailStr
from fastapi import BackgroundTasks

from app.core.config import settings
from app.services.email import send_email


def get_password_reset_email_template(username: str, reset_url: str) -> str:
    """
    Generate the HTML content for a password reset email
    """
    email_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Reset Your Password</title>
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
                <h2>Password Reset</h2>
            </div>
            <div class="content">
                <p>Hello {{ username }},</p>
                <p>We received a request to reset your password. Please click the button below to create a new password:</p>
                <div style="text-align: center;">
                    <a href="{{ reset_url }}" class="button">Reset Password</a>
                </div>
                <p>Or copy and paste the following link into your browser:</p>
                <p>{{ reset_url }}</p>
                <p>This link will expire in 1 hour. If you didn't request a password reset, you can safely ignore this email.</p>
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
        reset_url=reset_url,
        app_name=settings.APP_NAME
    )


async def send_password_reset_email(
    background_tasks: BackgroundTasks, 
    username: str,
    email_to: EmailStr, 
    token: str
):
    """
    Send a password reset email with a link to reset the user's password
    """
    # Create a reset URL that points to the frontend
    reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}&email={email_to}"
    subject = f"Reset your password for {settings.APP_NAME}"
    
    html_content = get_password_reset_email_template(username, reset_url)
    
    # Send email asynchronously
    return await send_email(
        email_to=email_to,
        subject=subject,
        html_content=html_content,
    ) 