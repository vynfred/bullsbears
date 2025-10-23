#!/usr/bin/env python3
"""
Development server runner for Options Trading Analyzer.
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run the development server."""
    # Change to backend directory
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env file not found. Please copy .env.example to .env and configure your API keys.")
        print("   cp ../.env.example .env")
        return 1
    
    # Install dependencies if needed
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        print("📦 Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Run the FastAPI server
    print("🚀 Starting Options Trading Analyzer API...")
    print("📊 API will be available at: http://localhost:8000")
    print("📚 API documentation: http://localhost:8000/docs")
    print("🔍 Health check: http://localhost:8000/health")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload",
            "--log-level", "info"
        ])
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        return 0

if __name__ == "__main__":
    sys.exit(main())
