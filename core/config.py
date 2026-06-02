import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # Railway provides postgres:// but SQLAlchemy requires postgresql://
    _raw_db_url: str = os.getenv("DATABASE_URL", "sqlite:///./askSashkoAi.db")
    database_url: str = _raw_db_url.replace("postgres://", "postgresql://", 1)

    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_pass: str = os.getenv("SMTP_PASS", "")
    owner_email: str = os.getenv("OWNER_EMAIL", "")

    daily_cost_cap_usd: float = float(os.getenv("DAILY_COST_CAP_USD", "1.0"))

    # Rate limits
    session_message_limit: int = 20
    ip_daily_message_limit: int = 40
    chat_burst_limit: str = "10/minute"       # slowapi — burst protection per IP
    contact_burst_limit: str = "5/hour"       # slowapi — anti-spam on contact forms

    # CORS — comma-separated origins for production
    # e.g. "https://asksashko.ai,https://www.asksashko.ai"
    allowed_origins_raw: str = os.getenv("ALLOWED_ORIGINS", "")

    # RAG
    chunk_size: int = 500
    chunk_overlap: int = 50
    rag_top_n: int = 5

    knowledge_resources_dir: str = "knowledge_resources"
    vector_store_dir: str = "vector_store"

    # Approved topics for the chatbot
    approved_topics: list[str] = [
        "professional background",
        "skills",
        "work experience",
        "projects",
        "work history",
        "education",
        "hobbies",
        "personal life",
        "technology opinions",
        "tech opinions",
        "how to contact",
        "contact",
        "career",
        "python",
        "backend",
        "ai",
        "machine learning",
        "developer",
        "portfolio",
    ]

    # OpenAI pricing (USD per 1M tokens) — used for cost tracking
    openai_input_cost_per_1m: float = 2.50   # gpt-4o input
    openai_output_cost_per_1m: float = 10.00  # gpt-4o output


settings = Settings()

# Parsed allowed origins list
ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in settings.allowed_origins_raw.split(",") if o.strip()]
    if settings.allowed_origins_raw
    else ["*"]
)

