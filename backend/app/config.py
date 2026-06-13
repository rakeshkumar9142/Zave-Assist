from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    appwrite_endpoint: str = "https://cloud.appwrite.io/v1"
    appwrite_project_id: str = ""
    appwrite_api_key: str = ""
    appwrite_database_id: str = "zave_assist"
    gemini_api_key: str = ""
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def appwrite_configured(self) -> bool:
        return bool(self.appwrite_project_id and self.appwrite_api_key)


settings = Settings()
