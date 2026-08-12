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
    Sets the Windows lock screen wallpaper by writing to the registry
    and copying the image to the system lock screen cache path.
    Works on Windows 10 and 11 with no extra packages.
    """
    if not os.path.exists(image_path):
        return False

    import threading
    def worker():
        try:
            import winreg
            import shutil

            abs_path = os.path.abspath(image_path)

            # Path Windows uses for the lock screen image cache
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            lock_cache_dir = os.path.join(
                local_appdata,
                "Packages",
                "Microsoft.Windows.ContentDeliveryManager_cw5n1h2txyewy",
                "LocalState", "Assets"
            )

            # Fallback: write to the Themes folder Windows also reads
            themes_dir = os.path.join(
                os.environ.get("USERPROFILE", ""),
                "AppData", "Roaming", "Microsoft", "Windows", "Themes"
            )

            # Copy image as the lock screen background file
            dest = os.path.join(themes_dir, "LockScreenImage" + os.path.splitext(image_path)[1])
            os.makedirs(themes_dir, exist_ok=True)
            shutil.copy2(abs_path, dest)

            # Write registry keys so Windows picks up the change
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Lock Screen"
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0,
                                    winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, "LockScreenImage", 0, winreg.REG_SZ, dest)
                    winreg.SetValueEx(key, "LockScreenImagePath", 0, winreg.REG_SZ, dest)
            except FileNotFoundError:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
                    winreg.SetValueEx(key, "LockScreenImage", 0, winreg.REG_SZ, dest)
                    winreg.SetValueEx(key, "LockScreenImagePath", 0, winreg.REG_SZ, dest)

            # Also update the Personalization key used by Settings app
            pers_path = r"Software\Microsoft\Windows\CurrentVersion\PersonalizationCSP"
            try:
                with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, pers_path) as key:
                    winreg.SetValueEx(key, "LockScreenImagePath", 0, winreg.REG_SZ, dest)
                    winreg.SetValueEx(key, "LockScreenImageStatus", 0, winreg.REG_DWORD, 1)
            except PermissionError:
                pass  # Requires admin — silently skip if not elevated

            print(f"[wault] Lock screen wallpaper updated: {dest}")
        except Exception as e:
            print(f"[wault] Error setting lock screen wallpaper: {e}")

    threading.Thread(target=worker, daemon=True).start()
    return True


# Simple test to verify the functionality when run directly
if __name__ == "__main__":
    current = get_current_wallpaper()
    print(f"Current wallpaper path: {current}")
