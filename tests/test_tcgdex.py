import unittest
from types import SimpleNamespace

from app.tcgdex import serialize_card_details


class TCGdexSerializationTests(unittest.TestCase):
    def test_details_map_to_collection_fields_and_keep_api_metadata(self):
        card = SimpleNamespace(
            id="swsh3-136",
            name="Pikachu",
            localId="136",
            variants=SimpleNamespace(
                normal=True,
                reverse=True,
                holo=False,
                firstEdition=False,
                wPromo=False,
            ),
            set=SimpleNamespace(
                id="swsh3",
                name="Darkness Ablaze",
                cardCount=SimpleNamespace(total=189),
            ),
            rarity="Common",
            category="Pokemon",
            hp=60,
            types=["Lightning"],
            get_image_url=lambda quality, extension: (
                f"https://assets.tcgdex.net/cards/{quality}.{extension}"
            ),
        )

        result = serialize_card_details(card)

        self.assertEqual(result["name"], "Pikachu")
        self.assertEqual(result["variant"], "Normal, Reverse")
        self.assertEqual(result["collection_name"], "Darkness Ablaze")
        self.assertEqual(result["number"], "swsh3-136")
        self.assertEqual(result["collection_number"], "136/189")
        self.assertEqual(result["image_url"], "https://assets.tcgdex.net/cards/high.jpg")
        self.assertEqual(result["extra_data"]["tcgdex_id"], "swsh3-136")
        self.assertEqual(result["extra_data"]["types"], ["Lightning"])


if __name__ == "__main__":
    unittest.main()
