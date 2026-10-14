import io
import unittest
import zipfile
from decimal import Decimal

from backend import dealer_catalogue as catalogue
from backend import product_identity as identity


def keys(**product):
    return {key for _, key in identity.identity_keys(**product)}


class IdentityKeyTests(unittest.TestCase):
    def test_the_same_product_described_differently_shares_keys(self):
        a = keys(name="Samsung 55 inch 4K Smart TV", brand="Samsung", model="UA55AU7700")
        b = keys(name="4K SMART TV 55in - Samsung", brand="SAMSUNG Electronics", model="ua55-au7700")
        self.assertTrue(a & b)
        self.assertEqual(a, b)

    def test_word_order_punctuation_and_unit_spacing_do_not_matter(self):
        a = keys(name="Philips Air Fryer 4.1 L, Black", brand="Philips", model="HD9252/90")
        b = keys(name="Black Philips Air-Fryer 4.1L", brand="Philips", model="HD9252-90")
        self.assertTrue(a & b)

    def test_same_name_but_different_model_is_a_different_product(self):
        a = keys(name="Philips Straightener 5000", brand="Philips", model="BHS522")
        b = keys(name="Philips Straightener 5000", brand="Philips", model="BHS530")
        self.assertFalse(a & b)

    def test_same_model_under_another_brand_is_a_different_product(self):
        a = keys(name="Pro Speaker X1", brand="Sony", model="X1")
        b = keys(name="Pro Speaker X1", brand="Bose", model="X1")
        self.assertFalse(a & b)

    def test_a_plus_model_is_not_the_base_model(self):
        for base, plus in (
            (dict(name="Galaxy S24", brand="Samsung", model="Galaxy S24"), dict(name="Galaxy S24+", brand="Samsung", model="Galaxy S24+")),
            (dict(name="Redmi Note 14 Pro 5G", brand="Redmi", model="Redmi Note 14 Pro 5G"), dict(name="Redmi Note 14 Pro+ 5G", brand="Redmi", model="Redmi Note 14 Pro+ 5G")),
        ):
            self.assertFalse(keys(**base) & keys(**plus), base["name"])
            self.assertEqual(identity.similarity(base, plus), 0.0)

    def test_a_brand_repeated_inside_the_model_is_still_the_same_product(self):
        a = keys(name="Samsung Galaxy S26", brand="Samsung", model="Samsung Galaxy S26")
        b = keys(name="Galaxy S26", brand="Samsung", model="Galaxy S26")
        self.assertTrue(a & b)

    def test_a_barcode_alone_identifies_a_product(self):
        a = keys(name="Mystery item", brand="", gtin="4006381333931")
        b = keys(name="Totally different words", brand="Acme", gtin=" 4006381333931 ")
        self.assertTrue(a & b)

    def test_part_number_matches_across_names(self):
        a = keys(name="Daikin 1.5 ton 5 star split AC", brand="Daikin", mpn="JTKJ60XV")
        b = keys(name="AC by Daikin inverter", brand="DAIKIN INDIA", mpn="jtkj-60xv")
        self.assertTrue(a & b)

    def test_too_little_information_gives_no_keys_instead_of_wrong_ones(self):
        self.assertEqual(identity.identity_keys(name="TV", brand="", model="", mpn="", gtin=""), [])

    def test_very_long_names_still_make_bounded_keys(self):
        long_name = " ".join(f"word{index}" for index in range(120))
        for _, key in identity.identity_keys(name=long_name, brand="Acme", model="M1"):
            self.assertLessEqual(len(key), 255)


class BarcodeTests(unittest.TestCase):
    def test_valid_barcodes_are_kept_and_invalid_ones_dropped(self):
        self.assertEqual(identity.gtins("4006381333931"), ["4006381333931"])
        self.assertEqual(identity.gtins("4006381333932"), [])  # wrong check digit
        self.assertEqual(identity.gtins("12345"), [])
        self.assertEqual(identity.gtins("4006381333931; 036000291452"), ["4006381333931", "036000291452"])
        self.assertEqual(identity.gtins(None), [])


class SimilarityTests(unittest.TestCase):
    def test_close_names_are_offered_for_review(self):
        row = {"name": "Philips 3000 Series Dual Basket Air Fryer", "brand": "Philips", "model": ""}
        pool = [
            {"id": "1", "name": "Philips 3000 Series Dual Basket Airfryer", "brand": "Philips", "model": "NA352/00"},
            {"id": "2", "name": "Philips Hair Straightener 5000", "brand": "Philips", "model": "BHS522"},
        ]
        found = identity.similar_products(row, pool, threshold=0.7)
        self.assertEqual([item["id"] for item in found], ["1"])

    def test_different_model_numbers_are_never_similar(self):
        a = {"name": "Philips Straightener 5000", "brand": "Philips", "model": "BHS522"}
        b = {"name": "Philips Straightener 5000", "brand": "Philips", "model": "BHS530"}
        self.assertEqual(identity.similarity(a, b), 0.0)


class ReadingFilesTests(unittest.TestCase):
    def test_csv_headings_in_everyday_words_are_understood(self):
        data = "Product Name,Make,Model No,EAN,Sub Category,MRP\nSamsung TV,Samsung,UA55,4006381333931,Televisions,\"42,990\"\n".encode()
        rows = catalogue.parse_catalogue_file("stock.csv", data)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["name"], rows[0]["brand"], rows[0]["model"], rows[0]["gtin"], rows[0]["item"], rows[0]["price"]),
                         ("Samsung TV", "Samsung", "UA55", "4006381333931", "Televisions", "42,990"))
        self.assertEqual(rows[0]["_row"], "2")

    def test_semicolons_byte_order_marks_and_blank_lines_are_handled(self):
        data = "﻿Name;Brand\n\nLG Fridge;LG\n".encode("utf-8")
        rows = catalogue.parse_catalogue_file("x.csv", data)
        self.assertEqual([r["name"] for r in rows], ["LG Fridge"])

    def test_problems_with_the_file_are_explained(self):
        for name, content, fragment in (
            ("a.csv", b"", "empty"),
            ("a.csv", b"Brand,Model\nSamsung,X\n", "product name column"),
            ("a.csv", b"Name\n", "at least one product"),
            ("a.pdf", b"x", "CSV or Excel"),
            ("old.xls", b"x", "xlsx"),
            ("big.csv", b"x" * (catalogue.MAX_FILE_BYTES + 1), "5 MB"),
        ):
            with self.assertRaises(catalogue.CatalogueError) as caught:
                catalogue.parse_catalogue_file(name, content)
            self.assertIn(fragment, str(caught.exception), name)

    def test_too_many_rows_are_refused(self):
        body = "Name,Brand\n" + "\n".join(f"P{i},B" for i in range(catalogue.MAX_ROWS + 1))
        with self.assertRaises(catalogue.CatalogueError):
            catalogue.parse_catalogue_file("many.csv", body.encode())

    def test_excel_files_are_read_without_extra_libraries(self):
        sheet = (
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="D1" t="s"><v>2</v></c></row>'
            '<row r="2"><c r="A2" t="s"><v>3</v></c><c r="B2" t="inlineStr"><is><t>Sony</t></is></c><c r="D2"><v>4006381333931</v></c></row>'
            "</sheetData></worksheet>"
        )
        strings = (
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<si><t>Name</t></si><si><t>Brand</t></si><si><t>EAN</t></si><si><t>Sony Bravia 43 inch</t></si></sst>"
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("xl/worksheets/sheet1.xml", sheet)
            archive.writestr("xl/sharedStrings.xml", strings)
        rows = catalogue.parse_catalogue_file("catalogue.xlsx", buffer.getvalue())
        self.assertEqual((rows[0]["name"], rows[0]["brand"], rows[0]["gtin"]), ("Sony Bravia 43 inch", "Sony", "4006381333931"))

    def test_a_broken_excel_file_is_reported_not_crashed_on(self):
        with self.assertRaises(catalogue.CatalogueError):
            catalogue.parse_catalogue_file("bad.xlsx", b"this is not a zip file")


class CleaningRowsTests(unittest.TestCase):
    def test_a_good_row_is_tidied(self):
        row, errors, warnings = catalogue.clean_row({"name": "  Samsung   TV ", "brand": "Samsung", "price": "₹ 42,990", "gtin": "4006381333931"})
        self.assertEqual((errors, warnings), ([], []))
        self.assertEqual(row["name"], "Samsung TV")
        self.assertEqual(row["price"], Decimal("42990.00"))

    def test_missing_name_or_brand_stops_the_row(self):
        _, errors, _ = catalogue.clean_row({"name": "", "brand": ""})
        self.assertEqual(len(errors), 2)

    def test_bad_barcode_and_price_only_warn(self):
        row, errors, warnings = catalogue.clean_row({"name": "TV", "brand": "LG", "gtin": "123", "price": "cheap"})
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 2)
        self.assertIsNone(row["price"])
        self.assertEqual(row["gtin"], "")

    def test_over_long_values_are_refused(self):
        _, errors, _ = catalogue.clean_row({"name": "x" * 300, "brand": "LG"})
        self.assertTrue(errors)

    def test_template_can_be_read_back(self):
        rows = catalogue.parse_catalogue_file("template.csv", catalogue.template_csv().encode())
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["name"] and row["brand"] for row in rows))
        self.assertEqual(rows[1]["gtin"], "8710103834012")


if __name__ == "__main__":
    unittest.main()
