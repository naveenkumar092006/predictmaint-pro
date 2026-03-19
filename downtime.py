# downtime.py — Downtime Calculator & Machine Comparison Engine

import random
from datetime import datetime

# ── DOWNTIME CALCULATOR ───────────────────────────────────────────────────────

# Production rates per machine (units per hour)
PRODUCTION_RATES = {
    "MCH-101": {"rate": 120,  "unit": "parts",      "value_per_unit": 850},
    "MCH-102": {"rate": 80,   "unit": "pressings",  "value_per_unit": 1200},
    "MCH-103": {"rate": 500,  "unit": "units",      "value_per_unit": 200},
    "MCH-104": {"rate": 60,   "unit": "cycles",     "value_per_unit": 1500},
    "MCH-105": {"rate": 40,   "unit": "batches",    "value_per_unit": 3500},
    "MCH-106": {"rate": 1,    "unit": "MW",         "value_per_unit": 8000},
}

REPAIR_TIMES = {
    "Overheating":    {"min": 4,  "max": 12, "label": "Cooling system repair"},
    "Bearing Issue":  {"min": 8,  "max": 24, "label": "Bearing replacement"},
    "Valve Blockage": {"min": 3,  "max": 8,  "label": "Valve cleaning/replacement"},
    "Wear and Tear":  {"min": 24, "max": 72, "label": "Full overhaul"},
}

def calculate_downtime(machine_id, failure_type, failure_probability):
    """Calculate estimated downtime and production loss."""
    random.seed(hash(machine_id + failure_type) % 999)

    prod  = PRODUCTION_RATES.get(machine_id, {"rate":100,"unit":"units","value_per_unit":500})
    repair= REPAIR_TIMES.get(failure_type, {"min":6,"max":18,"label":"General repair"})

    # Estimated repair hours based on failure probability
    severity_factor = failure_probability / 100
    est_hours = round(repair["min"] + (repair["max"] - repair["min"]) * severity_factor, 1)

    # Production loss
    units_lost     = round(prod["rate"] * est_hours)
    revenue_lost   = round(units_lost * prod["value_per_unit"])
    labor_cost     = round(est_hours * 1500)   # Rs.1500/hour labor
    penalty_cost   = round(revenue_lost * 0.1) # 10% penalty/delay cost
    total_loss     = revenue_lost + labor_cost + penalty_cost

    # Preventive vs breakdown comparison
    preventive_cost   = round(total_loss * 0.3)
    breakdown_loss    = total_loss
    savings_if_prev   = round(breakdown_loss - preventive_cost)

    # Shifts affected
    shifts_affected = max(1, round(est_hours / 8))

    return {
        "machine_id":          machine_id,
        "failure_type":        failure_type,
        "failure_probability": failure_probability,
        "repair_label":        repair["label"],
        "estimated_hours":     est_hours,
        "shifts_affected":     shifts_affected,
        "production_rate":     prod["rate"],
        "unit":                prod["unit"],
        "units_lost":          units_lost,
        "revenue_lost":        revenue_lost,
        "labor_cost":          labor_cost,
        "penalty_cost":        penalty_cost,
        "total_loss":          total_loss,
        "preventive_cost":     preventive_cost,
        "breakdown_loss":      breakdown_loss,
        "savings_if_preventive": savings_if_prev,
        "urgency": ("🔴 CRITICAL — Act immediately" if failure_probability > 60
                    else "🟡 WARNING — Schedule soon" if failure_probability > 30
                    else "🟢 MONITOR — Continue operations"),
    }


def calculate_all_downtime(predictions):
    """Calculate downtime for all machines."""
    results = {}
    total_potential_loss = 0
    for mid, pred in predictions.items():
        dt = calculate_downtime(mid, pred["failure_type"], pred["failure_probability"])
        results[mid] = dt
        total_potential_loss += dt["total_loss"]
    return results, total_potential_loss


# ── MACHINE COMPARISON ────────────────────────────────────────────────────────

def compare_machines(pred1, pred2, mid1, mid2):
    """Generate a detailed side-by-side comparison of two machines."""

    def winner(v1, v2, higher_is_better=True):
        if higher_is_better:
            return mid1 if v1 > v2 else (mid2 if v2 > v1 else "TIE")
        else:
            return mid1 if v1 < v2 else (mid2 if v2 < v1 else "TIE")

    comparisons = [
        {
            "metric":    "Health Score",
            "unit":      "%",
            "val1":      pred1["health_score"],
            "val2":      pred2["health_score"],
            "winner":    winner(pred1["health_score"], pred2["health_score"], True),
            "higher_good": True,
        },
        {
            "metric":    "Failure Risk",
            "unit":      "%",
            "val1":      pred1["failure_probability"],
            "val2":      pred2["failure_probability"],
            "winner":    winner(pred1["failure_probability"], pred2["failure_probability"], False),
            "higher_good": False,
        },
        {
            "metric":    "Remaining Useful Life",
            "unit":      "days",
            "val1":      pred1["rul_days"],
            "val2":      pred2["rul_days"],
            "winner":    winner(pred1["rul_days"], pred2["rul_days"], True),
            "higher_good": True,
        },
        {
            "metric":    "Temperature",
            "unit":      "°C",
            "val1":      pred1["readings"]["temperature"],
            "val2":      pred2["readings"]["temperature"],
            "winner":    winner(pred1["readings"]["temperature"], pred2["readings"]["temperature"], False),
            "higher_good": False,
        },
        {
            "metric":    "Vibration",
            "unit":      "mm/s",
            "val1":      pred1["readings"]["vibration"],
            "val2":      pred2["readings"]["vibration"],
            "winner":    winner(pred1["readings"]["vibration"], pred2["readings"]["vibration"], False),
            "higher_good": False,
        },
        {
            "metric":    "Pressure",
            "unit":      "bar",
            "val1":      pred1["readings"]["pressure"],
            "val2":      pred2["readings"]["pressure"],
            "winner":    winner(pred1["readings"]["pressure"], pred2["readings"]["pressure"], False),
            "higher_good": False,
        },
        {
            "metric":    "Est. Repair Cost",
            "unit":      "Rs.",
            "val1":      pred1["cost_estimate"]["total_estimated"],
            "val2":      pred2["cost_estimate"]["total_estimated"],
            "winner":    winner(pred1["cost_estimate"]["total_estimated"],
                               pred2["cost_estimate"]["total_estimated"], False),
            "higher_good": False,
        },
        {
            "metric":    "Anomaly Detected",
            "unit":      "",
            "val1":      "YES" if pred1["is_anomaly"] else "NO",
            "val2":      "YES" if pred2["is_anomaly"] else "NO",
            "winner":    (mid1 if not pred1["is_anomaly"] and pred2["is_anomaly"]
                          else mid2 if pred2["is_anomaly"] == False and pred1["is_anomaly"]
                          else "TIE"),
            "higher_good": False,
        },
    ]

    # Overall winner
    wins1 = sum(1 for c in comparisons if c["winner"] == mid1)
    wins2 = sum(1 for c in comparisons if c["winner"] == mid2)
    overall_winner = mid1 if wins1 > wins2 else (mid2 if wins2 > wins1 else "TIE")

    return {
        "machine1":       mid1,
        "machine2":       mid2,
        "pred1":          pred1,
        "pred2":          pred2,
        "comparisons":    comparisons,
        "wins1":          wins1,
        "wins2":          wins2,
        "overall_winner": overall_winner,
        "recommendation": _generate_recommendation(pred1, pred2, mid1, mid2, overall_winner),
    }


def _generate_recommendation(pred1, pred2, mid1, mid2, winner):
    """Generate a recommendation based on comparison."""
    recs = []
    if pred1["status"] == "Critical":
        recs.append(f"⚠️ {mid1} needs IMMEDIATE attention — schedule maintenance within 3 days.")
    if pred2["status"] == "Critical":
        recs.append(f"⚠️ {mid2} needs IMMEDIATE attention — schedule maintenance within 3 days.")
    if pred1["rul_days"] < pred2["rul_days"]:
        recs.append(f"🔧 {mid1} has lower remaining life — prioritize its maintenance first.")
    else:
        recs.append(f"🔧 {mid2} has lower remaining life — prioritize its maintenance first.")
    if winner != "TIE":
        recs.append(f"✅ Overall {winner} is in better condition based on all metrics.")
    else:
        recs.append("⚖️ Both machines are in similar condition — monitor both equally.")
    return recs
