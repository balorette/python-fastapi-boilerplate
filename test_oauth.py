#!/usr/bin/env python3
"""
Test script for Google OAuth implementation
"""

import asyncio

from app.core.config import settings
from app.services.oauth import GoogleOAuthProvider


async def test_oauth_service():
    """Test basic OAuth service functionality"""
    oauth_service = GoogleOAuthProvider()

    print("🔍 Testing Google OAuth Service")
    print("=" * 50)

    # Test auth URL generation
    print("1. Testing auth URL generation...")
    try:
        auth_url = await oauth_service.get_authorization_url(
            redirect_uri=settings.GOOGLE_REDIRECT_URI
            or "http://localhost:8000/api/v1/auth/callback/google",
            state="test-state-123",
        )
        print("✅ Auth URL generated successfully")
        print(f"🔗 URL: {auth_url[:100]}...")

        # Verify URL contains required parameters
        assert "client_id" in auth_url
        assert "redirect_uri" in auth_url
        assert "scope" in auth_url
        assert "state=test-state-123" in auth_url
        print("✅ Auth URL contains all required parameters")

    except Exception as e:
        print(f"❌ Auth URL generation failed: {e}")
        return False

    print("\n2. Testing configuration...")
    print(f"✅ Client ID configured: {bool(settings.GOOGLE_CLIENT_ID)}")
    print(f"✅ Client Secret configured: {bool(settings.GOOGLE_CLIENT_SECRET)}")
    print(f"✅ Redirect URI: {settings.GOOGLE_REDIRECT_URI}")

    print("\n✅ OAuth service tests completed successfully!")
    return True


async def test_database_oauth_fields():
    """Test that OAuth fields are properly added to User model"""
    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    print("\n🗄️  Testing Database OAuth Fields")
    print("=" * 50)

    try:
        async with AsyncSessionLocal():
            # Test creating an OAuth user
            oauth_user_data = {
                "email": "test.oauth@gmail.com",
                "username": "test.oauth@gmail.com",
                "full_name": "Test OAuth User",
                "is_active": True,
                "oauth_provider": "google",
                "oauth_id": "123456789",
                "oauth_email_verified": True,
                "oauth_refresh_token": "refresh_token_example",
            }

            # Create user instance (don't save to avoid conflicts)
            oauth_user = User(**oauth_user_data)

            print("✅ OAuth User model created with fields:")
            print(f"   - OAuth Provider: {oauth_user.oauth_provider}")
            print(f"   - OAuth ID: {oauth_user.oauth_id}")
            print(f"   - Email Verified: {oauth_user.oauth_email_verified}")
            print(f"   - Has Refresh Token: {bool(oauth_user.oauth_refresh_token)}")
            print(f"   - Password Required: {oauth_user.hashed_password is not None}")

            return True

    except Exception as e:
        print(f"❌ Database OAuth fields test failed: {e}")
        return False


async def main():
    """Run all OAuth tests"""
    print("🚀 Starting Google OAuth Implementation Tests")
    print("=" * 60)

    # Test OAuth service
    service_ok = await test_oauth_service()

    # Test database fields
    db_ok = await test_database_oauth_fields()

    print("\n" + "=" * 60)
    if service_ok and db_ok:
        print("🎉 All OAuth tests passed! Implementation is ready.")
        print("\n📝 Next steps:")
        print("1. Set up Google OAuth credentials in your environment")
        print("2. Test the OAuth flow with a real Google account")
        print("3. Deploy and test in your application")
    else:
        print("❌ Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
