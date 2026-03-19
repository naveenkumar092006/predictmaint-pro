# twofa.py — Email OTP Authentication via Gmail SMTP

import random
import string
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from datetime import datetime, timedelta
from config import Config

_otp_store = {}

def generate_otp(username):
    """Generate a secure 6-digit OTP valid for 5 minutes."""
    otp = ''.join(random.choices(string.digits, k=6))
    _otp_store[username] = {
        "otp":     otp,
        "expires": datetime.now() + timedelta(minutes=5),
        "used":    False
    }
    print(f"\n[2FA] OTP generated for {username}: {otp}\n")
    return otp

def send_otp_email(email_address, otp, username):
    """Send OTP via Gmail SMTP."""
    try:
        if not Config.MAIL_USERNAME or Config.MAIL_USERNAME == 'your_email@gmail.com':
            print(f"[2FA EMAIL] Not configured. OTP for {username}: {otp}")
            return False, "Email not configured"

        # Build professional HTML email
        html = f"""
        <!DOCTYPE html>
        <html>
        <body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif">
        <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px">
          <tr><td align="center">
            <table width="480" cellpadding="0" cellspacing="0"
                   style="background:#0d1828;border-radius:16px;overflow:hidden;border:1px solid rgba(0,212,255,0.2)">

              <!-- Header -->
              <tr><td style="background:linear-gradient(135deg,#0a1525,#0d2040);padding:32px;text-align:center;border-bottom:1px solid rgba(0,212,255,0.15)">
                <div style="font-size:28px;margin-bottom:8px">⚙️</div>
                <div style="color:#00d4ff;font-size:22px;font-weight:700;letter-spacing:1px">PredictMaint Pro</div>
                <div style="color:#556677;font-size:12px;letter-spacing:2px;text-transform:uppercase;margin-top:4px">Industrial Intelligence Platform</div>
              </td></tr>

              <!-- Body -->
              <tr><td style="padding:32px">
                <p style="color:#aabbcc;font-size:15px;margin:0 0 20px">
                  Hello <strong style="color:#fff">{username}</strong>,
                </p>
                <p style="color:#8899aa;font-size:14px;margin:0 0 24px;line-height:1.6">
                  Your login verification code for <strong style="color:#00d4ff">PredictMaint Pro</strong> is:
                </p>

                <!-- OTP Box -->
                <div style="background:rgba(0,212,255,0.08);border:2px solid rgba(0,212,255,0.3);
                            border-radius:12px;padding:24px;text-align:center;margin:0 0 24px">
                  <div style="color:#00d4ff;font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px">
                    Verification Code
                  </div>
                  <div style="color:#ffffff;font-size:42px;font-weight:700;letter-spacing:12px;
                              font-family:'Courier New',monospace">
                    {otp}
                  </div>
                  <div style="color:#556677;font-size:12px;margin-top:12px">
                    ⏱ Valid for 5 minutes only
                  </div>
                </div>

                <p style="color:#556677;font-size:13px;margin:0 0 8px;line-height:1.6">
                  🔒 Enter this code on the verification screen to complete your login.
                </p>
                <p style="color:#445566;font-size:12px;margin:0;line-height:1.6">
                  If you did not request this code, please ignore this email and contact your system administrator immediately.
                </p>
              </td></tr>

              <!-- Footer -->
              <tr><td style="background:rgba(0,0,0,0.3);padding:16px 32px;text-align:center;border-top:1px solid rgba(255,255,255,0.05)">
                <div style="color:#334455;font-size:11px;letter-spacing:1px">
                  PredictMaint Pro &nbsp;|&nbsp; Industrial Predictive Maintenance System
                </div>
                <div style="color:#2a3a4a;font-size:10px;margin-top:4px">
                  Do not reply to this email &nbsp;|&nbsp; This is an automated message
                </div>
              </td></tr>

            </table>
          </td></tr>
        </table>
        </body>
        </html>
        """

        # Plain text fallback
        plain = f"""
PredictMaint Pro — Login Verification

Hello {username},

Your OTP verification code is: {otp}

This code is valid for 5 minutes only.
Do not share this code with anyone.

— PredictMaint Pro Security System
        """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🔐 PredictMaint Pro — Your Login OTP: {otp}"
        msg['From']    = f"PredictMaint Pro <{Config.MAIL_USERNAME}>"
        msg['To']      = email_address
        msg.attach(MIMEText(plain, 'plain'))
        msg.attach(MIMEText(html,  'html'))

        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
        server.starttls()
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        server.sendmail(Config.MAIL_USERNAME, email_address, msg.as_string())
        server.quit()

        print(f"[2FA EMAIL] OTP sent to {email_address}")
        return True, f"OTP sent to {email_address}"

    except smtplib.SMTPAuthenticationError:
        print(f"[2FA EMAIL] Auth failed — check Gmail App Password in config.py")
        return False, "Email authentication failed"
    except smtplib.SMTPException as e:
        print(f"[2FA EMAIL] SMTP error: {e}")
        return False, "Email sending failed"
    except Exception as e:
        print(f"[2FA EMAIL] Error: {e}")
        return False, str(e)

def verify_otp(username, otp_input):
    """Verify OTP — returns (success, message)."""
    if username not in _otp_store:
        return False, "No OTP found. Please login again."
    record = _otp_store[username]
    if record["used"]:
        return False, "OTP already used. Please login again."
    if datetime.now() > record["expires"]:
        del _otp_store[username]
        return False, "OTP expired. Please request a new one."
    if otp_input.strip() != record["otp"]:
        return False, "Incorrect OTP. Please try again."
    record["used"] = True
    return True, "Verified successfully."

def get_remaining_seconds(username):
    if username in _otp_store and not _otp_store[username]["used"]:
        remaining = int((_otp_store[username]["expires"] - datetime.now()).total_seconds())
        return max(0, remaining)
    return 0
