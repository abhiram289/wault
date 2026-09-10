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
    Sets the Windows lock screen wallpaper using the official Windows Runtime (WinRT)
    UserProfile.LockScreen API called via Windows PowerShell without requiring any external dependencies.
    """
    if not os.path.exists(image_path):
        return False

    import threading
    def worker():
        try:
            import subprocess
            import base64

            abs_path = os.path.abspath(image_path).replace("'", "''")

            ps_script = f"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
}}
$asTaskAction = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'
}}

$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.System.UserProfile.LockScreen, Windows.System.UserProfile, ContentType=WindowsRuntime]

$op = [Windows.Storage.StorageFile]::GetFileFromPathAsync('{abs_path}')
$netTask = $asTaskGeneric.MakeGenericMethod([Windows.Storage.StorageFile]).Invoke($null, @($op))
$netTask.Wait()
$file = $netTask.Result

$action = [Windows.System.UserProfile.LockScreen]::SetImageFileAsync($file)
$netActionTask = $asTaskAction.Invoke($null, @($action))
$netActionTask.Wait()
"""
            encoded = base64.b64encode(ps_script.encode('utf-16le')).decode('ascii')
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
                capture_output=True,
                text=True,
                creationflags=creation_flags
            )

            if res.returncode == 0:
                print(f"[wault] Lock screen wallpaper updated successfully: {abs_path}")
            else:
                print(f"[wault] Lock screen PowerShell error: {res.stderr.strip()}")
        except Exception as e:
            print(f"[wault] Error setting lock screen wallpaper: {e}")

    threading.Thread(target=worker, daemon=True).start()
    return True


# Simple test to verify the functionality when run directly
if __name__ == "__main__":
    current = get_current_wallpaper()
    print(f"Current wallpaper path: {current}")
