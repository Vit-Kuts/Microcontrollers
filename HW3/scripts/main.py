# -*- coding: utf-8 -*-
"""
Main orchestration script for VSCode debug configuration generation
Gathers all necessary information and calls specific scripts for file generation
"""

import os
import sys
import subprocess
from pathlib import Path

# Add scripts directory to path for imports
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))

# Импорты из utils
from utils.file_utils import get_project_root, ensure_directory, get_project_name
from utils.openocd_utils import (
    get_mcu_type,
    get_mcu_family,
    find_svd_file,
    get_openocd_target_config,
    get_interface_config
)

# Импорты из config
from config.launch_json import generate_launch_json
from config.tasks_json import generate_tasks_json
from config.c_cpp_properties import generate_c_cpp_properties
from config.settings import generate_settings


def get_environment_variables() -> dict:
    """Get all required environment variables"""
    return {
        'gdb_path': os.environ.get('ARM_GDB_PATH', ''),
        'openocd_path': os.environ.get('OPENOCD_PATH', ''),
        'openocd_scripts': os.environ.get('OPENOCD_SCRIPTS', ''),
        'svd_dir': os.environ.get('SVD_DIR', ''),
    }


def print_environment_variables(env_vars: dict) -> None:
    """Print environment variables status"""
    print("\nEnvironment variables:")
    for key, value in env_vars.items():
        display_name = key.upper()
        print(f"  {display_name}: {value if value else 'Not set'}")


def print_summary(project_name: str, mcu_type: str, project_root: Path) -> None:
    """Print final summary"""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Project: {project_name}")
    print(f"  MCU: {mcu_type if mcu_type else 'Unknown'}")
    if mcu_type:
        family = get_mcu_family(mcu_type)
        if family:
            print(f"  MCU Family: {family}")
    print(f"  .vscode folder: {project_root / '.vscode'}")
    print(f"  Generated/Updated files:")
    print(f"    - launch.json")
    print(f"    - tasks.json")
    print(f"    - c_cpp_properties.json")
    print(f"    - settings.json")
    print("=" * 60)


def run_add_sources_script() -> bool:
    """Run add_sources.py script to synchronize source files"""
    add_sources_path = Path(__file__).resolve().parent / "add_sources.py"
    
    if not add_sources_path.exists():
        print(f"\n[WARNING] {add_sources_path} not found, skipping...")
        return False
    
    print("\n" + "=" * 60)
    print("Running add_sources.py (synchronizing source files)")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, str(add_sources_path)],
            cwd=Path(__file__).resolve().parent.parent,
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


def main() -> int:
    """Main orchestration function"""
    try:
        print("=" * 60)
        print("Generate VSCode Debug Configuration")
        print("=" * 60)
        
        # 1. Get project information
        project_root = get_project_root()
        print(f"Project root: {project_root}")
        
        # 2. Ensure .vscode folder exists
        print("\n" + "=" * 60)
        print("Checking .vscode folder")
        print("=" * 60)
        
        vscode_dir = project_root / ".vscode"
        if not ensure_directory(vscode_dir):
            print("[ERROR] Could not create .vscode folder")
            return 1
        
        # 3. Get environment variables
        env_vars = get_environment_variables()
        print_environment_variables(env_vars)
        
        # 4. Get project name
        project_name = get_project_name(project_root)
        print(f"\nProject name: {project_name}")
        
        # 5. Determine MCU type
        print("\n" + "=" * 60)
        print("MCU Detection")
        print("=" * 60)
        mcu_type = get_mcu_type(project_root)
        
        if mcu_type:
            print(f"\n[OK] MCU type detected: {mcu_type}")
            family = get_mcu_family(mcu_type)
            if family:
                print(f"  MCU family: {family}")
        else:
            print("\n[FAILED] MCU type not detected")
            print("  [INFO] Will use default OpenOCD target: target/stm32f1x.cfg")
            print("  [INFO] You can manually set MCU type in CMakeLists.txt or .ioc file")
        
        # 6. Find SVD file
        print("\n" + "=" * 60)
        print("SVD File Search")
        print("=" * 60)
        
        svd_file = ""
        if env_vars['svd_dir']:
            svd_path = Path(env_vars['svd_dir'])
            print(f"SVD_DIR = {svd_path}")
            
            # Проверяем существование директории
            if not svd_path.exists():
                print(f"  [WARNING] SVD directory does not exist: {svd_path}")
                print(f"  [INFO] Please check the SVD_DIR environment variable")
            elif mcu_type:
                svd_file_path = find_svd_file(svd_path, mcu_type)
                if svd_file_path:
                    svd_file = svd_file_path
                    print(f"\n[OK] SVD file found: {svd_file}")
                else:
                    print("\n[FAILED] SVD file not found")
                    print("  [INFO] Debugging will work without SVD, but peripheral registers won't be displayed")
                    print("  [INFO] To enable SVD support, download SVD files for your MCU")
            else:
                print("  [WARNING] Cannot search for SVD file: MCU type unknown")
        else:
            print("  [INFO] SVD_DIR environment variable not set")
            print("  [INFO] SVD support disabled")
            print("  [INFO] To enable SVD support, set SVD_DIR to your SVD files folder")
        
        # 7. Get OpenOCD configurations
        print("\n" + "=" * 60)
        print("OpenOCD Configuration")
        print("=" * 60)
        
        target_config = get_openocd_target_config(mcu_type) if mcu_type else "target/stm32f1x.cfg"
        print(f"  Target config: {target_config}")
        
        interface_config = get_interface_config(
            env_vars['openocd_scripts'],
            debugger_type="stlink"
        )
        print(f"  Interface config: {interface_config}")
        
        # 8. Generate configuration files
        print("\n" + "=" * 60)
        print("Generating configuration files")
        print("=" * 60)
        
        success = True
        
        # Generate/update launch.json
        if not generate_launch_json(
            project_root, 
            project_name, 
            env_vars['gdb_path'],
            env_vars['openocd_path'], 
            env_vars['openocd_scripts'], 
            svd_file,
            target_config, 
            interface_config
        ):
            success = False
        
        # Generate/update tasks.json
        if not generate_tasks_json(
            project_root, 
            env_vars['openocd_scripts'],
            interface_config, 
            target_config,
            project_name
        ):
            success = False
        
        # Generate/update c_cpp_properties.json
        if not generate_c_cpp_properties(project_root):
            success = False
        
        # Generate/update settings.json
        if not generate_settings(project_root):
            success = False
        
        # 9. Print summary
        if success:
            print_summary(project_name, mcu_type, project_root)
            print("\n[SUCCESS] Configuration files generated successfully!")
            
            # 10. Run add_sources.py (синхронизация исходников)
            run_add_sources_script()
            
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