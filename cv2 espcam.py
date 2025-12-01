import cv2
import numpy as np
from ultralytics import YOLO
import requests
import time

model_path = "C:/Users/Arya/runs/detect/train9/weights/best.pt"
esp32_ip = "10.162.179.31"
esp_cam_url = "http://10.162.179.91:81/stream"
roi_belok = np.array([[490, 110], [800, 110], [800, 540], [490, 540]], np.int32)
heartbeat_interval = 2.0

model = YOLO(model_path)
cap = cv2.VideoCapture(esp_cam_url)
if not cap.isOpened():
    print("Error: Gagal membuka stream ESP-CAM.")
    exit()
print("Berhasil terhubung ke ESP-CAM.")
last_heartbeat_time = 0
status_koneksi = "Menunggu..."

try:
    logo = cv2.imread('C:/Users/Arya/Downloads/wordart.png', cv2.IMREAD_UNCHANGED) 
    tinggi_logo = 100
    rasio = tinggi_logo / logo.shape[0]
    lebar_logo = int(logo.shape[1] * rasio)
    logo_kecil = cv2.resize(logo, (lebar_logo, tinggi_logo))
    logo_bgr = logo_kecil[:, :, 0:3]
    mask_alpha = logo_kecil[:, :, 3]
    mask_alpha_inv = cv2.bitwise_not(mask_alpha)
    print("Logo berhasil dimuat.")
except Exception:
    logo = None
    print("Logo tidak ditemukan, melanjutkan tanpa logo.")

while True:
    start_time = time.time()
    ret, frame = cap.read()
    if not ret:
        status_koneksi = "Stream Terputus"
        time.sleep(2)
        continue

    panel = frame.copy()
    cv2.rectangle(panel, (5, 5), (450, 220), (0, 0, 0), -1)
    alpha_panel = 0.6
    frame = cv2.addWeighted(panel, alpha_panel, frame, 1 - alpha_panel, 0)

    cv2.polylines(frame, [roi_belok], isClosed=True, color=(0, 255, 255), thickness=2)

    results = model(frame)
    mobil_di_jalur_belok = False
    jumlah_mobil_di_roi = 0

    for result in results:
        for box in result.boxes:
            if box.conf[0] > 0.50:
                class_name = model.names[int(box.cls[0])]
                if class_name in ['hotwheels', 'objects']:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    reference_point = (int((x1 + x2) / 2), int((y1 + y2) / 2))
                    if cv2.pointPolygonTest(roi_belok, reference_point, False) >= 0:
                        mobil_di_jalur_belok = True
                        jumlah_mobil_di_roi += 1
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)
                        cv2.putText(frame, "MOBIL BELOK", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)

    if mobil_di_jalur_belok:
        current_time = time.time()
        if current_time - last_heartbeat_time > heartbeat_interval:
            try:
                requests.get(f'http://{esp32_ip}/triggerBelok', timeout=1)
                last_heartbeat_time = current_time
                status_koneksi = "Tersambung"
            except requests.exceptions.RequestException:
                status_koneksi = "Gagal Kirim"

    status_text = "MOBIL TERDETEKSI!" if mobil_di_jalur_belok else "JALUR AMAN"
    status_color = (0, 0, 255) if mobil_di_jalur_belok else (0, 255, 0)
    end_time = time.time()
    fps = 1 / (end_time - start_time)
    
    cv2.putText(frame, f"STATUS: {status_text}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
    cv2.putText(frame, f"Mobil di Zona: {jumlah_mobil_di_roi}", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, f"FPS: {int(fps)}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, f"Koneksi ESP32: {status_koneksi}", (20, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    if last_heartbeat_time > 0:
        waktu_lalu = int(time.time() - last_heartbeat_time)
        cv2.putText(frame, f"Sinyal Terakhir: {waktu_lalu} detik lalu", (20, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    if logo is not None:
        tinggi_frame, lebar_frame, _ = frame.shape
        y_offset = 20
        x_offset = lebar_frame - lebar_logo - 20
        
        if y_offset + tinggi_logo < tinggi_frame and x_offset + lebar_logo < lebar_frame:
            roi = frame[y_offset:y_offset + tinggi_logo, x_offset:x_offset + lebar_logo]
            frame_bg = cv2.bitwise_and(roi, roi, mask=mask_alpha_inv)
            logo_fg = cv2.bitwise_and(logo_bgr, logo_bgr, mask=mask_alpha)
            frame[y_offset:y_offset + tinggi_logo, x_offset:x_offset + lebar_logo] = cv2.add(frame_bg, logo_fg)

    cv2.imshow('Deteksi - Panel Status', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()