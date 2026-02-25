from dependency_injector import containers, providers

from src.core.di.modules.core import CoreContainer
from src.instagram.repositories.impl.supabase_instagram_account_repository import SupabaseInstagramAccountRepository
from src.instagram.services.instagram_service import InstagramService
from src.instagram.services.instagram_account_service import InstagramAccountService
from src.instagram.services.webhook.owner_resolver import InstagramWebhookOwnerResolver
from src.instagram.services.instagram_webhook_service import InstagramWebhookService



class InstagramContainer(containers.DeclarativeContainer):
    """
    Instagram Module Container.
    """
    core = providers.Container(CoreContainer)

    # Repositories
    instagram_account_repository = providers.Selector(
        core.db_backend,
        supabase=providers.Factory(
            SupabaseInstagramAccountRepository,
            client=core.supabase_session,
        ),
    )

    # Services
    instagram_service = providers.Factory(
        InstagramService, instagram_account_repo=instagram_account_repository
    )

    instagram_account_service = providers.Factory(
        InstagramAccountService, repo=instagram_account_repository
    )

    instagram_webhook_owner_resolver = providers.Factory(
        InstagramWebhookOwnerResolver, instagram_account_service=instagram_account_service
    )

    instagram_webhook_service = providers.Factory(
        InstagramWebhookService,
        owner_resolver=instagram_webhook_owner_resolver,
        instagram_service=instagram_service,
    )
