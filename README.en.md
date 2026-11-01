# Handy Sync for PotPlayer

🌐 **Language:** [English](README.en.md) | [ภาษาไทย](README.md)

---

A modern desktop GUI application built with Python and Flet to synchronize **The Handy** with video playback on **PotPlayer** in real-time.

---

## ✨ Key Features

- **Real-time PotPlayer Synchronization**: Seamlessly detects playback states (Play/Pause) and exact playback positions (Current Time) via the Windows API.
- **Bilingual Support**: Includes both English (`handy_sync_flet_english.py`) and Thai (`handy_sync_flet_thai.py`) interface implementations.
- **System Tray Integration**: Minimize the application to the Windows system tray to keep your workspace clean.
- **Global Hotkeys & Mouse Wheel Controls**: Easily adjust stroke length, speed, and time offsets on the fly.
- **Adjustable Window Opacity**: Customize window transparency for unobtrusive overlaying.
- **Persistent Configuration**: Automatically saves your Handy Connection Key and preferred offset settings locally in your user profile.

---

## 📁 Project Structure

```text
├── handy_sync_flet_english.py  # English GUI source code
├── handy_sync_flet_thai.py     # Thai GUI source code
├── requirements.txt            # Python dependencies
├── icon.ico / .jpg / .png      # Application icons
├── README.md                   # Documentation in Thai
├── README.en.md                # Documentation in English
└── .gitignore                  # Git ignore rules for build artifacts & executables
```

---

## ⚙️ Tech Stack

- **Python 3**
- **[Flet](https://flet.dev/)**: Flutter-powered desktop GUI framework for Python
- **ctypes / Win32 API**: Low-level Windows messaging to inspect PotPlayer status
- **Requests**: Interacting with The Handy API v2 (HSSP sync & playback control)
- **pystray & Pillow**: System tray icon & menu management
- **keyboard & pynput**: Global keyboard shortcuts and mouse listeners

---

## 📥 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/fiwflash/handy-sync-potplayer.git
cd handy-sync-potplayer
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
- For **English** interface:
  ```bash
  python handy_sync_flet_english.py
  ```
- For **Thai** interface:
  ```bash
  python handy_sync_flet_thai.py
  ```

---

## 🚀 Quick Start Guide

1. Launch **PotPlayer** and start playing your video.
2. Launch the **Handy Sync** application.
3. Enter your **The Handy Connection Key**.
4. Click **Connect** — the app will automatically detect PotPlayer and sync with playback.
