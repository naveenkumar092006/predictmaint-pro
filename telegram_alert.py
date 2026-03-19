# telegram_alert.py — Real Telegram Bot Alerts

import json
import urllib.request
import urllib.error
from datetime import datetime
from config import Config


def _send(token, chat_id, text, parse_mode="Markdown"):
    """Core send function."""
    url     = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id":    str(chat_id),
        "text":       text,
        "parse_mode": parse_mode
    }).encode('utf-8')
    req = urllib.request.Request(
        url, data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get('ok'):
                return True, "Sent!"
            return False, data.get('description', 'Failed')
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return False, f"HTTP {e.code}: {body[:80]}"
    except Exception as e:
        return False, str(e)


def is_configured():
    """Check if Telegram is properly configured."""
    token   = getattr(Config, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(Config, 'TELEGRAM_CHAT_ID', '')
    return bool(token and token not in ('YOUR_BOT_TOKEN', '', None) and
                chat_id and chat_id not in ('YOUR_CHAT_ID', '', None))


def send_telegram_alert(machine_id, prediction):
    """Send critical machine alert to Telegram."""
    token   = getattr(Config, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(Config, 'TELEGRAM_CHAT_ID', '')

    if not is_configured():
        print(f"[Telegram] Not configured — alert for {machine_id} skipped")
        return False, "Telegram not configured. Add BOT_TOKEN and CHAT_ID in config.py"

    status = prediction.get('status', 'Unknown')
    risk   = prediction.get('failure_probability', 0)
    health = prediction.get('health_score', 0)
    issue  = prediction.get('failure_type', 'Unknown')
    rul    = prediction.get('rul_days', 0)
    cost   = prediction.get('cost_estimate', {}).get('total_estimated', 0)
    name   = prediction.get('machine_info', {}).get('name', machine_id)
    sols   = prediction.get('solutions', ['Check immediately'])
    icon   = "🔴" if status == 'Critical' else "🟡"

    msg = (
        f"{icon} *FACTORY ALERT — PredictMaint Pro*\n\n"
        f"🏭 *Machine:* `{machine_id}` — {name}\n"
        f"📊 *Status:* {status}\n"
        f"⚠️ *Failure Risk:* {risk}%\n"
        f"💚 *Health Score:* {health}%\n"
        f"🔧 *Issue:* {issue}\n"
        f"⏱️ *RUL:* {rul} days remaining\n"
        f"💰 *Est. Cost:* Rs.{cost:,}\n\n"
        f"✅ *Action Required:*\n_{sols[0]}_\n\n"
        f"🕐 _{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}_\n"
        f"_PredictMaint Pro — Industrial AI System_"
    )

    ok, result = _send(token, chat_id, msg)
    if ok:
        print(f"[Telegram] ✅ Alert sent for {machine_id}")
    else:
        print(f"[Telegram] ❌ Failed for {machine_id}: {result}")
    return ok, result


def send_telegram_daily_report(report):
    """Send daily factory health report."""
    token   = getattr(Config, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(Config, 'TELEGRAM_CHAT_ID', '')

    if not is_configured():
        return False, "Telegram not configured"

    critical = [r for r in report if r['status'] == 'Critical']
    warning  = [r for r in report if r['status'] == 'Warning']
    healthy  = [r for r in report if r['status'] == 'Healthy']
    avg_h    = round(sum(r['health_score'] for r in report) / len(report), 1)
    total_cost = sum(r.get('cost_estimate', {}).get('total_estimated', 0) for r in report)

    msg = (
        f"📊 *DAILY FACTORY REPORT*\n"
        f"_{datetime.now().strftime('%A, %d %B %Y — %H:%M')}_\n\n"
        f"🔴 Critical: *{len(critical)}* machine(s)\n"
        f"🟡 Warning:  *{len(warning)}* machine(s)\n"
        f"🟢 Healthy:  *{len(healthy)}* machine(s)\n"
        f"📈 Avg Health: *{avg_h}%*\n"
        f"💰 Total Risk Cost: *Rs.{total_cost:,}*\n\n"
    )

    for r in sorted(report, key=lambda x: x.get('failure_probability', 0), reverse=True):
        mid   = r.get('machine_id', '???')
        h     = r.get('health_score', 0)
        risk  = r.get('failure_probability', 0)
        st    = r.get('status', '?')
        icon2 = "🔴" if st == 'Critical' else "🟡" if st == 'Warning' else "🟢"
        msg += f"{icon2} `{mid}`: Health={h}% | Risk={risk}%\n"

    msg += f"\n_— PredictMaint Pro Auto Report_"

    ok, result = _send(token, chat_id, msg)
    if ok:
        print("[Telegram] ✅ Daily report sent")
    return ok, result


def send_telegram_test():
    """Send a test message to verify configuration."""
    token   = getattr(Config, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(Config, 'TELEGRAM_CHAT_ID', '')

    if not is_configured():
        return False, "Not configured"

    msg = ("✅ *PredictMaint Pro — Test Message*\n\n"
           "Your Telegram alerts are configured correctly!\n"
           f"_Sent at {datetime.now().strftime('%H:%M:%S')}_")
    return _send(token, chat_id, msg)
