# -*- coding: utf-8 -*-
"""tasks.json generator"""

import json
from pathlib import Path
from typing import Dict, Any
import platform


def generate_tasks_json(project_root: Path, openocd_scripts: str,
                       interface_config: str, target_config: str,
                       project_name: str) -> bool:
    """Generate or update tasks.json with build, flash, clean and monitor tasks"""
    
    vscode_dir = project_root / ".vscode"
    tasks_file = vscode_dir / "tasks.json"
    
    scripts_path = Path(openocd_scripts).as_posix() if openocd_scripts else ""
    
    # Build full paths for OpenOCD config files
    interface_path = f"{scripts_path}/{interface_config}" if scripts_path else "interface/stlink.cfg"
    target_path = f"{scripts_path}/{target_config}" if scripts_path else "target/stm32f1x.cfg"
    
    is_windows = platform.system() == "Windows"
    
    # Формируем команды для Windows (CMD стиль с ;)
    if is_windows:
        # Для PowerShell используем ; вместо &&
        build_debug_cmd = "cmake --fresh --preset Debug ; cmake --build --preset Debug ; copy build\\Debug\\compile_commands.json compile_commands.json"
        build_release_cmd = "cmake --fresh --preset Release ; cmake --build --preset Release ; copy build\\Release\\compile_commands.json compile_commands.json"
    else:
        # Для Linux/Mac
        build_debug_cmd = "cmake --fresh --preset Debug && cmake --build --preset Debug && cp build/Debug/compile_commands.json compile_commands.json"
        build_release_cmd = "cmake --fresh --preset Release && cmake --build --preset Release && cp build/Release/compile_commands.json compile_commands.json"
    
    default_tasks = {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "Build Debug",
                "type": "shell",
                "command": build_debug_cmd,
                "group": {
                    "kind": "build",
                    "isDefault": True
                },
                "problemMatcher": [
                    "$gcc"
                ],
                "detail": "Configuration and build Debug",
                "icon": {
                    "color": "terminal.ansiYellow",
                    "id": "debug"
                }
            },
            {
                "label": "Build Release",
                "type": "shell",
                "command": build_release_cmd,
                "group": "build",
                "problemMatcher": [
                    "$gcc"
                ],
                "detail": "Configuration and build Release",
                "icon": {
                    "color": "terminal.ansiCyan",
                    "id": "rocket"
                }
            },
            {
                "label": "Flash STM32",
                "type": "shell",
                "command": "openocd",
                "args": [
                    "-f",
                    interface_path,
                    "-f",
                    target_path,
                    "-c",
                    f"program build/${{input:firmwareType}}/{project_name}.elf verify reset exit"
                ],
                "problemMatcher": [],
                "detail": "Flash firmware to STM32 (choose Debug/Release)",
                "icon": {
                    "color": "terminal.ansiGreen",
                    "id": "zap"
                },
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": False,
                    "panel": "dedicated"
                }
            },
            {
                "label": "Clean Build Folders",
                "type": "shell",
                "command": "cmake -E rm -rf ${input:cleanOption}",
                "problemMatcher": [],
                "detail": "Delete build folders (Debug/Release/Both)",
                "icon": {
                    "color": "terminal.ansiRed",
                    "id": "trash"
                },
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": False,
                    "panel": "dedicated"
                }
            },
            {
                "label": "Monitor resume",
                "type": "shell",
                "command": "openocd",
                "args": [
                    "-f",
                    interface_path,
                    "-f",
                    target_path,
                    "-c",
                    "init; resume; exit"
                ],
                "problemMatcher": [],
                "presentation": {
                    "echo": True,
                    "reveal": "never",
                    "focus": False,
                    "panel": "dedicated"
                },
                "detail": "Resume microcontroller after debugging",
                "icon": {
                    "color": "terminal.ansiBlue",
                    "id": "play"
                }
            },
            {
                "label": "Sync Sources",
                "type": "shell",
                "command": "python",
                "args": [
                    "scripts/add_sources.py"
                ],
                "problemMatcher": [],
                "detail": "Run add_sources.py to synchronize source files",
                "icon": {
                    "color": "terminal.ansiMagenta",
                    "id": "sync"
                },
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": False,
                    "panel": "dedicated"
                }
            }
        ],
        "inputs": [
            {
                "id": "firmwareType",
                "description": "Select firmware type to flash:",
                "type": "pickString",
                "options": [
                    "Debug",
                    "Release"
                ],
                "default": "Debug"
            },
            {
                "id": "cleanOption",
                "description": "Select which folders to clean:",
                "type": "pickString",
                "options": [
                    {
                        "value": "build/Debug",
                        "label": "Debug"
                    },
                    {
                        "value": "build/Release",
                        "label": "Release"
                    },
                    {
                        "value": "build/Debug build/Release",
                        "label": "Both"
                    }
                ],
                "default": "build/Debug"
            }
        ]
    }  # <-- This closing brace was missing!
    
    # If file exists, merge
    if tasks_file.exists():
        try:
            with open(tasks_file, 'r', encoding='utf-8') as f:
                existing_tasks = json.load(f)
            
            # Merge tasks
            merged = _merge_tasks_config(existing_tasks, default_tasks, 
                                        project_name, interface_path, target_path)
            
            with open(tasks_file, 'w', encoding='utf-8') as f:
                json.dump(merged, f, indent=4)
            
            print(f"[SUCCESS] Updated {tasks_file}")
            return True
            
        except Exception as e:
            print(f"[WARNING] Could not parse existing tasks.json: {e}")
            print("[INFO] Creating new file with default configuration")
    
    # Create new file
    try:
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(default_tasks, f, indent=4)
        print(f"[SUCCESS] Generated {tasks_file}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write tasks.json: {e}")
        return False


def _merge_tasks_config(existing: Dict[str, Any], default: Dict[str, Any], 
                        project_name: str, interface_path: str, 
                        target_path: str) -> Dict[str, Any]:
    """Merge existing tasks.json with default configuration (internal function)"""
    
    merged = existing.copy()
    
    # Ensure version
    if 'version' not in merged:
        merged['version'] = default['version']
    
    # Ensure inputs exist
    if 'inputs' not in merged:
        merged['inputs'] = default['inputs']
    
    # Ensure tasks exist
    if 'tasks' not in merged:
        merged['tasks'] = default['tasks']
    else:
        # Update or add tasks
        default_tasks_dict = {task['label']: task for task in default['tasks']}
        existing_tasks_dict = {task['label']: task for task in merged['tasks']}
        
        for label, default_task in default_tasks_dict.items():
            if label in existing_tasks_dict:
                existing_task = existing_tasks_dict[label]
                
                if label in ['Build Debug', 'Build Release']:
                    existing_task['command'] = default_task['command']
                elif label in ['Flash STM32', 'Monitor resume']:
                    existing_task['args'] = default_task['args']
                elif label == 'Sync Sources':
                    existing_task['args'] = default_task['args']
                
                for key, value in default_task.items():
                    if key not in existing_task:
                        existing_task[key] = value
            else:
                merged['tasks'].append(default_task)
    
    return merged