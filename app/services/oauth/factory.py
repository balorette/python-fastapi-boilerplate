"""OAuth provider factory for creating provider instances."""


from app.core.exceptions import ValidationError
from app.services.oauth.base import BaseOAuthProvider
from app.services.oauth.google import GoogleOAuthProvider


class OAuthProviderFactory:
    """Factory for creating OAuth provider instances."""

    _providers: dict[str, type[BaseOAuthProvider]] = {
        "google": GoogleOAuthProvider,
        # Future providers can be added here:
        # "entra": EntraIDOAuthProvider,
        # "okta": OktaOAuthProvider,
    }

    @classmethod
    def create_provider(cls, provider_name: str) -> BaseOAuthProvider:
        """Create an OAuth provider instance.
        
        Args:
            provider_name: Name of the OAuth provider (google, entra, okta)
            
        Returns:
            BaseOAuthProvider: Instance of the requested provider
            
        Raises:
            ValidationError: If provider is not supported
        """
        provider_class = cls._providers.get(provider_name.lower())

        if not provider_class:
            supported = list(cls._providers.keys())
            raise ValidationError(
                f"Unsupported OAuth provider: {provider_name}. "
                f"Supported providers: {', '.join(supported)}"
            )

        return provider_class()

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported OAuth providers."""
        return list(cls._providers.keys())

    @classmethod
    def register_provider(cls, name: str, provider_class: type[BaseOAuthProvider]) -> None:
        """Register a new OAuth provider.
        
        Args:
            name: Provider name
            provider_class: Provider class that implements BaseOAuthProvider
        """
        cls._providers[name.lower()] = provider_class
