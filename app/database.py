from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
import os


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DATABASE_URL, future=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
