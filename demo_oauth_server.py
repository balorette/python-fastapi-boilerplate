#!/usr/bin/env python3
"""
Demo OAuth server to test Google OAuth implementation
Run this to test the OAuth endpoints locally
"""

import asyncio
import uvicorn
from app.main import app

if __name__ == "__main__":
    print("🚀 Starting OAuth Demo Server")
    print("=" * 50)
    print("📋 Available endpoints:")
    print("  • POST /api/v1/auth/authorize")
    print("  • GET  /api/v1/auth/callback/google")
    print("  • POST /api/v1/auth/token")
    print("  • POST /api/v1/auth/login (existing)")
    print("  • GET  /api/v1/users/me (current-user endpoint)")
    print("  • GET  /docs (FastAPI documentation)")
    print("=" * 50)
    print("🌐 Server starting at: http://localhost:8000")
    print("📖 Documentation at: http://localhost:8000/docs")
    print("\n💡 To test OAuth:")
    print("1. Go to http://localhost:8000/docs")
    print("2. Call POST /api/v1/auth/authorize with provider=google")
    print("3. After Google redirect, exchange the code via POST /api/v1/auth/token")
    print("4. Set up your Google OAuth credentials first!")
    print("=" * 50)

    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
