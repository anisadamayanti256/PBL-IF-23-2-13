from mysql.connector import connect
from ultralytics import YOLO # Library Paling Utama YOLO dalam Ultralytics
import cv2 #Library Utama ke-2 untuk menampilkan output
import cvzone # Library Utama ke-3 untuk bounding-box
import pyttsx3 # Library Utama ke-4 untuk menghasilkan Feedback Suara

# Library tambahan 
import math # Untuk perhitungan math, bisa juga menggunakan numpy
import time # Untuk waktu dan timestamp
import os # Untuk mengatur direktori

def insert_detection_to_database(cursor, class_name, x1, y1, w, h, conf):
    """Select database user untuk check."""
    queryUser = """
    SELECT * FROM user
    WHERE nama = %s
    """
    cursor.execute(queryUser, (class_name,))
    user = cursor.fetchone()

    if user is not None:
        # Fetch the user data
        user_id = user[0]

        """Insert detection information into the database."""
        query = """
        INSERT INTO realtime (id_user, xAxis, yAxis, width, height, conf, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (user_id, x1, y1, w, h, conf, "Detected (Hadir)")
        cursor.execute(query, values)
    else:
        print(f"No user found with name {class_name}")

def set_working_directory(directory):
    """Mengubah direktori kerja ke lokasi yang sesuai."""    
    os.chdir(directory)

def initialize_yolo_model(model_path):
    """Inisialisasi model YOLO."""
    return YOLO(model_path)

def initialize_camera(width=1280, height=720):
    """Inisialisasi kamera."""
    available_camera_index = []

    # Check for available cameras in indexes 1-11
    for i in range(10):
        cam = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cam.isOpened():
            available_camera_index.append(i)
            cam.release()
            break
        
    print(available_camera_index[-1])

    cam = cv2.VideoCapture(available_camera_index[-1], cv2.CAP_DSHOW)
    cam.set(3, width)
    cam.set(4, height)
    
    if not cam.isOpened():
        raise Exception("No camera detected")

    return cam

def initialize_text_to_speech_engine():
    """Inisialisasi engine text-to-speech."""
    return pyttsx3.init()

def reset_feedback_count(feedback_dict):
    """Mereset dictionary feedback_count."""
    feedback_dict.clear()

def main():
    # Mengatur direktori kerja
    set_working_directory(os.path.join(os.path.dirname(__file__)))

    # Inisialisasi model YOLO
    model = initialize_yolo_model("LastTrain.pt")

    # Daftar nama kelas yang dikenali
    classNames = ["Afdhol Dzikri", "Bagas Hilmi", "Fahmi Aziz", "Iqbal Dufriandes", "Marco Philips Sirait", "Unknown Face"]

    # Inisialisasi kamera
    cam = initialize_camera(1280, 720)

    # Inisialisasi engine text-to-speech
    engine = initialize_text_to_speech_engine()

    # Konfigurasi reset feedback
    reset_time = time.time()
    reset_duration = 30  # 10 menit (600 detik)
    feedback_count = {}
    exit_key = 27  # Key code for 'q'

    connection = connect(
        host="localhost",
        user="root",
        password="",
        database="db_facerec"
    )

    # Create a cursor object to interact with the database
    cursor = connection.cursor()

    while True:
        current = time.time()

        # Membaca frame dari kamera
        success, img = cam.read()

        # Keluar dari loop jika tidak berhasil atau tombol 'q' ditekan
        if not success or cv2.waitKey(1) & 0xFF == exit_key:
            break

        # Periksa apakah sudah waktunya untuk mereset feedback_count
        if current - reset_time >= reset_duration:
            reset_feedback_count(feedback_count)
            reset_time = current  # Perbarui waktu reset

        # Deteksi objek menggunakan model YOLO
        results = model(img, stream=True)

        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Mendapatkan koordinat bounding box
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                # Menghitung kepercayaan deteksi
                conf = math.ceil((box.conf[0] * 100)) / 100
                float(conf)

                # Mendapatkan nama kelas
                cls = int(box.cls[0])

                if conf < 0.65:
                    cls = len(classNames) - 1  # Set class to "Unknown" yang merupakan kelas terakhir

                    # Menambahkan kotak bounding-box dan teks peringatan untuk kelas yang tidak dikenali
                    w, h = x2 - x1, y2 - y1
                    cvzone.cornerRect(img,
                                      (x1, y1, w, h),
                                      l=32, t=7, rt=3,
                                      colorR=(0, 0, 0), colorC=(0, 0, 255)
                                      )
                    cvzone.putTextRect(img,
                                       f'{classNames[cls]} {conf}',
                                       (max(0, x1), max(35, y1)),
                                       scale=3, thickness=2,
                                       colorT=(255, 255, 255), colorR=(139, 0, 0)
                                       )
                    if classNames[cls] not in feedback_count or feedback_count[classNames[cls]] < 2:
                        engine.say("Unknown")
                        engine.runAndWait()
                        # Memperbarui jumlah feedback untuk kelas ini
                        feedback_count[classNames[cls]] = feedback_count.get(classNames[cls], 0) + 1

                else:
                    # Menambahkan kotak bounding-box dan teks untuk kelas yang dikenali
                    w, h = x2 - x1, y2 - y1
                    cvzone.cornerRect(img,
                                      (x1, y1, w, h),
                                      l=32, t=7, rt=3,
                                      colorR=(255, 0, 0), colorC=(0, 255, 0)
                                      )
                    cvzone.putTextRect(img,
                                       f'{classNames[cls]} {conf}',
                                       (max(0, x1), max(35, y1)),
                                       scale=3, thickness=2,
                                       colorT=(255, 255, 255), colorR=(0, 0, 139)
                                       )
                    if classNames[cls] not in feedback_count or feedback_count[classNames[cls]] < 1:
                        engine.say(f"Hello, {classNames[cls]}")
                        engine.runAndWait()
                        # Memperbarui jumlah feedback untuk kelas ini
                        feedback_count[classNames[cls]] = feedback_count.get(classNames[cls], 0) + 1
                        print(classNames[cls], x1, y1, w, h, conf)
                        insert_detection_to_database(cursor, classNames[cls], x1, y1, w, h, conf)
                        connection.commit()

        ret, buffer = cv2.imencode('.jpg', img)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    # Menutup kamera dan jendela tampilan
    cam.release()
    cv2.destroyAllWindows()
    
    cursor.close()
    connection.close()

# Run the program
if __name__ == "__main__":
    main()
