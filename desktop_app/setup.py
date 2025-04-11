#!/usr/bin/env python
"""
ForexScalperAI Desktop App Setup Utility

This script helps set up and install the desktop application.
It performs the following tasks:
1. Installs required dependencies
2. Creates desktop and start menu shortcuts
3. Sets up auto-start functionality (optional)
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def check_requirements():
    """Check and install required packages"""
    print("Checking and installing required packages...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt5", "pywin32", "requests"])
        print("✅ Required packages installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install required packages")
        return False


def create_shortcuts():
    """Create desktop and start menu shortcuts"""
    print("Creating shortcuts...")
    
    try:
        import win32com.client
        
        # Get paths
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        start_menu_path = os.path.join(os.environ["APPDATA"], 
                                     "Microsoft", "Windows", "Start Menu", "Programs", "ForexScalperAI")
        
        # Create start menu folder if it doesn't exist
        os.makedirs(start_menu_path, exist_ok=True)
        
        # Create desktop shortcut
        ws = win32com.client.Dispatch("WScript.Shell")
        desktop_shortcut = ws.CreateShortCut(os.path.join(desktop_path, "ForexScalperAI.lnk"))
        desktop_shortcut.TargetPath = sys.executable
        desktop_shortcut.Arguments = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        desktop_shortcut.WorkingDirectory = os.path.dirname(os.path.abspath(__file__))
        desktop_shortcut.IconLocation = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.ico")
        desktop_shortcut.Description = "ForexScalperAI Trading Bot"
        desktop_shortcut.Save()
        
        # Create start menu shortcut
        start_menu_shortcut = ws.CreateShortCut(os.path.join(start_menu_path, "ForexScalperAI.lnk"))
        start_menu_shortcut.TargetPath = sys.executable
        start_menu_shortcut.Arguments = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        start_menu_shortcut.WorkingDirectory = os.path.dirname(os.path.abspath(__file__))
        start_menu_shortcut.IconLocation = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.ico")
        start_menu_shortcut.Description = "ForexScalperAI Trading Bot"
        start_menu_shortcut.Save()
        
        print("✅ Shortcuts created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create shortcuts: {str(e)}")
        return False


def setup_auto_start():
    """Set up auto-start functionality"""
    print("Setting up auto-start functionality...")
    
    try:
        import winreg
        
        # Open registry key
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_WRITE
        )
        
        # Set value
        winreg.SetValueEx(
            key, 
            "ForexScalperAI", 
            0, 
            winreg.REG_SZ, 
            f'"{sys.executable}" "{os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")}"'
        )
        
        # Close key
        winreg.CloseKey(key)
        
        print("✅ Auto-start setup successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to set up auto-start: {str(e)}")
        return False


def create_icon():
    """Create default icon if not exists"""
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.ico")
    if not os.path.exists(icon_path):
        # Create a simple icon (this is a placeholder)
        try:
            from PIL import Image, ImageDraw
            
            # Create resources directory if it doesn't exist
            os.makedirs(os.path.dirname(icon_path), exist_ok=True)
            
            # Create a simple icon (green circle)
            img = Image.new('RGBA', (256, 256), color=(0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse((20, 20, 236, 236), fill=(0, 150, 0, 255))
            
            # Save as PNG first
            png_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.png")
            img.save(png_path)
            
            # Convert to ICO if possible
            try:
                img.save(icon_path)
                print("✅ Created default icon")
            except Exception:
                # If PIL can't save as ICO, we'll just use the PNG
                print("⚠️ Created PNG icon only")
                
            return True
        except Exception as e:
            print(f"⚠️ Could not create icon: {str(e)}")
            return False
    return True


def main():
    """Main setup function"""
    print("\n=======================================")
    print("   ForexScalperAI Desktop App Setup")
    print("=======================================\n")
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Setup failed at requirements stage")
        return False
    
    # Create icon
    create_icon()
    
    # Create shortcuts
    if not create_shortcuts():
        print("\n⚠️ Could not create shortcuts, but continuing setup")
    
    # Ask about auto-start
    auto_start = input("\nDo you want to set up auto-start on Windows boot? (y/n): ").lower().strip()
    if auto_start == 'y':
        setup_auto_start()
    
    print("\n=======================================")
    print("   Setup Complete!")
    print("=======================================")
    print("\nYou can now start ForexScalperAI from:")
    print("- Desktop shortcut")
    print("- Start menu")
    print("- Directly running the main.py script")
    print("\nEnjoy trading with ForexScalperAI!")
    
    # Ask if the user wants to start the app now
    start_now = input("\nDo you want to start ForexScalperAI now? (y/n): ").lower().strip()
    if start_now == 'y':
        # Start the app
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        subprocess.Popen([sys.executable, script_path])
        print("\n✅ ForexScalperAI has been started")
    
    return True


if __name__ == "__main__":
    main()
