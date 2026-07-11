from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    dev_torn_player_id: int
    xanax_item_id: int
    dev_torn_player_name: str = "the developer"
    jwt_secret: str
    api_key_encryption_secret: str
    frontend_origin: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
