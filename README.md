# wallv

A fast, keyboard-first Windows wallpaper switcher inspired by the interaction model of Raycast.

## What changed

**Raycast inspired UI** - clean & compact centered launcher, instant search, keyboard-first selection, preview pane.
**Global hotkey** - `Alt+W` (or whatever is in `config.json`) works only on the desktop with no other apps focused.
**Keyboard UX** - type to filter, `↑/↓` to move, `Enter` to apply, `Esc` to close.
**Clean tray controls** - open, reload, change folder, quit.

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

## Hotkey

The shipped configuration keeps:

```json
"hotkey_modifiers": ["alt"],
"hotkey_key": "w"
```

So the global launcher shortcut is **Alt+W**.

If Windows says the shortcut cannot be registered, another program already owns it. Change the values in `config.json`, restart wallv, and check the console output.

## Important

This is Windows specific. The global hotkey and desktop transition use Win32 APIs, so those parts are intentionally Windows-specific.
