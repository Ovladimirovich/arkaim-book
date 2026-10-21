"""config -- unified project configuration."""

from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent
CORE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT / "runtime"

dotenv_path = RUNTIME_DIR / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)


class Config:
    PROJECT_ROOT: Path = ROOT
    RUNTIME_DIR: Path = RUNTIME_DIR
    BASE_DIR: Path = CORE_DIR
    KNOWLEDGE_DIR: Path = CORE_DIR / "KNOWLEDGE"
    GENOME_DIR: Path = CORE_DIR / "GENOME"
    CHROMA_DIR: Path = CORE_DIR / "CHROMA_DB"
    SOURCE_OF_TRUTH: Path = CORE_DIR / "SOURCE_OF_TRUTH"
    MEMORY_DIR: Path = RUNTIME_DIR / "memory"
    DRAFTS_DIR: Path = RUNTIME_DIR / "data" / "drafts"
    PROMPTS_DIR: Path = RUNTIME_DIR / "prompts"
    SKILLS_DIR: Path = RUNTIME_DIR / "skills"

    # ── Knowledge M5/M6/M7 (конфликты, рассуждения, исправления) ─────────
    KNOWLEDGE_RUNTIME_DATA_DIR: Path = RUNTIME_DIR / "runtime_data" / "knowledge"

    @classmethod
    def knowledge_repo_dir(cls, env_name: str) -> Path:
        """Единый путь к репозиторию M5/M6/M7.

        Env-переменная (KNOWLEDGE_CONFLICT_DIR / KNOWLEDGE_REASONING_DIR /
        KNOWLEDGE_CORRECTION_DIR) имеет приоритет над общим каталогом.
        Значение читается при каждом вызове, чтобы динамическое
        переопределение в тестах работало.
        """
        value = os.getenv(env_name, "").strip()
        return Path(value) if value else cls.KNOWLEDGE_RUNTIME_DATA_DIR

    GATEWAY_HOST: str = os.getenv("GATEWAY_HOST", "127.0.0.1")
    GATEWAY_PORT: int = int(os.getenv("GATEWAY_PORT", "8080"))
    CORE_HOST: str = os.getenv("CORE_HOST", "127.0.0.1")
    CORE_PORT: int = int(os.getenv("CORE_PORT", "8642"))

    HERMES_URL: str = os.getenv("HERMES_URL", f"http://{GATEWAY_HOST}:{GATEWAY_PORT}")
    HERMES_API_KEY: str = os.getenv("HERMES_API_KEY", "hermes-local-dev-key")

    GIGACHAT_CLIENT_ID: str = os.getenv("GIGACHAT_CLIENT_ID", "")
    GIGACHAT_CLIENT_SECRET: str = os.getenv("GIGACHAT_CLIENT_SECRET", "")
    GIGACHAT_SCOPE: str = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    GIGACHAT_TOKEN: str = os.getenv("GIGACHAT_TOKEN", "")
    GIGACHAT_VERIFY_SSL: bool = (
        os.getenv("GIGACHAT_VERIFY_SSL", "true").lower() == "true"
    )

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    PROVIDER_CHAIN = os.getenv("PROVIDER_CHAIN", "gigachat,openrouter").split(",")

    API_PORT: int = int(os.getenv("API_PORT", "9090"))
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "GigaChat-Pro")
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL", "intfloat/multilingual-e5-small"
    )
    APP_TITLE: str = "Arkaim Book Intelligence"
    APP_VERSION: str = "1.0.0"

    ALLOWED_ORIGINS: list = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    API_KEYS: list = [
        k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()
    ]
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "change-me-in-production")
    AUTH_DB_PATH: str = os.getenv(
        "AUTH_DB_PATH", str(RUNTIME_DIR / "memory" / "data" / "auth.db")
    )

    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_BOT_USERNAME: str = os.getenv("TELEGRAM_BOT_USERNAME", "")
    TELEGRAM_ADMIN_CHAT_ID: str = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    GENOME_VERSION: str = "1.0.0"

    # ── ComfyUI (локальный или Colab Cloudflare Tunnel) ──────────────
    COMFYUI_URL: str = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
    MIN_VALIDATION_SCORE: float = 0.7

    # ── Email / SMTP ───────────────────────────────────
    EMAIL_MODE: str = os.getenv("EMAIL_MODE", "mock").strip().lower()
    SMTP_HOST: str = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "").strip()
    SMTP_PASS: str = os.getenv("SMTP_PASS", "").strip()
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "").strip()
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@arkaim.local").strip()
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "Arkaim").strip()
    EMAIL_DIGEST_INTERVAL: int = int(
        os.getenv("EMAIL_DIGEST_INTERVAL", "604800")
    )  # 7 дней

    # ── Crowdfunding ───────────────────────────────────
    CROWDFUNDING_ENABLED: bool = (
        os.getenv("CROWDFUNDING_ENABLED", "true").lower() == "true"
    )
    CROWDFUNDING_URLS: str = os.getenv("CROWDFUNDING_URLS", "[]")
    CROWDFUNDING_CHECK_INTERVAL: int = int(
        os.getenv("CROWDFUNDING_CHECK_INTERVAL", "3600")
    )
    CROWDFUNDING_WEBHOOK_URL: str = os.getenv("CROWDFUNDING_WEBHOOK_URL", "")
    CROWDFUNDING_USER_AGENT: str = os.getenv("CROWDFUNDING_USER_AGENT", "")


config = Config()
