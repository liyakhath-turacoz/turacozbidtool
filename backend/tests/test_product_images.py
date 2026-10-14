import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
import uuid
import asyncio

from fastapi import HTTPException
from backend import main
from backend.scripts.collect_product_images import Collector, model_match_score


class ProductImageTests(unittest.TestCase):
    def test_local_image_resolver_rejects_paths_and_urls_outside_product_folder(self):
        valid = "/product-images/12345678-1234-1234-1234-123456789abc.webp"
        self.assertEqual(main.local_product_image_path(valid).name, "12345678-1234-1234-1234-123456789abc.webp")
        for value in ("/product-images/../secret.webp", "/product-images/a.webp?x=1", "https://example.com/a.webp", "/private/a.webp"):
            self.assertIsNone(main.local_product_image_path(value))

    def test_product_api_accepts_local_image_and_rejects_unsafe_urls(self):
        base = {"name": "Example Model", "category": "Phones", "brand": "Example", "location": "Delhi"}
        self.assertEqual(main.ProductIn(**base, image_url="/product-images/12345678-1234-1234-1234-123456789abc.webp").image_url,
                         "/product-images/12345678-1234-1234-1234-123456789abc.webp")
        with self.assertRaises(ValueError):
            main.ProductIn(**base, image_url="javascript:alert(1)")
        with self.assertRaises(ValueError):
            main.ProductIn(**base, image_url="/product-images/../../secret.png")

    def test_product_upload_validation_checks_real_image_bytes(self):
        image = BytesIO()
        from PIL import Image
        Image.new("RGB", (96, 96), "white").save(image, format="PNG")
        self.assertEqual(main.validate_product_image(image.getvalue()), ".png")
        with self.assertRaises(HTTPException):
            main.validate_product_image(b"not an image")

    def test_local_image_route_serves_only_existing_app_owned_file(self):
        with TemporaryDirectory() as directory, patch.object(main, "PRODUCT_IMAGE_ROOT", Path(directory)):
            filename = f"{uuid.uuid4()}.webp"
            (Path(directory) / filename).write_bytes(b"webp-data")
            response = main.get_product_image(filename)
            self.assertEqual(response.media_type, "image/webp")
            with self.assertRaises(HTTPException) as error:
                main.get_product_image("../../secret.webp")
            self.assertEqual(error.exception.status_code, 404)

    def test_collector_requires_product_specific_evidence(self):
        product = {"name": "Samsung Galaxy S26+", "brand": "Samsung", "model": "SM-S947B"}
        self.assertGreaterEqual(model_match_score(product, "Samsung Galaxy S26+ SM-S947B product", "", "https://example.com/sm-s947b.jpg"), 6)
        self.assertLess(model_match_score(product, "Company logo and social links", "Samsung", "https://example.com/logo.jpg"), 6)

    def test_downloaded_product_image_is_normalized_to_webp(self):
        collector = Collector(delay=0)
        image = BytesIO()
        from PIL import Image
        Image.new("RGB", (2000, 1000), "blue").save(image, format="JPEG")
        result = collector.to_webp(image.getvalue())
        with Image.open(BytesIO(result)) as normalized:
            self.assertEqual(normalized.format, "WEBP")
            self.assertLessEqual(max(normalized.size), 1200)

    def test_admin_product_api_rejects_remote_images_for_new_products(self):
        payload = main.ProductIn(name="Example Model", category="Phones", brand="Example", location="Delhi", image_url="https://example.com/phone.jpg")
        with patch.object(main.catalog_repo, "create_product") as create:
            with self.assertRaises(HTTPException) as error:
                main.create_product(payload, {"sub": "admin"})
        self.assertEqual(error.exception.status_code, 422)
        create.assert_not_called()

    def test_admin_product_can_attach_only_an_uploaded_local_file(self):
        with TemporaryDirectory() as directory, patch.object(main, "PRODUCT_IMAGE_ROOT", Path(directory)):
            from PIL import Image
            content = BytesIO()
            Image.new("RGB", (96, 96), "white").save(content, format="PNG")
            image_url = f"/product-images/{uuid.uuid4()}.png"
            (Path(directory) / image_url.rsplit("/", 1)[1]).write_bytes(content.getvalue())
            payload = main.ProductIn(name="Example Model", category="Phones", brand="Example", location="Delhi", image_url=image_url)
            with patch.object(main.catalog_repo, "create_product", return_value="new-product") as create:
                result = main.create_product(payload, {"sub": "admin"})
            self.assertEqual(result["id"], "new-product")
            create.assert_called_once()

    def test_legacy_remote_image_can_be_kept_but_not_replaced_with_another_url(self):
        legacy_url = "https://cdn.example.com/existing-product.jpg"
        payload = main.ProductIn(name="Example Model", category="Phones", brand="Example", location="Delhi", image_url=legacy_url)
        cursor = MagicMock()
        cursor.fetchone.return_value = {"image_url": legacy_url}
        db_mock = MagicMock()
        db_mock.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = cursor
        with patch.object(main, "db", db_mock), patch.object(main.catalog_repo, "update_product") as update:
            result = main.update_product("product-1", payload, {"sub": "admin"})
        self.assertEqual(result["status"], "updated")
        update.assert_called_once()

        payload.image_url = "https://cdn.example.com/different-product.jpg"
        with patch.object(main, "db", db_mock), patch.object(main.catalog_repo, "update_product") as update:
            with self.assertRaises(HTTPException) as error:
                main.update_product("product-1", payload, {"sub": "admin"})
        self.assertEqual(error.exception.status_code, 422)
        update.assert_not_called()

    def test_product_deletion_keeps_shared_image_and_removes_unreferenced_image(self):
        with TemporaryDirectory() as directory, patch.object(main, "PRODUCT_IMAGE_ROOT", Path(directory)):
            filename = f"{uuid.uuid4()}.webp"
            target = Path(directory) / filename
            target.write_bytes(b"image")
            cursor = MagicMock()
            cursor.fetchone.return_value = {"count": 1}
            db_mock = MagicMock()
            db_mock.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = cursor
            with patch.object(main, "db", db_mock):
                main.delete_product_image_if_unreferenced(f"/product-images/{filename}")
            self.assertTrue(target.exists())
            cursor.fetchone.return_value = {"count": 0}
            with patch.object(main, "db", db_mock):
                main.delete_product_image_if_unreferenced(f"/product-images/{filename}")
            self.assertFalse(target.exists())

    def test_admin_upload_stores_file_under_local_image_folder(self):
        with TemporaryDirectory() as directory, patch.object(main, "PRODUCT_IMAGE_ROOT", Path(directory)), patch.object(main, "db") as db_mock, patch.object(main, "audit"):
            from PIL import Image
            from fastapi import UploadFile
            image = BytesIO()
            Image.new("RGB", (96, 96), "white").save(image, format="PNG")
            image.seek(0)
            result = asyncio.run(main.admin_upload_product_image(UploadFile(file=image, filename="phone.png"), {"sub": "admin"}))
            stored = Path(directory) / result["filename"]
            self.assertTrue(stored.is_file())
            self.assertEqual(result["image_url"], f"/product-images/{result['filename']}")
            db_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
