import unittest

from app.crop_utils import card_name_from_filename, is_jpeg_upload


class CropUploadTests(unittest.TestCase):
    def test_card_name_uses_filename_without_path_or_extension(self):
        self.assertEqual(
            card_name_from_filename(r"C:\cards\Pikachu V.jpg"),
            "Pikachu V",
        )

    def test_card_name_is_limited_to_card_name_column_length(self):
        self.assertEqual(len(card_name_from_filename(f"{'A' * 110}.jpg")), 100)

    def test_card_name_rejects_empty_filename(self):
        with self.assertRaises(ValueError):
            card_name_from_filename("")

    def test_jpeg_upload_requires_jpeg_type_and_signature(self):
        self.assertTrue(is_jpeg_upload("image/jpeg", b"\xff\xd8\xffpayload"))
        self.assertFalse(is_jpeg_upload("image/png", b"\xff\xd8\xffpayload"))
        self.assertFalse(is_jpeg_upload("image/jpeg", b"not an image"))


if __name__ == "__main__":
    unittest.main()
