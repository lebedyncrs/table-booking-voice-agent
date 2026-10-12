from typing import Annotated

from fastapi import Depends
from redis.asyncio.client import Redis

from gas.core.auth import get_session_id
from gas.core.redis import get_redis_session
from gas.core.settings import SettingsSchema, get_settings
from gas.services.base import AbstractPosService
from gas.services.pos import get_company_pos_service

Settings = Annotated[SettingsSchema, Depends(get_settings)]
RedisSession = Annotated[Redis, Depends(get_redis_session)]
CurrentSessionId = Annotated[str, Depends(get_session_id)]


CurrentPosService = Annotated[AbstractPosService, Depends(get_company_pos_service)]
