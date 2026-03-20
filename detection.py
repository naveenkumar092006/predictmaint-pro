# detection.py — Machine Detection Engine
# Maps real objects on webcam → machine IDs for PredictMaint Pro

import cv2
import numpy as np
import time
import random
import threading
import os

# ── Object → Machine ID mapping ──────────────────────────────────────────────
OBJECT_TO_MACHINE = {
    'bottle': 'MCH-101', 'cup': 'MCH-101', 'wine glass': 'MCH-101',
    'laptop': 'MCH-102', 'keyboard': 'MCH-102', 'tv': 'MCH-102', 'monitor': 'MCH-102',
    'book': 'MCH-103', 'backpack': 'MCH-103', 'suitcase': 'MCH-103',
    'cell phone': 'MCH-104', 'remote': 'MCH-104',
    'chair': 'MCH-105', 'couch': 'MCH-105', 'sofa': 'MCH-105',
    'person': 'MCH-106',
}

MACHINE_NAMES = {
    'MCH-101': 'CNC Milling Machine',
    'MCH-102': 'Hydraulic Press',
    'MCH-103': 'Conveyor Belt System',
    'MCH-104': 'Industrial Compressor',
    'MCH-105': 'Rotary Kiln',
    'MCH-106': 'Turbine Generator',
}

STATUS_COLORS = {
    'CRITICAL': (0, 0, 255),
    'WARNING':  (0, 165, 255),
    'NORMAL':   (0, 220, 80),
    'UNKNOWN':  (180, 180, 180),
}

# Sensor baselines per machine (matching your models.py AGE_FACTOR)
BASELINES = {
    'MCH-101': dict(base_temp=68,  base_vib=1.2, base_press=4.5, base_hours=1200),
    'MCH-102': dict(base_temp=72,  base_vib=1.8, base_press=5.0, base_hours=2800),
    'MCH-103': dict(base_temp=65,  base_vib=1.0, base_press=4.0, base_hours=900),
    'MCH-104': dict(base_temp=78,  base_vib=2.5, base_press=5.8, base_hours=3500),
    'MCH-105': dict(base_temp=82,  base_vib=3.0, base_press=6.2, base_hours=4100),
    'MCH-106': dict(base_temp=60,  base_vib=0.8, base_press=3.8, base_hours=500),
}


class MachineDetector:
    def __init__(self):
        self.net = None
        self.classes = []
        self.detection_lock = threading.Lock()
        self.machine_state = {}
        self.detected_machines = {}
        self.last_seen = {}
        self.force_failure = set()
        self.force_overheat = set()
        self._load_model()

    def _load_model(self):
        proto   = os.path.join(os.path.dirname(__file__), 'models_cv', 'MobileNetSSD_deploy.prototxt')
        weights = os.path.join(os.path.dirname(__file__), 'models_cv', 'MobileNetSSD_deploy.caffemodel')
        if os.path.exists(proto) and os.path.exists(weights):
            try:
                self.net = cv2.dnn.readNetFromCaffe(proto, weights)
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                self.classes = [
                    'background','aeroplane','bicycle','bird','boat','bottle','bus',
                    'car','cat','chair','cow','diningtable','dog','horse','motorbike',
                    'person','pottedplant','sheep','sofa','train','tvmonitor',
                    'laptop','keyboard','cell phone','book','cup','backpack','remote'
                ]
                print("✅ MobileNet-SSD loaded (named object detection)")
                return
            except Exception as e:
                print(f"⚠️  DNN load failed: {e}")
        print("⚠️  No DNN model found → using contour detection (always works)")
        print("    Place distinct objects in front of camera — each becomes a machine.")

    def detect(self, frame):
        if self.net is not None:
            detections = self._detect_dnn(frame)
        else:
            detections = self._detect_contour(frame)
        with self.detection_lock:
            self._update_states(detections)
            annotated = self._draw(frame.copy(), detections)
        return annotated, detections

    def _detect_dnn(self, frame):
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)),
                                     0.007843, (300, 300), 127.5)
        self.net.setInput(blob)
        out = self.net.forward()
        detections, seen = [], set()
        for i in range(out.shape[2]):
            conf = float(out[0, 0, i, 2])
            if conf < 0.30: continue
            idx = int(out[0, 0, i, 1])
            if idx >= len(self.classes): continue
            label  = self.classes[idx]
            mch_id = OBJECT_TO_MACHINE.get(label)
            if not mch_id or mch_id in seen: continue
            seen.add(mch_id)
            x1 = int(out[0, 0, i, 3] * w); y1 = int(out[0, 0, i, 4] * h)
            x2 = int(out[0, 0, i, 5] * w); y2 = int(out[0, 0, i, 6] * h)
            detections.append({'label': label, 'machine_id': mch_id,
                                'confidence': conf,
                                'bbox': (max(0,x1), max(0,y1), min(w,x2), min(h,y2))})
        return detections

    def _detect_contour(self, frame):
        h, w  = frame.shape[:2]
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur  = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 30, 100)
        kern  = cv2.getStructuringElement(cv2.MORPH_RECT, (12, 12))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kern)
        cnts1, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kern2 = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
        th    = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kern2)
        cnts2, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        all_cnts = list(cnts1) + list(cnts2)
        min_area = (w * h) * 0.005
        max_area = (w * h) * 0.88
        valid = sorted([c for c in all_cnts
                        if min_area < cv2.contourArea(c) < max_area],
                       key=cv2.contourArea, reverse=True)
        filtered = []
        for cnt in valid:
            x, y, bw, bh = cv2.boundingRect(cnt)
            overlap = False
            for fc in filtered:
                fx, fy, fbw, fbh = cv2.boundingRect(fc)
                if abs(x - fx) < 60 and abs(y - fy) < 60:
                    overlap = True
                    break
            if not overlap:
                filtered.append(cnt)
            if len(filtered) >= 4:
                break
        def guess_label(cnt):
            x, y, bw, bh = cv2.boundingRect(cnt)
            ratio = bw / max(bh, 1)
            area  = cv2.contourArea(cnt)
            if ratio < 0.6:        return 'bottle'
            if ratio > 1.8:        return 'laptop'
            if area < (w*h)*0.03:  return 'cell phone'
            return 'box'
        order = ['MCH-101','MCH-102','MCH-103','MCH-104']
        dets  = []
        for i, cnt in enumerate(filtered[:4]):
            x, y, bw, bh = cv2.boundingRect(cnt)
            label  = guess_label(cnt)
            mch_id = OBJECT_TO_MACHINE.get(label, order[i])
            dets.append({'label': label, 'machine_id': mch_id,
                         'confidence': 0.75,
                         'bbox': (x, y, x+bw, y+bh)})
        return dets

    def _update_states(self, detections):
        now     = time.time()
        det_ids = set()
        for det in detections:
            mid = det['machine_id']
            det_ids.add(mid)
            self.last_seen[mid] = now
            if mid not in self.machine_state:
                self._init_machine(mid)
            s = self.machine_state[mid]
            s['detection_count'] += 1
            s['bbox']       = det['bbox']
            s['confidence'] = det['confidence']
            s['object_label'] = det['label']
            s['visible']    = True
            wear = min(s['detection_count'] / 800.0, 1.0)
            temp  = s['base_temp']  + wear * 30 + random.uniform(-1.5, 1.5)
            vib   = s['base_vib']   + wear * 3.5 + random.uniform(-0.2, 0.2)
            press = s['base_press'] + wear * 2.5 + random.uniform(-0.2, 0.2)
            hours = s['base_hours'] + s['detection_count'] * 0.05
            # Random spike (5% chance)
            if random.random() < 0.05:
                spike = random.choice(['temp','vib','press'])
                if spike == 'temp':  temp  += random.uniform(10, 25)
                if spike == 'vib':   vib   += random.uniform(1.5, 4)
                if spike == 'press': press += random.uniform(1, 3)
            # Demo overrides
            if mid in self.force_failure:
                temp  = random.uniform(94, 105)
                vib   = random.uniform(6, 8)
                press = random.uniform(8, 10)
                hours = random.uniform(4200, 4800)
            if mid in self.force_overheat:
                temp  = random.uniform(88, 100)
                press = random.uniform(7, 9)
            s['temperature'] = round(temp,  2)
            s['vibration']   = round(vib,   3)
            s['pressure']    = round(press, 2)
            s['hours']       = round(hours, 1)
            s['wear']        = round(wear,  3)
        for mid, s in self.machine_state.items():
            if mid not in det_ids:
                s['visible'] = False
        self.detected_machines = {
            mid: self.machine_state[mid]
            for mid in det_ids if mid in self.machine_state
        }

    def _init_machine(self, mid):
        b = BASELINES.get(mid, dict(base_temp=70, base_vib=1.5,
                                    base_press=4.8, base_hours=1500))
        self.machine_state[mid] = {
            **b,
            'temperature': b['base_temp'], 'vibration': b['base_vib'],
            'pressure': b['base_press'],   'hours': b['base_hours'],
            'wear': 0.0, 'detection_count': 0, 'visible': True,
            'bbox': (0,0,0,0), 'confidence': 0.0,
            'object_label': 'unknown', 'machine_id': mid,
            'machine_name': MACHINE_NAMES.get(mid, mid),
        }

    def _draw(self, frame, detections):
        h, w = frame.shape[:2]
        for det in detections:
            mid = det['machine_id']
            s   = self.machine_state.get(mid, {})
            x1, y1, x2, y2 = det['bbox']
            temp  = s.get('temperature', 0)
            vib   = s.get('vibration', 0)
            press = s.get('pressure', 0)
            if mid in self.force_failure or temp > 90 or vib > 5.5 or press > 7.5:
                status = 'CRITICAL'
            elif temp > 80 or vib > 4.0 or press > 6.5:
                status = 'WARNING'
            else:
                status = 'NORMAL'
            color = STATUS_COLORS[status]
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
            cl = 16
            for cx,cy,dx,dy in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
                cv2.line(frame,(cx,cy),(cx+dx*cl,cy),color,3)
                cv2.line(frame,(cx,cy),(cx,cy+dy*cl),color,3)
            tag = f" {mid} | {MACHINE_NAMES.get(mid,mid)} "
            (tw,th2),_ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame,(x1,y1-th2-10),(x1+tw,y1),color,-1)
            cv2.putText(frame,tag,(x1,y1-4),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,0),1,cv2.LINE_AA)
            # Sensor overlay box
            bx = x2+6 if x2+166 <= w else x1-166
            by = y1
            lines = [
                f"T: {s.get('temperature',0):.1f}C",
                f"V: {s.get('vibration',0):.2f}mm/s",
                f"P: {s.get('pressure',0):.1f}bar",
                f"H: {s.get('hours',0):.0f}h",
                f"[{status}]",
            ]
            overlay = frame.copy()
            cv2.rectangle(overlay,(bx,by),(bx+155,by+len(lines)*18+8),(20,20,20),-1)
            cv2.addWeighted(overlay,0.75,frame,0.25,0,frame)
            for j,ln in enumerate(lines):
                lc = color if ln.startswith('[') else (180,220,255)
                cv2.putText(frame,ln,(bx+4,by+16+j*18),
                            cv2.FONT_HERSHEY_SIMPLEX,0.42,lc,1,cv2.LINE_AA)
        # HUD
        cv2.rectangle(frame,(0,0),(230,60),(10,10,10),-1)
        cv2.putText(frame,"PredictMaint Pro | LIVE CAM",
                    (8,18),cv2.FONT_HERSHEY_SIMPLEX,0.48,(0,200,255),1,cv2.LINE_AA)
        cv2.putText(frame,f"Detected: {len(detections)} machine(s)",
                    (8,38),cv2.FONT_HERSHEY_SIMPLEX,0.44,(200,200,200),1,cv2.LINE_AA)
        cv2.putText(frame,time.strftime("%H:%M:%S"),
                    (8,55),cv2.FONT_HERSHEY_SIMPLEX,0.4,(100,100,100),1,cv2.LINE_AA)
        return frame

    def get_detected_machines(self):
        with self.detection_lock:
            return dict(self.detected_machines)

    def get_all_states(self):
        with self.detection_lock:
            return dict(self.machine_state)

    def trigger_failure(self, mid=None):
        targets = [mid] if mid else list(self.machine_state.keys())
        for m in targets:
            self.force_failure.add(m)
            self.force_overheat.discard(m)

    def simulate_overheat(self, mid=None):
        targets = [mid] if mid else list(self.machine_state.keys())
        for m in targets:
            self.force_overheat.add(m)
            self.force_failure.discard(m)

    def reset_machines(self):
        self.force_failure.clear()
        self.force_overheat.clear()
        self.machine_state.clear()
        self.detected_machines.clear()
        self.last_seen.clear()


detector = MachineDetector()
