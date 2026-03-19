# notifications.py — Notification Center + Maintenance History

from datetime import datetime, timedelta
import random

# ── IN-MEMORY STORES ──────────────────────────────────────────────────────────
_notifications   = []
_maint_history   = []
_notif_counter   = 0
_history_counter = 0

# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────
def add_notification(machine_id, machine_name, severity, title, message):
    global _notif_counter
    _notif_counter += 1
    _notifications.insert(0, {
        "id":           _notif_counter,
        "machine_id":   machine_id,
        "machine_name": machine_name,
        "severity":     severity,          # critical / warning / info
        "title":        title,
        "message":      message,
        "read":         False,
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "time_ago":     "Just now"
    })
    # Keep max 50
    if len(_notifications) > 50:
        _notifications.pop()

def get_notifications():
    now = datetime.now()
    for n in _notifications:
        ts   = datetime.strptime(n["timestamp"], "%Y-%m-%d %H:%M:%S")
        diff = int((now - ts).total_seconds())
        if diff < 60:
            n["time_ago"] = f"{diff}s ago"
        elif diff < 3600:
            n["time_ago"] = f"{diff//60}m ago"
        elif diff < 86400:
            n["time_ago"] = f"{diff//3600}h ago"
        else:
            n["time_ago"] = f"{diff//86400}d ago"
    return _notifications

def mark_read(notif_id):
    for n in _notifications:
        if n["id"] == notif_id:
            n["read"] = True
            return True
    return False

def mark_all_read():
    for n in _notifications:
        n["read"] = True

def clear_notifications():
    _notifications.clear()

def unread_count():
    return sum(1 for n in _notifications if not n["read"])

def seed_notifications(predictions):
    """Auto-generate notifications from predictions."""
    if len(_notifications) < 3:
        for mid, pred in predictions.items():
            if pred["status"] == "Critical":
                add_notification(mid, pred["machine_info"]["name"], "critical",
                    f"CRITICAL: {mid} Failure Risk High",
                    f"{pred['failure_type']} detected. Risk: {pred['failure_probability']}%. Immediate action required!")
            elif pred["status"] == "Warning":
                add_notification(mid, pred["machine_info"]["name"], "warning",
                    f"WARNING: {mid} Needs Attention",
                    f"Health score dropped to {pred['health_score']}%. Schedule maintenance soon.")
            if pred["is_anomaly"]:
                add_notification(mid, pred["machine_info"]["name"], "warning",
                    f"ANOMALY: Unusual pattern in {mid}",
                    f"Isolation Forest detected anomalous sensor readings.")

# ── MAINTENANCE HISTORY ───────────────────────────────────────────────────────
def add_maintenance_record(machine_id, machine_name, maint_type,
                           description, technician, cost, health_before, health_after):
    global _history_counter
    _history_counter += 1
    _maint_history.insert(0, {
        "id":             _history_counter,
        "machine_id":     machine_id,
        "machine_name":   machine_name,
        "type":           maint_type,
        "description":    description,
        "technician":     technician,
        "cost":           cost,
        "health_before":  health_before,
        "health_after":   health_after,
        "improvement":    round(health_after - health_before, 1),
        "date":           datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status":         "Completed"
    })

def get_maintenance_history(machine_id=None):
    if machine_id:
        return [r for r in _maint_history if r["machine_id"] == machine_id]
    return _maint_history

def seed_maintenance_history():
    """Seed with sample maintenance records."""
    if not _maint_history:
        samples = [
            ("MCH-101","CNC Milling Machine","Preventive","Bearing replacement and lubrication service","engineer1",12500,62,88),
            ("MCH-104","Industrial Compressor","Corrective","Emergency cooling system repair","engineer1",28000,32,75),
            ("MCH-105","Rotary Kiln","Preventive","Full overhaul — wear parts replaced","engineer1",45000,28,72),
            ("MCH-102","Hydraulic Press","Preventive","Valve inspection and pressure test","engineer1",9500,70,91),
            ("MCH-103","Conveyor Belt","Inspection","Routine belt tension check","engineer1",3500,85,87),
            ("MCH-106","Turbine Generator","Preventive","Blade inspection and balancing","engineer1",22000,68,90),
        ]
        for mid,name,mtype,desc,tech,cost,hb,ha in samples:
            add_maintenance_record(mid,name,mtype,desc,tech,cost,hb,ha)
            # Backdate records
            if _maint_history:
                days_back = random.randint(5,60)
                ts = datetime.now() - timedelta(days=days_back)
                _maint_history[0]["date"] = ts.strftime("%Y-%m-%d %H:%M")

seed_maintenance_history()
