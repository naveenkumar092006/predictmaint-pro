# esp32_sensor.py — Real IoT Sensor Integration
# ============================================================
# This file handles REAL sensor data from ESP32 hardware.
# Upload esp32_firmware/firmware.ino to your ESP32 using Arduino IDE.
#
# Hardware needed (~₹650 total):
#   ESP32 DevKit        ₹350  — search "ESP32 WROOM DevKit"
#   DS18B20 sensor      ₹80   — search "DS18B20 waterproof"
#   MPU6050 module      ₹120  — search "MPU6050 GY-521"
#   BMP280 module       ₹100  — search "BMP280 pressure sensor"
#   Jumper wires        ₹50   — search "jumper wire kit"
# ============================================================

import threading
import time
from datetime import datetime
from collections import deque

# Per-machine live sensor buffer — stores last 100 readings
_sensor_buffers = {}   # machine_id → deque of readings
_sensor_lock    = threading.Lock()
_last_seen      = {}   # machine_id → timestamp

# ── Public API ─────────────────────────────────────────────────────────────

def receive_esp32_data(machine_id, temperature, vibration, pressure,
                       operating_hours=None, device_id=None):
    """
    Called by Flask route when ESP32 POST arrives.
    Stores reading in buffer and returns it for ML processing.
    """
    reading = {
        'machine_id':      machine_id,
        'temperature':     round(float(temperature), 2),
        'vibration':       round(float(vibration),   3),
        'pressure':        round(float(pressure),    2),
        'operating_hours': round(float(operating_hours or 0), 1),
        'device_id':       device_id or 'ESP32-001',
        'source':          'hardware',   # ← tells dashboard this is REAL data
        'timestamp':       datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    with _sensor_lock:
        if machine_id not in _sensor_buffers:
            _sensor_buffers[machine_id] = deque(maxlen=100)
        _sensor_buffers[machine_id].appendleft(reading)
        _last_seen[machine_id] = time.time()
    return reading


def get_latest_reading(machine_id):
    """Get most recent hardware reading for a machine. None if no hardware."""
    with _sensor_lock:
        buf = _sensor_buffers.get(machine_id)
        if buf and len(buf) > 0:
            # Only return if received within last 30 seconds
            age = time.time() - _last_seen.get(machine_id, 0)
            if age < 30:
                return buf[0]
    return None


def get_reading_history(machine_id, n=30):
    """Get last n readings for charts."""
    with _sensor_lock:
        buf = _sensor_buffers.get(machine_id, deque())
        return list(buf)[:n]


def get_connected_devices():
    """Returns list of ESP32 devices currently sending data."""
    now = time.time()
    with _sensor_lock:
        return [
            {'machine_id': mid, 'last_seen': _last_seen[mid],
             'age_seconds': round(now - _last_seen[mid], 1),
             'online': (now - _last_seen[mid]) < 10}
            for mid in _last_seen
        ]


def is_hardware_active(machine_id):
    """True if we have a recent real reading from ESP32."""
    return get_latest_reading(machine_id) is not None
