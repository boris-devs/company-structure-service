from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	POSTGRES_HOST: str = "db"
	POSTGRES_PORT: int = 5432
	POSTGRES_USER: str = "postgres"
	POSTGRES_PASSWORD: str = "postgres"
	POSTGRES_DB: str = "company_manager"
	LOG_LEVEL: str = "INFO"

	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

	@property
	def async_postgres_db_url(self):
		return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

	@property
	def sync_postgres_db_url(self):
		return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()