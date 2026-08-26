import base64
import io
import json
import asyncio
import threading
import mss
import requests
from PIL import Image
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pynput import keyboard
import os

_loop: asyncio.AbstractEventLoop | None = None

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
config = {
    "hotkey": "<ctrl>+<alt>+a",
    "lm_studio_url": "http://localhost:1234/v1/chat/completions",
    "overlay_width_vw": 35,
    "overlay_opacity": 0.6
}

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r') as f:
            config.update(json.load(f))
    except Exception as e:
        print(f"[Warn] Config load failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _loop
    _loop = asyncio.get_running_loop()
    threading.Thread(target=hotkey_listener, daemon=True).start()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clients = set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    # Send config immediately
    await websocket.send_text(json.dumps({"type": "config", "data": config}))
    try:
        while True:
            await websocket.receive_text()
    except:
        clients.discard(websocket)

@app.post("/trigger")
async def trigger_capture():
    """HTTP fallback for Wayland (hotkeys don't work on raw Wayland)."""
    threading.Thread(target=capture_and_stream, daemon=True).start()
    return {"ok": True}

async def broadcast(message: str):
    for client in list(clients):
        try:
            await client.send_text(message)
        except:
            clients.discard(client)

def _send(message: str):
    """Thread-safe: schedule broadcast on FastAPI's event loop."""
    if _loop:
        asyncio.run_coroutine_threadsafe(broadcast(message), _loop)

def capture_and_stream():
    print("[Capture] Snapping screen...")
    b64_img = ""
    cap_file = "/tmp/odyssy_cap.png"

    # Method 1: mss (works on X11 and XWayland)
    try:
        with mss.mss() as sct:
            sct_img = sct.grab(sct.monitors[1])
            img_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
        b64_img = base64.b64encode(img_bytes).decode('utf-8')
        print("[Capture] mss OK")
    except Exception as e:
        print(f"[Capture] mss failed: {e}")

    # Method 2: gnome-screenshot (GNOME Wayland)
    if not b64_img:
        try:
            import subprocess
            subprocess.run(['gnome-screenshot', '-f', cap_file], check=True, timeout=5)
            with open(cap_file, 'rb') as f:
                b64_img = base64.b64encode(f.read()).decode('utf-8')
            print("[Capture] gnome-screenshot OK")
        except Exception as e:
            print(f"[Capture] gnome-screenshot failed: {e}")

    # Method 3: grim (wlroots Wayland: Sway, Hyprland)
    if not b64_img:
        try:
            import subprocess
            subprocess.run(['grim', cap_file], check=True, timeout=5)
            with open(cap_file, 'rb') as f:
                b64_img = base64.b64encode(f.read()).decode('utf-8')
            print("[Capture] grim OK")
        except Exception as e:
            print(f"[Capture] grim failed: {e}")

    # Method 4: scrot (X11 fallback)
    if not b64_img:
        try:
            import subprocess
            subprocess.run(['scrot', cap_file], check=True, timeout=5)
            with open(cap_file, 'rb') as f:
                b64_img = base64.b64encode(f.read()).decode('utf-8')
            print("[Capture] scrot OK")
        except Exception as e:
            print(f"[Capture] scrot failed: {e}")

    if not b64_img:
        print("[Error] All capture methods failed.")
        _send(json.dumps({"type": "error", "data": "Screen capture failed. Install gnome-screenshot (GNOME Wayland) or grim (wlroots."}))  
        return

    # Resize + compress to JPEG to keep payload under LM Studio limits
    try:
        img_bytes = base64.b64decode(b64_img)
        img = Image.open(io.BytesIO(img_bytes))
        max_dim = config.get("max_image_dim", 1280)
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=85)
        b64_img = base64.b64encode(buf.getvalue()).decode('utf-8')
        print(f"[Capture] Resized to {img.size}, JPEG {len(buf.getvalue())//1024}KB")
    except Exception as e:
        print(f"[Capture] Resize failed (sending original): {e}")

    try:
        payload = {
            "model": config.get("model", "local-model"),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Explain what's on this screen concisely."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                    ]
                }
            ],
            "temperature": 0.7,
            "max_tokens": 512,
            "stream": True
        }

        _send(json.dumps({"type": "status", "data": "Thinking..."}))

        with requests.post(config["lm_studio_url"], json=payload, stream=True, timeout=120) as r:
            if r.status_code != 200:
                _send(json.dumps({"type": "error", "data": f"LM Studio error: {r.status_code}"}))
                return

            for line in r.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: ") and decoded != "data: [DONE]":
                        try:
                            chunk = json.loads(decoded[6:])
                            delta = chunk["choices"][0]["delta"]
                            print(f"[Stream] delta keys: {list(delta.keys())}")  # debug

                            # Standard content (non-thinking models)
                            text = delta.get("content") or ""
                            # Thinking models (Qwen3, QwQ, etc.) use reasoning_content
                            reasoning = delta.get("reasoning_content") or ""
                            token = reasoning + text

                            if token:
                                _send(json.dumps({"type": "token", "data": token}))
                        except:
                            pass
        _send(json.dumps({"type": "done"}))
    except requests.exceptions.RequestException as req_err:
        print(f"[Error] Network: {req_err}")
        _send(json.dumps({"type": "error", "data": "Cannot reach LM Studio. Is it running?"}))
    except Exception as e:
        print(f"[Error] {e}")
        _send(json.dumps({"type": "error", "data": str(e)}))

def on_activate():
    import threading
    threading.Thread(target=capture_and_stream, daemon=True).start()

def hotkey_listener():
    hotkey = config["hotkey"]
    print(f"M5 Server running. Press {hotkey} to capture.")
    with keyboard.GlobalHotKeys({hotkey: on_activate}) as h:
        h.join()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
