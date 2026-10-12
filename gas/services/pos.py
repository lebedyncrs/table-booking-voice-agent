from typing import Annotated

from fastapi import Header

from gas.services.base import AbstractPosService
from gas.services.otostolik.service import OtostolikService


async def get_company_pos_service(
    client_id: Annotated[int, Header(alias="x-client-id")] = 124,
) -> AbstractPosService:
    return OtostolikService(client_id)
