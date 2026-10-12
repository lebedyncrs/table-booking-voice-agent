from enum import IntEnum, StrEnum


class SwaggerTags(StrEnum):
    MCP = "MCP"
    MENU = "Menu"
    CART = "Cart"
    ORDERS = "Orders"


class UserKind(IntEnum):
    USER = 1
    SERVICE = 2


class PosServiceType(IntEnum):
    LESZNOE = 1


HEADER_MCP_SESSION_ID_KEY = "mcp-session-id"
COOKIE_SESSION_ID_KEY = "session_id"


class Units(StrEnum):
    KILOGRAM = "kg"
    GRAM = "g"
    LITER = "l"
    MILLILITER = "ml"
    PIECE = "pc"


class PaymentMethods(StrEnum):
    CASH = "cash"
    CARD = "card"


class DeliveryMethods(StrEnum):
    ON_ADDRESS = "on_address"
    PICKUP = "pickup"
