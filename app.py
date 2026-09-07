from flask import Flask, render_template, request, redirect, flash
from datetime import datetime
import os
import requests
import gspread
import json  # เพิ่มระบบอ่านข้อความกุญแจดิจิทัล
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
app.secret_key = "super_secret_key_for_flash_messages"

# 🔑 ตั้งค่าระบบส่งข้อมูลหาบอทหลายตัวพร้อมกัน (แบบที่ 1)
TELEGRAM_BOTS = [
    {
        'token': 'ว่าง', 
        'chat_id': 'ว่าง'
    },  # 👤 บอทตัวที่ 1 (ของคุณเดิม)
    {
        'token': '8870626887:AAHATmusjdF7G34VE2yRUpKVT2mrZ0d8Vyk', 
        'chat_id': '8638315134'
    },  # 👥 เจ บอทตัวที่ 2 (อย่าลืมใส่เครื่องหมายคอมม่าคั่นตรงท้ายบรรทัดนี้ด้วยนะครับ)
    {
        'token': '8954632792:AAHWbeFnBZW50Pjpt69wcu4p2iUdwLKj5i8', 
        'chat_id': '5343949498'
    }   # 🤖 พี่เกรท บอทตัวที่ 3 (ที่เพิ่มเข้ามาใหม่)
]

GOOGLE_JSON_KEY = 'google_key.json' 
SPREADSHEET_NAME = 'Clockin1'

# 🗂️ รายชื่อพนักงานในระบบ
EMPLOYEE_DATA = {
    "170440": {"name": "บุญฤทธิ์ เสวตเวช (เป้)", "branch": "Marketing"},
    "070244": {"name": "จีรารัตน์ ผ่านสุวรรณ (จีปู)", "branch": "Marketing"},
    "040642": {"name": "เมธัส หุรินทร์ (ไมค์)", "branch": "Marketing"},
    "280637": {"name": "สุพรรษา มึอดทน (แหม่ม)", "branch": "Manager"},
    "301037": {"name": "ปภัสรา คำปลิว (ปอ)", "branch": "Admin"},
    "090447": {"name": "ศุภมาส วาระสิทธิ์ (ปู)", "branch": "Admin"},
    "290336": {"name": "จริญญา กุ่มประสิทธิ์ (นิว)", "branch": "Admin"},
    "180948": {"name": "ฑิฆัมพร นาคแก้ว (อิงค์)", "branch": "Admin"},
    "071233": {"name": "เสาวลักษณ์ ภูลังกา (เปิ้ล)", "branch": "Admin"},
    "030631": {"name": "ดาเวือน จวน (ดา)", "branch": "Admin"},
    "191044": {"name": "เจษฏา เสือไธสง (บอม)", "branch": "Admin"},
    "040343": {"name": "ปรเมษฐ์ เนตรประชา (บิว)", "branch": "Admin"},
    "220140": {"name": "ขวัญวิไล ดวงศรี (ปาเก้)", "branch": "Admin"},
    "031142": {"name": "ปรมัทถ์ อับดุลเลาะ (ปอนด์)", "branch": "Marketing Manager"},
    "220435": {"name": "ปวิตร มณเฑียรประเสริฐ (เอ็ม)", "branch": "Manager"},
    "121240": {"name": "อัครเดช พุทธชัย (มอส)", "branch": "Manager"},
    "071222": {"name": "สุกฤษฎิ์ เร่บ้านเกาะ (แพท)", "branch": "Supervisor"},
    "031035": {"name": "ศศิรินทร์ พิทักษรัตนมณี (เกรท)", "branch": "Supervisor"},
    "170833": {"name": "ภุชงค์ แจ่มโชว์ (กัส)", "branch": "Supervisor"}
}

def append_to_google_sheet(row_data):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # 🛡️ ส่วนที่แก้ไข: เช็คว่าถ้าอยู่บน Render ให้ดึงกุญแจจาก Environment ถ้าอยู่ในคอมให้ดึงจากไฟล์
        google_key_env = os.environ.get('GOOGLE_JSON_KEY')
        
        if google_key_env:
            # ใช้กุญแจจากหน้าเว็บ Render
            key_data = json.loads(google_key_env)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(key_data, scope)
        else:
            # ใช้กุญแจจากไฟล์ในคอมพิวเตอร์ของคุณ
            creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_KEY, scope)
            
        client = gspread.authorize(creds)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        sheet.append_row(row_data)
    except Exception as e:
        print("บันทึกลง Google Sheets ไม่สำเร็จ:", e)

def send_telegram_notify(message, image_path=None):
    try:
        # 🔄 วนลูปสั่งให้บอททุกตัวที่ระบุไว้ใน TELEGRAM_BOTS ส่งข้อความออกไปพร้อมกัน
        for bot in TELEGRAM_BOTS:
            token = bot['token']
            chat_id = bot['chat_id']
            
            # ตรวจสอบว่าคนเซ็ตตั้งค่าข้ามข้อความเริ่มต้นหรือยัง
            if 'ใส่_TOKEN_' in token or 'ใส่_CHAT_ID_' in chat_id:
                continue
                
            if image_path and os.path.exists(image_path):
                url = f"https://api.telegram.org/bot{token}/sendPhoto"
                files = {'photo': open(image_path, 'rb')}
                data = {'chat_id': chat_id, 'caption': message}
                requests.post(url, files=files, data=data)
            else:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {'chat_id': chat_id, 'text': message}
                requests.post(url, data=data)
    except Exception as e:
        print("ส่ง Telegram ไม่สำเร็จ:", e)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/clock', methods=['POST'])
def clock():
    emp_id = request.form.get('emp_id')
    action = request.form.get('action')
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    display_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    photo = request.files.get('photo')
    
    if emp_id and photo:
        if emp_id not in EMPLOYEE_DATA:
            flash(f"❌ รหัสพนักงาน [{emp_id}] ไม่ถูกต้อง! กรุณาตรวจสอบและลองใหม่อีกครั้ง", "danger")
            return redirect('/')
            
        emp_name = EMPLOYEE_DATA[emp_id]["name"]
        emp_branch = EMPLOYEE_DATA[emp_id]["branch"]
            
        UPLOAD_FOLDER = 'static/uploads'
        if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
        
        file_extension = os.path.splitext(photo.filename)[1]
        filename = f"{emp_id}_{action}_{current_time}{file_extension}"
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        photo.save(image_path)
        
        row_data = [emp_id, emp_name, emp_branch, action, display_time, filename]
        append_to_google_sheet(row_data)
        
        telegram_message = f"⏱️ มีพนักงานลงเวลา\n📌 รหัสพนักงาน: {emp_id}\n👤 ชื่อ: {emp_name}\n🏢 ตำแหน่ง: {emp_branch}\n🔄 ทำการ: {action}\n⏰ เวลา: {display_time}"
        send_telegram_notify(telegram_message, image_path)
        
        flash(f"🎉 บันทึก [{action}] สำเร็จ!\n👤 คุณ: {emp_name}\n⏰ เวลา: {display_time}", "success")
            
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
