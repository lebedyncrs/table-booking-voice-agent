from itertools import chain

from pydantic import BaseModel, Field

from .menu import Menu, Product, ProductModifierOption


class DiscountCondition(BaseModel):
    def match(self, menu: Menu, item: Product | ProductModifierOption):
        # TODO: implement me
        return True


class Discount(BaseModel):
    price: float = 0.0
    percent: int = 0
    conditions: list[DiscountCondition] = Field(default_factory=list)

    def _math_conditions(self, menu: Menu, item: Product | ProductModifierOption):
        for condition in self.conditions:
            if not condition.match(menu, item):
                return False
        return True

    def apply(self, menu: Menu):
        for item in chain(menu.products, menu.modifier_options):
            if self._math_conditions(menu, item):
                item.price -= item.price * (self.percent / 100) + self.price
