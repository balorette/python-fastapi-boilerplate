#!/bin/bash

# Initialize database script
set -e

echo "🗄️ Initializing database..."

# Determine if uv is available
if command -v uv &> /dev/null; then
    echo "📦 Using uv..."
    PYTHON_CMD="uv run python"
else
    echo "📦 Using standard python..."
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    PYTHON_CMD="python"
fi

# Create database initialization script
cat > init_db.py << 'EOF'
#!/usr/bin/env python3
"""Database initialization script."""

import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir.parent))

from app.core.database import init_database

async def main():
    """Initialize the database."""
    try:
        await init_database()
        print("✅ Database initialization completed successfully!")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Run the initialization
$PYTHON_CMD init_db.py

# Clean up
rm init_db.py

echo "✅ Database initialization completed!"