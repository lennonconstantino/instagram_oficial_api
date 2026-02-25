from dependency_injector import containers, providers
from src.core.di.modules.core import CoreContainer
from src.instagram.services.instagram import InstagramService
from src.instagram.repositories.session import SessionRepository
from src.instagram.handlers.chatbot import ChatbotHandler
from src.core.config.settings import settings

class InstagramContainer(containers.DeclarativeContainer):
    """
    Instagram Module Container.
    """
    
    # Dependência do container core
    core = providers.DependenciesContainer()

    # Repositories
    session_repository = providers.Singleton(
        SessionRepository,
        redis_client=core.redis_client
    )

    # Services
    instagram_service = providers.Factory(
        InstagramService,
        base_url=settings.instagram.base_url,
        token=settings.instagram.access_token,
    )

    # Handlers
    chatbot_handler = providers.Singleton(
        ChatbotHandler,
        service=instagram_service,
        sessions=session_repository,
    )
