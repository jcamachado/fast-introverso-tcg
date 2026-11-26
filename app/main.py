# app/main.py (excerpt showing the relevant parts)
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from io import BytesIO
import os
import re
import shutil
import uuid
import zipfile
from datetime import datetime
from typing import List, Optional
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# IMPORTANT: These imports should be in this order
from app.database import engine, Base, get_db
from app.models import User, Card
from app.auth import hash_password, verify_password, authenticate_user, get_current_user, get_current_admin_user
from app.admin import setup_admin
from app.tcgdex import (
    TCGdexUnavailable,
    get_card,
    search_cards,
    serialize_card_details,
    serialize_card_result,
)
from app.crop_utils import card_name_from_filename, is_jpeg_upload

app = FastAPI(title="TCG Collection Manager")

# Static files
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Setup admin - wrap in try/except for safety
try:
    setup_admin(app)
    print("✓ Admin panel mounted at /admin")
except Exception as e:
    print(f"⚠️ Admin setup failed: {e}")
    print("Continuing without admin panel...")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ====== AUTH ROUTES ======

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Invalid credentials"}
        )
    
    response = RedirectResponse(url="/home", status_code=303)
    response.set_cookie(key="user_id", value=str(user.id))
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("user_id")
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "is_register": True})

@app.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    # Check if user exists
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "is_register": True, "error": "Username already exists"}
        )
    
    # Create user
    new_user = User(
        username=username,
        password_hash=hash_password(password),
        is_admin=False
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    response = RedirectResponse(url="/login", status_code=303)
    response.set_cookie(key="user_id", value=str(new_user.id))
    return response

# ====== CRUD ROUTES ======

@app.get("/home", response_class=HTMLResponse)
async def home(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("home.html", {"request": request, "user": current_user})

@app.get("/cards", response_class=HTMLResponse)
async def list_cards(
    request: Request, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Card).where(Card.owner_id == current_user.id)
        .order_by(Card.name)
    )
    cards = result.scalars().all()
    
    # Add image placeholder logic
    for card in cards:
        if not card.picture_path or not os.path.exists(f"static/{card.picture_path}"):
            card.has_image = False
        else:
            card.has_image = True
    
    return templates.TemplateResponse(
        "cards.html", 
        {"request": request, "cards": cards, "user": current_user}
    )

@app.post("/cards/share")
async def share_cards(
    request: Request,
    selected_ids: Optional[List[int]] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not selected_ids:
        return RedirectResponse(url="/cards", status_code=303)
    
    result = await db.execute(
        select(Card).where(Card.id.in_(selected_ids), Card.owner_id == current_user.id)
    )
    cards = result.scalars().all()
    
    lines = []
    for card in cards:
        # Flatten all fields into a string
        fields = [
            card.name,
            card.variant or "",
            card.collection_name or "",
            card.number or "",
            card.collection_number or "",
            card.picture_path or "",
            str(card.quantity),
            str(card.value),
            json.dumps(card.extra_data) if card.extra_data else ""
        ]
        lines.append(" | ".join(fields))
    
    output = "\n".join(lines)
    filename = f"shared_cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    # Save to file
    os.makedirs("static/exports", exist_ok=True)
    with open(f"static/exports/{filename}", "w") as f:
        f.write(output)
    
    return PlainTextResponse(output, media_type="text/plain")

@app.get("/cards/create", response_class=HTMLResponse)
async def create_card_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("create.html", {"request": request, "user": current_user})

@app.get("/api/tcgdex/cards")
async def search_tcgdex_cards(
    q: str,
    current_user: User = Depends(get_current_user)
):
    query = q.strip()
    if len(query) < 2 or len(query) > 80:
        raise HTTPException(status_code=422, detail="Search terms must be 2 to 80 characters.")

    try:
        cards = await search_cards(query)
    except TCGdexUnavailable as error:
        raise HTTPException(
            status_code=502,
            detail="TCGdex is unavailable. Please try again later."
        ) from error

    return [serialize_card_result(card) for card in cards]

@app.get("/api/tcgdex/cards/{card_id}")
async def get_tcgdex_card(
    card_id: str,
    current_user: User = Depends(get_current_user)
):
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", card_id):
        raise HTTPException(status_code=422, detail="Invalid TCGdex card ID.")

    try:
        card = await get_card(card_id)
    except TCGdexUnavailable as error:
        raise HTTPException(
            status_code=502,
            detail="TCGdex is unavailable. Please try again later."
        ) from error

    if card is None:
        raise HTTPException(status_code=404, detail="TCGdex card not found.")

    return serialize_card_details(card)

@app.get("/cards/crop_card", response_class=HTMLResponse)
async def crop_card_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    return templates.TemplateResponse(
        "crop_cards.html",
        {
            "request": request,
            "user": current_user
        }
    )

async def read_cropped_uploads(names: List[str], pictures: List[UploadFile]):
    if not pictures or len(names) != len(pictures):
        raise HTTPException(
            status_code=422,
            detail="Each cropped image must have a matching filename."
        )

    uploads = []
    for name, picture in zip(names, pictures):
        try:
            card_name = card_name_from_filename(name)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        content = await picture.read()
        if not is_jpeg_upload(picture.content_type, content):
            raise HTTPException(
                status_code=415,
                detail="Cropped images must be JPEG files."
            )
        uploads.append((card_name, content))
    return uploads

@app.post("/api/crops/save")
async def save_cropped_cards(
    names: List[str] = Form(...),
    pictures: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    uploads = await read_cropped_uploads(names, pictures)
    cards = []
    written_paths = []
    os.makedirs("static/uploads", exist_ok=True)

    try:
        for name, content in uploads:
            filename = f"{uuid.uuid4().hex}.jpg"
            file_path = os.path.join("static", "uploads", filename)
            written_paths.append(file_path)
            with open(file_path, "wb") as image_file:
                image_file.write(content)
            cards.append(Card(
                name=name,
                picture_path=f"uploads/{filename}",
                owner_id=current_user.id
            ))

        db.add_all(cards)
        await db.commit()
    except Exception:
        await db.rollback()
        for file_path in written_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
        raise

    return {
        "cards": [
            {"id": card.id, "name": card.name}
            for card in cards
        ]
    }

@app.post("/api/crops/download")
async def download_cropped_cards(
    names: List[str] = Form(...),
    pictures: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    uploads = await read_cropped_uploads(names, pictures)
    archive = BytesIO()
    used_names = set()

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for name, content in uploads:
            archive_name = f"{name}.jpg"
            suffix = 2
            while archive_name in used_names:
                archive_name = f"{name} ({suffix}).jpg"
                suffix += 1
            used_names.add(archive_name)
            zip_file.writestr(archive_name, content)

    return Response(
        content=archive.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="cropped-cards.zip"'}
    )

@app.post("/cards/create")
async def create_card(
    request: Request,
    name: str = Form(...),
    variant: Optional[str] = Form(None),
    collection_name: Optional[str] = Form(None),
    number: Optional[str] = Form(None),
    collection_number: Optional[str] = Form(None),
    quantity: int = Form(1),
    value: float = Form(0.0),
    extra_data: Optional[str] = Form(None),
    picture: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Handle image upload
    picture_path = None
    if picture and picture.filename:
        # Clean filename
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{picture.filename}"
        file_path = f"static/uploads/{filename}"
        content = await picture.read()
        with open(file_path, "wb") as f:
            f.write(content)
        picture_path = f"uploads/{filename}"
    
    # Parse extra_data
    extra_data_dict = {}
    if extra_data:
        try:
            extra_data_dict = json.loads(extra_data)
        except:
            pass
    
    new_card = Card(
        name=name,
        variant=variant,
        collection_name=collection_name,
        number=number,
        collection_number=collection_number,
        picture_path=picture_path,
        quantity=quantity,
        value=value,
        extra_data=extra_data_dict,
        owner_id=current_user.id
    )
    
    db.add(new_card)
    await db.commit()
    
    return RedirectResponse(url="/cards", status_code=303)

@app.get("/cards/edit/{card_id}", response_class=HTMLResponse)
async def edit_card_page(
    request: Request,
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Card).where(Card.id == card_id, Card.owner_id == current_user.id)
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    return templates.TemplateResponse(
        "edit.html", 
        {"request": request, "card": card, "user": current_user}
    )

@app.post("/cards/edit/{card_id}")
async def edit_card(
    request: Request,
    card_id: int,
    name: str = Form(...),
    variant: Optional[str] = Form(None),
    collection_name: Optional[str] = Form(None),
    number: Optional[str] = Form(None),
    collection_number: Optional[str] = Form(None),
    quantity: int = Form(1),
    value: float = Form(0.0),
    extra_data: Optional[str] = Form(None),
    picture: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Card).where(Card.id == card_id, Card.owner_id == current_user.id)
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Update fields
    card.name = name
    card.variant = variant
    card.collection_name = collection_name
    card.number = number
    card.collection_number = collection_number
    card.quantity = quantity
    card.value = value
    
    if extra_data:
        try:
            card.extra_data = json.loads(extra_data)
        except:
            pass
    
    # Handle image upload
    if picture and picture.filename:
        # Delete old image if exists
        if card.picture_path and os.path.exists(f"static/{card.picture_path}"):
            os.remove(f"static/{card.picture_path}")
        
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{picture.filename}"
        file_path = f"static/uploads/{filename}"
        content = await picture.read()
        with open(file_path, "wb") as f:
            f.write(content)
        card.picture_path = f"uploads/{filename}"
    
    card.updated_at = datetime.utcnow()
    await db.commit()
    
    return RedirectResponse(url="/cards", status_code=303)

@app.post("/cards/delete/{card_id}")
async def delete_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify ownership
    result = await db.execute(
        select(Card).where(Card.id == card_id, Card.owner_id == current_user.id)
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Delete image if exists
    if card.picture_path and os.path.exists(f"static/{card.picture_path}"):
        os.remove(f"static/{card.picture_path}")
    
    await db.delete(card)
    await db.commit()
    
    return RedirectResponse(url="/cards", status_code=303)


# app/main.py - Add these routes

@app.get("/register-admin", response_class=HTMLResponse)
async def register_admin_page(request: Request):
    """Show admin registration form"""
    return templates.TemplateResponse(
        "register_admin.html", 
        {"request": request}
    )

@app.post("/register-admin")
async def register_admin(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    admin_secret: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Create a new admin user"""
    # Check if admin secret matches
    ADMIN_SECRET = os.getenv("ADMIN_SETUP_KEY", "change-me-in-production")
    
    if admin_secret != ADMIN_SECRET:
        return templates.TemplateResponse(
            "register_admin.html", 
            {
                "request": request, 
                "error": "Invalid admin secret key"
            }
        )
    
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        return templates.TemplateResponse(
            "register_admin.html", 
            {
                "request": request, 
                "error": "Username already exists"
            }
        )
    
    # Create admin user
    new_user = User(
        username=username,
        password_hash=hash_password(password),
        is_admin=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Log them in immediately
    response = RedirectResponse(url="/home", status_code=303)
    response.set_cookie(key="user_id", value=str(new_user.id))
    return response