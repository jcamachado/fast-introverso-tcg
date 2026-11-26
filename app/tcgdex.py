import asyncio
from urllib.error import HTTPError, URLError

from tcgdexsdk import Query, TCGdex


class TCGdexUnavailable(Exception):
    pass


async def _run_sdk_call(call, *, missing_ok: bool = False):
    try:
        return await asyncio.to_thread(call)
    except HTTPError as error:
        if missing_ok and error.code == 404:
            return None
        raise TCGdexUnavailable from error
    except (URLError, TimeoutError) as error:
        raise TCGdexUnavailable from error


def _search_cards_sync(name: str):
    sdk = TCGdex("en")
    query = Query().contains("name", name).paginate(1, 10)
    return sdk.card.listSync(query)


async def search_cards(name: str):
    return await _run_sdk_call(lambda: _search_cards_sync(name))


def _get_card_sync(card_id: str):
    return TCGdex("en").card.getSync(card_id)


async def get_card(card_id: str):
    return await _run_sdk_call(lambda: _get_card_sync(card_id), missing_ok=True)


def serialize_card_result(card) -> dict:
    return {
        "id": card.id,
        "name": card.name,
        "local_id": card.localId,
        "image_url": card.get_image_url("high", "jpg"),
    }


def serialize_card_details(card) -> dict:
    variants = [
        label
        for field, label in (
            ("normal", "Normal"),
            ("reverse", "Reverse"),
            ("holo", "Holo"),
            ("firstEdition", "First Edition"),
            ("wPromo", "W Promo"),
        )
        if getattr(card.variants, field, False)
    ]

    return {
        "id": card.id,
        "name": card.name,
        "variant": ", ".join(variants),
        "collection_name": card.set.name,
        "number": card.id,
        "collection_number": f"{card.localId}/{card.set.cardCount.total}",
        "image_url": card.get_image_url("high", "jpg"),
        "extra_data": {
            "tcgdex_id": card.id,
            "set_id": card.set.id,
            "rarity": card.rarity,
            "category": card.category,
            "hp": card.hp,
            "types": card.types,
        },
    }


