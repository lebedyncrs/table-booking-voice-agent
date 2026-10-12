import httpx

from gas.core.redis import redis_session
from gas.core.settings import get_settings
from gas.models.delivery import DeliveryAddress, GisAddress


class GeocodingError(Exception): ...


async def geocode(address: DeliveryAddress) -> GisAddress:
    formatted_address = f"{address.street} {address.building}, {address.city} {address.country}"

    cache_key = f"geocode:{formatted_address.strip().lower().replace(' ', '_')}"

    async with redis_session() as redis:
        data = await redis.get(cache_key)
        if data:
            return GisAddress.model_validate_json(data)

    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": formatted_address, "key": get_settings().GOOGLE_MAPS_API_KEY},
        )
        res.raise_for_status()

    try:
        result = res.json()["results"][0]
        address_components = {c["types"][0]: c["long_name"] for c in result["address_components"]}
        geocoded_address = GisAddress(
            country=address_components["country"],
            city=address_components["locality"],
            street=address_components["route"],
            building=address_components["street_number"],
            latitude=result["geometry"]["location"]["lat"],
            longitude=result["geometry"]["location"]["lng"],
            postal_code=address_components.get("postal_code"),
        )
    except (KeyError, IndexError) as err:
        raise GeocodingError() from err

    async with redis_session() as redis:
        await redis.set(cache_key, geocoded_address.model_dump_json(by_alias=True))
    return geocoded_address
