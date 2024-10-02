from pydantic import BaseModel, Extra

class Config(BaseModel):
    osu_api_key: str = ""
    osu_refresh_interval: int = 2

    class Config:
        extra = Extra.ignore