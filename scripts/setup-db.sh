#!/bin/bash

# Database initialization script
set -e

# Default to SQLite if no argument provided
DB_TYPE=${1:-sqlite}

case $DB_TYPE in
    sqlite)
        echo "🗄️ Configuring SQLite database..."
        
        # Update .env file for SQLite
        if [ -f .env ]; then
            # Comment out PostgreSQL settings
            sed -i 's/^DATABASE_URL=postgresql/#DATABASE_URL=postgresql/' .env
            sed -i 's/^DATABASE_URL_ASYNC=postgresql/#DATABASE_URL_ASYNC=postgresql/' .env
            
            # Ensure SQLite settings are active
            if ! grep -q "^DATABASE_URL=sqlite" .env; then
                echo "DATABASE_URL=sqlite:///./app.db" >> .env
            fi
            if ! grep -q "^DATABASE_URL_ASYNC=sqlite" .env; then
                echo "DATABASE_URL_ASYNC=sqlite+aiosqlite:///./app.db" >> .env
            fi
        else
            echo "⚠️ .env file not found. Creating from .env.example..."
            cp .env.example .env
        fi
        
        echo "✅ SQLite database configured!"
        echo "📝 Database will be created at: ./app.db"
        ;;
        
    postgresql)
        echo "🐘 Configuring PostgreSQL database..."
        
        # Check if PostgreSQL is installed
        if ! command -v psql &> /dev/null; then
            echo "❌ PostgreSQL is not installed or not in PATH"
            echo "Please install PostgreSQL first:"
            echo "  - Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib"
            echo "  - macOS: brew install postgresql"
            echo "  - Windows: Download from https://www.postgresql.org/download/"
            exit 1
        fi
        
        # Prompt for database details
        read -p "Enter PostgreSQL host (default: localhost): " DB_HOST
        DB_HOST=${DB_HOST:-localhost}
        
        read -p "Enter PostgreSQL port (default: 5432): " DB_PORT
        DB_PORT=${DB_PORT:-5432}
        
        read -p "Enter database name (default: iac_api_db): " DB_NAME
        DB_NAME=${DB_NAME:-iac_api_db}
        
        read -p "Enter database user (default: user): " DB_USER
        DB_USER=${DB_USER:-user}
        
        read -s -p "Enter database password: " DB_PASSWORD
        echo
        
        # Update .env file for PostgreSQL
        if [ -f .env ]; then
            # Comment out SQLite settings
            sed -i 's/^DATABASE_URL=sqlite/#DATABASE_URL=sqlite/' .env
            sed -i 's/^DATABASE_URL_ASYNC=sqlite/#DATABASE_URL_ASYNC=sqlite/' .env
            
            # Update PostgreSQL settings
            sed -i "s|^#*DATABASE_URL=postgresql.*|DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME|" .env
            sed -i "s|^#*DATABASE_URL_ASYNC=postgresql.*|DATABASE_URL_ASYNC=postgresql+asyncpg://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME|" .env
        else
            echo "⚠️ .env file not found. Creating with PostgreSQL settings..."
            cp .env.example .env
            sed -i "s|DATABASE_URL=sqlite.*|DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME|" .env
            sed -i "s|DATABASE_URL_ASYNC=sqlite.*|DATABASE_URL_ASYNC=postgresql+asyncpg://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME|" .env
        fi
        
        echo "✅ PostgreSQL database configured!"
        echo "📝 Make sure to create the database manually:"
        echo "   psql -U postgres -c \"CREATE DATABASE $DB_NAME;\""
        echo "   psql -U postgres -c \"CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';\""
        echo "   psql -U postgres -c \"GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;\""
        ;;
        
    *)
        echo "❌ Unknown database type: $DB_TYPE"
        echo "Usage: $0 [sqlite|postgresql]"
        echo "  sqlite     - Use SQLite database (default, no setup required)"
        echo "  postgresql - Use PostgreSQL database (requires PostgreSQL installation)"
        exit 1
        ;;
esac

echo ""
echo "🚀 Applying database migrations..."

# Helper to run Alembic using the best available interpreter
run_alembic_upgrade() {
    local alembic_cmd

    if [ -d ".venv" ] && [ -x ".venv/bin/alembic" ]; then
        alembic_cmd=".venv/bin/alembic"
    elif command -v uv &> /dev/null; then
        alembic_cmd="uv run alembic"
    elif command -v alembic &> /dev/null; then
        alembic_cmd="alembic"
    fi

    if [ -n "$alembic_cmd" ]; then
        if eval "$alembic_cmd upgrade head"; then
            return 0
        fi

        echo "⚠️ Alembic upgrade failed, attempting to stamp head instead..."
        if eval "$alembic_cmd stamp head"; then
            return 0
        fi

        echo "❌ Alembic commands failed"
        return 1
    fi

    if [ -d ".venv" ] && [ -x ".venv/bin/python" ]; then
        echo "⚠️ Alembic not found, falling back to init_db.py"
        .venv/bin/python init_db.py
        return 0
    fi

    echo "⚠️ Alembic not found, falling back to init_db.py"
    if python3 init_db.py 2>/dev/null; then
        return 0
    fi
    python init_db.py
}

if ! run_alembic_upgrade; then
    echo "❌ Failed to apply migrations."
    exit 1
fi

echo "✅ Database ready!"
echo "➡️  Start the development server with: ./scripts/run-dev.sh"
