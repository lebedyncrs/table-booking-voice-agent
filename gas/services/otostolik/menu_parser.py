import logging
import zlib
from collections import defaultdict
from collections.abc import Generator

from gas.models.menu import Category, Menu, Product, ProductModifier, ProductModifierOption

logger = logging.getLogger("otostolik.menu_parser")

MODIFIER_TYPE_MULTIPLE_CHOICE = "multiple-choice"
MODIFIER_TYPE_CHECKBOX = "checkbox"
MODIFIER_TYPE_SINGLE_CHOICE = "single-choice"
MODIFIER_TYPE_GLOBAL = "set"
MODIFIER_NOT_REQUIRED_OPTION_INDICATOR = "--"


def create_id(value: str) -> int:
    return zlib.crc32(value.strip().encode())


def parse_single_choice_modifier(
    modifier_data: dict,
) -> Generator[ProductModifier | ProductModifierOption, None, ProductModifier]:
    external_id = f"{MODIFIER_TYPE_SINGLE_CHOICE}:{modifier_data['name']}"
    modifier = ProductModifier(
        id=create_id(external_id),
        external_id=external_id,
        name=modifier_data["name"],
        limit_min=1,  # in single choice something always be selected 1 option
        limit_max=1,
    )
    yield modifier
    for option in modifier_data["value"].split(","):
        name = option.strip()
        if name == MODIFIER_NOT_REQUIRED_OPTION_INDICATOR:
            modifier.limit_min = None
            continue
        option_external_id = f"{external_id}:{name}"
        yield ProductModifierOption(
            id=create_id(option_external_id),
            external_id=option_external_id,
            modifier_id=modifier.id,
            name=name,
            price=modifier_data.get("addonPrice", 0.0),
            limit_max=1,
        )
    return modifier


def parse_modifier_checkbox_option(modifier: ProductModifier, modifier_option_data: dict):
    external_id = f"{MODIFIER_TYPE_CHECKBOX}:{modifier_option_data['name']}"
    return ProductModifierOption(
        id=create_id(f"{modifier.id}:{external_id}"),
        external_id=external_id,
        modifier_id=modifier.id,
        name=modifier_option_data["name"],
        price=modifier_option_data.get("addonPrice", 0.0),
        limit_max=1,
    )


def parse_multiple_choice_modifier(
    modifier_data: dict,
) -> Generator[ProductModifier | ProductModifierOption, None, ProductModifier]:
    external_id = f"{MODIFIER_TYPE_MULTIPLE_CHOICE}:{modifier_data['name']}"
    modifier = ProductModifier(
        id=create_id(external_id),
        external_id=external_id,
        name=modifier_data["name"],
        limit_max=modifier_data.get("max"),
    )
    yield modifier
    for option in modifier_data["value"].split(","):
        name = option.strip()
        option_external_id = f"{external_id}:{name}"
        yield ProductModifierOption(
            id=create_id(option_external_id),
            modifier_id=modifier.id,
            external_id=option_external_id,
            name=name,
            price=modifier_data.get("addonPrice", 0.0),
        )
    return modifier


def parse_global_modifier(
    modifier_data: dict,
) -> Generator[ProductModifier | ProductModifierOption]:
    checkbox_modifier_options: list[ProductModifierOption] = []
    checkbox_modifier_ext_id = f"{modifier_data['id']}:{MODIFIER_TYPE_CHECKBOX}"
    checkbox_modifier = ProductModifier(
        id=create_id(checkbox_modifier_ext_id),
        external_id=checkbox_modifier_ext_id,
        name=modifier_data["name"],
    )
    for modifier_item in modifier_data["items"]:
        if modifier_item["type"] == MODIFIER_TYPE_SINGLE_CHOICE:
            yield from parse_single_choice_modifier(modifier_item)
        elif modifier_item["type"] == MODIFIER_TYPE_MULTIPLE_CHOICE:
            yield from parse_multiple_choice_modifier(modifier_item)
        elif modifier_item["type"] == MODIFIER_TYPE_CHECKBOX:
            option = parse_modifier_checkbox_option(checkbox_modifier, modifier_item)
            checkbox_modifier_options.append(option)
            yield option
        else:
            logger.warning(f"Unsupported modifier type {modifier_item['type']}")

    if checkbox_modifier_options:
        yield checkbox_modifier


def parse_product(
    product_data: dict, category_id: int, global_modifiers: dict
) -> Generator[Product | ProductModifier | ProductModifierOption]:
    product_modifiers_id: list[int] = []
    checkbox_modifier_options: list[ProductModifierOption] = []
    checkbox_modifier = ProductModifier(
        id=create_id(f"{MODIFIER_TYPE_CHECKBOX}:{product_data['name']}"),
        name="",
    )
    for product_modifier_data in product_data.get("additionalFields") or []:
        if product_modifier_data["type"] == MODIFIER_TYPE_GLOBAL:
            product_modifiers_id.extend(global_modifiers[product_modifier_data["value"]])
        elif product_modifier_data["type"] == MODIFIER_TYPE_SINGLE_CHOICE:
            modifier = yield from parse_single_choice_modifier(product_modifier_data)
            product_modifiers_id.append(modifier.id)
            yield modifier
        elif product_modifier_data["type"] == MODIFIER_TYPE_MULTIPLE_CHOICE:
            modifier = yield from parse_multiple_choice_modifier(product_modifier_data)
            product_modifiers_id.append(modifier.id)
            yield modifier
        elif product_modifier_data["type"] == MODIFIER_TYPE_CHECKBOX:
            option = parse_modifier_checkbox_option(checkbox_modifier, product_modifier_data)
            checkbox_modifier_options.append(option)
            yield option

    if checkbox_modifier_options:
        product_modifiers_id.append(checkbox_modifier.id)
        yield checkbox_modifier

    product = Product(
        id=create_id(product_data["name"]),
        external_id=product_data["name"],
        category_id=category_id,
        name=product_data["name"],
        description=product_data.get("desc"),
        price=product_data.get("price", 0.0),
        modifiers_id=product_modifiers_id,
    )
    yield product

    for variant_data in product_data.get("priceOptions") or []:
        product_variant = Product(
            id=create_id(f"{product.id}:{variant_data['name']}"),
            external_id=variant_data["name"],
            category_id=category_id,
            parent_id=product.id,
            name=variant_data["name"],
            description=product_data.get("desc"),
            price=variant_data["price"],
            modifiers_id=product_modifiers_id,
        )
        yield product_variant


def iter_otostolik_menu(
    menu_data: dict,
) -> Generator[Category | Product | ProductModifier | ProductModifierOption]:
    global_modifiers: dict[str, list[int]] = defaultdict(list)
    for modifier_data in menu_data.get("addonFieldsSets", []):
        for modifier in parse_global_modifier(modifier_data):
            if isinstance(modifier, ProductModifier):
                global_modifiers[modifier_data["id"]].append(modifier.id)
            yield modifier

    for category_data in menu_data.get("categories", []):
        category = Category(
            id=create_id(category_data["name"]),
            external_id=category_data["name"],
            name=category_data["name"],
        )
        yield category

        for product_data in category_data.get("items", []):
            if product_data.get("isDisabled", False):
                continue
            yield from parse_product(product_data, category.id, global_modifiers)


def parse_menu(menu_data: dict):
    menu = Menu()
    for item in iter_otostolik_menu(menu_data):
        if isinstance(item, Category):
            menu.add_category(item)
        elif isinstance(item, Product):
            menu.add_product(item)
        elif isinstance(item, ProductModifier):
            menu.add_modifier(item)
        elif isinstance(item, ProductModifierOption):
            menu.add_modifier_option(item)
        else:
            raise ValueError(f"Unexpected menu item type {type(item)}")
    return menu
