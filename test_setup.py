# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 06:19:23 2025

@author: mahes
"""

# test_setup.py in project root
from pathlib import Path
import sys

def test_environment():
    """Test if all required components are working"""
    try:
        # Test imports
        import textual
        import breeze_connect
        import pandas
        print("✓ All required packages installed")
        
        # Test project structure
        project_root = Path(__file__).parent
        required_files = [
            'autologin.py',
            'interface/terminal_ui.py',
            '.env'
        ]
        
        for file in required_files:
            if not (project_root / file).exists():
                print(f"✗ Missing file: {file}")
            else:
                print(f"✓ Found file: {file}")
                
        # Test .env file
        from dotenv import load_dotenv
        import os
        load_dotenv()
        credentials = [
            'ICICI_API_KEY',
            'ICICI_API_SECRET',
            'ICICI_TOTP_SECRET'
        ]
        
        for cred in credentials:
            if os.getenv(cred):
                print(f"✓ Found credential: {cred}")
            else:
                print(f"✗ Missing credential: {cred}")
                
        return True
        
    except Exception as e:
        print(f"Error during setup test: {e}")
        return False

if __name__ == "__main__":
    test_environment()