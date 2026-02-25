"""
Dependency Injection Container.
"""

from dependency_injector import containers, providers

from src.core.di.modules.core import CoreContainer
from src.core.di.modules.instagram import InstagramContainer


class Container(containers.DeclarativeContainer):
    """
    Main Dependency Injection Container.
    
    Aggregates all modular containers and provides a centralized access point
    for the application's dependencies.
    """

    # Wiring configuration
    wiring_config = containers.WiringConfiguration(
        modules=[
            "src.instagram.services.instagram_service",
            "src.instagram.services.instagram_account_service",
            "src.instagram.services.instagram_webhook_service",
            "src.instagram.services.webhook.owner_resolver",
            "src.main",
        ],
    )
    # Core Infrastructure
    core = providers.Container(CoreContainer)

    # Instagram Module
    instagram = providers.Container(InstagramContainer)
