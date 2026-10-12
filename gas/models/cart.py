from datetime import datetime

from pydantic import BaseModel, Field

from gas import constants
from gas.models.delivery import DeliveryInfo
from gas.models.menu import Product, ProductModifierOption


class CartProductModifierOptionItem(BaseModel):
    option: ProductModifierOption
    quantity: int = 1


class CartProductItem(BaseModel):
    product: Product
    modifiers: list[CartProductModifierOptionItem]
    quantity: int = 1
    notes: str | None = None


class Cart(BaseModel):
    items: list[CartProductItem] = Field(default_factory=list)
    payment_method: constants.PaymentMethods
    delivery: DeliveryInfo
    created_at: datetime = Field(default_factory=datetime.now)
    notes: str | None = None
