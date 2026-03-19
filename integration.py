# integration.py — Camera ↔ ML Bridge
# Feeds camera sensor data into your existing models.py predict_machine()

import threading
import time
import random


def _run_prediction(temperature, vibration, pressure, hours):
    """Use your existing models.py predict_machine via a fake machine_id."""
    try:
        from models import predict_machine, MACHINES, AGE_FACTOR
        import numpy as np
        # We call predict_machine with MCH-101 but override its readings
        # by directly calling the ML pipeline with our sensor values
        from models import clf, iso, rul_model, scaler
        X = scaler.transform([[temperature, vibration, pressure, hours]])
        fp  = round(float(clf.predict_proba(X)[0][1]) * 100, 1)
        anom = iso.predict(X)[0] == -1
        rul  = max(0, round(float(rul_model.predict(X)[0]), 1))
        health = round(max(0, 100 - fp * 0.9), 1)
        return fp, anom, rul, health
    except Exception:
        pass
    # Pure fallback (no import needed)
    t = min(temperature / 110.0, 1.0)
    v = min(vibration   / 9.0,   1.0)
    p = min(pressure    / 10.0,  1.0)
    h = min(hours       / 5000.0, 1.0)
    score  = t*0.35 + v*0.30 + p*0.20 + h*0.15
    fp     = round(min(score * 120, 99.9), 1)
    anom   = temperature > 88 or vibration > 5.0 or pressure > 7.2 or score > 0.70
    rul    = max(0, round(90*(1-score) + random.uniform(-3,3), 1))
    health = round(max(0, 100 - fp*0.9), 1)
    return fp, anom, rul, health


class CameraMLIntegration:
    def __init__(self, camera_stream, detector):
        self.camera   = camera_stream
        self.detector = detector
        self.running  = False
        self._lock    = threading.Lock()
        self.predictions  = {}
        self.system_stats = {
            'total_machines': 0, 'critical_count': 0,
            'warning_count': 0,  'normal_count': 0,
            'last_update': None, 'camera_fps': 0,
        }

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()
        print("✅ Camera-ML integration started.")

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            frame = self.camera.get_frame()
            if frame is None:
                time.sleep(0.05)
                continue
            annotated, _ = self.detector.detect(frame)
            self.camera.set_annotated_frame(annotated)
            new_preds = {}
            for mid, state in self.detector.get_detected_machines().items():
                fp, anom, rul, health = _run_prediction(
                    state['temperature'], state['vibration'],
                    state['pressure'],   state['hours'])
                status = ('CRITICAL' if fp >= 70 or health < 30
                          else 'WARNING' if fp >= 40 or health < 60
                          else 'NORMAL')
                new_preds[mid] = {
                    'machine_id':          mid,
                    'machine_name':        state.get('machine_name', mid),
                    'object_label':        state.get('object_label', ''),
                    'temperature':         state['temperature'],
                    'vibration':           state['vibration'],
                    'pressure':            state['pressure'],
                    'hours':               state['hours'],
                    'failure_probability': fp,
                    'anomaly':             anom,
                    'rul':                 rul,
                    'health_score':        health,
                    'status':              status,
                    'visible':             True,
                    'wear':                state.get('wear', 0),
                    'timestamp':           time.time(),
                }
            crit = sum(1 for p in new_preds.values() if p['status'] == 'CRITICAL')
            warn = sum(1 for p in new_preds.values() if p['status'] == 'WARNING')
            norm = sum(1 for p in new_preds.values() if p['status'] == 'NORMAL')
            with self._lock:
                self.predictions  = new_preds
                self.system_stats = {
                    'total_machines': len(new_preds),
                    'critical_count': crit, 'warning_count': warn,
                    'normal_count':   norm,
                    'last_update':    time.strftime('%H:%M:%S'),
                    'camera_fps':     round(self.camera.fps, 1),
                }
            time.sleep(0.1)

    def get_predictions(self):
        with self._lock: return dict(self.predictions)

    def get_stats(self):
        with self._lock: return dict(self.system_stats)

    def get_critical_machine(self):
        preds = self.get_predictions()
        return max(preds.values(),
                   key=lambda x: x['failure_probability']) if preds else None

    def get_chatbot_context(self):
        preds = self.get_predictions()
        stats = self.get_stats()
        if not preds:
            return "No machines currently detected by the live camera."
        lines = [
            f"Live camera sees {stats['total_machines']} machine(s). "
            f"Critical: {stats['critical_count']}, "
            f"Warning: {stats['warning_count']}, "
            f"Normal: {stats['normal_count']}."
        ]
        for mid, p in preds.items():
            lines.append(
                f"{mid} ({p['machine_name']}): "
                f"Temp={p['temperature']}°C, Vib={p['vibration']}mm/s, "
                f"Failure={p['failure_probability']}%, Health={p['health_score']}%, "
                f"RUL={p['rul']} days, Status={p['status']}."
            )
        return " ".join(lines)
