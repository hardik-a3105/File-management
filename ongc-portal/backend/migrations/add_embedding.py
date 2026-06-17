import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqlalchemy import text
from app.database import engine


async def run():
    async with engine.connect() as conn:
        await conn.execute(text("ALTER TABLE files ADD COLUMN IF NOT EXISTS embedding vector(384);"))
        await conn.commit()
        print("Added embedding column.")


asyncio.run(run())
