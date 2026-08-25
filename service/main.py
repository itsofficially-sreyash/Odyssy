import base64
import json
import asyncio
import mss
import requests
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pynput import keyboard

import os

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

app = FastAPI()
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
        clients.remove(websocket)

async def broadcast(message: str):
    for client in list(clients):
        try:
            await client.send_text(message)
        except:
            clients.remove(client)

def capture_and_stream():
    print("[Capture] Snapping screen...")
    b64_img = ""
    try:
        # Try mss (X11 / Windows)
        with mss.mss() as sct:
            sct_img = sct.grab(sct.monitors[1])
            img_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
        b64_img = base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        print(f"[Capture] mss failed: {e}. Trying grim (Wayland)...")
        try:
            import subprocess
            subprocess.run(['grim', '/tmp/odyssy_cap.png'], check=True)
            with open('/tmp/odyssy_cap.png', 'rb') as f:
                b64_img = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e2:
            print(f"[Error] grim capture failed: {e2}")
            asyncio.run(broadcast(json.dumps({"type": "error", "data": "Screen capture failed."})))
            return

    try:
        payload = {
            "model": "local-model",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Explain what's on this screen concisely."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                    ]
                }
            ],
            "temperature": 0.7,
            "max_tokens": 512,
            "stream": True
        }
        
        asyncio.run(broadcast(json.dumps({"type": "status", "data": "Thinking..."})))
        
        with requests.post(config["lm_studio_url"], json=payload, stream=True, timeout=10) as r:
            if r.status_code != 200:
                asyncio.run(broadcast(json.dumps({"type": "error", "data": f"LM Studio error: {r.status_code}"})))
                return
                
            for line in r.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: ") and decoded != "data: [DONE]":
                        try:
                            chunk = json.loads(decoded[6:])
                            if "content" in chunk["choices"][0]["delta"]:
                                text = chunk["choices"][0]["delta"]["content"]
                                asyncio.run(broadcast(json.dumps({"type": "token", "data": text})))
                        except:
                            pass
        asyncio.run(broadcast(json.dumps({"type": "done"})))
    except requests.exceptions.RequestException as req_err:
        print(f"[Error] Network: {req_err}")
        asyncio.run(broadcast(json.dumps({"type": "error", "data": "Cannot reach LM Studio. Is it running?"})))
    except Exception as e:
        print(f"[Error] {e}")
        asyncio.run(broadcast(json.dumps({"type": "error", "data": str(e)})))

def on_activate():
    import threading
    threading.Thread(target=capture_and_stream, daemon=True).start()

def hotkey_listener():
    hotkey = config["hotkey"]
    print(f"M5 Server running. Press {hotkey} to capture.")
    with keyboard.GlobalHotKeys({hotkey: on_activate}) as h:
        h.join()

@app.on_event("startup")
async def startup_event():
    import threading
    threading.Thread(target=hotkey_listener, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
