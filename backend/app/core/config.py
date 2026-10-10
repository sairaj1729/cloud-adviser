import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Cloud Advisor V1 Backend"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "super_secret_jwt_key_change_in_production_12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "cloud_advisor"

    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    PLATFORM_AWS_ACCOUNT_ID: str = "123456789012"
    PLATFORM_AWS_IAM_ROLE_ARN: str = "arn:aws:iam::123456789012:role/CloudAdvisorBackendRole"

    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""

    GCP_PROJECT_ID: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
