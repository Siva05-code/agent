#!/usr/bin/env python3
"""
Start Manufacturing Equipment Maintenance Query Agent
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    print("🚀 Manufacturing Equipment Maintenance Query Agent")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("backend/main_openrouter.py").exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Install dependencies if needed
    print("📦 Checking dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencies ready")
    except subprocess.CalledProcessError:
        print("⚠️  Some dependencies might be missing, but continuing...")
    
    print("\n🌐 Starting server...")
    print("📝 Open your browser: http://127.0.0.1:8000")
    print("\nPress Ctrl+C to stop")
    print("-" * 50)
    
    # Start the server
    try:
        os.chdir("backend")
        subprocess.run([sys.executable, "main_openrouter.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
