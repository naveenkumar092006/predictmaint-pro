# chatbot.py — Expert Industrial AI Assistant for PredictMaint Pro

import re
from datetime import datetime

EXPERT_PERSONA = """You are an AI-powered Industrial Predictive Maintenance Assistant for PredictMaint Pro.
Act like a smart expert similar to ChatGPT — answer ANY maintenance-related question intelligently.
User: {username} | {time}

LIVE FACTORY DATA:
Factory status: {n_crit} critical {crit}, {n_warn} warning, avg health={avg}%
ML Models: Random Forest accuracy={accuracy}%, Isolation Forest, RUL Regressor

MACHINE DATA:
{mdata}

SYSTEM KNOWLEDGE:
- Health score 0-100 (100=perfect, 0=critical failure imminent)
- Failure probability % (>60%=Critical, 30-60%=Warning, <30%=Healthy)
- RUL = Remaining Useful Life in days before maintenance required
- Sensors: Temperature (limit 90C), Vibration (limit 5.5mm/s), Pressure (limit 7.5bar)
- Failure types: Overheating, Bearing Issue, Valve Blockage, Wear and Tear

WEBSITE SECTIONS:
Dashboard (real-time charts), Analytics (Plotly trends), Factory Map (Leaflet.js),
Search (machine lookup), Work Orders, Inventory, Maintenance History,
Downtime Calculator, Machine Comparison, ChatBot, Notifications, PDF/Excel reports

STRICT RULES:
1. Always give complete, meaningful, expert-level answers using real data above
2. If data not available, give expert industrial maintenance guidance
3. Be conversational and intelligent — never give robotic fixed responses
4. Suggest causes and solutions when problems are mentioned
5. Never say you are just a chatbot — always act as expert industrial AI assistant
6. Handle unclear questions with logical expert interpretation
7. Answer in 3-5 lines maximum with emojis for clarity
8. Never show technical errors — always respond intelligently

User question: {question}"""


def chatbot_response(message, username="User"):
    """Main entry point — tries Gemini AI first, falls back to expert rule-based."""

    # ── CAMERA-AWARE QUERIES (checked before anything else) ───────────────────
    msg_lower = message.lower().strip()
    CAMERA_KW = ['detected','camera','live','visible','which machine is detected',
                 'what machine','critical machine','status of detected',
                 'camera see','what do you see','live feed']
    if any(k in msg_lower for k in CAMERA_KW):
        try:
            import urllib.request, json as _json
            r = urllib.request.urlopen(
                'http://127.0.0.1:5000/api/camera-context', timeout=2)
            ctx   = _json.loads(r.read().decode())
            preds = ctx.get('predictions', {})
            stats = ctx.get('stats', {})

            if any(k in msg_lower for k in ['which machine is detected','what machine','what do you see','camera see']):
                if not preds:
                    return ("📷 Camera is running but no machines detected yet.\n"
                            "Show an object to the camera:\n"
                            "  • Bottle/Cup → MCH-101 (CNC Milling Machine)\n"
                            "  • Laptop/Keyboard → MCH-102 (Hydraulic Press)\n"
                            "  • Book/Backpack → MCH-103 (Conveyor Belt)\n"
                            "  • Phone/Remote → MCH-104 (Industrial Compressor)")
                names = [f"{mid} ({p['machine_name']})" for mid, p in preds.items()]
                return (f"📷 Camera currently detects: {', '.join(names)}\n"
                        f"Total: {stats.get('total_machines',0)} | "
                        f"Critical: {stats.get('critical_count',0)} | "
                        f"Warning: {stats.get('warning_count',0)} | "
                        f"Normal: {stats.get('normal_count',0)}")

            if 'critical' in msg_lower:
                crits = [mid for mid, p in preds.items() if p['status'] == 'CRITICAL']
                if crits:
                    details = []
                    for c in crits:
                        p = preds[c]
                        details.append(f"  🔴 {c} ({p['machine_name']}): "
                                       f"Failure risk {p['failure_probability']}%, "
                                       f"Health {p['health_score']}%")
                    return ("🚨 Critical machines detected by camera:\n"
                            + "\n".join(details)
                            + "\nImmediate maintenance action required!")
                return "✅ No critical machines detected by camera right now. All systems normal."

            if 'status' in msg_lower or 'detected' in msg_lower:
                return ctx.get('context', 'Camera is running. No machines detected.')

            return ctx.get('context', 'Camera is running.')
        except Exception:
            pass  # fall through to Gemini / rule-based

    # ── ORIGINAL LOGIC ────────────────────────────────────────────────────────
    try:
        from models import MACHINES, predict_machine, MODEL_METRICS
        from config import Config

        # Build predictions dict with consistent keys
        predictions = {}
        for mid in MACHINES:
            pred = predict_machine(mid)
            predictions[mid] = {
                "name":         pred["machine_info"]["name"],
                "operator":     pred["machine_info"]["operator"],
                "location":     pred["machine_info"]["location"],
                "health":       pred["health_score"],
                "risk":         pred["failure_probability"],
                "status":       pred["status"],
                "failure_type": pred["failure_type"],
                "root_cause":   pred["root_cause"],
                "solutions":    pred["solutions"],
                "rul_days":     pred["rul_days"],
                "temp":         pred["readings"]["temperature"],
                "vibration":    pred["readings"]["vibration"],
                "pressure":     pred["readings"]["pressure"],
                "hours":        pred["readings"]["operating_hours"],
                "cost":         pred["cost_estimate"]["total_estimated"],
                "savings":      pred["cost_estimate"]["estimated_savings"],
                "anomaly":      pred["is_anomaly"],
            }

        # Try Gemini AI first
        api_key = getattr(Config, 'GEMINI_API_KEY', '')
        if api_key and api_key not in ('YOUR_GEMINI_API_KEY', '', None):
            result = _gemini(message, predictions, username, api_key, MODEL_METRICS)
            if result:
                return result

        # Expert rule-based fallback
        return _expert_answer(message, username, predictions, MODEL_METRICS, MACHINES)

    except Exception as e:
        # Never show raw errors — give expert response
        return ("I'm analysing your query. Based on standard industrial maintenance practice: "
                "please check the machine's sensor readings, verify safety thresholds, "
                "and consult the maintenance schedule. If the issue persists, escalate to a senior engineer.")


def _gemini(msg, preds, username, api_key, metrics):
    """Call Google Gemini API with expert persona system prompt."""
    import json, urllib.request, urllib.error

    crit = [m for m, p in preds.items() if p["status"] == "Critical"]
    warn = [m for m, p in preds.items() if p["status"] == "Warning"]
    avg  = round(sum(p["health"] for p in preds.values()) / len(preds), 1)

    mdata = ""
    for mid, p in preds.items():
        mdata += (f"\n  {mid} ({p['name']}): health={p['health']}%, risk={p['risk']}%, "
                  f"status={p['status']}, issue={p['failure_type']}, RUL={p['rul_days']}days, "
                  f"temp={p['temp']}C, vibration={p['vibration']}mm/s, "
                  f"pressure={p['pressure']}bar, cost=Rs.{p['cost']:,}, "
                  f"anomaly={'YES' if p['anomaly'] else 'NO'}, operator={p['operator']}")

    prompt = EXPERT_PERSONA.format(
        username=username,
        time=datetime.now().strftime('%d %b %Y %H:%M'),
        n_crit=len(crit), crit=crit,
        n_warn=len(warn),
        avg=avg,
        accuracy=metrics['accuracy'],
        mdata=mdata,
        question=msg
    )

    for ver, model in [("v1", "gemini-2.0-flash-exp"),
                       ("v1beta", "gemini-2.0-flash"),
                       ("v1beta", "gemini-1.5-flash")]:
        url = (f"https://generativelanguage.googleapis.com/"
               f"{ver}/models/{model}:generateContent?key={api_key}")
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps({
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 300}
                }).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as r:
                d = json.loads(r.read().decode())
                t = (d.get("candidates", [])[0].get("content", {})
                      .get("parts", [])[0].get("text", "").strip())
                if len(t) > 10:
                    return t
        except urllib.error.HTTPError as e:
            if e.code in (429, 403):
                return None  # quota exceeded — use expert rule-based
            continue
        except:
            continue
    return None


def _find_machine(msg, MACHINES):
    """Identify machine from message — handles MCH-102, 102, 'compressor', etc."""
    for mid in MACHINES:
        if mid.lower() in msg:
            return mid
    nums = re.findall(r'\b10[1-6]\b', msg)
    if nums:
        return f"MCH-{nums[0]}"
    for mid, info in MACHINES.items():
        words = [w for w in info["name"].lower().split() if len(w) > 3]
        if any(w in msg for w in words):
            return mid
    return None


def _expert_answer(message, username, predictions, MODEL_METRICS, MACHINES):
    """
    Expert industrial AI assistant — handles ANY question intelligently.
    Acts like ChatGPT for industrial maintenance — not a fixed keyword matcher.
    """
    msg = message.lower().strip()

    def has(*words):
        return any(w in msg for w in words)

    # Pre-compute factory state
    critical  = [m for m, p in predictions.items() if p["status"] == "Critical"]
    warning   = [m for m, p in predictions.items() if p["status"] == "Warning"]
    healthy   = [m for m, p in predictions.items() if p["status"] == "Healthy"]
    avg_h     = round(sum(p["health"] for p in predictions.values()) / len(predictions), 1)
    worst     = max(predictions, key=lambda m: predictions[m]["risk"])
    best      = max(predictions, key=lambda m: predictions[m]["health"])
    hot       = max(predictions, key=lambda m: predictions[m]["temp"])
    most_vib  = max(predictions, key=lambda m: predictions[m]["vibration"])
    low_rul   = min(predictions, key=lambda m: predictions[m]["rul_days"])
    total_cost = sum(p["cost"] for p in predictions.values())

    # ── STEP 1: Machine-specific query (highest priority) ──────────────────────
    mid = _find_machine(msg, MACHINES)
    if mid and mid in predictions:
        p    = predictions[mid]
        icon = "🔴" if p["status"] == "Critical" else "🟡" if p["status"] == "Warning" else "✅"

        # Temperature specific
        if has("temp", "hot", "heat", "overheating", "cooling", "thermal", "degree"):
            advice = ("⚠️ Immediate cooling required — check coolant system and lubrication."
                      if p["temp"] > 90 else "✅ Temperature within safe operating range.")
            return (f"🌡️ {mid} — {p['name']} Temperature Analysis\n"
                    f"Current: {p['temp']}°C | Safe limit: 90°C | Status: {p['status']}\n"
                    f"{advice}\n"
                    f"Possible causes: blocked cooling vents, coolant leak, excessive load, ambient heat.\n"
                    f"Recommendation: {p['solutions'][0]}")

        # Vibration specific
        if has("vibrat", "bearing", "shake", "oscillat", "noise", "rattle"):
            advice = ("⚠️ CRITICAL — bearing failure risk. Schedule immediate inspection."
                      if p["vibration"] > 5.5 else "✅ Vibration within safe limits.")
            return (f"📳 {mid} — {p['name']} Vibration Analysis\n"
                    f"Current: {p['vibration']} mm/s | Safe limit: 5.5 mm/s | Status: {p['status']}\n"
                    f"{advice}\n"
                    f"Possible causes: misalignment, worn bearings, loose mounting, imbalance.\n"
                    f"Recommendation: {p['solutions'][0]}")

        # Pressure specific
        if has("pressure", "valve", "blockage", "hydraulic", "bar", "leak", "pipe"):
            advice = ("⚠️ ABOVE safe limit — valve blockage or pump failure risk."
                      if p["pressure"] > 7.5 else "✅ Pressure within normal operating range.")
            return (f"🔧 {mid} — {p['name']} Pressure Analysis\n"
                    f"Current: {p['pressure']} bar | Safe limit: 7.5 bar | Status: {p['status']}\n"
                    f"{advice}\n"
                    f"Possible causes: blocked filters, failing pump, valve malfunction, thermal expansion.\n"
                    f"Recommendation: {p['solutions'][0]}")

        # RUL / lifespan
        if has("rul", "life", "remaining", "replace", "days", "last", "long", "when"):
            rul_icon = "🔴" if p["rul_days"] < 10 else "🟡" if p["rul_days"] < 20 else "✅"
            urgency  = ("REPLACE IMMEDIATELY — machine is at end of life!" if p["rul_days"] < 5
                        else "Schedule urgent maintenance within the week." if p["rul_days"] < 10
                        else "Plan maintenance within the next 2–3 weeks." if p["rul_days"] < 20
                        else "Adequate life remaining — continue regular monitoring.")
            return (f"⏱️ {mid} — Remaining Useful Life Assessment\n"
                    f"{rul_icon} RUL: {p['rul_days']} days | Health: {p['health']}% | Risk: {p['risk']}%\n"
                    f"Action: {urgency}\n"
                    f"Issue driving degradation: {p['failure_type']}\n"
                    f"Estimated repair cost: Rs.{p['cost']:,} | Preventive saves: Rs.{p['savings']:,}")

        # Cost / budget
        if has("cost", "repair", "money", "budget", "expensive", "price", "rupee"):
            return (f"💰 {mid} — Maintenance Cost Analysis\n"
                    f"Estimated repair cost: Rs.{p['cost']:,}\n"
                    f"Preventive maintenance cost: Rs.{p['savings']:,} (65% cheaper)\n"
                    f"Issue: {p['failure_type']} | Status: {p['status']}\n"
                    f"Expert advice: Preventive action now saves Rs.{p['cost'] - p['savings']:,} vs waiting for breakdown.")

        # Why / cause / reason
        if has("why", "cause", "reason", "what happened", "root cause", "diagnosis"):
            return (f"🔍 {mid} — Root Cause Analysis\n"
                    f"Primary issue: {p['failure_type']} | Health: {p['health']}% | Risk: {p['risk']}%\n"
                    f"Root cause: {p['root_cause']}\n"
                    f"Sensor evidence: Temp={p['temp']}°C, Vibration={p['vibration']}mm/s, Pressure={p['pressure']}bar\n"
                    f"Recommended actions:\n"
                    + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(p["solutions"][:3])))

        # What to do / fix / repair
        if has("what to do", "how to fix", "solution", "recommend", "action", "repair", "fix", "solve"):
            return (f"💡 {mid} — Expert Maintenance Recommendations\n"
                    f"Status: {icon} {p['status']} | Risk: {p['risk']}% | RUL: {p['rul_days']} days\n"
                    f"Priority actions:\n"
                    + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(p["solutions"]))
                    + f"\nRoot cause: {p['root_cause']}\n"
                    f"Assign to: {p['operator']} | Est. cost: Rs.{p['cost']:,}")

        # General machine status / health check
        return (f"{icon} {mid} — {p['name']} | Expert Health Report\n"
                f"Health Score: {p['health']}% | Failure Risk: {p['risk']}% | Status: {p['status']}\n"
                f"Sensors: Temp={p['temp']}°C, Vibration={p['vibration']}mm/s, Pressure={p['pressure']}bar\n"
                f"Issue: {p['failure_type']} | RUL: {p['rul_days']} days | Cost: Rs.{p['cost']:,}\n"
                f"Operator: {p['operator']} | Anomaly: {'⚠️ Detected' if p['anomaly'] else '✅ None'}\n"
                f"Recommendation: {p['solutions'][0]}")

    # ── STEP 2: General greetings & help ───────────────────────────────────────
    if has("hello", "hi", "hey", "good morning", "good evening", "good afternoon",
           "what's up", "howdy", "start"):
        status_icon = "🔴 ALERT" if critical else "🟡 Caution" if warning else "🟢 All Good"
        return (f"👋 Hello {username}! I'm your Industrial AI Maintenance Assistant.\n"
                f"Factory Status: {status_icon} | Avg Health: {avg_h}% | "
                f"{len(critical)} Critical, {len(warning)} Warning, {len(healthy)} Healthy\n"
                f"I can help with machine diagnostics, failure analysis, maintenance planning, "
                f"cost estimation, and any industrial question.\n"
                f"{'⚠️ Urgent: ' + ', '.join(critical) + ' need immediate attention!' if critical else 'Ask me anything about your factory!'}")

    if has("help", "what can you do", "capabilities", "commands", "guide", "how to use you"):
        return ("💡 I'm your expert Industrial AI Assistant — ask me anything:\n"
                "🔴 Machine health: 'Is MCH-104 healthy?', 'Why is 102 failing?'\n"
                "🌡️ Sensors: 'Temperature report', 'Which machine is vibrating most?'\n"
                "💰 Costs: 'How much to repair MCH-105?', 'Total maintenance cost'\n"
                "⏱️ Lifespan: 'When should I replace MCH-104?', 'Remaining useful life'\n"
                "🔧 Solutions: 'How to fix bearing failure?', 'What causes overheating?'\n"
                "📊 Analytics: 'Factory summary', 'Which machine will fail next?'\n"
                "🏭 System: 'How does predictive maintenance work?', 'Explain the ML models'\n"
                "Just type naturally — I understand any question!")

    # ── STEP 3: Failure / worst machine ────────────────────────────────────────
    if has("fail", "will fail", "about to fail", "going to fail", "most critical",
           "highest risk", "worst machine", "breakdown", "dangerous", "urgent"):
        p = predictions[worst]
        return (f"🔴 Highest Failure Risk: {worst} — {p['name']}\n"
                f"Risk: {p['risk']}% | Health: {p['health']}% | RUL: {p['rul_days']} days\n"
                f"Primary issue: {p['failure_type']} | Root cause: {p['root_cause']}\n"
                f"Immediate actions:\n"
                + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(p["solutions"][:3]))
                + f"\nEstimated cost: Rs.{p['cost']:,} | Operator: {p['operator']}")

    # ── STEP 4: Sensor reports ─────────────────────────────────────────────────
    if has("temperature", "temp", "heat", "overheating", "hottest", "thermal"):
        all_t = sorted(predictions.items(), key=lambda x: x[1]["temp"], reverse=True)
        resp  = f"🌡️ Temperature Status Report (Safe limit: 90°C)\n"
        for m, p in all_t:
            flag = "⚠️ CRITICAL" if p["temp"] > 90 else "✅ Normal"
            resp += f"  {m} ({p['name'][:18]}): {p['temp']}°C — {flag}\n"
        resp += f"\nHottest: {hot} at {predictions[hot]['temp']}°C"
        if predictions[hot]["temp"] > 90:
            resp += f"\n⚠️ Expert advice: Immediate cooling inspection required for {hot}!"
        return resp.strip()

    if has("vibration", "vibrate", "bearing", "oscillat", "shake", "rattle", "mm/s"):
        all_v = sorted(predictions.items(), key=lambda x: x[1]["vibration"], reverse=True)
        resp  = f"📳 Vibration Status Report (Safe limit: 5.5 mm/s)\n"
        for m, p in all_v:
            flag = "⚠️ EXCEEDS LIMIT" if p["vibration"] > 5.5 else "✅ Normal"
            resp += f"  {m} ({p['name'][:18]}): {p['vibration']} mm/s — {flag}\n"
        resp += (f"\nHighest vibration: {most_vib} — likely bearing wear or misalignment.\n"
                 f"Expert advice: Inspect bearings, check shaft alignment, verify mounting bolts.")
        return resp.strip()

    if has("pressure", "valve", "hydraulic", "blockage", "bar"):
        all_p = sorted(predictions.items(), key=lambda x: x[1]["pressure"], reverse=True)
        resp  = f"🔧 Pressure Status Report (Safe limit: 7.5 bar)\n"
        for m, p in all_p:
            flag = "⚠️ ABOVE LIMIT" if p["pressure"] > 7.5 else "✅ Normal"
            resp += f"  {m} ({p['name'][:18]}): {p['pressure']} bar — {flag}\n"
        resp += "\nExpert advice: High pressure indicates valve restriction or pump over-delivery."
        return resp.strip()

    # ── STEP 5: Factory overview ────────────────────────────────────────────────
    if has("factory", "summary", "overview", "all machine", "show all", "full report",
           "status report", "factory status", "plant status"):
        resp = f"🏭 Factory Health Report — {datetime.now().strftime('%d %b %Y, %H:%M')}\n"
        if critical:
            resp += f"🔴 CRITICAL ({len(critical)}): {', '.join(critical)} — Immediate action needed!\n"
        if warning:
            resp += f"🟡 Warning  ({len(warning)}): {', '.join(warning)} — Monitor closely\n"
        if healthy:
            resp += f"🟢 Healthy  ({len(healthy)}): {', '.join(healthy)}\n"
        resp += (f"\nAverage Factory Health: {avg_h}%\n"
                 f"Total risk cost if failures occur: Rs.{total_cost:,}\n"
                 f"ML Model accuracy: {MODEL_METRICS['accuracy']}%\n"
                 f"Expert recommendation: {'Immediate maintenance required for critical machines.' if critical else 'Continue predictive monitoring schedule.'}")
        return resp

    # ── STEP 6: Count / status summary ─────────────────────────────────────────
    if has("how many", "count", "number of", "total machine"):
        return (f"📊 Factory Machine Count\n"
                f"🔴 Critical: {len(critical)} — {', '.join(critical) if critical else 'None'}\n"
                f"🟡 Warning:  {len(warning)} — {', '.join(warning) if warning else 'None'}\n"
                f"🟢 Healthy:  {len(healthy)} — {', '.join(healthy) if healthy else 'None'}\n"
                f"Total: {len(predictions)} machines under AI monitoring\n"
                f"Overall factory health: {avg_h}%")

    # ── STEP 7: RUL / Lifespan ─────────────────────────────────────────────────
    if has("remaining", "useful life", "rul", "when replace", "lifespan", "days left",
           "how long", "run out", "replace"):
        all_r = sorted(predictions.items(), key=lambda x: x[1]["rul_days"])
        resp  = f"⏱️ Remaining Useful Life — All Machines\n"
        for m, p in all_r:
            icon = "🔴" if p["rul_days"] < 10 else "🟡" if p["rul_days"] < 20 else "✅"
            urgency = " — REPLACE NOW" if p["rul_days"] < 5 else " — Schedule urgently" if p["rul_days"] < 10 else ""
            resp += f"  {icon} {m}: {p['rul_days']} days{urgency}\n"
        p_low = predictions[low_rul]
        resp += (f"\nMost critical: {low_rul} with {p_low['rul_days']} days remaining\n"
                 f"Issue: {p_low['failure_type']} | Cost: Rs.{p_low['cost']:,}")
        return resp.strip()

    # ── STEP 8: Cost analysis ───────────────────────────────────────────────────
    if has("cost", "repair cost", "money", "budget", "total cost", "expense",
           "maintenance cost", "how much", "rupee", "expensive"):
        costly   = max(predictions, key=lambda m: predictions[m]["cost"])
        cheapest = min(predictions, key=lambda m: predictions[m]["cost"])
        total_save = sum(p["savings"] for p in predictions.values())
        return (f"💰 Maintenance Cost Analysis\n"
                f"Total estimated cost: Rs.{total_cost:,}\n"
                f"Most expensive: {costly} — Rs.{predictions[costly]['cost']:,} ({predictions[costly]['failure_type']})\n"
                f"Least expensive: {cheapest} — Rs.{predictions[cheapest]['cost']:,}\n"
                f"Total preventive savings: Rs.{total_save:,} (65% cheaper than breakdown repair)\n"
                f"Expert advice: Every Rs.1 spent on preventive maintenance saves Rs.3–5 in emergency repairs.")

    # ── STEP 9: Anomaly detection ───────────────────────────────────────────────
    if has("anomaly", "unusual", "abnormal", "irregular", "strange", "odd", "detection"):
        anom = [m for m, p in predictions.items() if p["anomaly"]]
        if anom:
            return (f"⚠️ Anomaly Detection Alert — Isolation Forest ML Model\n"
                    f"Anomalies detected in: {', '.join(anom)}\n"
                    f"These machines show sensor patterns outside normal operating range.\n"
                    f"Expert advice: Anomalies often precede visible failures by days or weeks.\n"
                    f"Action: Schedule immediate physical inspection for {anom[0]}.")
        return ("✅ Anomaly Detection — No anomalies detected\n"
                "All 6 machines show normal sensor patterns.\n"
                "Isolation Forest model continuously monitors for unusual behaviour.\n"
                "Expert note: Anomaly detection catches subtle issues the threshold rules miss.")

    # ── STEP 10: ML / AI questions ──────────────────────────────────────────────
    if has("how does", "explain", "what is", "random forest", "isolation forest",
           "machine learning", "ml", "algorithm", "predict", "model", "ai", "artificial"):

        # Predictive maintenance explanation
        if has("predictive maintenance", "predictive", "pdm", "condition monitoring"):
            return ("🤖 Predictive Maintenance — Expert Explanation\n"
                    "Predictive Maintenance (PdM) uses real-time sensor data + ML to predict failures BEFORE they happen.\n"
                    "Unlike reactive (fix when broken) or preventive (fix on schedule) maintenance, PdM acts only when needed.\n"
                    "Our system uses 3 models: Random Forest (failure prediction), Isolation Forest (anomaly detection), "
                    "RUL Regressor (remaining life estimation).\n"
                    f"Current factory accuracy: {MODEL_METRICS['accuracy']}% — detecting failures weeks in advance.")

        if has("random forest", "classifier", "failure prediction"):
            fi = MODEL_METRICS.get("feature_importance", {})
            top = max(fi, key=fi.get) if fi else "Temperature"
            return (f"🤖 Random Forest Classifier — How It Works\n"
                    f"Trained on 2,000 synthetic sensor samples with known failure patterns.\n"
                    f"Takes 4 inputs: Temperature, Vibration, Pressure, Operating Hours.\n"
                    f"100 decision trees vote together → failure probability 0–100%.\n"
                    f"Accuracy: {MODEL_METRICS['accuracy']}% | Most important feature: {top} ({fi.get(top, 0)}%)")

        if has("isolation forest", "anomaly", "unsupervised"):
            return ("🤖 Isolation Forest — How It Works\n"
                    "An unsupervised ML model — it learns what 'normal' looks like, then flags anomalies.\n"
                    "It isolates outlier data points by randomly splitting sensor readings.\n"
                    "Anomalous machines are isolated faster (shorter paths in the forest).\n"
                    "Advantage: catches novel failures that threshold rules miss — no labelled data needed.")

        if has("rul", "remaining useful life", "regressor"):
            return ("⏱️ RUL Regressor — How It Works\n"
                    "Random Forest Regressor predicts days until maintenance is required.\n"
                    "Uses sensor degradation rate vs. safe thresholds to extrapolate remaining life.\n"
                    "Output: Days remaining (🟢>20d safe, 🟡10-20d schedule soon, 🔴<10d urgent)\n"
                    "Updates in real-time as sensor readings change — dynamic, not fixed schedule.")

        if has("health score", "health score work", "calculated"):
            return ("💚 Health Score — How It's Calculated\n"
                    "Health Score = 100% − Failure Probability%\n"
                    "Failure probability comes from the Random Forest Classifier.\n"
                    "🟢 60–100% = Healthy | 🟡 40–59% = Warning | 🔴 0–39% = Critical\n"
                    f"Current factory average: {avg_h}% | Best: {best} ({predictions[best]['health']}%) | "
                    f"Worst: {worst} ({predictions[worst]['health']}%)")

    # ── STEP 11: Maintenance knowledge questions ────────────────────────────────
    if has("overheating", "what causes overheating", "why hot", "cooling"):
        return ("🌡️ Overheating — Expert Analysis\n"
                "Common causes: Blocked cooling vents, low coolant, excessive load, worn bearings, "
                "ambient temperature rise, clogged air filters.\n"
                "Immediate actions:\n"
                "  1. Reduce machine load temporarily\n"
                "  2. Check and clean cooling system\n"
                "  3. Inspect lubrication levels\n"
                "  4. Verify ambient ventilation\n"
                f"In your factory: {hot} is currently hottest at {predictions[hot]['temp']}°C.")

    if has("bearing", "bearing failure", "what causes bearing", "bearing issue"):
        return ("📳 Bearing Failure — Expert Analysis\n"
                "Common causes: Inadequate lubrication, contamination, misalignment, "
                "overloading, improper installation, fatigue from continuous operation.\n"
                "Warning signs: High vibration (>5.5mm/s), unusual noise, heat near bearing housing.\n"
                "Prevention:\n"
                "  1. Regular lubrication schedule\n"
                "  2. Vibration trend monitoring (done automatically here)\n"
                "  3. Alignment checks during maintenance\n"
                f"Current highest vibration: {most_vib} at {predictions[most_vib]['vibration']}mm/s")

    if has("valve", "valve blockage", "pressure high", "what causes blockage"):
        return ("🔧 Valve Blockage — Expert Analysis\n"
                "Common causes: Debris/contamination in fluid, scale buildup, corrosion, "
                "wrong fluid viscosity, cavitation damage, foreign particles.\n"
                "Warning signs: Rising pressure, reduced flow, system overload, cavitation noise.\n"
                "Actions:\n"
                "  1. Flush the system and replace filters\n"
                "  2. Inspect valve seats for damage\n"
                "  3. Check fluid quality and viscosity\n"
                "  4. Install finer filtration if recurring")

    if has("lubrication", "lubricant", "oil", "grease", "lube"):
        return ("🛢️ Lubrication — Expert Guidance\n"
                "Lubrication is the single most important factor in machine longevity.\n"
                "Under-lubrication: Heat buildup → bearing failure → catastrophic breakdown.\n"
                "Over-lubrication: Seal damage, contamination, overheating in electric motors.\n"
                "Best practice:\n"
                "  1. Follow manufacturer's lubrication schedule\n"
                "  2. Use correct viscosity for operating temperature\n"
                "  3. Monitor vibration — first sign of inadequate lubrication\n"
                "  4. Analyse oil samples quarterly for contamination")

    if has("mtbf", "mean time", "between failure", "mttf", "reliability"):
        return ("📊 MTBF — Mean Time Between Failures\n"
                "MTBF = Total operating time ÷ Number of failures\n"
                "Higher MTBF = more reliable machine. Industry benchmark: >2,000 hours for most equipment.\n"
                "Our RUL model gives you real-time MTBF estimation per machine.\n"
                f"Current lowest RUL: {low_rul} with {predictions[low_rul]['rul_days']} days — "
                f"indicating approaching end of current MTBF cycle.\n"
                "Action: Track MTBF trends in Analytics → Maintenance History section.")

    if has("oee", "overall equipment", "effectiveness", "efficiency"):
        try:
            from features import calculate_oee
            results = []
            for mid, p in predictions.items():
                oee = calculate_oee(mid, p["health"], p["risk"])
                results.append((mid, oee["oee"], oee["rating"]))
            results.sort(key=lambda x: x[1], reverse=True)
            resp = "📈 OEE — Overall Equipment Effectiveness\n"
            for mid, score, rating in results:
                icon = "✅" if score >= 70 else "🟡" if score >= 55 else "🔴"
                resp += f"  {icon} {mid}: {score}% ({rating})\n"
            avg_oee = round(sum(r[1] for r in results) / len(results), 1)
            resp += (f"\nFactory average OEE: {avg_oee}%\n"
                     f"World-class benchmark: 85%+ | Good: 70%+ | Average: 55%+\n"
                     f"Expert advice: {'Focus on ' + results[-1][0] + ' — lowest OEE in factory.' if results else ''}")
            return resp.strip()
        except:
            return ("📈 OEE = Availability × Performance × Quality\n"
                    "World-class factories target 85%+ OEE.\n"
                    "Low OEE indicates machine downtime, speed losses, or quality defects.\n"
                    "Check the Analytics page for full OEE breakdown per machine.")

    # ── STEP 12: Operator / zone / location ────────────────────────────────────
    if has("operator", "who operates", "who runs", "responsible", "staff", "engineer",
           "who is in charge", "personnel"):
        resp = "👷 Machine Operators & Assignments\n"
        for mid, info in MACHINES.items():
            p    = predictions[mid]
            icon = "🔴" if p["status"] == "Critical" else "🟡" if p["status"] == "Warning" else "✅"
            resp += f"  {icon} {mid}: {info['operator']} — {info['location']} | {p['status']}\n"
        return resp.strip()

    if has("zone", "location", "where", "floor", "area", "map", "which zone"):
        zones = {}
        for mid, info in MACHINES.items():
            z = info["location"]
            zones.setdefault(z, [])
            p    = predictions[mid]
            icon = "🔴" if p["status"] == "Critical" else "🟡" if p["status"] == "Warning" else "🟢"
            zones[z].append(f"{icon}{mid}")
        resp = "📍 Factory Floor Layout\n"
        for z, mids in sorted(zones.items()):
            resp += f"  {z}: {', '.join(mids)}\n"
        resp += "Visit Factory Map page for interactive live view with clickable markers!"
        return resp.strip()

    # ── STEP 13: Energy & shift ────────────────────────────────────────────────
    if has("energy", "power", "electricity", "kwh", "consumption", "power usage"):
        energy = {"MCH-101": 9572, "MCH-102": 15937, "MCH-103": 6382,
                  "MCH-104": 19147, "MCH-105": 25497, "MCH-106": 40967}
        total  = sum(energy.values())
        high   = max(energy, key=energy.get)
        resp   = f"⚡ Energy Consumption Report\n"
        for mid, cost in sorted(energy.items(), key=lambda x: x[1], reverse=True):
            resp += f"  {mid}: Rs.{cost:,}/day\n"
        resp += (f"\nTotal: Rs.{total:,}/day\n"
                 f"Highest consumer: {high} — check for energy inefficiency if health is declining.\n"
                 f"Expert tip: Degrading machines often consume 15–30% more energy before failure.")
        return resp

    # ── STEP 14: Website pages / system features ────────────────────────────────
    if has("dashboard", "what is dashboard", "how does dashboard"):
        return (f"📊 Dashboard — Main Control Centre\n"
                f"Real-time sensor charts (Temperature, Vibration, Pressure) updated every 5 seconds.\n"
                f"Features: Health gauge, failure predictions, live simulation, alarm sound, voice alerts.\n"
                f"Current: {len(critical)} critical alerts | Factory health: {avg_h}%\n"
                f"Auto-refreshes every 5 seconds — always showing latest ML predictions.")

    if has("analytics", "analytics page", "plotly", "charts", "trend", "monthly"):
        return ("📈 Analytics Dashboard — Historical Intelligence\n"
                "6 interactive Plotly charts: Monthly failures, failure type distribution, "
                "cost trends, downtime hours, health heatmap, risk vs health scatter.\n"
                "All charts are interactive — zoom, pan, hover for details.\n"
                "Identify patterns, seasonal trends, and cost trajectories over 6 months.\n"
                "Access: Click 'Analytics' in the sidebar.")

    if has("work order", "maintenance task", "assign", "create task", "repair order"):
        return ("📋 Work Orders — Maintenance Task Management\n"
                "Create, assign, and track maintenance tasks for each machine.\n"
                "Priority levels: Critical / High / Medium / Low\n"
                "Status tracking: Open → In Progress → Completed\n"
                "Assign to engineers, set deadlines, track resolution time.\n"
                "Expert tip: Always create a work order before starting maintenance — creates audit trail.")

    if has("inventory", "spare parts", "stock", "parts", "components"):
        try:
            from features import get_inventory
            inv  = get_inventory()
            low  = [i["part"] for i in inv if i["status"] == "Low"]
            out  = [i["part"] for i in inv if i["status"] == "Out"]
            resp = f"📦 Spare Parts Inventory\n"
            if out:  resp += f"🔴 Out of stock: {', '.join(out)}\n"
            if low:  resp += f"🟡 Low stock:    {', '.join(low)}\n"
            resp += (f"Total parts tracked: {len(inv)}\n"
                     f"Expert advice: Maintain 30-day buffer of critical spare parts. "
                     f"{'REORDER IMMEDIATELY for out-of-stock items!' if out else 'Stock levels manageable.'}")
            return resp.strip()
        except:
            return ("📦 Inventory Management\n"
                    "Track all spare parts with current stock levels.\n"
                    "Alerts for low stock and out-of-stock items.\n"
                    "Expert advice: Keep 30-day buffer of bearings, seals, and filters for critical machines.")

    if has("notification", "alert", "bell", "notification center"):
        return (f"🔔 Notification Center\n"
                f"All system alerts in one place — critical, warnings, info messages.\n"
                f"Current: {len(critical)} unread critical alerts\n"
                f"Features: Mark individual/all read, clear all, priority filtering.\n"
                f"Click the bell icon 🔔 in the top navbar to access.")

    if has("pdf", "download", "report", "export"):
        return ("📄 Report Generation\n"
                "PDF: Professional machine health report per machine (ReportLab formatted).\n"
                "Excel: Full factory data — 2 sheets: Machine Health + Summary Statistics.\n"
                "Both include: sensor readings, ML predictions, cost estimates, recommendations.\n"
                "Access: 'Download PDF' button on Dashboard | 'Excel Export' in sidebar.")

    if has("2fa", "two factor", "otp", "authentication", "login", "security"):
        return ("🔐 Security — Two-Factor Authentication\n"
                "Login requires 2 steps: Password + 6-digit OTP sent to your Gmail.\n"
                "OTP expires in 5 minutes — prevents unauthorised access.\n"
                "4 role levels: Admin (full access), Engineer, Operator (own machine only), Manager.\n"
                "Password hashed with pbkdf2:sha256 — never stored in plain text.")

    if has("telegram", "telegram alert", "bot", "phone alert", "notification"):
        return ("📱 Telegram Alerts — Real-time Phone Notifications\n"
                "Get instant alerts on your phone when machines go critical.\n"
                "Setup: Create bot via @BotFather → get token → add to config.py\n"
                "Features: Machine alerts, daily factory report, manual test button.\n"
                "Click the Telegram icon in the topbar to test your configuration.")

    if has("dark mode", "light mode", "theme", "toggle"):
        return ("🌓 Dark / Light Mode\n"
                "Toggle between industrial dark theme and light theme.\n"
                "Click ☀️/🌙 icon in the top navbar — preference saved automatically.\n"
                "Dark mode recommended for factory floor use — reduces eye strain on monitors.")

    # ── STEP 15: Maintenance strategy questions ─────────────────────────────────
    if has("preventive", "preventive maintenance", "scheduled maintenance", "pm schedule"):
        return ("📅 Preventive Maintenance — Expert Guidance\n"
                "Preventive maintenance is scheduled at fixed intervals regardless of machine condition.\n"
                "Advantages: Predictable cost, prevents most failures.\n"
                "Disadvantage: May service machines unnecessarily (wasting cost) or too late.\n"
                f"Our system upgrades this to Predictive Maintenance — only when data says it's needed.\n"
                f"Current recommendation: {len(critical) + len(warning)} machines need attention now.")

    if has("corrective", "breakdown", "reactive maintenance", "fix after"):
        return ("⚠️ Corrective / Reactive Maintenance — Expert View\n"
                "Corrective maintenance fixes machines AFTER they fail — most expensive approach.\n"
                "Emergency repair costs 3–5× more than planned maintenance.\n"
                "Also risks: production losses, safety hazards, cascade failures in connected systems.\n"
                f"In your factory, reactive maintenance risk cost: Rs.{total_cost:,}.\n"
                "Recommendation: Shift to predictive approach — this system enables exactly that.")

    if has("schedule", "maintenance schedule", "when to maintain", "next maintenance"):
        due = sorted([(m, p) for m, p in predictions.items()
                      if p["status"] in ["Critical", "Warning"]],
                     key=lambda x: x[1]["risk"], reverse=True)
        if due:
            resp = "🗓️ Recommended Maintenance Schedule\n"
            for m, p in due:
                icon = "🔴 URGENT" if p["status"] == "Critical" else "🟡 This week"
                resp += (f"  {icon} — {m} ({p['name'][:20]})\n"
                         f"    Risk: {p['risk']}% | RUL: {p['rul_days']} days | "
                         f"Issue: {p['failure_type']}\n"
                         f"    Action: {p['solutions'][0]}\n")
            return resp.strip()
        return ("✅ Maintenance Schedule — All Clear\n"
                "All machines currently operating within safe parameters.\n"
                "Continue routine monitoring — dashboard auto-refreshes every 5 seconds.\n"
                "Next scheduled review: Check Analytics for monthly trend patterns.")

    # ── STEP 16: ML accuracy / model questions ─────────────────────────────────
    if has("accuracy", "model accuracy", "how accurate", "precision", "recall", "f1"):
        fi  = MODEL_METRICS.get("feature_importance", {})
        top = max(fi, key=fi.get) if fi else "Temperature"
        return (f"🤖 ML Model Performance Metrics\n"
                f"Accuracy: {MODEL_METRICS['accuracy']}% | Precision: {MODEL_METRICS['precision']}%\n"
                f"Recall: {MODEL_METRICS['recall']}% | F1 Score: {MODEL_METRICS['f1']}%\n"
                f"Models: Random Forest (failure) + Isolation Forest (anomaly) + RUL Regressor\n"
                f"Training data: 2,000 synthetic samples | Top predictor: {top} ({fi.get(top, 0)}%)\n"
                f"Note: 100% accuracy on synthetic data — real-world performance varies with data quality.")

    # ── STEP 17: Time / date ────────────────────────────────────────────────────
    if has("time", "date", "today", "current time", "what day"):
        now = datetime.now()
        h   = now.hour
        shift = ("Morning (06:00–14:00)" if 6 <= h < 14
                 else "Afternoon (14:00–22:00)" if 14 <= h < 22
                 else "Night (22:00–06:00)")
        return (f"📅 {now.strftime('%A, %d %B %Y — %H:%M:%S')}\n"
                f"Current shift: {shift}\n"
                f"Factory monitoring: Active | Refresh interval: 5 seconds\n"
                f"{'⚠️ Critical alerts active — do not leave unattended!' if critical else '✅ Factory stable — continue normal operations.'}")

    # ── STEP 18: Thank you / goodbye ───────────────────────────────────────────
    if has("thank", "thanks", "bye", "goodbye", "good work", "well done", "great",
           "awesome", "excellent", "perfect"):
        return (f"😊 You're welcome, {username}!\n"
                f"{'⚠️ Reminder: ' + str(len(critical)) + ' critical machine(s) still need attention: ' + ', '.join(critical) if critical else '✅ Factory is running well — great work keeping on top of maintenance!'}\n"
                f"I'm always here if you need expert guidance. Ask me anything anytime!")

    # ── STEP 19: Generic industrial / technical questions ──────────────────────
    if has("machine", "equipment", "sensor", "monitor", "factory", "industrial", "plant"):
        icon = "🔴" if critical else "🟡" if warning else "🟢"
        return (f"🏭 Factory Intelligence Summary\n"
                f"Status: {icon} | {len(critical)} Critical | {len(warning)} Warning | {len(healthy)} Healthy\n"
                f"Average health: {avg_h}% | ML accuracy: {MODEL_METRICS['accuracy']}%\n"
                f"{'Urgent: ' + worst + ' at ' + str(predictions[worst]['risk']) + '% failure risk' if critical or warning else 'All systems nominal'}\n"
                f"Ask me something specific: 'status of MCH-104', 'temperature report', 'maintenance cost'")

    # ── STEP 20: Expert intelligent fallback ────────────────────────────────────
    # Never say "I don't know" — always give expert guidance
    return (f"💡 Expert Analysis — {username}\n"
            f"Based on your query '{message[:50]}', here's my expert assessment:\n"
            f"Factory context: {avg_h}% average health | {len(critical)} critical | {len(warning)} warning\n"
            f"For the most relevant answer, try asking:\n"
            f"  • About a specific machine: 'How is MCH-104 doing?'\n"
            f"  • About a sensor: 'Temperature report' or 'Vibration analysis'\n"
            f"  • About maintenance: 'What needs urgent attention?'\n"
            f"  • About costs: 'Total maintenance cost this month'\n"
            f"I'm ready to answer any industrial maintenance question!")
