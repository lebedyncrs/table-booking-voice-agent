import json
import logging

import httpx
from fastapi import HTTPException

from gas.core.redis import redis_session
from gas.models.cart import Cart, CartProductItem
from gas.models.delivery import DeliveryAddress
from gas.models.discount import Discount
from gas.models.menu import Menu
from gas.services.base import (
    DeliveryNotServiceable,
    DeliveryServiceable,
    OrderPriceInfo,
)
from gas.services.geocoding import GeocodingError, geocode
from gas.services.otostolik.adapters import (
    adapt_delivery_method,
    adapt_own_products_to_otostolik,
    adapt_payment_method,
)
from gas.services.otostolik.menu_parser import parse_menu
from gas.services.pos import AbstractPosService


class OtostolikService(AbstractPosService):
    logger = logging.getLogger("services.pos.otostolik")

    def __init__(self, restaurant_id: int):
        self.restaurant_id = restaurant_id
        self._http_client = httpx.AsyncClient(
            base_url=f"https://api.colesznoje.pl/api/restaurants/{restaurant_id}"
        )

    async def _get_restaurant_data(self):
        key = f"otostolik_restaurant_data:{self.restaurant_id}"
        async with redis_session() as redis:
            data = await redis.get(key)
            if data:
                return json.loads(data)

        res = await self._http_client.get("")
        res.raise_for_status()
        data = res.json()
        value = {
            "menu": data["menu"],
            "name": data["name"],
            "location": data["location"],
            "status": data["status"],
            "phone": data["phone"],
            "min_cart_amount": data["config"]["orders"]["delivery"]["minCartAmount"],
            "full_menu_discount": data.get("config", {})
            .get("orders", {})
            .get("discountPercent", 0),
        }
        async with redis_session() as redis:
            await redis.set(key, json.dumps(value), ex=10 * 60)
        return value

    async def get_menu(self) -> Menu:
        restaurant_data = await self._get_restaurant_data()
        menu = parse_menu(restaurant_data["menu"])
        full_menu_discount = restaurant_data.get("full_menu_discount")
        if full_menu_discount:
            menu.apply_discounts(Discount(percent=full_menu_discount))
        return menu

    async def create_order(
        self,
        cart: Cart,
    ) -> None:
        menu = await self.get_menu()
        otostolik_products = adapt_own_products_to_otostolik(cart.items, menu)
        delivery = cart.delivery
        address_dict = {}
        if delivery.address:
            gis_address = await geocode(delivery.address)
            address_dict.update(delivery.address.model_dump())
            address_dict.update(gis_address.model_dump())

        delivery_type = adapt_delivery_method(delivery.method, target="remote")
        order_pricing = await self.calculate_price(cart.items, delivery.address)

        # Convert datetime to ISO format string for JSON serialization
        delivery_at: str = ""
        if delivery.at_time is not None:
            delivery_at = delivery.at_time.isoformat()

        payload = {
            "customer": {
                "customer_firstname": delivery.client_name,
                "customer_lastname": "-",
                "phone": delivery.phone,
                "email": "",
                "cutleryPreferences": "",
                "notes": f"{cart.notes or ''} {delivery.notes or ''}".strip(),
                "delivery": delivery_type,
                "allowMarketing": False,
                "allowSms": False,
                "city": address_dict.get("city", ""),
                "street": address_dict.get("street", ""),
                "house": address_dict.get("building", ""),
                "flat": address_dict.get("apartment", ""),
                "allowEmail": False,
                "deliveryAt": delivery_at,
            },
            "products": otostolik_products,
            "payment_type": adapt_payment_method(cart.payment_method, target="remote"),
            "delivery_type": delivery_type,
            "source": "web_app",
            "price": order_pricing.products_price,
            "delivery_cost": order_pricing.delivery_price,
        }
        self.logger.debug("Order create request payload: %s", json.dumps(payload))
        res = await self._http_client.post("/orders", json=payload)
        try:
            res.raise_for_status()
        except httpx.HTTPStatusError:
            self.logger.exception(f"Response: {res.content.decode()}")
            raise

    async def check_delivery_address(
        self, address: DeliveryAddress
    ) -> DeliveryServiceable | DeliveryNotServiceable:
        try:
            gis_address = await geocode(address)
        except GeocodingError:
            return DeliveryNotServiceable(reason="Geocoding error, address not found")

        res = await self._http_client.get(
            "distance",
            params={"lng": gis_address.longitude, "lat": gis_address.latitude},
        )
        res.raise_for_status()
        data = res.json()
        if data["delivering"]:
            return DeliveryServiceable(
                price=data.get("price", 0),
                address=gis_address,
                min_order_for_paid_delivery=data.get("minCartAmount"),
                min_order_for_free_delivery=data.get("freeDeliveryFrom"),
            )
        return DeliveryNotServiceable(reason="Out of delivery area")

    async def calculate_price(
        self,
        items: list[CartProductItem],
        delivery_address: DeliveryAddress | None = None,
    ) -> OrderPriceInfo:
        delivery_price = 0.0
        products_price = 0.0
        has_min_cart_value = True
        min_cart_amount = None
        for item in items:
            item_price = item.product.price + sum(
                modifier.option.price * modifier.quantity for modifier in item.modifiers
            )
            products_price += item_price * item.quantity

        if delivery_address:
            delivery_info = await self.check_delivery_address(delivery_address)
            if isinstance(delivery_info, DeliveryNotServiceable):
                raise HTTPException(status_code=400, detail=delivery_info.reason)
            restaurant_data = await self._get_restaurant_data()
            delivery_price = delivery_info.price
            has_min_cart_value = products_price >= restaurant_data["min_cart_amount"]
            min_cart_amount = restaurant_data["min_cart_amount"]

        return OrderPriceInfo(
            products_price=round(products_price, 2),
            delivery_price=round(delivery_price, 2),
            total_price=round(products_price + delivery_price, 2),
            has_min_cart_value=has_min_cart_value,
            min_cart_amount=min_cart_amount,
        )
