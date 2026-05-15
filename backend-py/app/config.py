from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_EXPIRES_IN: str = "24h"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    UPLOAD_DIR: str = "/data/uploads"
    CHROMA_PERSIST_DIR: str = "/data/chroma"
    MAX_FILE_SIZE: int = 104857600
    MAX_FILES_PER_PAPER: int = 50
    DEFAULT_FREE_GENERATIONS: int = 20
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""
    CORS_ORIGIN: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
