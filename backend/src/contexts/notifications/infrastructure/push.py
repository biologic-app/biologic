from functools import lru_cache

from src.contexts.notifications.application.push_dispatcher import PushDispatcher
from src.contexts.notifications.infrastructure.push_sender import WebPushSender
from src.core.config import get_settings
from src.core.database import get_session_factory


@lru_cache
def get_push_dispatcher() -> PushDispatcher:
    sender = WebPushSender(session_factory=get_session_factory(), settings=get_settings())
    return PushDispatcher(sender=sender)
