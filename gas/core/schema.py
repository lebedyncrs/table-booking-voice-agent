import abc

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel, abc.ABC):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)
