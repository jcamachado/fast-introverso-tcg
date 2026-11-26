# app/admin.py
from fastapi import FastAPI, Request
from fastadmin import ModelAdmin, register, fastapi_app
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import User, Card
from app.auth import get_current_user
from datetime import datetime

# ===== USER ADMIN =====
@register
class UserAdmin(ModelAdmin):
    model = User
    icon = "fa-users"
    list_display = ["id", "username", "email", "is_admin", "is_active", "created_at"]
    list_display_links = ["id", "username"]
    search_fields = ["username", "email"]
    list_filter = ["is_admin", "is_active", "created_at"]
    list_per_page = 25
    ordering = ["-created_at"]
    
    # Fields to show in detail view
    fields = ["username", "email", "is_admin", "is_active", "created_at", "updated_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    
    # Exclude fields from forms
    exclude = ["password_hash"]
    
    # Custom actions
    actions = ["make_admin", "remove_admin", "activate_users", "deactivate_users"]
    
    async def get_queryset(self, request: Request, session: AsyncSession):
        """Show all users to admins"""
        query = select(self.model)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def make_admin(self, request: Request, session: AsyncSession, ids: list):
        """Make selected users admin"""
        result = await session.execute(
            select(self.model).where(self.model.id.in_(ids))
        )
        users = result.scalars().all()
        for user in users:
            user.is_admin = True
        await session.commit()
        return f"{len(users)} users were made admin"
    
    async def remove_admin(self, request: Request, session: AsyncSession, ids: list):
        """Remove admin status from selected users"""
        result = await session.execute(
            select(self.model).where(self.model.id.in_(ids))
        )
        users = result.scalars().all()
        for user in users:
            # Don't remove admin from the last admin
            if user.is_admin:
                user.is_admin = False
        await session.commit()
        return f"{len(users)} users had admin status removed"
    
    async def activate_users(self, request: Request, session: AsyncSession, ids: list):
        """Activate selected users"""
        result = await session.execute(
            select(self.model).where(self.model.id.in_(ids))
        )
        users = result.scalars().all()
        for user in users:
            user.is_active = True
        await session.commit()
        return f"{len(users)} users activated"
    
    async def deactivate_users(self, request: Request, session: AsyncSession, ids: list):
        """Deactivate selected users"""
        result = await session.execute(
            select(self.model).where(self.model.id.in_(ids))
        )
        users = result.scalars().all()
        for user in users:
            user.is_active = False
        await session.commit()
        return f"{len(users)} users deactivated"

# ===== CARD ADMIN =====
@register
class CardAdmin(ModelAdmin):
    model = Card
    icon = "fa-id-card"
    list_display = ["id", "name", "variant", "collection_name", "quantity", "value", "owner", "created_at"]
    list_display_links = ["id", "name"]
    search_fields = ["name", "variant", "collection_name", "number", "collection_number"]
    list_filter = ["collection_name", "created_at", "owner_id"]
    list_per_page = 25
    ordering = ["-created_at", "name"]
    
    fields = [
        "name", "variant", "collection_name", "number", "collection_number",
        "quantity", "value", "owner", "picture_path", "extra_data",
        "created_at", "updated_at"
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    
    # Custom display
    async def owner(self, request: Request, obj: Card):
        """Display owner name instead of ID"""
        return f"User #{obj.owner_id}" if obj.owner_id else "Unknown"
    
    async def get_queryset(self, request: Request, session: AsyncSession):
        """Show all cards to admins"""
        query = select(self.model)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_context(self, request: Request, context: dict, session: AsyncSession):
        """Add extra context to the view"""
        context.update({
            "total_cards": await session.scalar(select(self.model).count()),
            "total_users": await session.scalar(select(User).count()),
        })
        return context

# ===== SETUP FUNCTION =====
def setup_admin(app):
    """Setup FastAdmin with custom configuration"""
    # Create admin app
    admin_app = fastapi_app(app)
    
    # Mount admin at /admin
    app.mount("/admin", admin_app)
    
    print("✓ Admin panel mounted at /admin")
    print("  • Users: /admin/user")
    print("  • Cards: /admin/card")
    
    return admin_app