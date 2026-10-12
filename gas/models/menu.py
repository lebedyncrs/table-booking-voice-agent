from functools import cached_property
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from gas.models.discount import Discount


class ProductModifierOption(BaseModel):
    id: int
    modifier_id: int
    external_id: str = ""
    name: str
    description: str | None = None
    price: float = 0
    limit_min: int | None = None
    limit_max: int | None = None

    def __hash__(self) -> int:
        return self.id


class ProductModifier(BaseModel):
    id: int
    external_id: str = ""
    name: str
    description: str | None = None
    limit_min: int | None = None
    limit_max: int | None = None

    def __hash__(self) -> int:
        return self.id


class Product(BaseModel):
    id: int
    external_id: str = ""
    parent_id: int | None = None
    category_id: int
    name: str
    description: str | None = None
    price: float
    modifiers_id: list[int] = Field(default_factory=list)

    def __hash__(self) -> int:
        return self.id


class Category(BaseModel):
    id: int
    external_id: str = ""
    name: str
    description: str | None = None

    def __hash__(self) -> int:
        return self.id


class Menu(BaseModel):
    categories: set[Category] = Field(default_factory=set)
    products: set[Product] = Field(default_factory=set)
    modifiers: set[ProductModifier] = Field(default_factory=set)
    modifier_options: set[ProductModifierOption] = Field(default_factory=set)

    def add_category(self, category: Category):
        self.categories.add(category)

    def add_product(self, product: Product):
        self.products.add(product)

    def add_modifier(self, modifier: ProductModifier):
        self.modifiers.add(modifier)

    def add_modifier_option(self, option: ProductModifierOption):
        self.modifier_options.add(option)

    def apply_discounts(self, *discounts: "Discount"):
        for discount in discounts:
            discount.apply(self)

    @cached_property
    def categories_dict(self):
        return {item.id: item for item in self.categories}

    @cached_property
    def products_dict(self):
        return {item.id: item for item in self.products}

    @cached_property
    def modifiers_dict(self):
        return {item.id: item for item in self.modifiers}

    @cached_property
    def modifier_options_dict(self):
        return {item.id: item for item in self.modifier_options}

    @cached_property
    def _category_products_id(self) -> dict[int, list[int]]:
        products_dict = {}
        for product in self.products:
            products_dict.setdefault(product.category_id, []).append(product.id)
        return products_dict

    @cached_property
    def _products_variants_id(self) -> dict[int, list[int]]:
        variants_dict = {}
        for product in self.products:
            if product.parent_id:
                variants_dict.setdefault(product.parent_id, []).append(product.id)
        return variants_dict

    @cached_property
    def _modifier_options_id(self) -> dict[int, list[int]]:
        modifiers_dict = {}
        for option in self.modifier_options:
            modifiers_dict.setdefault(option.modifier_id, []).append(option.id)
        return modifiers_dict

    def get_category(self, category_id: int):
        return self.categories_dict[category_id]

    def get_category_products(self, category_id: int):
        if category_id not in self._category_products_id:
            return []
        return [self.get_product(p_id) for p_id in self._category_products_id[category_id]]

    def get_product(self, product_id: int) -> Product:
        return self.products_dict[product_id]

    def get_product_variants(self, product_id: int) -> list[Product]:
        if product_id not in self._products_variants_id:
            return []
        return [self.get_product(v_id) for v_id in self._products_variants_id[product_id]]

    def get_modifier(self, modifier_id: int) -> ProductModifier:
        return self.modifiers_dict[modifier_id]

    def get_modifier_option(self, option_id: int) -> ProductModifierOption:
        return self.modifier_options_dict[option_id]

    def get_options_for_modifier(self, modifier_id: int) -> list[ProductModifierOption]:
        return [self.get_modifier_option(o_id) for o_id in self._modifier_options_id[modifier_id]]
