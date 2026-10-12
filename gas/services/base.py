import abc

from pydantic import BaseModel

from gas.models.cart import Cart, CartProductItem
from gas.models.delivery import DeliveryAddress, GisAddress
from gas.models.menu import Menu


class OrderPriceInfo(BaseModel):
    products_price: float
    delivery_price: float
    total_price: float
    has_min_cart_value: bool
    min_cart_amount: float | None


class DeliveryServiceable(BaseModel):
    address: GisAddress
    price: float
    min_order_for_paid_delivery: float = 0
    min_order_for_free_delivery: float = 0


class DeliveryNotServiceable(BaseModel):
    reason: str
    address: GisAddress | None = None


class AbstractPosService(abc.ABC):
    @abc.abstractmethod
    async def get_menu(self) -> Menu: ...

    @abc.abstractmethod
    async def create_order(self, cart: Cart) -> None: ...

    @abc.abstractmethod
    async def calculate_price(
        self, items: list[CartProductItem], delivery_address: DeliveryAddress | None = None
    ) -> OrderPriceInfo: ...

    @abc.abstractmethod
    async def check_delivery_address(
        self, address: DeliveryAddress
    ) -> DeliveryServiceable | DeliveryNotServiceable: ...
