# wallv

A fast, keyboard-first Windows wallpaper switcher inspired by the interaction model of Raycast.

## What changed

- **Raycast-style command palette UI** — compact centered launcher, instant search, keyboard-first selection, preview pane, subtle dark glass styling.
- **Global hotkey actually opens the launcher from anywhere** — the old desktop-focus gate has been removed. `Alt+W` (or whatever is in `config.json`) works while another application is focused.
- **More reliable Windows hotkey registration** — uses `MOD_NOREPEAT`, reports Windows registration errors, and unregisters cleanly on exit.
- **Foreground handling** — briefly uses a topmost window position so Windows is less likely to refuse focus after a global-hotkey activation.
- **Async thumbnail loading + disk cache** — the UI stays responsive while a large wallpaper folder is scanned.
- **Better keyboard UX** — type to filter, `↑/↓` to move, `Enter` to apply, `Esc` to close.
- **Current wallpaper awareness** — the current wallpaper is marked in the result list.
- **Multi-monitor transition retained** — wallpaper cross-fade continues to happen behind the desktop.
- **Cleaner tray controls** — open, reload, change folder, quit.
- **No bundled virtual environment** — the source archive is much smaller and reproducible.

## Install

Open PowerShell in this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Then run:

```powershell
python main.py
```

For a background launch, use:

```text
run_wallv.bat
```

For debugging, run `python main.py` from a terminal so Windows/PySide errors remain visible.

## Hotkey

The shipped configuration keeps:

```json
"hotkey_modifiers": ["alt"],
"hotkey_key": "w"
```

So the global launcher shortcut is **Alt+W**.

If Windows says the shortcut cannot be registered, another program already owns it. Change the values in `config.json`, restart wallv, and check the console output.

## Important

This is a Windows app. The global hotkey and desktop transition use Win32 APIs, so those parts are intentionally Windows-specific.
