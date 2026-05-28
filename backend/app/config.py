from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    app_name: str = "MortgageSesame"
    app_env: str = "development"
    backend_url: str = "http://localhost:8000"
    public_site_url: str = "http://localhost:5173"
    admin_app_url: str = "http://localhost:5174"
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    # Database
    database_url: str = "postgresql+asyncpg://mortgagesesame:mortgagesesame@localhost:5432/mortgagesesame"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str = "CHANGE_ME"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # AI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o"
    ai_fast_model: str = "gpt-4o-mini"

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_agent_voice_name: str = ""

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "MortgageSesame"

    # Social
    instagram_access_token: str = ""
    instagram_business_account_id: str = ""
    tiktok_access_token: str = ""
    facebook_page_access_token: str = ""
    facebook_page_id: str = ""
    linkedin_access_token: str = ""
    google_business_account_id: str = ""

    # Storage
    storage_backend: str = "local"
    s3_bucket: str = ""
    s3_region: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Agent
    agent_api_key: str = "CHANGE_ME"
    agent_webhook_url: str = ""

    # Booking
    calendly_link: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
