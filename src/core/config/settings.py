"""
Configuration module for the project.
Handles environment variables and application settings.
"""

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """API server settings."""

    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )
    use_fake_sender: bool = Field(
        default=False, description="Use fake sender in development environment"
    )
    bypass_subscription_check: bool = Field(
        default=False,
        description="Bypass subscription validation (Development only)",
    )

    model_config = SettingsConfigDict(
        env_prefix="API_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    backend: str = Field(default="supabase", description="Database backend (e.g. supabase)")

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class SupabaseSettings(BaseSettings):
    """Supabase connection settings."""

    url: str | None = Field(default=None, description="Supabase project URL")
    key: str | None = Field(default=None, description="Supabase anon key")
    service_key: str | None = Field(
        default=None, 
        description="Supabase service role key",
        validation_alias=AliasChoices("SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY")
    )
    db_schema: str = Field(
        default="public", description="Default database schema (e.g. public, app)"
    )
    project_ref: str | None = Field(default=None, description="Supabase project reference")
    anon_key: str | None = Field(default=None, description="Supabase anon key")

    model_config = SettingsConfigDict(
        env_prefix="SUPABASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

class InstagramSettings(BaseSettings):
    """Instagram settings."""

    access_token: str | None = Field(default=None, description="Instagram Access Token")
    app_id: str | None = Field(default=None, description="Instagram App ID")
    app_secret: str | None = Field(default=None, description="Instagram App Secret")
    verify_token: str | None = Field(default=None, description="Instagram Verify Token")
    api_version: str | None = Field(default=None, description="Instagram API Version")

    @property
    def base_url(self) -> str:
        return f"https://graph.instagram.com/{self.api_version}"

    model_config = SettingsConfigDict(
        env_prefix="INSTAGRAM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class RedisSettings(BaseSettings):
    """Redis connection settings."""

    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: str | None = Field(default=None, description="Redis password")
    db: int = Field(default=0, description="Redis DB")

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class Settings(BaseSettings):
    """Main application settings."""
    
    api: APISettings = Field(default_factory=APISettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    supabase: SupabaseSettings = Field(default_factory=SupabaseSettings)
    instagram: InstagramSettings = Field(default_factory=InstagramSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)


    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


# Global settings instance
settings = Settings()
