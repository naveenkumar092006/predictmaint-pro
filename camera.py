# camera.py — Live Camera Stream Handler
# PredictMaint Pro — Camera Vision Module

import cv2
import threading
import time
import numpy as np


class CameraStream:
    def __init__(self, src=0):
        self.src = src
        self.cap = None
        self.frame = None
        self.annotated_frame = None
        self.running = False
        self.lock = threading.Lock()
        self.fps = 0
        self._fps_counter = 0
        self._fps_timer = time.time()

    def start(self):
        self.cap = cv2.VideoCapture(self.src)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            raise RuntimeError("Cannot open webcam. Check connection.")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.running = True
        t = threading.Thread(target=self._capture_loop, daemon=True)
        t.start()
        print("✅ Camera stream started.")

    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame.copy()
                self._fps_counter += 1
                elapsed = time.time() - self._fps_timer
                if elapsed >= 1.0:
                    self.fps = self._fps_counter / elapsed
                    self._fps_counter = 0
                    self._fps_timer = time.time()
            else:
                time.sleep(0.01)

    def get_frame(self):
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def set_annotated_frame(self, frame):
        with self.lock:
            self.annotated_frame = frame.copy()

    def get_annotated_frame(self):
        with self.lock:
            if self.annotated_frame is not None:
                return self.annotated_frame.copy()
            if self.frame is not None:
                return self.frame.copy()
            return None

    def generate_mjpeg(self):
        while self.running:
            frame = self.get_annotated_frame()
            if frame is None:
                time.sleep(0.05)
                continue
            ret, jpeg = cv2.imencode('.jpg', frame,
                                     [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret:
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' +
                   jpeg.tobytes() + b'\r\n')
            time.sleep(0.033)

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        print("🛑 Camera stream stopped.")


camera_stream = CameraStream(src=0)
