"""
Handy Sync - Flet version (English)
Final + Tray + Opacity + NoConsole + Status Bar
"""
import sys
import os
from pathlib import Path

# ---------- Log Redirect ----------
if sys.stdout is None or sys.stderr is None:
    try:
        _log_path = Path.home() / ".handy_sync.log"
        if _log_path.exists() and _log_path.stat().st_size > 2 * 1024 * 1024:
            _log_path.unlink()
        _log_file = open(_log_path, "a", encoding="utf-8", buffering=1)
        if sys.stdout is None: sys.stdout = _log_file
        if sys.stderr is None: sys.stderr = _log_file
    except Exception:
        if sys.stdout is None: sys.stdout = open(os.devnull, "w")
        if sys.stderr is None: sys.stderr = open(os.devnull, "w")
# ----------------------------------

import asyncio
import ctypes
import json
import math
import threading
import time

import flet as ft
import requests

try:
    from pynput import mouse
    HAS_MOUSE = True
except ImportError:
    HAS_MOUSE = False

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

CONFIG_PATH = Path.home() / ".handy_sync_config.json"

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_config(data: dict):
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------- PotPlayer ----------
user32 = ctypes.windll.user32
WM_USER = 0x0400
POT_GET_CURRENT_TIME = 0x5004
POT_GET_TOTAL_TIME = 0x5002
POT_GET_PLAY_STATUS = 0x5006

def find_potplayer() -> int:
    for cls in ("PotPlayer64", "PotPlayer"):
        hwnd = user32.FindWindowW(cls, None)
        if hwnd:
            return hwnd
    return 0

def get_title(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if not length:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value

def get_potplayer_state(hwnd: int) -> dict:
    status = user32.SendMessageW(hwnd, WM_USER, POT_GET_PLAY_STATUS, 0)
    current = user32.SendMessageW(hwnd, WM_USER, POT_GET_CURRENT_TIME, 0)
    total = user32.SendMessageW(hwnd, WM_USER, POT_GET_TOTAL_TIME, 0)
    title = get_title(hwnd)
    filename = title.split(" - PotPlayer")[0].strip() if " - PotPlayer" in title else ""
    return {"filename": filename, "current_ms": current, "total_ms": total, "status": status}

# ---------- Handy ----------
class HandyClient:
    def __init__(self, connection_key: str):
        self.key = connection_key
        self.base = "https://www.handyfeeling.com/api/handy/v2"
        self.session = requests.Session()
        self.session.headers.update({
            "X-Connection-Key": connection_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self.client_server_offset = 0
        self.last_rtt_ms = 0

    def _put(self, path: str, data: dict | None = None) -> dict:
        r = self.session.put(f"{self.base}/{path}", json=data or {}, timeout=15)
        r.raise_for_status()
        return r.json()

    def setup_script(self, url: str):
        return self._put("hssp/setup", {"url": url})

    def play(self, start_ms: int, estimated_server_time: int):
        return self._put("hssp/play", {"startTime": start_ms, "estimatedServerTime": estimated_server_time})

    def set_slide(self, min_pct: int, max_pct: int):
        return self._put("slide", {"min": min_pct, "max": max_pct})

    def get_server_time(self) -> int:
        r = self.session.get(f"{self.base}/servertime", timeout=5)
        r.raise_for_status()
        return r.json().get("serverTime", int(time.time() * 1000))

    def measure_time_offset(self, samples: int = 6) -> tuple[int, int]:
        offsets, rtts = [], []
        for _ in range(samples):
            t_send = time.time() * 1000
            server_time = self.get_server_time()
            t_recv = time.time() * 1000
            rtt = t_recv - t_send
            offsets.append(server_time + rtt / 2 - t_recv)
            rtts.append(rtt)
        if len(offsets) >= 4:
            offsets.sort(); offsets = offsets[1:-1]
            rtts.sort(); rtts = rtts[1:-1]
        self.client_server_offset = int(sum(offsets) / len(offsets))
        self.last_rtt_ms = int(sum(rtts) / len(rtts))
        return self.client_server_offset, self.last_rtt_ms

    def estimated_server_time(self) -> int:
        return int(time.time() * 1000 + self.client_server_offset)

def upload_script_to_handy(script_path: str) -> str:
    upload_url = "https://www.handyfeeling.com/api/hosting/v2/upload"
    with open(script_path, "rb") as f:
        files = {"file": (os.path.basename(script_path), f, "application/json")}
        r = requests.post(upload_url, files=files, timeout=60)
        r.raise_for_status()
        data = r.json()
        if "url" in data:
            return data["url"]
        if isinstance(data.get("result"), dict) and "url" in data["result"]:
            return data["result"]["url"]
        raise RuntimeError(f"Upload response missing url: {data}")

# ---------- App ----------
def main(page: ft.Page):
    page.title = "Handy Sync"
    page.window.width = 280
    page.window.height = 330
    page.window.min_width = 280
    page.window.min_height = 200
    page.window.resizable = True
    page.window.always_on_top = True
    page.window.title_bar_hidden = True
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.spacing = 0

    event_queue = asyncio.Queue()

    state = {
        "folder": "",
        "key": "",
        "handy": None,
        "loaded_scripts": {},
        "delay_presets": {"Speaker": 0, "Wireless": 150},
        "current_delay_preset": "Speaker",
        "stroke_presets": {"Full": (0, 100), "Short": (20, 80), "Mid": (30, 70)},
        "current_stroke": "Full",
        "sync_shortcut": "X1",
        "tune_value": 0,
        "opacity": 1.0,
        "conn_status": "disconnected",
        "sync_status": "idle",
        "sync_msg": "",
        "sync_status_at": 0.0,
    }

    tray_icon = None

    def save():
        save_config({
            "folder": state["folder"], "key": state["key"],
            "delay_presets": state["delay_presets"],
            "current_delay_preset": state["current_delay_preset"],
            "stroke_presets": state["stroke_presets"],
            "current_stroke": state["current_stroke"],
            "sync_shortcut": state["sync_shortcut"],
            "opacity": state["opacity"],
        })

    def load():
        cfg = load_config()
        state["folder"] = cfg.get("folder", "")
        state["key"] = cfg.get("key", "")
        if "delay_presets" in cfg: state["delay_presets"] = cfg["delay_presets"]
        if "stroke_presets" in cfg:
            state["stroke_presets"] = {k: tuple(v) for k, v in cfg["stroke_presets"].items()}
        state["current_delay_preset"] = cfg.get("current_delay_preset", "Speaker")
        state["current_stroke"] = cfg.get("current_stroke", "Full")
        state["sync_shortcut"] = cfg.get("sync_shortcut", "X1")
        state["tune_value"] = state["delay_presets"].get(state["current_delay_preset"], 0)
        state["opacity"] = cfg.get("opacity", 1.0)

    load()
    page.window.opacity = state["opacity"]

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    # --- UI Controls ---
    lbl_file = ft.Text("No video", size=11, weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
    lbl_time = ft.Text("--:--", size=11, color=ft.Colors.GREY_400)
    lbl_conn = ft.Text("● Disconnected", size=11, color=ft.Colors.GREY_500)
    lbl_sync = ft.Text("● Ready", size=11, color=ft.Colors.GREY_500)

    dd_delay = ft.Dropdown(
        options=[ft.dropdown.Option(k) for k in state["delay_presets"]],
        value=state["current_delay_preset"], width=260, height=40, text_size=12,
        content_padding=5, on_select=lambda e: on_delay_change(e),
    )

    tune_field = ft.TextField(
        value=str(state["tune_value"]), width=60, height=30, text_size=12,
        content_padding=5, text_align=ft.TextAlign.CENTER
    )

    main_content = ft.Column(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)

    def show_snack(msg):
        page.snack_bar = ft.SnackBar(content=ft.Text(msg, size=12))
        page.snack_bar.open = True
        page.update()

    # --- Status helpers ---
    def update_status_ui():
        cs = state["conn_status"]
        if cs == "connected":
            lbl_conn.value = "● Connected"; lbl_conn.color = ft.Colors.GREEN_400
        elif cs == "connecting":
            lbl_conn.value = "● Connecting..."; lbl_conn.color = ft.Colors.AMBER_400
        elif cs == "error":
            lbl_conn.value = "● Connection failed"; lbl_conn.color = ft.Colors.RED_400
        else:
            lbl_conn.value = "● Disconnected"; lbl_conn.color = ft.Colors.GREY_500

        ss = state["sync_status"]
        if ss == "syncing":
            lbl_sync.value = "● Syncing..."; lbl_sync.color = ft.Colors.AMBER_400
        elif ss == "ok":
            lbl_sync.value = "● Synced"; lbl_sync.color = ft.Colors.GREEN_400
        elif ss == "error":
            msg = state["sync_msg"] or "Sync failed"
            lbl_sync.value = f"● {msg}"; lbl_sync.color = ft.Colors.RED_400
        else:
            lbl_sync.value = "● Ready"; lbl_sync.color = ft.Colors.GREY_500

        try: page.update()
        except Exception: pass

    def set_conn_status(s):
        state["conn_status"] = s
        update_status_ui()

    def set_sync_status(s, msg=""):
        state["sync_status"] = s
        state["sync_msg"] = msg
        if s in ("ok", "error"):
            state["sync_status_at"] = time.time()
        update_status_ui()

    # --- Tray ---
    def setup_tray():
        nonlocal tray_icon
        if not HAS_TRAY:
            print("[LOG] pystray or pillow not found")
            return
        image = Image.new('RGB', (64, 64), color=(30, 30, 30))
        d = ImageDraw.Draw(image)
        d.ellipse([16, 16, 48, 48], fill=(0, 150, 255))
        d.rectangle([28, 12, 36, 52], fill=(30, 30, 30))

        def show_from_tray(icon=None, item=None):
            async def _show():
                try:
                    page.window.visible = True
                    await page.window.to_front()
                    page.update()
                except Exception as ex: print(f"[LOG] Show error: {ex}")
            asyncio.run_coroutine_threadsafe(_show(), page.loop)

        def quit_from_tray(icon=None, item=None):
            if tray_icon:
                try: tray_icon.stop()
                except: pass
            os._exit(0)

        menu = pystray.Menu(
            pystray.MenuItem("Show", show_from_tray, default=True),
            pystray.MenuItem("Exit", quit_from_tray)
        )
        tray_icon = pystray.Icon("HandySync", image, "Handy Sync", menu)
        threading.Thread(target=tray_icon.run, daemon=True).start()

    def hide_to_tray(e=None):
        if not HAS_TRAY:
            show_snack("pystray not installed")
            return
        page.window.visible = False
        page.update()

    # --- Logic ---
    def on_delay_change(e):
        state["current_delay_preset"] = e.control.value
        state["tune_value"] = state["delay_presets"].get(state["current_delay_preset"], 0)
        tune_field.value = str(state["tune_value"])
        page.update()

    def update_tune_field(delta):
        try:
            val = int(tune_field.value) + delta
            tune_field.value = str(val)
            page.update()
        except ValueError: pass

    def apply_tune(e=None):
        try:
            val = int(tune_field.value)
            state["delay_presets"][state["current_delay_preset"]] = val
            state["tune_value"] = val
            save()
            do_sync()
        except ValueError:
            print("[LOG] Apply Tune failed")

    def do_sync(e=None):
        if not state["handy"] or not state["folder"]:
            set_sync_status("error", "Setup required")
            show_snack("Please configure settings first")
            return
        hwnd = find_potplayer()
        if not hwnd:
            set_sync_status("error", "PotPlayer not found")
            show_snack("PotPlayer not found")
            return
        st = get_potplayer_state(hwnd)
        filename = st["filename"]
        if not filename:
            set_sync_status("error", "No video")
            show_snack("No video")
            return
        script_path = Path(state["folder"]) / (Path(filename).stem + ".funscript")
        if not script_path.exists():
            set_sync_status("error", "Script not found")
            show_snack(f"{script_path.name} not found")
            return
        try:
            set_sync_status("syncing")
            if filename not in state["loaded_scripts"]:
                url = upload_script_to_handy(str(script_path))
                state["loaded_scripts"][filename] = url
                state["handy"].setup_script(url)
            mn, mx = state["stroke_presets"].get(state["current_stroke"], (0, 100))
            state["handy"].set_slide(mn, mx)
            hwnd = find_potplayer()
            video_pos = get_potplayer_state(hwnd)["current_ms"]
            offset = state["delay_presets"].get(state["current_delay_preset"], 0)
            compensation = state["handy"].last_rtt_ms // 2
            state["handy"].play(video_pos + compensation + offset, state["handy"].estimated_server_time())
            set_sync_status("ok")
            show_snack("Sync successful")
        except Exception as ex:
            print(f"[LOG] Sync error: {ex}")
            err_lower = str(ex).lower()
            if "connection" in err_lower or "timeout" in err_lower or "retries" in err_lower:
                set_conn_status("error")
            set_sync_status("error", "Sync failed")
            show_snack(f"Sync error: {ex}")

    def reconnect(e=None):
        set_conn_status("connecting")
        if not state["key"]:
            set_conn_status("error")
            show_snack("Please set connection key first")
            return
        try:
            state["handy"] = HandyClient(state["key"])
            _, rtt = state["handy"].measure_time_offset()
            set_conn_status("connected")
            show_snack(f"Connected RTT: {rtt} ms")
        except Exception as ex:
            print(f"[LOG] Connect failed: {ex}")
            set_conn_status("error")
            show_snack(f"Error: {ex}")

    def select_stroke(name: str):
        state["current_stroke"] = name
        do_sync()

    # --- Pages ---
    def show_home():
        page.window.height = 330
        main_content.controls.clear()
        tune_row = ft.Row([
            ft.Text("Tune", size=12),
            ft.IconButton(ft.Icons.REMOVE, on_click=lambda e: update_tune_field(-10), icon_size=16, height=30, width=30, padding=0),
            tune_field,
            ft.IconButton(ft.Icons.ADD, on_click=lambda e: update_tune_field(10), icon_size=16, height=30, width=30, padding=0),
            ft.IconButton(ft.Icons.CHECK, on_click=apply_tune, icon_size=18, height=30, width=30, padding=0, icon_color=ft.Colors.GREEN_400),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=2)

        status_col = ft.Column([lbl_conn, lbl_sync], spacing=2, tight=True)

        btn_row = ft.Row([
            ft.IconButton(ft.Icons.SYNC, tooltip="Sync", on_click=do_sync, icon_size=24, width=40, height=40, padding=0),
            ft.IconButton(ft.Icons.WIFI, tooltip="Connect", on_click=reconnect, icon_size=24, width=40, height=40, padding=0),
            ft.IconButton(ft.Icons.SETTINGS, tooltip="Settings", on_click=lambda e: show_settings(), icon_size=24, width=40, height=40, padding=0),
            ft.IconButton(ft.Icons.GAMEPAD, tooltip="Stroke", on_click=lambda e: show_stroke(), icon_size=24, width=40, height=40, padding=0),
        ], alignment=ft.MainAxisAlignment.SPACE_EVENLY)

        main_content.controls.extend([
            lbl_file, lbl_time, dd_delay,
            ft.Divider(height=1), tune_row,
            ft.Divider(height=1), status_col,
            btn_row,
        ])
        page.update()

    def show_stroke():
        num_items = len(state["stroke_presets"])
        rows = math.ceil(num_items / 2)
        page.window.height = max(100 + (rows * 43), 160)
        main_content.controls.clear()
        grid = ft.GridView(expand=1, runs_count=2, max_extent=120, child_aspect_ratio=3.0, spacing=8, run_spacing=8)
        for name in state["stroke_presets"]:
            grid.controls.append(ft.Button(name, on_click=lambda e, n=name: select_stroke(n), height=35,
                style=ft.ButtonStyle(padding=0, text_style=ft.TextStyle(size=12))))
        main_content.controls.extend([
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_home(), icon_size=20, width=30, height=30, padding=0),
                ft.Text("Stroke Presets", size=12, weight=ft.FontWeight.BOLD),
            ]), grid,
        ])
        page.update()

    def show_settings():
        page.window.height = 380
        main_content.controls.clear()
        folder_field = ft.TextField(label="Folder", value=state["folder"], text_size=12, height=45, content_padding=8, expand=True)
        key_field = ft.TextField(label="Connection key", value=state["key"], password=True, text_size=12, height=45, content_padding=8)

        async def browse_folder(e):
            path = await file_picker.get_directory_path()
            if path:
                folder_field.value = path
                page.update()

        dd_shortcut = ft.Dropdown(
            options=[ft.dropdown.Option("X1"), ft.dropdown.Option("X2"), ft.dropdown.Option("Ctrl+Alt+S")],
            value=state["sync_shortcut"], label="Shortcut",
            width=240, height=45, text_size=12, content_padding=5,
        )
        opacity_slider = ft.Slider(min=0.4, max=1.0, divisions=6, label="{value}", value=state["opacity"], expand=True)

        def on_opacity_change(e):
            val = round(e.control.value, 1)
            state["opacity"] = val
            page.window.opacity = val
            page.update()
        opacity_slider.on_change = on_opacity_change

        def save_settings(e):
            state["folder"] = folder_field.value.strip()
            state["key"] = key_field.value.strip()
            state["sync_shortcut"] = dd_shortcut.value
            state["opacity"] = opacity_slider.value
            if state["key"]:
                state["handy"] = HandyClient(state["key"])
            save()
            setup_global_hotkeys()
            show_snack("Saved")
            show_home()

        main_content.controls.extend([
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_home(), icon_size=20, width=30, height=30, padding=0),
                ft.Text("Settings", size=14, weight=ft.FontWeight.BOLD),
            ]),
            ft.Row([folder_field,
                ft.IconButton(ft.Icons.FOLDER_OPEN, tooltip="Select folder", on_click=browse_folder, icon_size=20, width=40, height=40, padding=0),
            ], alignment=ft.MainAxisAlignment.START, spacing=5),
            key_field, dd_shortcut,
            ft.Row([ft.Text("Opacity", size=12, width=50), opacity_slider], alignment=ft.MainAxisAlignment.START),
            ft.Button("Manage Strokes", on_click=lambda e: show_stroke_manage(), height=35,
                style=ft.ButtonStyle(text_style=ft.TextStyle(size=12), padding=0)),
            ft.Button("Save", on_click=save_settings, height=35,
                style=ft.ButtonStyle(text_style=ft.TextStyle(size=12), padding=0)),
        ])
        page.update()

    def show_stroke_manage():
        page.window.height = 320
        main_content.controls.clear()
        list_view = ft.ListView(expand=1, spacing=4)

        def refresh_list():
            list_view.controls.clear()
            for name, (mn, mx) in state["stroke_presets"].items():
                list_view.controls.append(ft.Row([
                    ft.Text(f"{name}: {mn}-{mx}", size=12, expand=True),
                    ft.IconButton(ft.Icons.DELETE, data=name, on_click=delete_stroke, icon_size=16,
                        width=30, height=30, padding=0, icon_color=ft.Colors.RED_400)
                ]))
            page.update()

        def delete_stroke(e):
            name = e.control.data
            if name in state["stroke_presets"]:
                del state["stroke_presets"][name]
                if state["current_stroke"] == name:
                    state["current_stroke"] = "Full" if "Full" in state["stroke_presets"] else list(state["stroke_presets"].keys())[0]
                save()
                refresh_list()

        name_field = ft.TextField(label="Name", width=80, height=35, text_size=12, content_padding=5)
        min_field = ft.TextField(label="Min", width=60, height=35, text_size=12, content_padding=5, value="0")
        max_field = ft.TextField(label="Max", width=60, height=35, text_size=12, content_padding=5, value="100")

        def add_stroke(e):
            name = name_field.value.strip()
            try:
                mn = int(min_field.value); mx = int(max_field.value)
                if not name or not (0 <= mn <= 100) or not (0 <= mx <= 100) or mn >= mx:
                    raise ValueError
                state["stroke_presets"][name] = (mn, mx)
                save(); refresh_list()
                name_field.value = ""; page.update()
            except ValueError:
                show_snack("Invalid value")

        refresh_list()
        main_content.controls.extend([
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: show_settings(), icon_size=20, width=30, height=30, padding=0),
                ft.Text("Manage Strokes", size=14, weight=ft.FontWeight.BOLD),
            ]),
            list_view,
            ft.Row([name_field, min_field, max_field,
                ft.IconButton(ft.Icons.ADD, on_click=add_stroke, icon_size=20, width=30, height=30,
                    padding=0, icon_color=ft.Colors.GREEN_400)]),
        ])
        page.update()

    # --- Right-click menu ---
    async def handle_right_click(e):
        async def close_app(e=None):
            if HAS_MOUSE and hasattr(page, "_mouse_listener"):
                try: page._mouse_listener.stop()
                except: pass
            if HAS_KEYBOARD:
                try: keyboard.unhook_all()
                except: pass
            if tray_icon:
                try: tray_icon.stop()
                except: pass
            try:
                await page.window.destroy()
            except Exception: pass
            os._exit(0)

        def toggle_topmost(e=None):
            page.window.always_on_top = not page.window.always_on_top
            page.update()

        menu_items = [
            ft.TextButton(f"Always on top: {'ON' if page.window.always_on_top else 'OFF'}", on_click=toggle_topmost)
        ]
        if HAS_TRAY:
            menu_items.append(ft.TextButton("Hide to Tray", on_click=hide_to_tray))
        menu_items.append(ft.TextButton("Exit", on_click=close_app))

        dlg = ft.AlertDialog(
            title=ft.Text("Menu", size=14),
            content=ft.Column(menu_items, tight=True),
            actions=[], actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    drag_area = ft.WindowDragArea(
        content=ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.DRAG_INDICATOR, size=16, color=ft.Colors.GREY_600),
                ft.Text("Handy Sync", size=10, color=ft.Colors.GREY_500),
            ], alignment=ft.MainAxisAlignment.CENTER),
            height=25, bgcolor="#00000054", alignment=ft.Alignment.CENTER,
        ), maximizable=False,
    )

    page.add(ft.GestureDetector(
        on_secondary_tap=handle_right_click,
        content=ft.Container(
            content=ft.Column([
                drag_area,
                ft.Container(content=main_content, padding=8, expand=True)
            ], spacing=0),
            expand=True,
        ), drag_interval=10,
    ))

    async def refresh_loop():
        while True:
            hwnd = find_potplayer()
            if hwnd:
                st = get_potplayer_state(hwnd)
                lbl_file.value = (st["filename"] or "No video")[:30]
                sec = st["current_ms"] // 1000
                lbl_time.value = f"{sec//60:02d}:{sec%60:02d}"
                page.update()
            if state["sync_status"] in ("ok", "error"):
                if time.time() - state["sync_status_at"] > 3.0:
                    set_sync_status("idle")
            await asyncio.sleep(1)

    async def process_events():
        while True:
            event = await event_queue.get()
            if event == "SYNC": do_sync()
            event_queue.task_done()

    def setup_global_hotkeys():
        if HAS_MOUSE and hasattr(page, "_mouse_listener"):
            try: page._mouse_listener.stop()
            except: pass
        if HAS_KEYBOARD:
            try: keyboard.unhook_all_hotkeys()
            except: pass
        shortcut = state["sync_shortcut"]
        if HAS_MOUSE and shortcut in ("X1", "X2"):
            target = mouse.Button.x1 if shortcut == "X1" else mouse.Button.x2
            def on_click(x, y, button, pressed):
                if pressed and button == target:
                    asyncio.run_coroutine_threadsafe(event_queue.put("SYNC"), page.loop)
            listener = mouse.Listener(on_click=on_click)
            listener.daemon = True
            listener.start()
            page._mouse_listener = listener
        if HAS_KEYBOARD and shortcut == "Ctrl+Alt+S":
            try:
                keyboard.add_hotkey("ctrl+alt+s", lambda: asyncio.run_coroutine_threadsafe(event_queue.put("SYNC"), page.loop))
            except Exception as ex: print(f"[LOG] Hotkey error: {ex}")

    # --- Init ---
    show_home()
    setup_global_hotkeys()
    setup_tray()

    if state["key"]:
        try:
            state["handy"] = HandyClient(state["key"])
            state["handy"].measure_time_offset()
            set_conn_status("connected")
        except Exception:
            set_conn_status("error")
    else:
        set_conn_status("disconnected")

    page.run_task(refresh_loop)
    page.run_task(process_events)

if __name__ == "__main__":
    ft.run(main)