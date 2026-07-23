import hashlib
import json
import os
import secrets
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware

from app.database import Base, SessionLocal, engine
from app.models import Card, User

os.environ.setdefault("ADMIN_PREFIX", "admin")
os.environ.setdefault("ADMIN_USER_MODEL", "User")
os.environ.setdefault("ADMIN_USER_MODEL_USERNAME_FIELD", "username")
os.environ.setdefault("ADMIN_SECRET_KEY", os.getenv("SESSION_SECRET_KEY", "dev-admin-secret"))
os.environ.setdefault("ADMIN_SESSION_COOKIE_SECURE", "false")

from fastadmin import SqlAlchemyModelAdmin, fastapi_app, register_admin_model_class  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

PLACEHOLDER_DATA_URI = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E"
    "%3Crect width='100' height='100' fill='%23ddd'/%3E"
    "%3Ctext x='50' y='54' text-anchor='middle' font-size='12' fill='%23666'%3ENo Image%3C/text%3E%3C/svg%3E"
)

app = FastAPI(title="Fast Introverso TCG")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "dev-session-secret"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/admin", fastapi_app)
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def hash_password(password: str, salt: str | None = None) -> str:
    use_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), use_salt.encode("utf-8"), 120000)
    return f"{use_salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, _ = stored_hash.split("$", 1)
    except ValueError:
        return False
    return hash_password(password, salt) == stored_hash


async def get_current_user(request: Request) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401)
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=401)
        return user


async def save_upload(upload: UploadFile | None) -> str | None:
    if not upload or not upload.filename:
        return None
    suffix = Path(upload.filename).suffix or ".bin"
    filename = f"{uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename
    with destination.open("wb") as file_obj:
        file_obj.write(await upload.read())
    return f"/static/uploads/{filename}"


class UserAdmin(SqlAlchemyModelAdmin):
    list_display = ("id", "username", "is_superuser")
    search_fields = ("username",)

    async def authenticate(self, username: str, password: str):
        async with self.get_sessionmaker() as session:
            user = await session.scalar(select(User).where(User.username == username))
        if user and verify_password(password, user.password_hash):
            return user.id
        return None


class CardAdmin(SqlAlchemyModelAdmin):
    list_display = (
        "id",
        "owner_id",
        "name",
        "variant",
        "collection_name",
        "number",
        "collection_number",
        "quantity",
        "value",
    )
    search_fields = ("name", "variant", "collection_name", "number", "collection_number")

    async def orm_get_list(self, *args, **kwargs):
        filters = dict(kwargs.get("filters") or {})
        if self.user and not getattr(self.user, "is_superuser", False):
            filters[("owner_id", "exact")] = self.user.id
        kwargs["filters"] = filters
        return await super().orm_get_list(*args, **kwargs)

    async def orm_get_obj(self, id):
        obj = await super().orm_get_obj(id)
        if obj is None:
            return None
        if self.user and not getattr(self.user, "is_superuser", False) and obj.owner_id != self.user.id:
            return None
        return obj

    async def orm_save_obj(self, id, payload):
        if self.user and not getattr(self.user, "is_superuser", False):
            payload["owner_id"] = self.user.id
        return await super().orm_save_obj(id, payload)


register_admin_model_class(UserAdmin, [User], sqlalchemy_sessionmaker=SessionLocal)
register_admin_model_class(CardAdmin, [Card], sqlalchemy_sessionmaker=SessionLocal)


@app.on_event("startup")
async def startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/auth/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/auth/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.username == username))
        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"}, 401)
        request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@app.post("/auth/register")
async def register(username: str = Form(...), password: str = Form(...)):
    async with SessionLocal() as session:
        existing = await session.scalar(select(User).where(User.username == username))
        if existing:
            return RedirectResponse(url="/auth/login", status_code=303)
        session.add(User(username=username, password_hash=hash_password(password)))
        await session.commit()
    return RedirectResponse(url="/auth/login", status_code=303)


@app.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=303)


@app.get("/apag")
async def create_card_page(request: Request):
    user = await get_current_user(request)
    return templates.TemplateResponse("create.html", {"request": request, "user": user})


@app.post("/apag")
async def create_card(
    request: Request,
    name: str = Form(...),
    variant: str = Form(""),
    collection_name: str = Form(""),
    number: str = Form(""),
    collection_number: str = Form(""),
    quantity: int = Form(1),
    value: float = Form(0.0),
    picture: UploadFile | None = File(None),
    extra_data: str = Form("{}"),
):
    user = await get_current_user(request)
    try:
        extra_json = json.loads(extra_data or "{}")
        if not isinstance(extra_json, dict):
            extra_json = {}
    except json.JSONDecodeError:
        extra_json = {}

    picture_path = await save_upload(picture)
    async with SessionLocal() as session:
        session.add(
            Card(
                owner_id=user.id,
                name=name,
                variant=variant,
                collection_name=collection_name,
                number=number,
                collection_number=collection_number,
                quantity=quantity,
                value=value,
                picture_path=picture_path,
                extra_data=extra_json,
            )
        )
        await session.commit()
    return RedirectResponse(url="/cards", status_code=303)


@app.get("/cards")
async def list_cards(request: Request):
    user = await get_current_user(request)
    async with SessionLocal() as session:
        cards = (await session.scalars(select(Card).where(Card.owner_id == user.id).order_by(Card.id.desc()))).all()

    return templates.TemplateResponse(
        "cards.html",
        {
            "request": request,
            "cards": cards,
            "placeholder_image": PLACEHOLDER_DATA_URI,
            "user": user,
        },
    )


@app.get("/cards/{card_id}/edit")
async def edit_card_page(card_id: int, request: Request):
    user = await get_current_user(request)
    async with SessionLocal() as session:
        card = await session.get(Card, card_id)
        if not card or card.owner_id != user.id:
            raise HTTPException(status_code=404)
    return templates.TemplateResponse("edit.html", {"request": request, "card": card, "user": user})


@app.post("/cards/{card_id}/edit")
async def edit_card(
    card_id: int,
    request: Request,
    name: str = Form(...),
    variant: str = Form(""),
    collection_name: str = Form(""),
    number: str = Form(""),
    collection_number: str = Form(""),
    quantity: int = Form(1),
    value: float = Form(0.0),
    picture: UploadFile | None = File(None),
    extra_data: str = Form("{}"),
):
    user = await get_current_user(request)
    async with SessionLocal() as session:
        card = await session.get(Card, card_id)
        if not card or card.owner_id != user.id:
            raise HTTPException(status_code=404)

        card.name = name
        card.variant = variant
        card.collection_name = collection_name
        card.number = number
        card.collection_number = collection_number
        card.quantity = quantity
        card.value = value
        if picture and picture.filename:
            card.picture_path = await save_upload(picture)
        try:
            payload = json.loads(extra_data or "{}")
            card.extra_data = payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            card.extra_data = {}
        await session.commit()

    return RedirectResponse(url="/cards", status_code=303)


@app.post("/cards/{card_id}/delete")
async def delete_card(card_id: int, request: Request):
    user = await get_current_user(request)
    async with SessionLocal() as session:
        card = await session.get(Card, card_id)
        if not card or card.owner_id != user.id:
            raise HTTPException(status_code=404)
        await session.delete(card)
        await session.commit()
    return RedirectResponse(url="/cards", status_code=303)


@app.post("/cards/share")
async def share_cards(request: Request, selected_ids: list[int] = Form(default=[])):
    user = await get_current_user(request)
    async with SessionLocal() as session:
        cards = (
            await session.scalars(select(Card).where(Card.owner_id == user.id, Card.id.in_(selected_ids)).order_by(Card.id))
        ).all()

    share_file = BASE_DIR / "shared_cards.txt"
    with share_file.open("w", encoding="utf-8") as handle:
        for card in cards:
            handle.write(
                f"Name={card.name}; Variant={card.variant}; CollectionName={card.collection_name}; "
                f"Number={card.number}; CollectionNumber={card.collection_number}; Quantity={card.quantity}; "
                f"Value={card.value}; ExtraData={json.dumps(card.extra_data, ensure_ascii=False)}\n"
            )

    return FileResponse(path=share_file, media_type="text/plain", filename="shared_cards.txt")
