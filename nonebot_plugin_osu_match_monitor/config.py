from nonebot import get_driver
from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    osu_api_key: str = ""
    osu_refresh_interval: int = 2


global_config = get_driver().config
config = Config.parse_obj(global_config.dict())

api_key = config.osu_api_key
refresh_interval = config.osu_refresh_interval