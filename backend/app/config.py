import os
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
    database_url: str = "sqlite+aiosqlite:///./mortgagesesame.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str = "CHANGE_ME"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # FRED (Freddie Mac PMMS weekly rate data + Prime Rate for HELOC)
    # Free key at: https://fred.stlouisfed.org/docs/api/api_key.html
    fred_api_key: str = ""
    # HELOC = Prime Rate + this spread (Prime currently ~8.5%, so HELOC ~9.0%)
    heloc_prime_spread: float = 0.5

    # AI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o"
    ai_fast_model: str = "gpt-4o-mini"

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_agent_voice_name: str = ""
    agent_persona_name: str = ""       # what the voice agent calls itself

    # SignalWire
    signalwire_account_sid: str = ""
    signalwire_auth_token: str = ""
    signalwire_from_number: str = ""
    signalwire_space: str = ""

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = ""
    campaign_from_name: str = ""       # defaults to banker_name if empty
    campaign_from_email: str = ""      # defaults to smtp_user if empty

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

    # Internal admin seed (auto-created on startup if not exists)
    admin_seed_email: str = ""
    admin_seed_password: str = ""
    admin_seed_full_name: str = ""
    admin_seed_nmls_id: str = ""

    # Booking
    calcom_link: str = ""

    # Image generation — AI avatar / flyer creation
    avatar_provider: str = "auto"       # auto | openai | fal | replicate | passthrough
    fal_api_key: str = ""               # fal.ai — face-consistent generation (flux-pulid)
    replicate_api_token: str = ""       # Replicate — backup image generation
    media_storage_path: str = "./media" # local path for all generated files

    # Content pipeline mode switches
    campaign_video_provider: str = "mock"   # mock | heygen
    content_publish_mode: str = "mock"      # mock | live
    campaign_email_provider: str = "mock"   # mock | gmail | resend | sendgrid
    campaign_sms_provider: str = "mock"     # mock | signalwire | twilio
    campaign_direct_mail_provider: str = "mock"  # mock | lob | postgrid
    campaign_property_provider: str = "mock"     # mock | attom

    # Background removal
    remove_bg_api_key: str = ""         # remove.bg — 50 free/month, any Python version

    # Flyer compositing provider
    flyer_composer: str = "pillow"      # pillow | bannerbear (falls back to pillow on error)
    bannerbear_api_key: str = ""
    bannerbear_template_social_square: str = ""
    bannerbear_template_facebook_banner: str = ""
    bannerbear_template_story: str = ""
    bannerbear_template_wide_banner: str = ""

    # Banker identity — must be set in .env for each deployment
    banker_name: str = ""
    banker_nmls: str = ""
    app_1003_url: str = ""
    zillow_url: str = ""
    service_states: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        extra = "ignore"


settings = Settings()
