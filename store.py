"""Persistence: users, their book, every generated image, and an event log.

DATABASE_URL picks the database: Render Postgres in production, a local SQLite file when unset.
Images are stored in the database itself (JPEG, a few hundred KB each), so a book survives restarts and redeploys.
"""
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, create_engine,
                        func, select)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now():
    return datetime.now(timezone.utc)


def _url():
    url = os.environ.get("DATABASE_URL") or "sqlite:///storybook.db"
    # Render hands out postgres:// or postgresql:// URLs; SQLAlchemy needs the driver named.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


URL = _url()
engine = create_engine(URL, pool_pre_ping=True,
                       connect_args={"check_same_thread": False} if URL.startswith("sqlite") else {})
Session = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    google_sub: Mapped[str] = mapped_column(String(64), unique=True)  # Google's stable account id
    email: Mapped[str] = mapped_column(String(320))
    name: Mapped[str] = mapped_column(String(200), default="")
    picture: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Book(Base):
    """One book per user: the About Me details. The pictures live in Slot."""
    __tablename__ = "books"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(40), default="")
    age: Mapped[str] = mapped_column(String(3), default="")
    favorites: Mapped[str] = mapped_column(String(300), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Slot(Base):
    """One picture in a user's book: the cast reference, the cover, or a page."""
    __tablename__ = "slots"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    slot: Mapped[str] = mapped_column(String(20), primary_key=True)
    state: Mapped[str] = mapped_column(String(10), default="idle")  # idle | queued | drawing | done | error
    image: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=0)  # bumps on every new picture; busts the browser cache
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Event(Base):
    """Log of every image call (and sign-ins, PDFs). Also backs the hourly rate limit, so it survives restarts."""
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(20))      # image | login | pdf
    slot: Mapped[str] = mapped_column(String(20), default="")
    ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # None while an image is still drawing
    seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


Base.metadata.create_all(engine)


def aware(dt):
    """SQLite drops the timezone; treat stored times as UTC."""
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def upsert_user(sub, email, name, picture):
    with Session() as s:
        u = s.scalar(select(User).where(User.google_sub == sub))
        if u is None:
            u = User(google_sub=sub, email=email)
            s.add(u)
        u.email, u.name, u.picture, u.last_login = email, name or "", picture or "", now()
        s.commit()
        return u


def get_user(user_id):
    with Session() as s:
        return s.get(User, user_id)


def get_book(user_id):
    with Session() as s:
        book = s.get(Book, user_id) or Book(user_id=user_id, name="", age="", favorites="")
        slots = {x.slot: x for x in s.scalars(select(Slot).where(Slot.user_id == user_id))}
        return book, slots


def save_details(user_id, name, age, favorites):
    with Session() as s:
        b = s.get(Book, user_id)
        if b is None:
            b = Book(user_id=user_id)
            s.add(b)
        b.name, b.age, b.favorites = name, age, favorites
        s.commit()


def set_slot(user_id, slot, **fields):
    with Session() as s:
        x = s.get(Slot, (user_id, slot))
        if x is None:
            x = Slot(user_id=user_id, slot=slot, version=0, state="idle", error="")
            s.add(x)
        if "image" in fields:
            x.version = (x.version or 0) + 1
        for k, v in fields.items():
            setattr(x, k, v)
        s.commit()


def slot_image(user_id, slot):
    with Session() as s:
        x = s.get(Slot, (user_id, slot))
        return x.image if x else None


def log_event(kind, user_id=None, slot="", ok=None, seconds=None, detail=""):
    with Session() as s:
        e = Event(kind=kind, user_id=user_id, slot=slot, ok=ok, seconds=seconds, detail=detail[:2000])
        s.add(e)
        s.commit()
        return e.id


def finish_event(event_id, ok, seconds, detail=""):
    with Session() as s:
        e = s.get(Event, event_id)
        e.ok, e.seconds, e.detail = ok, seconds, detail[:2000]
        s.commit()


def images_in_last_hour(user_id):
    with Session() as s:
        return s.scalar(select(func.count(Event.id)).where(
            Event.user_id == user_id, Event.kind == "image", Event.created_at >= now() - timedelta(hours=1)))


def typical_seconds(slot_kind, default):
    """Median-ish time for recent successful image calls, so the progress bar can estimate how far along it is."""
    with Session() as s:
        q = select(Event.seconds).where(Event.kind == "image", Event.ok.is_(True))
        q = q.where(Event.slot == "ref") if slot_kind == "ref" else q.where(Event.slot != "ref")
        times = sorted(s.scalars(q.order_by(Event.id.desc()).limit(25)))
    return times[len(times) // 2] if times else default
