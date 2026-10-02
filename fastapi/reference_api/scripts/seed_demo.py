"""Seed demo data: `python -m scripts.seed_demo` (idempotent).

Same users, password and shape as Django's `manage.py seed_demo`, so the
client demos behave the same against either backend.
"""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.models import User
from app.auth.security import hash_password
from app.core.config import get_settings
from app.posts.models import Comment, Post

DEMO_USERS = [("ada@example.com", "Ada"), ("grace@example.com", "Grace")]
DEMO_PASSWORD = "demo-password-123"  # noqa: S105 - documented demo credential, local data only


async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessionmaker() as session, session.begin():
            users = []
            for email, name in DEMO_USERS:
                user = await session.scalar(select(User).where(User.email == email))
                if user is None:
                    user = User(
                        email=email,
                        display_name=name,
                        password_hash=hash_password(DEMO_PASSWORD, settings),
                    )
                    session.add(user)
                    await session.flush()
                users.append(user)

            if await session.scalar(
                select(Post.id).where(Post.author_id.in_([u.id for u in users]))
            ):
                print("Demo data already present.")  # noqa: T201 - CLI output
                return

            now = datetime.now(UTC)
            for index in range(45):
                created = now - timedelta(hours=index)
                post = Post(
                    author_id=users[index % 2].id,
                    title=f"Demo post {index + 1}",
                    body=f"Body of demo post {index + 1}.",
                    status="published",
                    published_at=created,
                    created_at=created,
                    updated_at=created,
                )
                session.add(post)
                await session.flush()
                for number in range(index % 4):
                    session.add(
                        Comment(
                            post_id=post.id,
                            author_id=users[(index + number + 1) % 2].id,
                            body=f"Comment {number + 1}",
                        )
                    )
        print(f"Seeded 45 posts. Sign in as {DEMO_USERS[0][0]} / {DEMO_PASSWORD}")  # noqa: T201
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
