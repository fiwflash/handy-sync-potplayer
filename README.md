# Handy Sync for PotPlayer

แอปพลิเคชัน GUI (สร้างด้วย Python + Flet) สำหรับเชื่อมต่อและควบคุมการทำงานของ The Handy ให้ซิงค์กับการเล่นวิดีโอบน PotPlayer อัตโนมัติแบบเรียลไทม์

---

## ✨ ฟีเจอร์หลัก (Features)

- **Sync กับ PotPlayer แบบเรียลไทม์**: ตรวจจับสถานะการเล่น (Play/Pause) และตำแหน่งเวลา (Current Position) ของ PotPlayer ผ่าน Windows API
- **รองรับทั้งสองภาษา**: มีโค้ดทั้งภาษาไทย (`handy_sync_flet_thai.py`) และภาษาอังกฤษ (`handy_sync_flet_english.py`)
- **System Tray Support**: ย่อโปรแกรมลง System Tray ที่มุมขวาล่างได้ ไม่รบกวนหน้าจอ
- **Hotkeys & Mouse Controls**: รองรับปุ่มลัดคีย์บอร์ดและการควบคุมผ่านเมาส์ (เช่น ปรับ Stroke / Speed / Offset)
- **ปรับแต่งความโปร่งใส (Opacity)**: สามารถปรับหน้าต่างให้โปร่งใสขณะใช้งานได้
- **บันทึกการตั้งค่าอัตโนมัติ**: บันทึกค่า Connection Key และ Offset ล่าสุดไว้ที่ User Profile

---

## 📁 โครงสร้างโปรเจกต์ (Project Structure)

```text
├── handy_sync_flet_thai.py     # Source code ภาษาไทย
├── handy_sync_flet_english.py  # Source code ภาษาอังกฤษ
├── requirements.txt            # รายการ Dependencies สำหรับ Python
├── icon.ico / .jpg / .png      # ไอคอนของโปรแกรม
└── .gitignore                  # กรองไฟล์ build, executable (.exe) และ backup
```

---

## ⚙️ เทคโนโลยีที่ใช้ (Tech Stack)

- **Python 3**
- **[Flet](https://flet.dev/)**: Framework พัฒนา Desktop GUI ด้วย Flutter engine
- **ctypes / Win32 API**: สื่อสารและดึงสถานะจาก Process ของ PotPlayer
- **Requests**: จัดการ HTTP API เรียกคำสั่งไปยัง The Handy API (v2)
- **pystray & Pillow**: จัดการ System Tray และ Icon
- **keyboard & pynput**: จัดการ Global Hotkeys / Mouse events

---

## 📥 วิธีติดตั้งและรันโปรเจกต์ (Getting Started)

### 1. Clone Repository
```bash
git clone https://github.com/fiwflash/handy-sync-potplayer.git
cd handy-sync-potplayer
```

### 2. ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
```

### 3. รันโปรแกรม
- สำหรับเวอร์ชันภาษาไทย:
  ```bash
  python handy_sync_flet_thai.py
  ```
- สำหรับเวอร์ชันภาษาอังกฤษ:
  ```bash
  python handy_sync_flet_english.py
  ```

---

## 🚀 วิธีใช้งานเบื้องต้น

1. เปิดเครื่องเล่น **PotPlayer** แล้วเล่นวิดีโอที่ต้องการ
2. เปิดโปรแกรม **Handy Sync**
3. ใส่ **Connection Key** ของเครื่อง The Handy
4. กดเชื่อมต่อ โปรแกรมจะค้นหา PotPlayer และเริ่มซิงค์อัตโนมัติ
