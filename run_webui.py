#!/usr/bin/env python3
"""
Simple startup script for Kebogyro Web UI
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    # Set up environment
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Add current directory to Python path
    sys.path.insert(0, str(project_root))
    
    # Check if .env exists, if not suggest creating one
    env_path = project_root / '.env'
    if not env_path.exists():
        print("🔧 .env file not found. Please create one based on .env.example")
        print("Example commands:")
        print("  cp .env.example .env")
        print("  # Edit .env with your settings")
        print()
    
    # Check required environment variables
    required_vars = ['OPENAI_API_BASE', 'OPENAI_API_KEY', 'KBG_OLLAMA_MODEL']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file or export them before running.")
        print()
    else:
        print("✅ All required environment variables are set")
        print()
    
    # Show current configuration
    print("🔍 Current configuration:")
    print(f"  OPENAI_API_BASE: {os.getenv('OPENAI_API_BASE', 'NOT SET')}")
    print(f"  OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
    print(f"  KBG_OLLAMA_MODEL: {os.getenv('KBG_OLLAMA_MODEL', 'NOT SET')}")
    print(f"  KBG_LLM_PROVIDER: {os.getenv('KBG_LLM_PROVIDER', 'NOT SET')}")
    print(f"  KBG_LLM_TEMPERATURE: {os.getenv('KBG_LLM_TEMPERATURE', 'NOT SET')}")
    print()
    
    # Run Streamlit
    print("🚀 Starting Streamlit Web UI...")
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "web_ui/app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Streamlit: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()