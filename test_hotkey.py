import ctypes
import ctypes.wintypes
import time

# Win32 Constants
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
VK_W = 0x57  # 'W' key

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def test_hotkey():
    hotkey_id = 99
    # Register Ctrl+Shift+W
    # hWnd = 0 means thread-specific
    success = user32.RegisterHotKey(0, hotkey_id, MOD_CONTROL | MOD_SHIFT, VK_W)
    if not success:
        err = kernel32.GetLastError()
        print(f"FAILED to register Ctrl+Shift+W. Error code: {err}")
        return
        
    print("SUCCESS: Ctrl+Shift+W registered. Press it now! (Waiting 5 seconds...)")
    
    start_time = time.time()
    msg = ctypes.wintypes.MSG()
    
    # Non-blocking peek message loop for 5 seconds
    while time.time() - start_time < 5:
        # PM_REMOVE = 1
        if user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):
            if msg.message == 0x0312:  # WM_HOTKEY
                if msg.wParam == hotkey_id:
                    print("HOTKEY PRESSED SUCCESSFULLY!")
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.05)
        
    user32.UnregisterHotKey(0, hotkey_id)
    print("Test finished.")

if __name__ == "__main__":
    test_hotkey()
