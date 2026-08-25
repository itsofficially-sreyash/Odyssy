# Odyssy - User Guide

Odyssy is a local, hotkey-triggered AI co-pilot that captures your screen, analyzes it using a local LM Studio model, and streams the answer simultaneously to a desktop overlay and a Flutter mobile app.

---

## 1. Prerequisites (All Platforms)

1. **LM Studio**: Download and install from [lmstudio.ai](https://lmstudio.ai).
2. **Model**: Download your preferred model (e.g., `qwen2.5-coder` or `qwen3.5-9b` if it has vision support). 
3. **Local Server**: Start the local server in LM Studio (usually on `http://localhost:1234/v1/chat/completions`). Ensure CORS is enabled in LM Studio settings if applicable.
4. **Python 3.10+**: Must be installed.
5. **Node.js & npm**: Required to build/run the Tauri overlay.
6. **Rust**: Required for the Tauri overlay ([rustup.rs](https://rustup.rs)).

---

## 2. Configuration (`config.json`)

At the root of the project, you have a `config.json` file:
```json
{
  "hotkey": "<ctrl>+<alt>+a",
  "lm_studio_url": "http://localhost:1234/v1/chat/completions",
  "overlay_width_vw": 35,
  "overlay_opacity": 0.6
}
```
- **hotkey**: Change this to your preferred global shortcut.
- **lm_studio_url**: Keep as is unless you changed the port in LM Studio.
- **overlay_width_vw** / **overlay_opacity**: Controls how the desktop overlay looks.

---

## 3. Running the Python Backend (Core Engine)

The Python backend is responsible for listening to the hotkey, capturing the screen, communicating with LM Studio, and hosting the WebSocket server. **This must be running for any of the frontends to work.**

### On Linux / Windows
1. Open a terminal and navigate to the `service` folder:
   ```bash
   cd path/to/Odyssy/service
   ```
2. Create and activate a virtual environment (recommended):
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   python main.py
   ```
*Note for Linux Wayland users:* If you are on Wayland, the script uses `mss` first and automatically falls back to `grim` if `mss` fails on fullscreen apps. Ensure `grim` is installed (`sudo apt install grim` or equivalent).

---

## 4. Running the Desktop Overlay (Tauri)

The desktop overlay is a translucent, always-on-top window that displays the AI's response on your computer.

### On Linux / Windows
1. Open a **new** terminal and navigate to the `overlay` folder:
   ```bash
   cd path/to/Odyssy/overlay
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the Tauri app in development mode:
   ```bash
   npm run tauri dev
   ```
4. **Triggering the AI**: Once the overlay says "Connected to local brain", go to your coding problem, IDE, or game, and press the hotkey (`Ctrl + Alt + A`). You will see the response stream in the overlay.

*(Note on Linux Evasion: Native APIs to hide this overlay from Google Meet screen sharing do not exist on Linux standard compositors. If you compile this on Windows, you can add `SetWindowDisplayAffinity` in `main.rs` to hide it.)*

---

## 5. Running the Mobile App (Flutter)

The mobile app connects over your local Wi-Fi to display the exact same streamed text as the desktop overlay.

1. Ensure your phone and your laptop are on the **same Wi-Fi network**.
2. Find your laptop's local IP address:
   - **Windows:** Open Command Prompt and type `ipconfig` (Look for `IPv4 Address`, e.g., `192.168.1.15`).
   - **Linux:** Open terminal and type `ip a` (Look for `inet` under your Wi-Fi interface).
3. Open a terminal and navigate to the `mobile` folder:
   ```bash
   cd path/to/Odyssy/mobile
   ```
4. Ensure Flutter is installed (`flutter doctor`).
5. Run the app on your connected device or emulator:
   ```bash
   flutter run
   ```
6. In the app, type your laptop's IP address (e.g., `192.168.1.15`) into the text field and press **Connect**.
7. Whenever you press the global hotkey on your laptop, the response will stream simultaneously to your phone!
