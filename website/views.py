from flask import Blueprint, render_template, Response, session, redirect, url_for, request, json
from . import DatabaseOperations as db
from passlib.hash import sha256_crypt
from threading import Thread
from datetime import datetime
from . import main
import cv2
import os
import time

#VARIABEL UMUM/GLOBAL & DEKLARASI APP/VIEWS
views = Blueprint('views', __name__)

database = db('localhost', 'root', '', 'db_facerec')
interval = 0.5
##############################################################################################################


#FUNGSI-FUNGSI DETEKSI & AMBIL DATA
main()
def generate_frames():
    global cap, save_path, file_name

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Save the frame to the dataset folder
        cv2.imwrite(os.path.join(save_path, file_name + f"-{int(time.time())}.png"), frame)

        # Convert the frame to JPEG and send it to the web page
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        # Wait for the specified interval before capturing the next frame
        time.sleep(interval)
##############################################################################################################


#HALAMAN HALAMAN DENGAN FUNGSI MENAMPILKAN/UTAMA
@views.route('/')
def home():
    if 'logged_in' in session:
        try:
            with database as cursor:
                # Execute your queries and fetch data here
                query_total = """
                SELECT COUNT(*) as total_pengguna FROM user;
                """
                cursor.execute(query_total)
                total_pengguna = cursor.fetchone()
                
                # Menghitung presentasi kehadiran hari ini
                hari_ini = datetime.now().strftime('%Y-%m-%d')

                query_presentasi = f"""
                    SELECT COUNT(*) as hadir_count
                    FROM kehadiran
                    WHERE DATE(created) = '{hari_ini}';
                """
                cursor.execute(query_presentasi)
                result_presentasi = cursor.fetchone()
                hadir_count = result_presentasi[0]
                
                presentasi_kehadiran = int((hadir_count / total_pengguna[0]) * 100) if total_pengguna[0] > 0 else 0
                
                query_statistik = f"""
                    SELECT COUNT(*) as hadir_count, created
                    FROM kehadiran
                    WHERE DATE(created) = '{hari_ini}'
                    GROUP BY created;
                """
                cursor.execute(query_statistik)
                statistik = cursor.fetchall()
                hadir_count_array = [row[0] for row in statistik]
                created_array = [row[1] for row in statistik]

                query_user = f"""
                    SELECT * from user
                """
                cursor.execute(query_user)
                users = cursor.fetchall()
                
        except Exception as e:
            print(f"Error: {e}")
        
        return render_template('admin/index.html', nama=session['nama'], username=session['username'], total_pengguna=total_pengguna, presentasi_kehadiran=presentasi_kehadiran, hadir=hadir_count_array, waktu=created_array, users=users)
    else:
        return redirect('/loginsignup')

@views.route('/history')
def history():
    if 'logged_in' in session:
        try:
            with database as cursor:
                # Execute your queries and fetch data here
                query = """
                SELECT kehadiran.*, user.nama, user.username, realtime.created, realtime.status
                FROM kehadiran
                LEFT JOIN realtime ON kehadiran.id_realtime = realtime.id                
                LEFT JOIN user ON realtime.id_user = user.id
                """
                cursor.execute(query)
                rows = cursor.fetchall()
        except Exception as e:
            print(f"Error: {e}")
            
        return render_template('admin/main_history.html',rows=rows, nama=session['nama'], username=session['username'])
    else:
        return redirect('/loginsignup')
    
@views.route('/update_kehadiran')
def update_kehadiran():
    try:
        with database as cursor:
            # Execute your queries and fetch data here
            query = """
            SELECT MAX(id_realtime) FROM kehadiran
            """
            cursor.execute(query)
            latest = cursor.fetchone()
            
            query_get = """
            SELECT * FROM realtime WHERE id > %s 
            """
            cursor.execute(query_get,(latest[0] or 0,))
            newest = cursor.fetchall()
            
            for data in newest:
                cursor.execute("INSERT INTO kehadiran (id_realtime) VALUES (%s)", (data[0],))
    
    except Exception as e:
        print(f"Error: {e}")
    
    return redirect('/history')
    
@views.route('/realtime')
def realtime():
    if 'logged_in' in session:
        try:
            with database as cursor:
                # Execute your queries and fetch data here
                query = """
                SELECT realtime.*, user.nama
                FROM realtime
                LEFT JOIN user ON realtime.id_user = user.id
                """
                cursor.execute(query)
                rows = cursor.fetchall()
        except Exception as e:
            print(f"Error: {e}")
        
        return render_template('admin/main_realtime.html', rows=rows, nama=session['nama'], username=session['username'])

    else:
        return redirect('/loginsignup')    
##############################################################################################################


#DETEKSI WEBCAM & AMBIL DATA
@views.route('/webcam')
def webcam():
    if 'logged_in' in session:
        return render_template('admin/detect_webcam.html', nama=session['nama'], username=session['username'])
    else:
        return redirect('/loginsignup')
    
@views.route('/videowebcam')
def videowebcam():
    return Response(main(),mimetype='multipart/x-mixed-replace; boundary=frame')

@views.route('/camdata')
def camdata():
    if 'logged_in' in session:
        return render_template('admin/detect_data.html', nama=session['nama'], username=session['username'])
    else:
        return redirect('/loginsignup')

@views.route('/startdata', methods=['POST'])
def startdata():
    global cap, save_path, file_name
    
    if 'logged_in' in session:
        # Get camera index from form
        camera_index = int(request.form['camera'])
        
        # Open the selected camera
        cap = cv2.VideoCapture(camera_index)

        # Check if the camera is opened successfully
        if not cap.isOpened():
            return "Error: Couldn't open the camera."

        # Set the save path for images
        static_path = os.path.join(os.path.dirname(__file__), 'static')
        save_path = os.path.join(static_path, 'images', 'dataset')
        
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        
        file_name = request.form['file_name']

        # Start capturing frames in a separate thread
        Thread(target=generate_frames).start()

        return render_template('admin/detect_data.html', nama=session['nama'], username=session['username'])    
    else:
        return redirect('/loginsignup')

@views.route('/videodata')
def videodata():
    return Response(generate_frames(),mimetype='multipart/x-mixed-replace; boundary=frame')

@views.route('/stopdata')
def stopdata():
    global cap
    
    if 'logged_in' in session:
        # Release the camera and return to the main page
        if cap:
            cap.release()
        return redirect('/camdata')
    else:
        return redirect('/loginsignup')
##############################################################################################################


#LOGIN, SIGN UP, & LOGOUT
@views.route('/loginsignup')
def loginsignup():
    return render_template('login.html')

@views.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if 'login' or 'signin' in request.form:
            # Handle login
            username = request.form['usr']
            password = request.form['pwd']

            # Query user from the database
            try:
                with database as cursor:
                    cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
                    user = cursor.fetchone()
                    
                    if user and sha256_crypt.verify(password, user[3]):
                        # Password matched, set session
                        session['logged_in'] = True
                        session['username'] = user[2]
                        session['nama'] = user[1]
                        print(session)
                        return redirect('/')
                    else:
                        # Password did not match
                        return render_template('login.html', error_message='Invalid login')
            except Exception as e:
                print(f"Error: {e}")
    return render_template('login.html')

@views.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'register' or 'signup' in request.form:
            # Handle signup
            username_up = request.form['usrup']
            print(username_up)
            password_up = request.form['pwdup']
            print(password_up)
            nama = request.form['nama']

            # Hash the password
            hashed_password = sha256_crypt.hash(password_up)

            try:
                with database as cursor:
                    cursor.execute("INSERT INTO user (nama, username, password) VALUES (%s,%s, %s)", (nama, username_up, hashed_password))
            except Exception as e:
                print(f"Error: {e}")
            # Insert user into the database
            
            return redirect('/loginsignup')   
    return render_template('login.html')

@views.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect('/loginsignup')
##############################################################################################################


#DETEKI KAMERA YANG ADA
@views.route('/get_available_cameras')
def get_available_cameras():
    available_cameras = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release()
    return {'available_cameras': available_cameras}