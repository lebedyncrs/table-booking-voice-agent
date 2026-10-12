from typing import Literal

from fastapi import APIRouter
from pydantic import Field

from gas import constants
from gas.core.schema import Schema
from gas.dependencies import CurrentPosService
from gas.models.delivery import DeliveryAddress
from gas.services.base import DeliveryServiceable

router = APIRouter(tags=[constants.SwaggerTags.MCP])


class DeliveryServiceableSchema(Schema):
    serviceable: Literal[True] = True
    price: float
    min_order_for_paid_delivery: float = 0
    min_order_for_free_delivery: float = 0


class DeliveryNotServiceableSchema(Schema):
    serviceable: Literal[False] = False
    reason: str


class CheckDeliveryResponse(Schema):
    address: DeliveryAddress
    info: DeliveryServiceableSchema | DeliveryNotServiceableSchema = Field(
        discriminator="serviceable"
    )


@router.post(
    "/delivery/check",
    operation_id="check_delivery_for_address",
    response_model=CheckDeliveryResponse,
)
async def check_delivery_for_address(pos: CurrentPosService, payload: DeliveryAddress):
    delivery_info = await pos.check_delivery_address(payload)

    info_schema = (
        DeliveryServiceableSchema
        if isinstance(delivery_info, DeliveryServiceable)
        else DeliveryNotServiceableSchema
    )

    address = payload.model_dump()
    if delivery_info.address:
        address.update(delivery_info.address.model_dump())
    return {
        "address": address,
        "info": info_schema(**delivery_info.model_dump()),
    }
