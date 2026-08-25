README.mdimport os
import subprocess
import time

def test_capture():
    print("Testing Screen Capture...")
    session_type = os.environ.get('XDG_SESSION_TYPE', 'unknown')
    print(f"Session type: {session_type}")
    
    # Try mss first (works on X11)
    try:
        import mss
        with mss.mss() as sct:
            filename = sct.shot(output='test_mss.png')
            print(f"mss capture successful: {filename}")
            return True
    except Exception as e:
        print(f"mss capture failed: {e}")
    
    # Try grim (works on Wayland)
    try:
        result = subprocess.run(['grim', 'test_grim.png'], capture_output=True, text=True)
        if result.returncode == 0:
            print("grim capture successful.")
            return True
        else:
            print(f"grim capture failed: {result.stderr}")
    except FileNotFoundError:
        print("grim not installed.")
        
    return False

if __name__ == "__main__":
    test_capture()
