# -*- coding: utf-8 -*-
"""settings.json generator"""

import json
from pathlib import Path
from typing import Dict, Any


def generate_settings(project_root: Path) -> bool:
    """Generate or update settings.json"""
    
    vscode_dir = project_root / ".vscode"
    settings_file = vscode_dir / "settings.json"
    
    # Default configuration
    default_settings = {
        "clang-format.executable": "clang-format",
        "clang-format.style": "Google",
        "[c]": {
            "editor.defaultFormatter": "xaver.clang-format"
        }
    }
    
    # If file exists, merge with existing
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                existing_settings = json.load(f)
            
            # Merge settings
            merged = _merge_settings(existing_settings, default_settings)
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(merged, f, indent=4)
            
            print(f"[SUCCESS] Updated {settings_file}")
            return True
            
        except Exception as e:
            print(f"[WARNING] Could not parse existing settings.json: {e}")
            print("[INFO] Creating new file with default configuration")
    
    # Create new file
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, indent=4)
        print(f"[SUCCESS] Generated {settings_file}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write settings.json: {e}")
        return False


def _merge_settings(existing: Dict[str, Any], default: Dict[str, Any]) -> Dict[str, Any]:
    """Merge existing settings.json with default values (internal function)"""
    
    merged = existing.copy()
    
    # Merge clang-format settings
    for key, value in default.items():
        if key not in merged:
            merged[key] = value
        elif key == "[c]" and isinstance(value, dict):
            # Merge [c] section
            if "[c]" not in merged:
                merged["[c]"] = {}
            for c_key, c_value in value.items():
                if c_key not in merged["[c]"]:
                    merged["[c]"][c_key] = c_value
    
    return merged