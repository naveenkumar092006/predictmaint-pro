# models.py — ML Models, Machine Data & Simulation Engine

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest, RandomForestRegressor
import joblib
import os
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split
import random
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# MACHINE DEFINITIONS
# ─────────────────────────────────────────────

# ── MULTI-FACTORY SUPPORT ──────────────────────────────────────────────────
FACTORIES = {
    "FAC-A": {"name": "Chennai Plant",    "city": "Chennai",   "manager": "Rajan Kumar"},
    "FAC-B": {"name": "Pune Plant",       "city": "Pune",      "manager": "Sneha Patil"},
    "FAC-C": {"name": "Hyderabad Plant",  "city": "Hyderabad", "manager": "Arjun Reddy"},
}

MACHINES = {
    "MCH-101": {"name": "CNC Milling Machine",    "installation_date": "2020-03-15", "last_maintenance": "2024-09-10", "operator": "Ravi Kumar",   "location": "Zone A", "factory": "FAC-A"},
    "MCH-102": {"name": "Hydraulic Press",         "installation_date": "2019-07-22", "last_maintenance": "2024-08-25", "operator": "Suresh Nair",  "location": "Zone B", "factory": "FAC-A"},
    "MCH-103": {"name": "Conveyor Belt System",    "installation_date": "2021-01-10", "last_maintenance": "2024-10-01", "operator": "Priya Sharma", "location": "Zone A", "factory": "FAC-B"},
    "MCH-104": {"name": "Industrial Compressor",   "installation_date": "2018-11-05", "last_maintenance": "2024-07-15", "operator": "Arun Patel",   "location": "Zone C", "factory": "FAC-B"},
    "MCH-105": {"name": "Rotary Kiln",             "installation_date": "2017-06-30", "last_maintenance": "2024-06-20", "operator": "Meena Raj",    "location": "Zone C", "factory": "FAC-C"},
    "MCH-106": {"name": "Turbine Generator",       "installation_date": "2022-02-14", "last_maintenance": "2024-11-01", "operator": "Vikram Singh", "location": "Zone B", "factory": "FAC-C"},
}

def get_factory_summary(predictions):
    """Returns per-factory health summary for multi-factory dashboard."""
    summary = {}
    for fid, finfo in FACTORIES.items():
        fmachines = [m for m,info in MACHINES.items() if info.get('factory') == fid]
        if not fmachines: continue
        healths = [predictions[m]['health_score'] for m in fmachines if m in predictions]
        risks   = [predictions[m]['failure_probability'] for m in fmachines if m in predictions]
        crits   = [m for m in fmachines if predictions.get(m,{}).get('status') == 'Critical']
        summary[fid] = {
            'factory_id':   fid,
            'name':         finfo['name'],
            'city':         finfo['city'],
            'manager':      finfo['manager'],
            'machines':     fmachines,
            'avg_health':   round(sum(healths)/len(healths), 1) if healths else 0,
            'avg_risk':     round(sum(risks)/len(risks), 1) if risks else 0,
            'critical':     crits,
            'status':       'Critical' if crits else 'Healthy',
        }
    return summary

AGE_FACTOR = {
    "MCH-101": 1.0, "MCH-102": 1.3, "MCH-103": 0.9,
    "MCH-104": 1.5, "MCH-105": 1.7, "MCH-106": 0.8
}

# ─────────────────────────────────────────────
# SENSOR HISTORY SIMULATION
# ─────────────────────────────────────────────

def generate_sensor_history(machine_id, n_points=30):
    np.random.seed(hash(machine_id) % 1000)
    af  = AGE_FACTOR.get(machine_id, 1.0)
    now = datetime.now()
    history = []
    for i in range(n_points):
        ts   = now - timedelta(hours=(n_points - i) * 2)
        temp = np.random.normal(65 * af, 8)
        vib  = np.random.normal(2.5 * af, 0.5)
        pres = np.random.normal(4.0 * af, 0.6)
        hrs  = 1200 * af + i * 2 + np.random.normal(0, 10)
        if machine_id in ("MCH-104", "MCH-105") and i > 24:
            temp += np.random.uniform(15, 25)
            vib  += np.random.uniform(1.0, 2.0)
            pres += np.random.uniform(0.8, 1.5)
        history.append({
            "timestamp":       ts.strftime("%Y-%m-%d %H:%M"),
            "temperature":     round(float(np.clip(temp, 30, 120)), 1),
            "vibration":       round(float(np.clip(vib,  0.5, 8.0)), 2),
            "pressure":        round(float(np.clip(pres, 1.0, 10.0)), 2),
            "operating_hours": round(float(hrs), 0)
        })
    return history

def get_current_readings(machine_id):
    return generate_sensor_history(machine_id, 30)[-1]

# ─────────────────────────────────────────────
# TRAINING DATA
# ─────────────────────────────────────────────

def _gen_classification_data(n=2000):
    np.random.seed(42)
    X, y = [], []
    for _ in range(n):
        temp = np.random.uniform(30, 120)
        vib  = np.random.uniform(0.5, 8.0)
        pres = np.random.uniform(1.0, 10.0)
        hrs  = np.random.uniform(100, 5000)
        fail = int((temp > 90) or (vib > 5.5) or (pres > 7.5) or (hrs > 4000)
                   or (temp > 75 and vib > 4.0) or (pres > 6.0 and hrs > 3000))
        X.append([temp, vib, pres, hrs]); y.append(fail)
    return np.array(X), np.array(y)

def _gen_rul_data(n=2000):
    np.random.seed(99)
    X, y = [], []
    for _ in range(n):
        temp = np.random.uniform(30, 120)
        vib  = np.random.uniform(0.5, 8.0)
        pres = np.random.uniform(1.0, 10.0)
        hrs  = np.random.uniform(100, 5000)
        rul  = max(0, 60 - (temp-30)/2 - vib*3 - (pres-1)*2 - hrs/200 + np.random.normal(0,3))
        X.append([temp, vib, pres, hrs]); y.append(rul)
    return np.array(X), np.array(y)

# ─────────────────────────────────────────────
# TRAIN MODELS — with persistence (train once, load forever)
# ─────────────────────────────────────────────
import os as _os
import joblib as _joblib

_MODEL_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'saved_models')
_os.makedirs(_MODEL_DIR, exist_ok=True)

_CLF_PATH  = _os.path.join(_MODEL_DIR, 'rf_classifier.pkl')
_ISO_PATH  = _os.path.join(_MODEL_DIR, 'iso_forest.pkl')
_RUL_PATH  = _os.path.join(_MODEL_DIR, 'rul_model.pkl')
_SCL_PATH  = _os.path.join(_MODEL_DIR, 'scaler.pkl')

# Always generate evaluation data (needed for MODEL_METRICS regardless of cache)
_Xc, _yc = _gen_classification_data()

if all(_os.path.exists(p) for p in [_CLF_PATH, _ISO_PATH, _RUL_PATH, _SCL_PATH]):
    print("[Models] ✅ Loading saved models — instant startup!")
    rf_classifier = _joblib.load(_CLF_PATH)
    iso_forest    = _joblib.load(_ISO_PATH)
    rul_model     = _joblib.load(_RUL_PATH)
    scaler        = _joblib.load(_SCL_PATH)
    _Xcs          = scaler.transform(_Xc)
else:
    print("[Models] 🔄 First run — training models (only happens once)...")
    scaler        = StandardScaler()
    _Xcs          = scaler.fit_transform(_Xc)

    rf_classifier = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=8)
    rf_classifier.fit(_Xcs, _yc)

    iso_forest    = IsolationForest(contamination=0.1, random_state=42)
    iso_forest.fit(_Xcs)

    _Xr, _yr      = _gen_rul_data()
    rul_model     = RandomForestRegressor(n_estimators=100, random_state=42)
    rul_model.fit(scaler.transform(_Xr), _yr)

    _joblib.dump(rf_classifier, _CLF_PATH)
    _joblib.dump(iso_forest,    _ISO_PATH)
    _joblib.dump(rul_model,     _RUL_PATH)
    _joblib.dump(scaler,        _SCL_PATH)
    print("[Models] ✅ Models saved! Future startups will be instant.")

# Evaluation metrics (always computed — uses loaded or freshly trained models)
_Xtr, _Xval, _ytr, _yval = train_test_split(_Xcs, _yc, test_size=0.2, random_state=7)
_ypred = rf_classifier.predict(_Xval)
MODEL_METRICS = {
    "accuracy":  round(accuracy_score(_yval, _ypred)  * 100, 2),
    "precision": round(precision_score(_yval, _ypred) * 100, 2),
    "recall":    round(recall_score(_yval, _ypred)    * 100, 2),
    "f1":        round(f1_score(_yval, _ypred)        * 100, 2),
    "confusion_matrix": confusion_matrix(_yval, _ypred).tolist(),
    "feature_importance": {
        "Temperature":     round(float(rf_classifier.feature_importances_[0]) * 100, 1),
        "Vibration":       round(float(rf_classifier.feature_importances_[1]) * 100, 1),
        "Pressure":        round(float(rf_classifier.feature_importances_[2]) * 100, 1),
        "Operating Hours": round(float(rf_classifier.feature_importances_[3]) * 100, 1),
    }
}

# ─────────────────────────────────────────────
# PREDICTION ENGINE
# ─────────────────────────────────────────────

def predict_machine(machine_id):
    reading  = get_current_readings(machine_id)
    features = np.array([[reading["temperature"], reading["vibration"],
                           reading["pressure"],    reading["operating_hours"]]])
    scaled   = scaler.transform(features)

    fail_prob    = float(rf_classifier.predict_proba(scaled)[0][1])
    health_score = round(100 - fail_prob * 100, 1)
    is_anomaly   = iso_forest.predict(scaled)[0] == -1
    anomaly_score= round(float(iso_forest.decision_function(scaled)[0]), 4)
    rul_days     = max(0, round(float(rul_model.predict(scaled)[0]), 1))

    status = "Critical" if fail_prob > 0.60 else "Warning" if fail_prob > 0.30 else "Healthy"

    failure_type, root_cause, solutions = _deduce_failure(reading)
    cost = _estimate_cost(failure_type, fail_prob)
    maint_date = (datetime.now() + timedelta(days=random.randint(3,5))).strftime("%Y-%m-%d") \
                 if fail_prob > 0.60 else None

    return {
        "machine_id":   machine_id,
        "machine_info": MACHINES[machine_id],
        "readings":     reading,
        "failure_probability":      round(fail_prob * 100, 1),
        "health_score":             health_score,
        "status":                   status,
        "is_anomaly":               bool(is_anomaly),
        "anomaly_score":            anomaly_score,
        "rul_days":                 rul_days,
        "failure_type":             failure_type,
        "root_cause":               root_cause,
        "solutions":                solutions,
        "cost_estimate":            cost,
        "suggested_maintenance_date": maint_date,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def _deduce_failure(reading):
    scores = {
        "Overheating":   reading["temperature"]     / 90,
        "Bearing Issue": reading["vibration"]        / 5.5,
        "Valve Blockage":reading["pressure"]         / 7.5,
        "Wear and Tear": reading["operating_hours"]  / 4000,
    }
    dominant = max(scores, key=scores.get)
    causes = {
        "Overheating":    ("High Temperature exceeded safe threshold",
                           ["Stop machine immediately","Check cooling system","Inspect lubrication","Inform maintenance team","Allow cooldown before restart"]),
        "Bearing Issue":  ("High Vibration exceeded safe threshold",
                           ["Inspect bearings and shaft alignment","Check lubrication levels","Replace worn bearings","Perform dynamic balancing"]),
        "Valve Blockage": ("High Pressure exceeded safe threshold",
                           ["Check relief valves","Inspect pipelines for blockage","Reduce operating pressure","Replace faulty pressure sensors"]),
        "Wear and Tear":  ("High Operating Hours exceeded safe threshold",
                           ["Schedule full overhaul","Replace consumable parts","Perform lubrication service","Log for predictive replacement cycle"]),
    }
    rc, sol = causes[dominant]
    return dominant, rc, sol

def _estimate_cost(failure_type, fail_prob):
    base = {
        "Overheating":    {"parts": 15000, "labor": 8000},
        "Bearing Issue":  {"parts": 22000, "labor": 12000},
        "Valve Blockage": {"parts": 18000, "labor": 9000},
        "Wear and Tear":  {"parts": 30000, "labor": 15000},
    }.get(failure_type, {"parts": 20000, "labor": 10000})
    m      = 1 + fail_prob
    spare  = round(base["parts"] * m)
    labor  = round(base["labor"] * m)
    total  = spare + labor
    return {
        "spare_parts_cost":  spare,
        "labor_cost":        labor,
        "total_estimated":   total,
        "preventive_cost":   round(total * 0.35),
        "breakdown_repair":  round(total * 1.8),
        "estimated_savings": round(total * 1.8 - total),
    }

# ─────────────────────────────────────────────
# DAILY REPORT
# ─────────────────────────────────────────────

def generate_daily_report():
    report = []
    for mid in MACHINES:
        p = predict_machine(mid)
        report.append({
            "machine_id":         mid,
            "name":               MACHINES[mid]["name"],
            "health_score":       p["health_score"],
            "failure_risk":       p["failure_probability"],
            "last_maintenance":   MACHINES[mid]["last_maintenance"],
            "status":             p["status"],
            "recommended_action": p["solutions"][0] if p["solutions"] else "Continue monitoring",
            "operator":           MACHINES[mid]["operator"],
        })
    return report

# ─────────────────────────────────────────────
# ANALYTICS DATA
# ─────────────────────────────────────────────

def generate_analytics_data():
    months = ["Jun","Jul","Aug","Sep","Oct","Nov"]
    return {
        "months":           months,
        "failure_counts":   [random.randint(2,8)      for _ in months],
        "maintenance_costs":[random.randint(40000,150000) for _ in months],
        "downtime_hours":   [random.randint(5,40)     for _ in months],
        "failure_type_distribution": {
            "Overheating": 12, "Bearing Issue": 8,
            "Valve Blockage": 6, "Wear and Tear": 9
        },
    }

# ─────────────────────────────────────────────
# LIVE SIMULATION
# ─────────────────────────────────────────────

def get_live_data(machine_id):
    base = get_current_readings(machine_id)
    af   = AGE_FACTOR.get(machine_id, 1.0)
    return {
        "temperature":     round(base["temperature"] + random.uniform(-2, 3)   * af, 1),
        "vibration":       round(base["vibration"]   + random.uniform(-0.1,0.2)* af, 2),
        "pressure":        round(base["pressure"]    + random.uniform(-0.2,0.3)* af, 2),
        "operating_hours": round(base["operating_hours"] + random.uniform(0,0.05), 2),
        "timestamp":       datetime.now().strftime("%H:%M:%S"),
    }
