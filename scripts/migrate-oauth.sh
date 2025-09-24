#!/bin/bash

# OAuth Migration Script
# Upgrades existing installations to include Google OAuth support

set -e

echo "🔄 Migrating to Google OAuth Support..."
echo "=" * 50

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "❌ No virtual environment found. Please run setup first:"
    echo "   ./scripts/setup-dev.sh"
    exit 1
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Activated venv"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Activated .venv"
fi

# Install OAuth dependencies
echo "📦 Installing Google OAuth dependencies..."
if command -v uv &> /dev/null; then
    echo "   Using uv (fast)..."
    uv pip install google-auth>=2.23.0 google-auth-oauthlib>=1.1.0
else
    echo "   Using pip..."
    pip install google-auth>=2.23.0 google-auth-oauthlib>=1.1.0
fi

# Update .env file with OAuth variables if they don't exist
echo "🔐 Updating environment configuration..."
if [ -f ".env" ]; then
    if ! grep -q "GOOGLE_CLIENT_ID" .env; then
        echo "" >> .env
        echo "# Google OAuth Configuration" >> .env
        echo "GOOGLE_CLIENT_ID=your-google-client-id" >> .env
        echo "GOOGLE_CLIENT_SECRET=your-google-client-secret" >> .env
        echo "GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/oauth/google/callback" >> .env
        echo "✅ Added OAuth environment variables to .env"
        echo "⚠️  Please update .env with your actual Google OAuth credentials"
    else
        echo "✅ OAuth environment variables already exist in .env"
    fi
else
    echo "❌ .env file not found. Please create one:"
    echo "   cp .env.example .env"
    exit 1
fi

# Run database migration to add OAuth fields
echo "🗄️  Updating database schema..."
if [ -f "alembic.ini" ]; then
    # Check if migration already exists
    if ! ls alembic/versions/*oauth* >/dev/null 2>&1; then
        echo "   Creating OAuth migration..."
        alembic revision --autogenerate -m "Add OAuth fields to User model"
    fi
    
    echo "   Applying migrations..."
    alembic upgrade head
    echo "✅ Database updated with OAuth fields"
else
    echo "❌ Alembic not configured. Database migration skipped."
fi

# Test OAuth service
echo "🧪 Testing OAuth integration..."
python -c "
try:
    from app.services.oauth import GoogleOAuthService
    oauth_service = GoogleOAuthService()
    auth_url, state = oauth_service.generate_auth_url('test-migration')
    print('✅ OAuth service working correctly')
except Exception as e:
    print(f'❌ OAuth service test failed: {e}')
    exit(1)
"

echo ""
echo "=" * 50
echo "🎉 OAuth Migration Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Set up Google OAuth in Google Cloud Console:"
echo "   - Create OAuth 2.0 Client ID"
echo "   - Enable Google+ API"
echo "   - Add redirect URI: http://localhost:8000/api/v1/auth/oauth/google/callback"
echo ""
echo "2. Update your .env file with actual Google OAuth credentials"
echo ""
echo "3. Test the OAuth endpoints:"
echo "   - GET  /api/v1/auth/oauth/google/authorize"
echo "   - POST /api/v1/auth/oauth/google/callback"
echo ""
echo "4. View documentation:"
echo "   - OAUTH_IMPLEMENTATION.md - Complete OAuth guide"
echo "   - README.md - Updated with OAuth information"
echo ""
echo "✨ Your API now supports both local and Google OAuth authentication!"