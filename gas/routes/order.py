from collections import defaultdict
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import Field

from gas import constants
from gas.core.schema import Schema
from gas.dependencies import CurrentPosService
from gas.models.cart import Cart, CartProductItem, CartProductModifierOptionItem
from gas.models.delivery import DeliveryAddress, DeliveryInfo
from gas.models.menu import Menu, ProductModifierOption
from gas.services.base import OrderPriceInfo

router = APIRouter(prefix="/orders", tags=[constants.SwaggerTags.MCP])


class ConsistencyValidationError(Exception): ...


class ProductModifierSchema(Schema):
    id: int = Field(alias="modifier_option_id")
    quantity: int = 1


class ProductItemSchema(Schema):
    id: int = Field(alias="product_variant_id")
    quantity: int = 1
    modifiers: list[ProductModifierSchema] = Field(default_factory=list)
    notes: str | None = Field(None, description="Notes specific for this product")


class DeliveryPickupSchema(Schema):
    method: Literal["pickup"] = "pickup"


class DeliveryOnAddressSchema(DeliveryAddress):
    method: Literal["on_address"] = "on_address"


class CalculatePriceRequestSchema(Schema):
    items: list[ProductItemSchema]
    delivery: DeliveryOnAddressSchema | DeliveryPickupSchema


def validate_product(menu: Menu, product_item: ProductItemSchema) -> CartProductItem:
    try:
        product = menu.get_product(product_item.id)
    except KeyError as error:
        raise HTTPException(
            status_code=400, detail=f"Product with id {product_item.id} not found"
        ) from error

    modifiers = []
    available_modifier_options: dict[int, ProductModifierOption] = {}
    for modifier_id in product.modifiers_id:
        available_modifier_options.update(
            {item.id: item for item in menu.get_options_for_modifier(modifier_id)}
        )
    modifiers_options_quantity: dict[int, int] = defaultdict(int)
    for item in product_item.modifiers:
        if item.id not in available_modifier_options:
            raise HTTPException(
                status_code=400,
                detail=f"Modifier option with id {item.id} not permitted for product {product.id}",
            )
        option = available_modifier_options[item.id]
        if option.limit_min and item.quantity < option.limit_min:
            raise HTTPException(
                status_code=400, detail=f"Quantity is less than min limit for option {item.id}"
            )
        if option.limit_max and item.quantity > option.limit_max:
            raise HTTPException(
                status_code=400, detail=f"Quantity is greater than max limit for option {item.id}"
            )
        modifiers_options_quantity[option.modifier_id] += item.quantity
        modifiers.append(CartProductModifierOptionItem(option=option, quantity=item.quantity))

    for modifier_id in product.modifiers_id:
        modifier = menu.get_modifier(modifier_id)
        quantity = modifiers_options_quantity[modifier_id]
        if modifier.limit_min and modifier.limit_min > quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Options total quantity for modifier id {modifier_id} should be not less than {modifier.limit_min}. Current quantity {quantity}",
            )
        if modifier.limit_max and modifier.limit_max < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Options total quantity for modifier id {modifier_id} should be not greater than {modifier.limit_max}. Current quantity {quantity}",
            )

    return CartProductItem(
        product=product,
        quantity=product_item.quantity,
        notes=product_item.notes,
        modifiers=modifiers,
    )


@router.post(
    "/price",
    operation_id="calculate_order_price",
    response_model_exclude_none=True,
    response_model=OrderPriceInfo,
)
async def calculate_price(pos: CurrentPosService, payload: CalculatePriceRequestSchema):
    menu = await pos.get_menu()
    products = [validate_product(menu, item) for item in payload.items]
    delivery = payload.delivery if isinstance(payload.delivery, DeliveryOnAddressSchema) else None
    return await pos.calculate_price(products, delivery)


class CreateOrderSchema(Schema):
    items: list[ProductItemSchema]
    payment_method: constants.PaymentMethods
    delivery: DeliveryInfo
    notes: str = ""


@router.post("")
async def create_order(pos: CurrentPosService, payload: CreateOrderSchema):
    menu = await pos.get_menu()
    products = [validate_product(menu, item) for item in payload.items]
    await pos.create_order(Cart(items=products, **payload.model_dump(exclude={"items"})))
    return {"success": True}
