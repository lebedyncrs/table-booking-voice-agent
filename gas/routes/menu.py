from fastapi import APIRouter
from pydantic import Field

from gas import constants
from gas.core.schema import Schema
from gas.dependencies import CurrentPosService

router = APIRouter(tags=[constants.SwaggerTags.MCP, constants.SwaggerTags.MENU])


class ProductModifierOptionSchema(Schema):
    id: int = Field(alias="modifier_option_id")
    name: str
    description: str | None = None
    price: float
    limit_min: int | None = Field(
        None,
        alias="quantity_min",
        description="Defines minimum quantity of given modifier option. Value greater than 0 make this option required",
    )
    limit_max: int | None = Field(
        None, alias="quantity_max", description="Defines maximum quantity of given modifier option."
    )


class ProductModifierSchema(Schema):
    id: int = Field(alias="modifier_id")
    name: str
    description: str | None = None
    options: list[ProductModifierOptionSchema]
    limit_min: int | None = Field(
        None,
        alias="total_quantity_min",
        description=(
            "Defines minimum total quantity of options for given modifier. Value greater than 0 make this modifier required"
        ),
    )
    limit_max: int | None = Field(
        None,
        alias="total_quantity_max",
        description="Defines maximum total quantity of options for given modifier.",
    )


class ProductVariantSchema(Schema):
    id: int = Field(alias="variant_id")
    name: str
    description: str | None = None
    price: float
    modifiers_id: list[int]


class ProductSchema(Schema):
    name: str
    description: str | None = None
    variants: list[ProductVariantSchema]


class CategorySchema(Schema):
    id: int = Field(alias="category_id")
    name: str
    description: str | None = None
    products: list[ProductSchema]


class MenuSchema(Schema):
    categories: list[CategorySchema]
    modifiers: list[ProductModifierSchema]


@router.get(
    "/menu", operation_id="get_menu", response_model_exclude_none=True, response_model=MenuSchema
)
async def get_menu(pos: CurrentPosService):
    menu = await pos.get_menu()
    categories = []
    modifiers = []
    for category in menu.categories:
        products = []
        categories.append(dict(products=products, **category.model_dump()))
        for product in menu.get_category_products(category.id):
            if product.parent_id:
                continue
            variants = menu.get_product_variants(product.id)
            if not variants:
                variants = [product]
            products.append(
                dict(variants=variants, **product.model_dump()),
            )
    for modifier in menu.modifiers:
        options = []
        modifiers.append(dict(options=options, **modifier.model_dump()))
        for option in menu.get_options_for_modifier(modifier.id):
            options.append(option.model_dump())

    return MenuSchema.model_validate(
        {"categories": categories, "modifiers": modifiers}, by_name=True
    )
