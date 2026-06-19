from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session
from app.core.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)


class BaseAgent:
    def __init__(self):
        self.session: AsyncSession | None = None

    async def __aenter__(self):
        self.session = async_session()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
