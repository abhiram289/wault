import os
import json

DEFAULT_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# Win32 Hotkey Modifiers Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

MODIFIER_MAP = {
    "alt": MOD_ALT,
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "shift": MOD_SHIFT,
    "win": MOD_WIN
}

# Mapping common virtual keys
VK_MAP = {
    "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45, "f": 0x46, "g": 0x47, "h": 0x48,
    "i": 0x49, "j": 0x4A, "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F, "p": 0x50,
    "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54, "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58,
    "y": 0x59, "z": 0x5A,
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34, "5": 0x35, "6": 0x36, "7": 0x37,
    "8": 0x38, "9": 0x39,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "space": 0x20, "enter": 0x0D, "tab": 0x09, "escape": 0x1B
}

class ConfigManager:
    def __init__(self, config_path=DEFAULT_CONFIG_FILE):
        self.config_path = config_path
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data = {}
        self.load_defaults()
        self.load()

    def load_defaults(self):
        # Default wallpapers folder inside project
        default_wallpapers_dir = os.path.join(self.base_dir, "wallpapers")
        default_cache_dir = os.path.join(self.base_dir, ".thumbnails")

        self.data = {
            "wallpaper_dir": default_wallpapers_dir,
            "thumbnail_cache_dir": default_cache_dir,
            "hotkey_modifiers": ["alt"],
            "hotkey_key": "w",
            "transition_ms": 300
        }

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                    self.data.update(loaded_data)
            except Exception as e:
                print(f"Error reading config: {e}. Resetting to defaults.")
        
        # Ensure directories exist
        os.makedirs(self.data["wallpaper_dir"], exist_ok=True)
        os.makedirs(self.data["thumbnail_cache_dir"], exist_ok=True)
        self.save()

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    @property
    def wallpaper_dir(self):
        return self.data["wallpaper_dir"]

    @wallpaper_dir.setter
    def wallpaper_dir(self, value):
        self.data["wallpaper_dir"] = value
        os.makedirs(value, exist_ok=True)
        self.save()

    @property
    def thumbnail_cache_dir(self):
        return self.data["thumbnail_cache_dir"]

    @property
    def transition_ms(self):
        return self.data.get("transition_ms", 500)

    @transition_ms.setter
    def transition_ms(self, value):
        self.data["transition_ms"] = value
        self.save()

    def get_hotkey_params(self):
        """
        Returns a tuple of (modifiers_mask, vk_code) for Win32 RegisterHotKey
        """
        mods = self.data.get("hotkey_modifiers", ["ctrl", "shift"])
        key = self.data.get("hotkey_key", "w").lower()

        # Compute modifier mask
        mod_mask = 0
        for m in mods:
            m_lower = m.lower()
            if m_lower in MODIFIER_MAP:
                mod_mask |= MODIFIER_MAP[m_lower]

        # Compute vk code
        vk_code = VK_MAP.get(key, 0x57) # default to W (0x57) if not found
        
        return mod_mask, vk_code

    def get_hotkey_string(self):
        mods = "+".join([m.capitalize() for m in self.data.get("hotkey_modifiers", ["Ctrl", "Shift"])])
        key = self.data.get("hotkey_key", "W").upper()
        return f"{mods}+{key}"
