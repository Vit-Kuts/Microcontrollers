# -*- coding: utf-8 -*-
"""c_cpp_properties.json generator"""

import json
from pathlib import Path
from typing import Dict, Any


def generate_c_cpp_properties(project_root: Path) -> bool:
    """Generate or update c_cpp_properties.json"""
    
    vscode_dir = project_root / ".vscode"
    c_cpp_file = vscode_dir / "c_cpp_properties.json"
    
    # Default configuration
    default_config = {
        "configurations": [
            {
                "name": "STM32",
                "compileCommands": "${workspaceFolder}/compile_commands.json",
                "cStandard": "c17",
                "cppStandard": "c++17"
            }
        ],
        "version": 4
    }
    
    # If file exists, merge with existing
    if c_cpp_file.exists():
        try:
            with open(c_cpp_file, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
            
            # Update existing configuration or add if missing
            merged = _merge_c_cpp_properties(existing_config, default_config)
            
            with open(c_cpp_file, 'w', encoding='utf-8') as f:
                json.dump(merged, f, indent=4)
            
            print(f"[SUCCESS] Updated {c_cpp_file}")
            return True
            
        except Exception as e:
            print(f"[WARNING] Could not parse existing c_cpp_properties.json: {e}")
            print("[INFO] Creating new file with default configuration")
    
    # Create new file
    try:
        with open(c_cpp_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
        print(f"[SUCCESS] Generated {c_cpp_file}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write c_cpp_properties.json: {e}")
        return False


def _merge_c_cpp_properties(existing: Dict[str, Any], default: Dict[str, Any]) -> Dict[str, Any]:
    """Merge existing c_cpp_properties.json with default values (internal function)"""
    
    # Start with existing configuration
    merged = existing.copy()
    
    # Ensure version is set
    if 'version' not in merged:
        merged['version'] = default['version']
    
    # Ensure configurations exist
    if 'configurations' not in merged or not merged['configurations']:
        merged['configurations'] = default['configurations']
    else:
        # Check if STM32 configuration exists
        stm32_config = None
        for config in merged['configurations']:
            if config.get('name') == 'STM32':
                stm32_config = config
                break
        
        if stm32_config:
            # Update existing STM32 config with defaults if missing
            default_stm32 = default['configurations'][0]
            for key, value in default_stm32.items():
                if key not in stm32_config:
                    stm32_config[key] = value
        else:
            # Add STM32 configuration
            merged['configurations'].append(default['configurations'][0])
    
    return merged