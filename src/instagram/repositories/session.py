from datetime import datetime
import redis.asyncio as redis
from src.instagram.models.webhook import UserSession
from src.core.config.settings import settings


class SessionRepository:
    """
    Repositório de sessões usando Redis.
    """

    def __init__(self):
        self._redis = redis.Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            password=settings.redis.password,
            db=settings.redis.db,
            decode_responses=True
        )
        self._ttl = 86400  # 24h

    async def get(self, user_id: str) -> UserSession:
        data = await self._redis.get(f"session:{user_id}")
        if data:
            return UserSession.model_validate_json(data)
        
        # Se não existir, cria uma nova e salva
        new_session = UserSession(user_id=user_id)
        await self.save(new_session)
        return new_session

    async def save(self, session: UserSession) -> None:
        session.updated_at = datetime.utcnow()
        await self._redis.set(
            f"session:{session.user_id}",
            session.model_dump_json(),
            ex=self._ttl
        )

    async def reset(self, user_id: str) -> None:
        new_session = UserSession(user_id=user_id)
        await self.save(new_session)

    async def delete(self, user_id: str) -> None:
        await self._redis.delete(f"session:{user_id}")
