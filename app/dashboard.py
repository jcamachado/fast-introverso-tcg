# app/dashboard.py
from fastadmin import DashboardWidgetAdmin, register
from sqlalchemy import select
from app.models import User, Card

@register
class StatsWidget(DashboardWidgetAdmin):
    title = "Collection Stats"
    widget_type = "info"
    
    async def get_context(self, request, session):
        total_users = await session.scalar(select(User).count())
        total_cards = await session.scalar(select(Card).count())
        total_value = await session.scalar(select(Card.value).sum()) or 0
        
        return {
            "total_users": total_users,
            "total_cards": total_cards,
            "total_value": f"${total_value:.2f}",
            "avg_cards_per_user": round(total_cards / total_users, 1) if total_users > 0 else 0
        }

@register
class RecentCardsWidget(DashboardWidgetAdmin):
    title = "Recent Cards"
    widget_type = "list"
    
    async def get_context(self, request, session):
        result = await session.execute(
            select(Card)
            .order_by(Card.created_at.desc())
            .limit(5)
        )
        recent_cards = result.scalars().all()
        
        return {
            "items": [
                {
                    "title": f"{card.name} ({card.collection_name or 'No Set'})",
                    "subtitle": f"Added by User #{card.owner_id}",
                    "icon": "fa-id-card"
                }
                for card in recent_cards
            ]
        }