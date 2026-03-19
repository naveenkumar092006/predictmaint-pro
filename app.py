# app.py — PredictMaint Pro v4 — COMPLETE EDITION

import os, io
from datetime import datetime
from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, flash, send_file, session)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from flask_mail import Mail, Message

from config       import Config
from database     import init_db
from auth         import get_user_by_id, verify_user, get_all_users, create_user, delete_user
from models       import (MACHINES, FACTORIES, predict_machine, generate_daily_report,
                           generate_analytics_data, get_live_data,
                           generate_sensor_history, MODEL_METRICS, get_factory_summary)
from features     import (generate_qr_code, generate_excel_report, calculate_oee,
                           get_work_orders, create_work_order, update_work_order_status,
                           get_inventory, get_checklist, get_current_shift, get_energy_data,
                           get_predictive_reorder)
from chatbot      import chatbot_response
from notifications import (add_notification, get_notifications, mark_read, mark_all_read,
                            clear_notifications, unread_count, seed_notifications,
                            add_maintenance_record, get_maintenance_history)
from twofa        import generate_otp, send_otp_email, verify_otp, get_remaining_seconds
from telegram_alert import send_telegram_alert, send_telegram_daily_report
from scheduler     import start_scheduler
from downtime     import calculate_downtime, calculate_all_downtime, compare_machines

# ── CAMERA VISION IMPORTS ──────────────────────────────────────────────────────
try:
    from camera      import camera_stream
    from detection   import detector
    from integration import CameraMLIntegration
    integration = CameraMLIntegration(camera_stream, detector)
    CAMERA_AVAILABLE = True
except ImportError as _ce:
    CAMERA_AVAILABLE = False
    integration = None
    print(f"⚠️  Camera module not available: {_ce}")

# ── APP SETUP ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)

if not os.environ.get('RENDER'):
    os.makedirs(os.path.join(os.path.dirname(__file__), 'instance'), exist_ok=True)

init_db()
login_manager = LoginManager(app)
login_manager.login_view    = 'login'
login_manager.login_message = 'Please log in.'
mail = Mail(app)

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(int(user_id))

# ── CONTEXT PROCESSOR — inject unread count globally ──────────────────────────
@app.context_processor
def inject_globals():
    if current_user.is_authenticated:
        return {"unread_notifications": unread_count()}
    return {"unread_notifications": 0}

# ── AUTH ───────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('dashboard') if current_user.is_authenticated else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        user     = verify_user(username, password)
        if user:
            otp = generate_otp(username)
            session['pending_user_id']  = user.id
            session['pending_username'] = username
            # Send OTP via Gmail if email configured
            if user.email:
                ok, msg = send_otp_email(user.email, otp, username)
                if ok:
                    # Mask email for display: vi***@gmail.com
                    parts = user.email.split('@')
                    masked = parts[0][:2] + '***@' + parts[1] if len(parts)==2 else '***'
                    session['email_sent']   = True
                    session['email_masked'] = masked
                else:
                    session['email_sent']   = False
                    session['email_masked'] = ''
            else:
                session['email_sent']   = False
                session['email_masked'] = ''
            return redirect(url_for('verify_2fa'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/verify-2fa', methods=['GET','POST'])
def verify_2fa():
    if 'pending_user_id' not in session:
        return redirect(url_for('login'))
    username  = session.get('pending_username','')
    remaining = get_remaining_seconds(username)
    if request.method == 'POST':
        otp_input = request.form.get('otp','').strip()
        ok, msg   = verify_otp(username, otp_input)
        if ok:
            user = get_user_by_id(session['pending_user_id'])
            session.pop('pending_user_id', None)
            session.pop('pending_username', None)
            login_user(user, remember=True)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        flash(f'{msg}', 'danger')
    email_sent   = session.get('email_sent', False)
    email_masked = session.get('email_masked', '')
    return render_template('twofa.html', username=username,
                           remaining=remaining, email_sent=email_sent,
                           email_masked=email_masked)

@app.route('/resend-otp')
def resend_otp():
    username = session.get('pending_username','')
    if username:
        otp  = generate_otp(username)
        uid  = session.get('pending_user_id')
        user = get_user_by_id(uid) if uid else None
        if user and user.email:
            ok, msg = send_otp_email(user.email, otp, username)
            if ok:
                session['email_sent'] = True
                flash('New OTP sent to your registered email address.', 'success')
            else:
                session['email_sent'] = False
                flash('Could not send email. Check server console for OTP.', 'warning')
        else:
            flash('Email not registered. Check server console for OTP.', 'warning')
    return redirect(url_for('verify_2fa'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# ── DASHBOARD ──────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    machine_ids   = ([current_user.assigned_machine]
                     if current_user.role=='operator' and current_user.assigned_machine
                     else list(MACHINES.keys()))
    predictions   = {mid: predict_machine(mid) for mid in machine_ids}
    selected_id   = request.args.get('machine', machine_ids[0])
    if selected_id not in predictions: selected_id = machine_ids[0]
    selected_pred = predictions[selected_id]
    history       = generate_sensor_history(selected_id)
    oee           = calculate_oee(selected_id, selected_pred['health_score'], selected_pred['failure_probability'])
    energy        = get_energy_data(selected_id)
    shift         = get_current_shift()
    # Auto-seed notifications
    seed_notifications(predictions)
    return render_template('dashboard.html',
        machines=MACHINES, machine_ids=machine_ids,
        predictions=predictions, selected_id=selected_id,
        selected_pred=selected_pred, history=history,
        daily_report=generate_daily_report(), model_metrics=MODEL_METRICS,
        oee=oee, energy=energy, shift=shift,
        now=datetime.now().strftime("%A, %d %B %Y — %H:%M")
    )

# ── NOTIFICATIONS ──────────────────────────────────────────────────────────────
@app.route('/notifications')
@login_required
def notifications():
    return render_template('notifications.html',
        notifications=get_notifications(), unread=unread_count())

@app.route('/notifications/read/<int:nid>', methods=['POST'])
@login_required
def notif_read(nid):
    mark_read(nid)
    return jsonify({"success": True})

@app.route('/notifications/read-all', methods=['POST'])
@login_required
def notif_read_all():
    mark_all_read()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications'))

@app.route('/notifications/clear', methods=['POST'])
@login_required
def notif_clear():
    clear_notifications()
    flash('All notifications cleared.', 'success')
    return redirect(url_for('notifications'))

@app.route('/api/notifications/count')
@login_required
def api_notif_count():
    return jsonify({"unread": unread_count()})

# ── MAINTENANCE HISTORY ────────────────────────────────────────────────────────
@app.route('/maintenance-history')
@login_required
def maintenance_history():
    mid = request.args.get('machine_id', None)
    history = get_maintenance_history(mid)
    return render_template('maint_history.html',
        history=history, machines=MACHINES, filter_mid=mid)

@app.route('/maintenance-history/add', methods=['POST'])
@login_required
def add_maint_history():
    mid = request.form.get('machine_id')
    add_maintenance_record(
        mid,
        MACHINES[mid]['name'] if mid in MACHINES else mid,
        request.form.get('type'),
        request.form.get('description'),
        request.form.get('technician', current_user.username),
        int(request.form.get('cost', 0)),
        float(request.form.get('health_before', 0)),
        float(request.form.get('health_after', 0)),
    )
    add_notification(mid, MACHINES.get(mid,{}).get('name',''), 'info',
                     f'Maintenance Logged: {mid}',
                     f"Maintenance record added by {current_user.username}")
    flash('Maintenance record added!', 'success')
    return redirect(url_for('maintenance_history'))

# ── SEARCH ─────────────────────────────────────────────────────────────────────
@app.route('/search')
@login_required
def search():
    mid    = request.args.get('machine_id','').upper().strip()
    result = history = qr = checklist = oee = energy = mhist = None
    if mid:
        if mid in MACHINES:
            result    = predict_machine(mid)
            history   = generate_sensor_history(mid)
            qr        = generate_qr_code(mid, request.host_url.rstrip('/'))
            checklist = get_checklist(mid, result['failure_type'])
            oee       = calculate_oee(mid, result['health_score'], result['failure_probability'])
            energy    = get_energy_data(mid)
            mhist     = get_maintenance_history(mid)
        else:
            flash(f'Machine "{mid}" not found.', 'warning')
    return render_template('search.html', result=result, history=history,
                           machines=MACHINES, query=mid, qr=qr,
                           checklist=checklist, oee=oee, energy=energy,
                           maint_history=mhist)

# ── ANALYTICS ──────────────────────────────────────────────────────────────────
@app.route('/analytics')
@login_required
def analytics():
    if not (current_user.can('view_costs') or current_user.can('generate_reports')):
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    preds = {mid: predict_machine(mid) for mid in MACHINES}
    return render_template('analytics.html',
        analytics=generate_analytics_data(), predictions=preds)

# ── WORK ORDERS ────────────────────────────────────────────────────────────────
@app.route('/workorders')
@login_required
def work_orders():
    return render_template('workorders.html',
        work_orders=get_work_orders(), machines=MACHINES)

@app.route('/workorders/create', methods=['POST'])
@login_required
def create_wo():
    wo = create_work_order(
        request.form.get('machine_id'), request.form.get('issue'),
        request.form.get('priority'),   request.form.get('assigned_to'),
        current_user.username)
    add_notification(wo['machine_id'], '', 'info',
                     f'New Work Order: {wo["id"]}', wo['issue'])
    flash(f'Work order {wo["id"]} created!', 'success')
    return redirect(url_for('work_orders'))

@app.route('/workorders/update', methods=['POST'])
@login_required
def update_wo():
    update_work_order_status(request.form.get('wo_id'), request.form.get('status'))
    flash('Work order updated!', 'success')
    return redirect(url_for('work_orders'))

# ── INVENTORY ──────────────────────────────────────────────────────────────────
@app.route('/inventory')
@login_required
def inventory():
    return render_template('inventory.html', inventory=get_inventory(), machines=MACHINES)

# ── FACTORY MAP ────────────────────────────────────────────────────────────────
@app.route('/map')
@login_required
def factory_map():
    preds = {mid: predict_machine(mid) for mid in MACHINES}
    return render_template('map.html', machines=MACHINES, predictions=preds)

# ── CHATBOT ────────────────────────────────────────────────────────────────────
@app.route('/chatbot')
@login_required
def chatbot():
    from config import Config
    has_gemini = bool(getattr(Config,'GEMINI_API_KEY','') not in
                      ('YOUR_GEMINI_API_KEY','',None))
    return render_template('chatbot.html', config_has_gemini=has_gemini)

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data  = request.get_json()
    reply = chatbot_response(data.get('message',''), current_user.username)
    return jsonify({"reply": reply, "timestamp": datetime.now().strftime("%H:%M")})

# ── USER MANAGEMENT ────────────────────────────────────────────────────────────
@app.route('/users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('users.html', users=get_all_users(), machines=MACHINES)

@app.route('/users/create', methods=['POST'])
@login_required
def create_user_route():
    if current_user.role != 'admin': return jsonify({"success":False}), 403
    ok, msg = create_user(request.form.get('username'), request.form.get('password'),
                          request.form.get('role'),     request.form.get('email'),
                          request.form.get('assigned_machine') or None)
    flash(msg, 'success' if ok else 'danger')
    return redirect(url_for('manage_users'))

@app.route('/users/delete/<int:uid>', methods=['POST'])
@login_required
def delete_user_route(uid):
    if current_user.role != 'admin': return jsonify({"success":False}), 403
    delete_user(uid)
    flash('User deleted.', 'success')
    return redirect(url_for('manage_users'))

# ── PDF REPORT ─────────────────────────────────────────────────────────────────
@app.route('/report/pdf/<machine_id>')
@login_required
def download_pdf(machine_id):
    if machine_id not in MACHINES:
        flash('Machine not found.', 'warning')
        return redirect(url_for('dashboard'))
    pred = predict_machine(machine_id)
    return send_file(io.BytesIO(_build_pdf(pred)),
        download_name=f"HealthReport_{machine_id}_{datetime.now().strftime('%Y%m%d')}.pdf",
        as_attachment=True, mimetype='application/pdf')

def _build_pdf(pred):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
    H    = ParagraphStyle('H',  fontSize=20, textColor=colors.HexColor('#00d4ff'), fontName='Helvetica-Bold', spaceAfter=4)
    Sub  = ParagraphStyle('Sub',fontSize=10, textColor=colors.HexColor('#888888'), spaceAfter=10)
    Sec  = ParagraphStyle('Sec',fontSize=13, textColor=colors.HexColor('#0a5c9e'), fontName='Helvetica-Bold', spaceBefore=12, spaceAfter=6)
    Body = ParagraphStyle('B',  fontSize=10, spaceAfter=5)
    Foot = ParagraphStyle('F',  fontSize=8,  textColor=colors.grey, alignment=1)
    def tbl(data,cw,bg):
        t=Table(data,colWidths=cw)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),bg),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),
            ('FONTSIZE',(0,0),(-1,-1),10),('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.white,colors.HexColor('#f9f9f9')]),('PADDING',(0,0),(-1,-1),6)]))
        return t
    c   = pred['cost_estimate']
    mid = pred['machine_id']
    oee = calculate_oee(mid, pred['health_score'], pred['failure_probability'])
    story=[
        Paragraph("Industrial Predictive Maintenance System", H),
        Paragraph(f"Machine Health Report — {datetime.now().strftime('%d %B %Y, %H:%M')}", Sub),
        HRFlowable(width="100%",thickness=1,color=colors.HexColor('#00d4ff')),Spacer(1,0.3*cm),
        Paragraph("Machine Information",Sec),
        tbl([["Machine ID",mid],["Name",pred['machine_info']['name']],
             ["Operator",pred['machine_info']['operator']],["Location",pred['machine_info']['location']],
             ["Installed",pred['machine_info']['installation_date']],
             ["Last Maintenance",pred['machine_info']['last_maintenance']]],
            [5*cm,12*cm],colors.HexColor('#e8f4fd')),
        Spacer(1,0.3*cm),Paragraph("Health & Prediction",Sec),
        tbl([["Health Score",f"{pred['health_score']}%"],
             ["Failure Probability",f"{pred['failure_probability']}%"],
             ["Status",pred['status']],["Anomaly","YES" if pred['is_anomaly'] else "NO"],
             ["RUL",f"{pred['rul_days']} days"],["OEE",f"{oee['oee']}% ({oee['rating']})"]]+
            ([["Maint. Date",pred['suggested_maintenance_date']]] if pred.get('suggested_maintenance_date') else []),
            [6*cm,11*cm],colors.HexColor('#fff3e0')),
        Spacer(1,0.3*cm),Paragraph("Failure Analysis",Sec),
        Paragraph(f"<b>Type:</b> {pred['failure_type']}",Body),
        Paragraph(f"<b>Root Cause:</b> {pred['root_cause']}",Body),
        *[Paragraph(f"  {i}. {s}",Body) for i,s in enumerate(pred['solutions'],1)],
        Spacer(1,0.3*cm),Paragraph("Cost Estimation (INR)",Sec),
        tbl([["Spare Parts",f"Rs.{c['spare_parts_cost']:,}"],["Labor",f"Rs.{c['labor_cost']:,}"],
             ["Total",f"Rs.{c['total_estimated']:,}"],["Preventive",f"Rs.{c['preventive_cost']:,}"],
             ["Breakdown",f"Rs.{c['breakdown_repair']:,}"],["Savings",f"Rs.{c['estimated_savings']:,}"]],
            [8*cm,9*cm],colors.HexColor('#e8f8e8')),
        Spacer(1,0.8*cm),HRFlowable(width="100%",thickness=0.5,color=colors.grey),
        Paragraph("Confidential — Industrial Predictive Maintenance System",Foot),
    ]
    doc.build(story)
    buf.seek(0)
    return buf.read()

# ── EXCEL EXPORT ───────────────────────────────────────────────────────────────
@app.route('/report/excel')
@login_required
def download_excel():
    preds = {mid: predict_machine(mid) for mid in MACHINES}
    return send_file(io.BytesIO(generate_excel_report(preds)),
        download_name=f"MachineReport_{datetime.now().strftime('%Y%m%d')}.xlsx",
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ── API ENDPOINTS ──────────────────────────────────────────────────────────────
@app.route('/api/live-data')
@login_required
def api_live_data():
    mid = request.args.get('machine_id','MCH-101')
    if mid not in MACHINES: return jsonify({"error":"Not found"}),404
    data = get_live_data(mid)
    pred = predict_machine(mid)
    data.update({"failure_probability":pred["failure_probability"],
                 "health_score":pred["health_score"],"rul_days":pred["rul_days"],
                 "status":pred["status"],"is_anomaly":pred["is_anomaly"]})
    # Save reading persistently to database
    try:
        from database import save_sensor_reading
        save_sensor_reading(mid, data, pred)
    except Exception:
        pass
    return jsonify(data)

@app.route('/api/predictions')
@login_required
def api_predictions():
    return jsonify({mid: predict_machine(mid) for mid in MACHINES})

@app.route('/api/send-alert/<machine_id>', methods=['POST'])
@login_required
def send_alert(machine_id):
    pred = predict_machine(machine_id)
    body = (f"CRITICAL ALERT — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"Machine: {machine_id} — {pred['machine_info']['name']}\n"
            f"Risk: {pred['failure_probability']}% | Type: {pred['failure_type']}\n"
            f"Action: {pred['solutions'][0]}")
    add_notification(machine_id, pred['machine_info']['name'], 'critical',
                     f'Alert Sent: {machine_id}', body)
    print(f"\n{'='*50}\n{body}\n{'='*50}")
    results = []
    # Send Email
    try:
        msg = Message(f"CRITICAL: {machine_id}", recipients=[Config.ALERT_RECIPIENT])
        msg.body = body; mail.send(msg)
        results.append("email")
    except Exception as e:
        print(f"[Email] {e}")
    # Send Telegram
    ok, tmsg = send_telegram_alert(machine_id, pred)
    if ok:
        results.append("telegram")
    method = "+".join(results) if results else "console"
    return jsonify({"success": True, "method": method})

@app.route('/api/whatsapp-alert/<machine_id>', methods=['POST'])
@login_required
def whatsapp_alert(machine_id):
    pred = predict_machine(machine_id)
    msg  = (f"🚨 *FACTORY ALERT*\n"
            f"Machine: *{machine_id}*\n"
            f"Status: *{pred['status']}*\n"
            f"Risk: *{pred['failure_probability']}%*\n"
            f"Issue: *{pred['failure_type']}*\n"
            f"Action: {pred['solutions'][0]}\n"
            f"Time: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    add_notification(machine_id, pred['machine_info']['name'], 'critical',
                     f'WhatsApp Alert: {machine_id}', f"WhatsApp alert simulated for {machine_id}")
    print(f"\n📱 WHATSAPP ALERT SIMULATION:\n{msg}\n")
    import urllib.parse
    wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
    return jsonify({"success": True, "message": msg, "method": "whatsapp_simulation", "wa_url": wa_url})

@app.route('/api/energy/<machine_id>')
@login_required
def api_energy(machine_id):
    return jsonify(get_energy_data(machine_id))

# ── TELEGRAM DAILY REPORT ─────────────────────────────────────────────────────
@app.route('/api/telegram-report', methods=['POST'])
@login_required
def api_telegram_report():
    report = generate_daily_report()
    ok, msg = send_telegram_daily_report(report)
    return jsonify({"success": ok, "message": msg})

# ── TELEGRAM MACHINE ALERT ────────────────────────────────────────────────────
@app.route('/api/telegram-alert/<machine_id>', methods=['POST'])
@login_required
def api_telegram_alert(machine_id):
    """Send Telegram alert for a specific machine."""
    if machine_id not in MACHINES:
        return jsonify({"success": False, "error": "Machine not found"}), 404
    pred = predict_machine(machine_id)
    ok, msg = send_telegram_alert(machine_id, pred)
    add_notification(machine_id, pred['machine_info']['name'], 'critical',
                     f'Telegram Alert: {machine_id}',
                     f"Telegram alert {'sent' if ok else 'failed'} for {machine_id}")
    return jsonify({"success": ok, "message": msg,
                    "method": "telegram" if ok else "failed"})

# ── TELEGRAM TEST ──────────────────────────────────────────────────────────────
@app.route('/api/telegram-test', methods=['POST'])
@login_required
def api_telegram_test():
    from telegram_alert import send_telegram_test
    ok, msg = send_telegram_test()
    return jsonify({"success": ok, "message": msg})

# ── RUN ────────────────────────────────────────────────────────────────────────

# ── DOWNTIME CALCULATOR ────────────────────────────────────────────────────────
@app.route('/downtime')
@login_required
def downtime():
    preds = {mid: predict_machine(mid) for mid in MACHINES}
    dt_data, total = calculate_all_downtime(preds)
    return render_template('downtime.html',
        downtime_data=dt_data, predictions=preds,
        total_loss=total, machines=MACHINES)

# ── MACHINE COMPARISON ─────────────────────────────────────────────────────────
@app.route('/compare')
@login_required
def compare():
    machine_list = list(MACHINES.keys())
    m1 = request.args.get('m1', machine_list[0])
    m2 = request.args.get('m2', machine_list[1])
    comparison = None
    if m1 in MACHINES and m2 in MACHINES and m1 != m2:
        pred1 = predict_machine(m1)
        pred2 = predict_machine(m2)
        comparison = compare_machines(pred1, pred2, m1, m2)
    elif m1 == m2:
        flash('Please select two different machines to compare.', 'warning')
    return render_template('compare.html',
        machines=MACHINES, m1=m1, m2=m2, comparison=comparison)

# ── MANUAL DAILY REPORT TRIGGER ──────────────────────────────────────────────
@app.route('/api/send-daily-report', methods=['POST'])
@login_required
def api_send_daily_report():
    """Manually trigger daily report — for demo purposes."""
    from scheduler import _run_daily_report
    import threading
    t = threading.Thread(target=_run_daily_report, daemon=True)
    t.start()
    return jsonify({"success": True,
                    "message": "Daily report sending to your email & Telegram!"})

# Start background scheduler (daily reports)
start_scheduler()


@app.route('/api/reorder-alerts')
@login_required
def api_reorder_alerts():
    """Predictive spare parts reorder — cross-references ML predictions with inventory."""
    preds = {mid: predict_machine(mid) for mid in MACHINES}
    alerts = get_predictive_reorder(preds)
    return jsonify({'success': True, 'alerts': alerts, 'count': len(alerts)})


@app.route('/api/factory-summary')
@login_required
def api_factory_summary():
    """Multi-factory health summary."""
    preds   = {mid: predict_machine(mid) for mid in MACHINES}
    summary = get_factory_summary(preds)
    return jsonify({'success': True, 'factories': summary, 'total': len(FACTORIES)})

@app.route('/api/ai-schedule', methods=['POST'])
@login_required
def api_ai_schedule():
    """Generate AI maintenance schedule using Gemini."""
    from chatbot import chatbot_response
    preds = {mid: predict_machine(mid) for mid in MACHINES}
    machine_info = ""
    for mid, p in preds.items():
        machine_info += (f"{mid} ({p['machine_info']['name']}): "
                        f"health={p['health_score']}%, risk={p['failure_probability']}%, "
                        f"RUL={p['rul_days']} days, issue={p['failure_type']}. ")
    prompt = (f"Create a detailed week-by-week maintenance schedule for the next 4 weeks "
              f"for these machines: {machine_info} "
              f"Prioritise by urgency. Be specific with dates and actions.")
    reply = chatbot_response(prompt, current_user.username)
    return jsonify({"success": True, "schedule": reply})

# ── CAMERA VISION ROUTES ───────────────────────────────────────────────────────

@app.route('/api/live-camera')
@login_required
def live_camera():
    """MJPEG stream — use as <img src='/api/live-camera'>"""
    if not CAMERA_AVAILABLE or not camera_stream.running:
        return "Camera not available", 503
    from flask import Response, stream_with_context
    return Response(stream_with_context(camera_stream.generate_mjpeg()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/detected-machines')
@login_required
def detected_machines():
    if not CAMERA_AVAILABLE:
        return jsonify({'success': False, 'machines': [], 'count': 0})
    preds = integration.get_predictions()
    return jsonify({
        'success': True,
        'count': len(preds),
        'machines': list(preds.values()),
        'stats': integration.get_stats(),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })

@app.route('/api/camera-predictions')
@login_required
def camera_predictions():
    if not CAMERA_AVAILABLE:
        return jsonify({'success': False, 'predictions': {}})
    preds    = integration.get_predictions()
    critical = integration.get_critical_machine()
    return jsonify({
        'success': True,
        'predictions': preds,
        'critical_machine': critical,
        'system_stats': integration.get_stats(),
    })

@app.route('/api/camera-stats')
@login_required
def camera_stats():
    if not CAMERA_AVAILABLE:
        return jsonify({'camera_running': False, 'total_machines': 0})
    stats = integration.get_stats()
    stats['camera_running'] = camera_stream.running
    return jsonify(stats)

@app.route('/api/camera-context')
@login_required
def camera_context():
    """Used by chatbot to get live camera context."""
    if not CAMERA_AVAILABLE:
        return jsonify({'context': 'Camera system not active.',
                        'predictions': {}, 'stats': {}})
    return jsonify({
        'context':     integration.get_chatbot_context(),
        'predictions': integration.get_predictions(),
        'stats':       integration.get_stats(),
    })

# ── DEMO CONTROL BUTTONS ───────────────────────────────────────────────────────

@app.route('/api/demo/trigger-failure', methods=['POST'])
@login_required
def demo_trigger_failure():
    if not CAMERA_AVAILABLE:
        return jsonify({'success': False, 'message': 'Camera not active'})
    data = request.get_json(silent=True) or {}
    detector.trigger_failure(data.get('machine_id'))
    return jsonify({'success': True, 'message': 'Failure triggered!'})

@app.route('/api/demo/simulate-overheat', methods=['POST'])
@login_required
def demo_simulate_overheat():
    if not CAMERA_AVAILABLE:
        return jsonify({'success': False, 'message': 'Camera not active'})
    data = request.get_json(silent=True) or {}
    detector.simulate_overheat(data.get('machine_id'))
    return jsonify({'success': True, 'message': 'Overheat simulation started!'})

@app.route('/api/demo/reset-machines', methods=['POST'])
@login_required
def demo_reset_machines():
    if not CAMERA_AVAILABLE:
        return jsonify({'success': False, 'message': 'Camera not active'})
    detector.reset_machines()
    return jsonify({'success': True, 'message': 'All machines reset to normal.'})


# ── ESP32 HARDWARE SENSOR ENDPOINT ────────────────────────────────────────────
# This route receives REAL sensor data from ESP32 hardware.
# Hardware setup: buy ESP32 + DS18B20 + MPU6050 + BMP280 (~Rs.650 total)
# Then flash esp32_firmware/firmware.ino using Arduino IDE.

try:
    from esp32_sensor import receive_esp32_data, get_connected_devices, is_hardware_active
    ESP32_AVAILABLE = True
except ImportError:
    ESP32_AVAILABLE = False

@app.route('/api/esp32-data', methods=['POST'])
def esp32_data():
    """Receives real sensor data from ESP32 hardware over WiFi."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "No JSON data"}), 400

    machine_id = data.get('machine_id', 'MCH-101')
    if machine_id not in MACHINES:
        return jsonify({"success": False, "error": f"Unknown machine {machine_id}"}), 404

    temp  = float(data.get('temperature', 0))
    vib   = float(data.get('vibration', 0))
    press = float(data.get('pressure', 0))
    hours = float(data.get('operating_hours', 0))

    # Store hardware reading
    if ESP32_AVAILABLE:
        reading = receive_esp32_data(machine_id, temp, vib, press, hours,
                                     data.get('device_id'))
    
    # Run ML prediction on REAL data
    pred = predict_machine(machine_id)

    # Save to database
    try:
        from database import save_sensor_reading
        sensor_data = {'temperature': temp, 'vibration': vib,
                       'pressure': press, 'operating_hours': hours}
        save_sensor_reading(machine_id, sensor_data, pred)
    except Exception:
        pass

    # Trigger notification if critical
    if pred['failure_probability'] > 60:
        add_notification(machine_id, MACHINES[machine_id]['name'], 'critical',
                        f'ESP32 Alert: {machine_id} CRITICAL',
                        f"Real sensor data — Failure risk: {pred['failure_probability']}%")

    return jsonify({
        "success":     True,
        "machine_id":  machine_id,
        "received":    {"temperature": temp, "vibration": vib,
                        "pressure": press, "hours": hours},
        "prediction":  {"health_score":        pred['health_score'],
                        "failure_probability": pred['failure_probability'],
                        "status":              pred['status'],
                        "rul_days":            pred['rul_days']},
        "source":      "hardware"
    })

@app.route('/api/esp32-devices')
@login_required
def esp32_devices():
    """List connected ESP32 devices."""
    if not ESP32_AVAILABLE:
        return jsonify({"devices": [], "message": "ESP32 module not loaded"})
    return jsonify({"devices": get_connected_devices(), "success": True})

# ── LIVE MONITOR PAGE ──────────────────────────────────────────────────────────

@app.route('/live-monitor')
@login_required
def live_monitor():
    return render_template('live_monitor.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # ── Start camera system ─────────────────────────────────────────────────
    if CAMERA_AVAILABLE:
        try:
            camera_stream.start()
            integration.start()
            print("✅ Camera + ML vision system active.")
        except Exception as cam_err:
            print(f"⚠️  Camera could not start: {cam_err}")
            print("    Running in dashboard-only mode.")
    # ────────────────────────────────────────────────────────────────────────
    print(f"\n{'='*60}\n  PredictMaint Pro v4 — COMPLETE EDITION + CAMERA VISION\n  http://0.0.0.0:{port}\n  Login: admin / Admin@123\n  Live Monitor: http://0.0.0.0:{port}/live-monitor\n{'='*60}\n")
    app.run(debug=False, host='0.0.0.0', port=port,
            threaded=True, use_reloader=False)