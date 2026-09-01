# -*- coding: utf-8 -*-
"""launch.json generator"""

import json
from pathlib import Path
from typing import Dict, Any


def generate_launch_json(project_root: Path, project_name: str, 
                        gdb_path: str, openocd_path: str,
                        openocd_scripts: str, svd_file: str,
                        target_config: str, interface_config: str) -> bool:
    """Generate or update launch.json"""
    
    vscode_dir = project_root / ".vscode"
    launch_file = vscode_dir / "launch.json"
    
    scripts_path = Path(openocd_scripts).as_posix() if openocd_scripts else ""
    
    # Проверяем существование конфигурационных файлов OpenOCD
    config_files = []
    if scripts_path and interface_config and target_config:
        # Проверяем, существуют ли файлы
        interface_full = Path(openocd_scripts) / interface_config
        target_full = Path(openocd_scripts) / target_config
        
        if not interface_full.exists():
            print(f"  [WARNING] Interface config not found: {interface_config}")
            print(f"  [INFO] Will use default: interface/stlink.cfg")
            interface_config = "interface/stlink.cfg"
        
        if not target_full.exists():
            print(f"  [WARNING] Target config not found: {target_config}")
            print(f"  [INFO] Will use default: target/stm32f1x.cfg")
            target_config = "target/stm32f1x.cfg"
        
        config_files = [
            f"{scripts_path}/{interface_config}",
            f"{scripts_path}/{target_config}"
        ]
    
    default_launch = {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Cortex Debug",
                "cwd": "${workspaceFolder}",
                "executable": f"build/Debug/{project_name}.elf",
                "request": "launch",
                "type": "cortex-debug",
                "gdbPath": gdb_path if gdb_path else "${command:embeddedBuildTools.getGdbPath}",
                "servertype": "openocd",
                "serverArgs": ["-d3"],
                "serverpath": openocd_path if openocd_path else "",
                "configFiles": config_files,
                "svdFile": svd_file if svd_file else "",
                "liveWatch": {
                    "enabled": True
                },
                "preLaunchTask": "Build Debug",
                "runToEntryPoint": "main",
                "postDebugTask": "Monitor resume"
            }
        ]
    }
    
    # If file exists, merge
    if launch_file.exists():
        try:
            with open(launch_file, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
            
            # Merge configurations
            merged = _merge_launch_config(existing_config, default_launch, project_name)
            
            with open(launch_file, 'w', encoding='utf-8') as f:
                json.dump(merged, f, indent=4)
            
            print(f"[SUCCESS] Updated {launch_file}")
            return True
            
        except Exception as e:
            print(f"[WARNING] Could not parse existing launch.json: {e}")
            print("[INFO] Creating new file with default configuration")
    
    # Create new file
    try:
        with open(launch_file, 'w', encoding='utf-8') as f:
            json.dump(default_launch, f, indent=4)
        print(f"[SUCCESS] Generated {launch_file}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write launch.json: {e}")
        return False


def _merge_launch_config(existing: Dict[str, Any], default: Dict[str, Any], 
                        project_name: str) -> Dict[str, Any]:
    """Merge existing launch.json with default configuration (internal function)"""
    
    merged = existing.copy()
    
    # Ensure version
    if 'version' not in merged:
        merged['version'] = default['version']
    
    # Ensure configurations exist
    if 'configurations' not in merged or not merged['configurations']:
        merged['configurations'] = default['configurations']
    else:
        # Find or create Cortex Debug configuration
        cortex_config = None
        for config in merged['configurations']:
            if config.get('name') == 'Cortex Debug':
                cortex_config = config
                break
        
        if cortex_config:
            # Update existing config with defaults
            default_cortex = default['configurations'][0]
            for key, value in default_cortex.items():
                if key not in cortex_config:
                    cortex_config[key] = value
                elif key == 'executable':
                    # Update executable path with current project name
                    cortex_config[key] = f"build/Debug/{project_name}.elf"
        else:
            # Add default Cortex Debug configuration
            merged['configurations'].append(default['configurations'][0])
    
    return merged