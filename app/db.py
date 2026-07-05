import os
from sqlmodel import SQLModel, Session
from dotenv import load_dotenv

load_dotenv()

_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crystalize.db")
_echo = os.getenv("DEBUG", "false").lower() == "true"

# Normaliza URL do PostgreSQL para asyncpg se necessário
# Railway/Heroku fornecem "postgresql://..." — SQLAlchemy async precisa de "postgresql+asyncpg://..."
if _DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in _DATABASE_URL:
    _DATABASE_URL = _DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

_is_postgres = _DATABASE_URL.startswith("postgresql")

if _is_postgres:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy.orm import Session as SASession

    engine = create_async_engine(_DATABASE_URL, echo=_echo)
    _async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create_db_and_tables():
        """Criar banco de dados e tabelas (async — PostgreSQL)."""
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def get_session():
        """Obter sessão async do banco de dados (PostgreSQL)."""
        async with _async_session_factory() as session:
            yield session

else:
    from sqlmodel import create_engine

    engine = create_engine(
        _DATABASE_URL,
        echo=_echo,
        connect_args={"check_same_thread": False},  # necessário para SQLite
    )

    def create_db_and_tables():
        """Criar banco de dados e tabelas (sync — SQLite)."""
        SQLModel.metadata.create_all(engine)

    def get_session():
        """Obter sessão do banco de dados (SQLite)."""
        with Session(engine) as session:
            yield session
