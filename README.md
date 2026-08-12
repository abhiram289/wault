# wault

A fast, keyboard-first Windows wallpaper switcher inspired by the interaction model of Raycast.

Press **Alt+W** from anywhere to instantly open a searchable wallpaper picker. Fuzzy search, grid/list view, live preview, and smooth transitions. Sits silently in the system tray and starts automatically at boot.


## Install

> **Requirements**: Windows 10/11, Python 3.11+

1. Clone the repo:
   ```
   git clone https://github.com/abhiram289/wault.git
   cd wault
   ```

2. Run the installer:
   ```
   install.bat
   ```

That's it. wault will launch in your system tray and register itself to auto-start on boot.


## Configuration

A `config.json` is auto-created on first run. You can edit it to change the hotkey or wallpaper folder:

```json
{
    "wallpaper_dir": "C:/Users/You/Pictures/Wallpapers",
    "hotkey_modifiers": ["alt"],
    "hotkey_key": "w"
}
```

If the hotkey conflicts with another app, modify it by chnaging the `hotkey_key`.


## Features

**Raycast inspired UI** - clean & compact centered launcher, instant search, keyboard-first selection, preview pane.
**Global hotkey** - `Alt+W` (or whatever is in `config.json`) works only on the desktop with no other apps focused.
**Keyboard UX** - type to filter, `↑/↓` to move, `Enter` to apply, `Esc` to close.
**Clean tray controls** - open, reload, change folder, quit.


## Requirements

- Windows 10 / 11
- Python 3.11+
- Dependencies (auto-installed by `install.bat`):
  - `PySide6` — UI framework
  - `Pillow` — image processing
  - `pywin32` — Win32 API (hotkeys, wallpaper, system tray)


## Notes

This is Windows specific. The global hotkey and desktop transition use Win32 APIs, so those parts are intentionally Windows-specific.
