# scheduler.py — Automated daily reports via email + Telegram

import schedule
import time
import threading
from datetime import datetime


def _send_daily_email_report():
    """Send professional daily factory health report via Gmail."""
    try:
        from models import MACHINES, predict_machine, generate_daily_report
        from config import Config
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        if not Config.MAIL_USERNAME or Config.MAIL_USERNAME == 'your_gmail@gmail.com':
            print("[Scheduler] Email not configured — skipping daily report")
            return

        report  = generate_daily_report()
        preds   = {mid: predict_machine(mid) for mid in MACHINES}
        critical = [r for r in report if r['status'] == 'Critical']
        warning  = [r for r in report if r['status'] == 'Warning']
        healthy  = [r for r in report if r['status'] == 'Healthy']
        avg_h    = round(sum(r['health_score'] for r in report) / len(report), 1)
        total_cost = sum(preds[r['machine_id']]['cost_estimate']['total_estimated']
                        for r in report)

        # Build rows for each machine
        rows_html = ""
        for r in sorted(report, key=lambda x: x['failure_risk'], reverse=True):
            status = r['status']
            color  = '#E63946' if status=='Critical' else '#FF8C00' if status=='Warning' else '#00C878'
            rows_html += f"""
            <tr>
              <td style="padding:10px 16px;font-weight:600;color:#0A1628">{r['machine_id']}</td>
              <td style="padding:10px 16px;color:#2C3E50">{r['machine_name']}</td>
              <td style="padding:10px 16px">
                <div style="background:#e0e0e0;border-radius:6px;height:10px;width:100px">
                  <div style="background:{color};border-radius:6px;height:10px;width:{r['health_score']}px"></div>
                </div>
                <span style="font-size:12px;color:#6C757D">{r['health_score']}%</span>
              </td>
              <td style="padding:10px 16px;color:{color};font-weight:600">{r['failure_risk']}%</td>
              <td style="padding:10px 16px">
                <span style="background:{color}22;color:{color};border:1px solid {color}44;
                             border-radius:12px;padding:3px 10px;font-size:12px;font-weight:600">
                  {status}
                </span>
              </td>
              <td style="padding:10px 16px;color:#2C3E50">
                Rs.{preds[r['machine_id']]['cost_estimate']['total_estimated']:,}
              </td>
            </tr>"""

        now = datetime.now().strftime('%A, %d %B %Y — %H:%M')
        alert_banner = ""
        if critical:
            names = ', '.join([r['machine_id'] for r in critical])
            alert_banner = f"""
            <div style="background:#FEE8EA;border:1px solid #F0A0A5;border-radius:8px;
                        padding:14px 20px;margin-bottom:24px">
              <strong style="color:#E63946">⚠️ CRITICAL ALERT:</strong>
              <span style="color:#A32D2D"> {len(critical)} machine(s) require immediate attention: {names}</span>
            </div>"""

        html = f"""
        <!DOCTYPE html><html><body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,sans-serif">
        <table width="100%" cellpadding="0" cellspacing="0" style="padding:32px 16px">
          <tr><td align="center">
            <table width="600" cellpadding="0" cellspacing="0"
                   style="background:#ffffff;border-radius:16px;overflow:hidden;
                          border:1px solid #d0e4f0;box-shadow:0 4px 16px rgba(0,0,0,.08)">
              <!-- Header -->
              <tr><td style="background:linear-gradient(135deg,#0A1628,#0D2847);padding:28px 32px">
                <table width="100%"><tr>
                  <td><div style="color:#00B4D8;font-size:22px;font-weight:700">⚙️ PredictMaint Pro</div>
                      <div style="color:#90B4CC;font-size:13px;margin-top:4px">Daily Factory Health Report</div></td>
                  <td align="right"><div style="color:#6888A8;font-size:12px">{now}</div></td>
                </tr></table>
              </td></tr>

              <!-- Summary KPIs -->
              <tr><td style="padding:24px 32px 16px">
                {alert_banner}
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td width="25%" style="padding:0 8px 0 0">
                      <div style="background:#FEE8EA;border-radius:10px;padding:14px;text-align:center">
                        <div style="font-size:28px;font-weight:700;color:#E63946">{len(critical)}</div>
                        <div style="font-size:11px;color:#A32D2D;text-transform:uppercase;margin-top:4px">Critical</div>
                      </div>
                    </td>
                    <td width="25%" style="padding:0 4px">
                      <div style="background:#FFF3E0;border-radius:10px;padding:14px;text-align:center">
                        <div style="font-size:28px;font-weight:700;color:#FF8C00">{len(warning)}</div>
                        <div style="font-size:11px;color:#854F0B;text-transform:uppercase;margin-top:4px">Warning</div>
                      </div>
                    </td>
                    <td width="25%" style="padding:0 4px">
                      <div style="background:#E6FAF2;border-radius:10px;padding:14px;text-align:center">
                        <div style="font-size:28px;font-weight:700;color:#00C878">{len(healthy)}</div>
                        <div style="font-size:11px;color:#0F6E56;text-transform:uppercase;margin-top:4px">Healthy</div>
                      </div>
                    </td>
                    <td width="25%" style="padding:0 0 0 8px">
                      <div style="background:#E8F6FA;border-radius:10px;padding:14px;text-align:center">
                        <div style="font-size:28px;font-weight:700;color:#00B4D8">{avg_h}%</div>
                        <div style="font-size:11px;color:#185FA5;text-transform:uppercase;margin-top:4px">Avg Health</div>
                      </div>
                    </td>
                  </tr>
                </table>
              </td></tr>

              <!-- Machine Table -->
              <tr><td style="padding:0 32px 24px">
                <div style="font-weight:700;color:#0A1628;font-size:15px;margin-bottom:12px">
                  Machine Status Overview
                </div>
                <table width="100%" cellpadding="0" cellspacing="0"
                       style="border:1px solid #d0e4f0;border-radius:10px;overflow:hidden;font-size:13px">
                  <thead>
                    <tr style="background:#0A1628;color:#ffffff">
                      <th style="padding:10px 16px;text-align:left;font-weight:600">Machine</th>
                      <th style="padding:10px 16px;text-align:left;font-weight:600">Name</th>
                      <th style="padding:10px 16px;text-align:left;font-weight:600">Health</th>
                      <th style="padding:10px 16px;text-align:left;font-weight:600">Risk</th>
                      <th style="padding:10px 16px;text-align:left;font-weight:600">Status</th>
                      <th style="padding:10px 16px;text-align:left;font-weight:600">Est. Cost</th>
                    </tr>
                  </thead>
                  <tbody>{rows_html}</tbody>
                </table>
              </td></tr>

              <!-- Total cost -->
              <tr><td style="padding:0 32px 24px">
                <div style="background:#E8F6FA;border:1px solid #B5D4F4;border-radius:8px;padding:14px 20px;
                            display:flex;justify-content:space-between;align-items:center">
                  <span style="color:#0A1628;font-weight:600">Total Potential Risk Cost (if all at-risk machines fail)</span>
                  <span style="color:#E63946;font-weight:700;font-size:18px">Rs.{total_cost:,}</span>
                </div>
              </td></tr>

              <!-- Footer -->
              <tr><td style="background:#f8fbff;padding:16px 32px;border-top:1px solid #d0e4f0">
                <div style="color:#9ABCCC;font-size:11px;text-align:center">
                  PredictMaint Pro — Industrial Predictive Maintenance System v6.0<br>
                  This is an automated daily report. Do not reply to this email.
                </div>
              </td></tr>
            </table>
          </td></tr>
        </table>
        </body></html>"""

        # Plain text fallback
        plain = f"""PredictMaint Pro — Daily Factory Report ({now})

SUMMARY:
  Critical: {len(critical)} machines
  Warning:  {len(warning)} machines
  Healthy:  {len(healthy)} machines
  Avg Health: {avg_h}%

MACHINES:
""" + "\n".join([f"  {r['machine_id']}: {r['health_score']}% health | {r['status']}"
                  for r in sorted(report, key=lambda x: x['failure_risk'], reverse=True)])

        msg = MIMEMultipart('alternative')
        msg['Subject'] = (f"[{'🔴 CRITICAL' if critical else '🟡 Warning' if warning else '🟢 Healthy'}] "
                          f"PredictMaint Pro — Daily Report {datetime.now().strftime('%d %b %Y')}")
        msg['From']    = f"PredictMaint Pro <{Config.MAIL_USERNAME}>"
        msg['To']      = Config.ALERT_RECIPIENT
        msg.attach(MIMEText(plain, 'plain'))
        msg.attach(MIMEText(html, 'html'))

        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
        server.starttls()
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        server.sendmail(Config.MAIL_USERNAME, Config.ALERT_RECIPIENT, msg.as_string())
        server.quit()
        print(f"[Scheduler] ✅ Daily email report sent to {Config.ALERT_RECIPIENT}")

    except Exception as e:
        print(f"[Scheduler] ❌ Daily email error: {e}")


def _send_daily_telegram_report():
    """Send daily report via Telegram."""
    try:
        from models import generate_daily_report
        from telegram_alert import send_telegram_daily_report, is_configured
        if not is_configured():
            return
        report = generate_daily_report()
        ok, msg = send_telegram_daily_report(report)
        if ok:
            print("[Scheduler] ✅ Daily Telegram report sent")
    except Exception as e:
        print(f"[Scheduler] ❌ Telegram report error: {e}")


def _run_daily_report():
    """Run both email and Telegram daily reports."""
    print(f"[Scheduler] 📊 Running daily reports at {datetime.now().strftime('%H:%M')}")
    _send_daily_email_report()
    _send_daily_telegram_report()


def start_scheduler():
    """Start background scheduler thread."""
    # Daily report at 8:00 AM
    schedule.every().day.at("08:00").do(_run_daily_report)

    # Also run once 5 seconds after startup (so you can test immediately)
    schedule.every(5).seconds.do(_run_startup_report)

    def _runner():
        while True:
            schedule.run_pending()
            time.sleep(60)

    thread = threading.Thread(target=_runner, daemon=True, name="DailyReportScheduler")
    thread.start()
    print("[Scheduler] ✅ Started — daily report scheduled at 08:00")
    return thread


_startup_done = False
def _run_startup_report():
    """Run once 5s after startup, then cancel."""
    global _startup_done
    if not _startup_done:
        _startup_done = True
        print("[Scheduler] ⏱️  Startup report in 5 seconds...")
        time.sleep(5)
        _run_daily_report()
    # Cancel this job after first run
    return schedule.CancelJob
