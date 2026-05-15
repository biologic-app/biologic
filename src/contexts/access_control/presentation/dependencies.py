from uuid import UUID

from fastapi import Header


async def get_actor_id(x_actor_id: UUID = Header(alias="X-Actor-Id")) -> UUID:
    return x_actor_id
