# app/admin.py
from fastadmin import register, ModelAdmin
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Card
from app.auth import get_current_user

@register
class UserAdmin(ModelAdmin):
    model = User
    icon = "fa-user"
    
    list_display = ["id", "username", "is_admin", "created_at"]
    search_fields = ["username"]
    list_filter = ["is_admin"]

@register
class CardAdmin(ModelAdmin):
    model = Card
    icon = "fa-id-card"
    list_display = ["id", "name", "variant", "collection_name", "quantity", "value", "owner_id", "created_at"]
    search_fields = ["name", "variant", "collection_name"]
    list_filter = ["collection_name"]
    
    async def get_queryset(self, request: Request, session: AsyncSession):
        """Apply row-level isolation - non-admin users only see their own cards"""
        user = await get_current_user(request)
        query = select(self.model)
        if not user.is_admin:
            query = query.where(self.model.owner_id == user.id)
        result = await session.execute(query)
        return result.scalars().all()

def setup_admin(app):
    # For FastAdmin 0.4.0, just pass the app
    # The @register decorators handle registration automatically
    pass