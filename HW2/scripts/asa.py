# -*- coding: utf-8 -*-
"""
Script to generate launch.json and tasks.json for Cortex Debug
Uses environment variables for tool paths
Can be run from CubeMX or command line
"""

import os
import re
import json
import sys
import subprocess
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """Get project root directory (where .ioc file is located)"""
    
    # Try to find .ioc file in parent directories
    current_dir = Path(__file__).resolve().parent
    
    # If script is in scripts folder, project root is parent
    if current_dir.name == 'scripts':
        return current_dir.parent
    
    # Look for .ioc file
    for parent in [current_dir] + list(current_dir.parents):
        ioc_files = list(parent.glob("*.ioc"))
        if ioc_files:
            return parent
    
    # Fallback: use current directory
    print(f"Warning: Could not find project root, using {current_dir}")
    return current_dir


def ensure_vscode_folder(project_root: Path) -> bool:
    """Create .vscode folder in project root if it doesn't exist"""
    
    vscode_dir = project_root / ".vscode"
    
    if not vscode_dir.exists():
        try:
            vscode_dir.mkdir(parents=True, exist_ok=True)
            print(f"[INFO] Created .vscode folder: {vscode_dir}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create .vscode folder: {e}")
            return False
    else:
        print(f"[INFO] .vscode folder already exists: {vscode_dir}")
        return True


def get_project_name(project_root: Path) -> str:
    """Get project name from .ioc file or CMakeLists.txt"""
    
    # Try to get from .ioc file
    ioc_files = list(project_root.glob("*.ioc"))
    if ioc_files:
        return ioc_files[0].stem
    
    # Try CMakeLists.txt
    cmake_file = project_root / "CMakeLists.txt"
    if cmake_file.exists():
        with open(cmake_file, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'project\((\w+)\s', content)
            if match:
                return match.group(1)
    
    return project_root.name


def get_mcu_type_from_ioc(project_root: Path) -> Optional[str]:
    """Extract MCU type from .ioc file"""
    
    ioc_files = list(project_root.glob("*.ioc"))
    if not ioc_files:
        return None
    
    ioc_file = ioc_files[0]
    print(f"Found .ioc file: {ioc_file.name}")
    
    with open(ioc_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Look for MCU definition in .ioc file
    match = re.search(r'^MCU=(.*?)$', content, re.MULTILINE)
    if match:
        mcu = match.group(1).strip()
        print(f"Detected MCU from .ioc: {mcu}")
        return mcu
    
    return None


def get_mcu_type_from_ld(project_root: Path) -> Optional[str]:
    """Extract MCU type from .ld file"""
    
    # Look for .ld file in project root or Debug folder
    ld_files = list(project_root.glob("*.ld"))
    if not ld_files:
        ld_files = list(project_root.glob("Debug/*.ld"))
    
    if not ld_files:
        return None
    
    ld_file = ld_files[0]
    print(f"Found linker script: {ld_file.name}")
    
    with open(ld_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Patterns to find MCU type
    patterns = [
        r'#define\s+STM32(\w+)',
        r'#define\s+(\w+)\s*/\*\s*MCU',
        r'/\*\s*MCU:\s*(\w+)\s*\*/',
        r'/\*\s*Device:\s*([^*]+)\s*\*/',
        r'(\w+)\s*/\*\s*Device',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            mcu = match.group(1)
            mcu = re.sub(r'xx$', '', mcu, flags=re.IGNORECASE)
            mcu = re.sub(r'x$', '', mcu, flags=re.IGNORECASE)
            mcu = mcu.upper()
            if not mcu.startswith('STM32'):
                mcu = f'STM32{mcu}'
            print(f"Detected MCU type: {mcu}")
            return mcu
    
    # Try to extract from filename
    mcu_match = re.search(r'(STM32\w+)', ld_file.name, re.IGNORECASE)
    if mcu_match:
        mcu = mcu_match.group(1).upper()
        mcu = re.sub(r'[Xx]+$', '', mcu)
        print(f"Detected MCU from filename: {mcu}")
        return mcu
    
    return None


def get_mcu_type(project_root: Path) -> Optional[str]:
    """Get MCU type from .ioc or .ld file"""
    
    # Try .ioc first (more reliable)
    mcu = get_mcu_type_from_ioc(project_root)
    if mcu:
        return mcu
    
    # Fallback to .ld
    return get_mcu_type_from_ld(project_root)


def find_svd_file_in_dir(svd_dir: Path, mcu_type: str) -> Optional[str]:
    """Find SVD file for given MCU type"""
    
    if not svd_dir.exists():
        print(f"  SVD directory does not exist: {svd_dir}")
        return None
    
    mcu_upper = mcu_type.upper()
    
    # Recursively search all subdirectories for SVD files
    svd_files = list(svd_dir.rglob("*.svd"))
    
    if not svd_files:
        print(f"  No SVD files found in {svd_dir}")
        return None
    
    # Extract base MCU model (e.g., STM32F103 from STM32F103C8T6)
    mcu_base = re.match(r'(STM32[F|G|H|L|U|W]\d+)', mcu_upper)
    if mcu_base:
        mcu_base_str = mcu_base.group(1)
        print(f"  Looking for SVD matching: {mcu_base_str}")
    else:
        mcu_base_str = mcu_upper[:7]
    
    # Try to find matching SVD
    for svd_file in svd_files:
        if mcu_base_str in svd_file.name.upper():
            print(f"  Found SVD: {svd_file.name}")
            return str(svd_file)
    
    # Try by family
    family = mcu_base_str[:-1] if mcu_base_str else mcu_upper
    for svd_file in svd_files:
        if family in svd_file.name.upper():
            print(f"  Found SVD by family: {svd_file.name}")
            return str(svd_file)
    
    print(f"  No matching SVD file found for {mcu_type}")
    return None


def get_openocd_target_config(mcu_type: str) -> str:
    """Get OpenOCD target config based on MCU type"""
    
    if not mcu_type:
        return "target/stm32f1x.cfg"
    
    mcu_upper = mcu_type.upper()
    
    config_mapping = {
        'STM32F0': 'target/stm32f0x.cfg',
        'STM32F1': 'target/stm32f1x.cfg',
        'STM32F2': 'target/stm32f2x.cfg',
        'STM32F3': 'target/stm32f3x.cfg',
        'STM32F4': 'target/stm32f4x.cfg',
        'STM32F7': 'target/stm32f7x.cfg',
        'STM32G0': 'target/stm32g0x.cfg',
        'STM32G4': 'target/stm32g4x.cfg',
        'STM32H5': 'target/stm32h5x.cfg',
        'STM32H7': 'target/stm32h7x.cfg',
        'STM32L0': 'target/stm32l0x.cfg',
        'STM32L1': 'target/stm32l1x.cfg',
        'STM32L4': 'target/stm32l4x.cfg',
        'STM32L5': 'target/stm32l5x.cfg',
        'STM32U5': 'target/stm32u5x.cfg',
        'STM32WB': 'target/stm32wbx.cfg',
        'STM32WL': 'target/stm32wlx.cfg',
    }
    
    for series, config in config_mapping.items():
        if mcu_upper.startswith(series):
            return config
    
    return "target/stm32f1x.cfg"


def get_interface_config(openocd_scripts: str) -> str:
    """Get available interface config"""
    
    if not openocd_scripts:
        return "interface/stlink.cfg"
    
    scripts_path = Path(openocd_scripts)
    
    interface_configs = [
        "interface/stlink.cfg",
        "interface/stlink-v2.cfg",
        "interface/stlink-v3.cfg",
    ]
    
    for config in interface_configs:
        if (scripts_path / config).exists():
            return config
    
    return "interface/stlink.cfg"


def generate_launch_json(project_root: Path, project_name: str, 
                         gdb_path: str, openocd_path: str,
                         openocd_scripts: str, svd_file: str,
                         target_config: str, interface_config: str) -> bool:
    """Generate launch.json"""
    
    scripts_path = Path(openocd_scripts).as_posix() if openocd_scripts else ""
    
    config_files = []
    if scripts_path and interface_config and target_config:
        config_files = [
            f"{scripts_path}/{interface_config}",
            f"{scripts_path}/{target_config}"
        ]
    
    launch_config = {
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
    
    vscode_dir = project_root / ".vscode"
    launch_file = vscode_dir / "launch.json"
    
    try:
        with open(launch_file, 'w', encoding='utf-8') as f:
            json.dump(launch_config, f, indent=4)
        print(f"[SUCCESS] Generated {launch_file}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write launch.json: {e}")
        return False


def generate_tasks_json(project_root: Path, openocd_scripts: str,
                        interface_config: str, target_config: str,
                        project_name: str) -> bool:
    """Generate tasks.json with build, flash, clean and monitor tasks"""
    
    scripts_path = Path(openocd_scripts).as_posix() if openocd_scripts else ""
    
    tasks_config = {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "Build Debug",
                "type": "shell",
                "command": "cmake --fresh --preset Debug && cmake --build --preset Debug",
                "group": {
                    "kind": "build",
                    "isDefault": True
                },
                "problemMatcher": ["$gcc"],
                "detail": "Configuration and build Debug",
                "icon": {
                    "color": "terminal.ansiYellow",
                    "id": "debug"
                }
            },
            {
                "label": "Build Release",
                "type": "shell",
                "command": "cmake --fresh --preset Release && cmake --build --preset Release",
                "group": "build",
                "problemMatcher": ["$gcc"],
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
                    "-f", f"{scripts_path}/{interface_config}",
                    "-f", f"{scripts_path}/{target_config}",
                    "-c", f"program build/${{input:firmwareType}}/{project_name}.elf verify reset exit"
                ] if scripts_path else ["-c", "echo OpenOCD path not configured"],
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
                "command": "powershell",
                "args": [
                    "-Command",
                    "if ('${input:cleanOption}' -eq 'Debug') { if (Test-Path 'build/Debug') { Remove-Item -Path 'build/Debug' -Recurse -Force; Write-Host 'Deleted build/Debug folder' } else { Write-Host 'build/Debug folder not found' } }",
                    "if ('${input:cleanOption}' -eq 'Release') { if (Test-Path 'build/Release') { Remove-Item -Path 'build/Release' -Recurse -Force; Write-Host 'Deleted build/Release folder' } else { Write-Host 'build/Release folder not found' } }",
                    "if ('${input:cleanOption}' -eq 'Both') { if (Test-Path 'build/Debug') { Remove-Item -Path 'build/Debug' -Recurse -Force; Write-Host 'Deleted build/Debug folder' }; if (Test-Path 'build/Release') { Remove-Item -Path 'build/Release' -Recurse -Force; Write-Host 'Deleted build/Release folder' }; Write-Host 'Cleanup completed' }"
                ],
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
                    "-f", f"{scripts_path}/{interface_config}",
                    "-f", f"{scripts_path}/{target_config}",
                    "-c", "init; resume; exit"
                ] if scripts_path else ["-c", "echo OpenOCD path not configured"],
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
                "args": ["scripts/add_sources.py"],
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
                "options": ["Debug", "Release"],
                "default": "Debug"
            },
            {
                "id": "cleanOption",
                "description": "Select which folders to clean:",
                "type": "pickString",
                "options": ["Debug", "Release", "Both"],
                "default": "Debug"
            }
        ]
    }
    
    vscode_dir = project_root / ".vscode"
    tasks_file = vscode_dir / "tasks.json"
    
    try:
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(tasks_config, f, indent=4)
        print(f"[SUCCESS] Generated {tasks_file}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write tasks.json: {e}")
        return False


def run_add_sources_script(script_path: Path) -> bool:
    """Run add_sources.py script"""
    
    add_sources_path = script_path.parent / "add_sources.py"
    
    if not add_sources_path.exists():
        print(f"\n[WARNING] {add_sources_path} not found, skipping...")
        return False
    
    print("\n" + "=" * 60)
    print("Running add_sources.py")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, str(add_sources_path)],
            cwd=script_path.parent.parent,
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print("\n[SUCCESS] add_sources.py completed successfully")
            return True
        else:
            print(f"\n[WARNING] add_sources.py exited with code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Failed to run add_sources.py: {e}")
        return False


def main():
    try:
        print("=" * 60)
        print("Generate VSCode Debug Configuration")
        print("=" * 60)
        
        # Get project root (where .ioc file is)
        project_root = get_project_root()
        print(f"Project root: {project_root}")
        
        # Create .vscode folder if it doesn't exist
        print("\n" + "=" * 60)
        print("Checking .vscode folder")
        print("=" * 60)
        
        if not ensure_vscode_folder(project_root):
            print("[ERROR] Could not create .vscode folder")
            return 1
        
        # Read environment variables
        gdb_path = os.environ.get('ARM_GDB_PATH', '')
        openocd_path = os.environ.get('OPENOCD_PATH', '')
        openocd_scripts = os.environ.get('OPENOCD_SCRIPTS', '')
        svd_dir = os.environ.get('SVD_DIR', '')
        
        print("\nEnvironment variables:")
        print(f"  ARM_GDB_PATH: {gdb_path if gdb_path else 'Not set'}")
        print(f"  OPENOCD_PATH: {openocd_path if openocd_path else 'Not set'}")
        print(f"  OPENOCD_SCRIPTS: {openocd_scripts if openocd_scripts else 'Not set'}")
        print(f"  SVD_DIR: {svd_dir if svd_dir else 'Not set'}")
        
        # Get project name
        project_name = get_project_name(project_root)
        print(f"\nProject name: {project_name}")
        
        # Determine MCU type
        mcu_type = get_mcu_type(project_root)
        if mcu_type:
            print(f"MCU type: {mcu_type}")
        else:
            print("MCU type: Unknown")
        
        # Find SVD file
        svd_file = ""
        if svd_dir and mcu_type:
            svd_path = find_svd_file_in_dir(Path(svd_dir), mcu_type)
            if svd_path:
                svd_file = svd_path
                print(f"SVD file: {svd_file}")
        
        # Get OpenOCD configurations
        target_config = get_openocd_target_config(mcu_type) if mcu_type else "target/stm32f1x.cfg"
        interface_config = get_interface_config(openocd_scripts) if openocd_scripts else "interface/stlink.cfg"
        
        print(f"OpenOCD interface: {interface_config}")
        print(f"OpenOCD target: {target_config}")
        
        # Generate configuration files
        print("\n" + "=" * 60)
        print("Generating configuration files")
        print("=" * 60)
        
        success = True
        
        if not generate_launch_json(project_root, project_name, gdb_path, 
                                     openocd_path, openocd_scripts, svd_file,
                                     target_config, interface_config):
            success = False
        
        if not generate_tasks_json(project_root, openocd_scripts,
                                   interface_config, target_config,
                                   project_name):
            success = False
        
        if success:
            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            print(f"  Project: {project_name}")
            print(f"  MCU: {mcu_type if mcu_type else 'Unknown'}")
            print(f"  .vscode folder: {project_root / '.vscode'}")
            print(f"  Launch.json: {project_root / '.vscode' / 'launch.json'}")
            print(f"  Tasks.json: {project_root / '.vscode' / 'tasks.json'}")
            print("=" * 60)
            print("\n[SUCCESS] Configuration files generated successfully!")
            
            # Run add_sources.py
            script_path = Path(__file__).resolve()
            run_add_sources_script(script_path)
            
            return 0
        else:
            print("\n[FAILED] Some files could not be generated")
            return 1
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())