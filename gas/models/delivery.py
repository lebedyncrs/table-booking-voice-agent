from pydantic import BaseModel, Field
from pydantic.types import FutureDatetime

from gas.constants import DeliveryMethods


class DeliveryAddress(BaseModel):
    country: str = "Poland"
    city: str
    street: str
    building: str = Field(examples=["1", "10B"])
    apartment: str | None = None
    notes: str | None = None


class GisAddress(BaseModel):
    country: str
    city: str
    street: str
    building: str
    latitude: float
    longitude: float
    postal_code: str | None = None


class DeliveryInfo(BaseModel):
    client_name: str
    phone: str
    at_time: FutureDatetime | None = Field(
        default=None, description="Deliver at specific time. null for as soon as possible"
    )
    notes: str | None = ""
    address: DeliveryAddress | None = None

    @property
    def method(self):
        return DeliveryMethods.ON_ADDRESS if self.address else DeliveryMethods.PICKUP
