import ctypes
import os

SPI_GETDESKWALLPAPER = 115
SPI_SETDESKWALLPAPER = 20

# Flags for SystemParametersInfo
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02

def get_current_wallpaper():
    """
    Retrieves the absolute path to the current desktop wallpaper image.
    """
    try:
        # Create a buffer of 512 characters
        buffer = ctypes.create_unicode_buffer(512)
        # Call SystemParametersInfoW to get the current wallpaper
        # SPI_GETDESKWALLPAPER retrieves the path of the current desktop wallpaper
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETDESKWALLPAPER, 
            ctypes.sizeof(buffer), 
            buffer, 
            0
        )
        if result:
            path = buffer.value
            if os.path.exists(path):
                return path
            
            # Sometimes Windows returns a path that points to a temporary transcode file
            # e.g. AppData\Roaming\Microsoft\Windows\Themes\TranscodedWallpaper
            # This is fine as we can read this file directly to render the current background!
            transcoded_path = os.path.join(
                os.environ.get("USERPROFILE", ""), 
                "AppData", "Roaming", "Microsoft", "Windows", "Themes", "TranscodedWallpaper"
            )
            if os.path.exists(transcoded_path):
                return transcoded_path
                
        return None
    except Exception as e:
        print(f"Error getting current wallpaper: {e}")
        return None

def set_wallpaper(image_path):
    """
    Sets the desktop wallpaper image path globally.
    """
    if not os.path.exists(image_path):
        print(f"Error: Wallpaper path does not exist: {image_path}")
        return False
        
    try:
        # SPIF_UPDATEINIFILE writes the new setting to the registry
        # SPIF_SENDCHANGE sends WM_SETTINGCHANGE to notify all top-level windows
        flags = SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 
            0, 
            image_path, 
            flags
        )
        return bool(result)
    except Exception as e:
        print(f"Error setting wallpaper: {e}")
        return False

def set_lockscreen_wallpaper(image_path):
    """
    Sets the Windows lockscreen wallpaper asynchronously.
    """
    if not os.path.exists(image_path):
        return False
        
    import threading
    def worker():
        try:
            import pythoncom
            pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
            try:
                import asyncio
                from winrt.windows.storage import StorageFile
                from winrt.windows.system.userprofile import LockScreen
                
                async def run_api():
                    f = await StorageFile.get_file_from_path_async(os.path.abspath(image_path))
                    await LockScreen.set_image_file_async(f)
                    
                asyncio.run(run_api())
                print(f"[wallv] Lockscreen wallpaper updated successfully.")
            finally:
                pythoncom.CoUninitialize()
        except Exception as e:
            print(f"[wallv] Error setting lockscreen wallpaper: {e}")

    threading.Thread(target=worker, daemon=True).start()
    return True

# Simple test to verify the functionality when run directly
if __name__ == "__main__":
    current = get_current_wallpaper()
    print(f"Current wallpaper path: {current}")
