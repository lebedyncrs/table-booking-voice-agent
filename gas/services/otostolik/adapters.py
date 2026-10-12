from typing import Any, Literal

from gas import constants
from gas.models.cart import CartProductItem
from gas.models.menu import Menu

# from gas.services.otostolik.menu_parser import ADDITIONAL_FIELDS_TYPE_SET

_PAYMENT_METHODS = {
    constants.PaymentMethods.CASH: "cash",
    constants.PaymentMethods.CARD: "card_on_place",
}
_PAYMENT_METHODS_REVERSED = {v: k for k, v in _PAYMENT_METHODS.items()}


def adapt_payment_method(payment_method: str, target: Literal["own", "remote"]):
    mapper = _PAYMENT_METHODS if target == "remote" else _PAYMENT_METHODS_REVERSED
    return mapper[payment_method]  # type: ignore


_DELIVERY_METHODS = {
    constants.DeliveryMethods.PICKUP: "takeout",
    constants.DeliveryMethods.ON_ADDRESS: "delivery",
}
_DELIVERY_METHODS_REVERSED = {v: k for k, v in _DELIVERY_METHODS.items()}


def adapt_delivery_method(payment_method: str, target: Literal["own", "remote"]):
    mapper = _DELIVERY_METHODS if target == "remote" else _DELIVERY_METHODS_REVERSED
    return mapper[payment_method]  # type: ignore


def adapt_own_products_to_otostolik(
    items: list[CartProductItem],
    parsed_menu: Menu,
) -> list[dict[str, Any]]:
    """Convert OUR products format to restaurant API format."""
    api_format_products = []

    for item in items:
        product = item.product

        category = parsed_menu.get_category(product.category_id)

        parent_product = None
        variants = []
        if product.parent_id:
            try:
                parent_product = parsed_menu.get_product(product.parent_id)
                variants = parsed_menu.get_product_variants(product.parent_id)
            except KeyError:
                pass

        if parent_product:
            product_name = f"{parent_product.name} {product.name}"
        else:
            product_name = product.name

        api_product = {
            "desc": product.description or "",
            "name": product_name,
            "price": product.price,
            "category": category.name if category else "",
            "amount": item.quantity,
            "selectedAdditionalFields": [],
            "notes": item.notes or "",
        }

        if product.parent_id and variants:
            api_product["priceOptions"] = [{"name": v.name, "price": v.price} for v in variants]

        if item.modifiers:
            grouped_modifiers = {}
            for modifier_item in item.modifiers:
                option = modifier_item.option
                try:
                    modifier = parsed_menu.get_modifier(option.modifier_id)
                    group_name = modifier.name

                    if group_name not in grouped_modifiers:
                        grouped_modifiers[group_name] = []

                    grouped_modifiers[group_name].append(
                        {"name": option.name, "quantity": modifier_item.quantity}
                    )
                except KeyError:
                    continue

            if grouped_modifiers:
                formatted_modifiers: list[str] = []
                for group_name, modifier_items in grouped_modifiers.items():
                    modifier_list = ", ".join(
                        [f"{item['quantity']}x{item['name']}" for item in modifier_items]
                    )
                    formatted_modifiers.append(f"{group_name}: {modifier_list}")

                api_product["selectedAdditionalFields"] = formatted_modifiers

        api_format_products.append(api_product)

    return api_format_products
