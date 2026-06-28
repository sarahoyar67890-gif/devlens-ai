#!/usr/bin/env python3
"""
DevLens AI — Startup Script
Run this to start the application: python run.py
"""
import os
import sys
import subprocess

def check_ollama():
    import httpx
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        models = r.json().get("models", [])
        names = [m["name"] for m in models]
        print(f"✓ Ollama running. Models: {', '.join(names) if names else 'none pulled yet'}")
        if not names:
            print("  ⚠  No models found. Run: ollama pull llama3")
        return True
    except Exception:
        print("⚠  Ollama not running. AI features will use rule-based fallback.")
        print("   To enable full AI: install Ollama + run: ollama pull llama3")
        return False

def main():
    print("=" * 50)
    print("  DevLens AI — GitHub Portfolio Analyzer")
    print("=" * 50)

    # Create .env from example if not exists
    if not os.path.exists(".env") and os.path.exists(".env.example"):
        import shutil
        shutil.copy(".env.example", ".env")
        print("✓ Created .env from .env.example")

    os.makedirs("data", exist_ok=True)
    print("✓ Data directory ready")

    check_ollama()

    print("\n🚀 Starting DevLens AI on http://localhost:8000\n")

    import threading
    import webbrowser
    import time

    def open_browser():
        time.sleep(2)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
