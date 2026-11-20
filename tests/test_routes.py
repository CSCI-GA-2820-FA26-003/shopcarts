######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
TestShopcartService API Service Test Suite
"""

# pylint: disable=duplicate-code, too-many-lines
import os
import logging
from unittest import TestCase
from unittest.mock import patch
from werkzeug.exceptions import Gone
from wsgi import app
from service.common import status
from service.models import (
    db,
    Shopcart,
    Item,
    DataValidationError,
    STATUS_ACTIVE,
    STATUS_CHECKED_OUT,
)
from service.common import error_handlers
from service.routes import customer_id_type
from .factories import ShopcartFactory, ItemFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)
BASE_URL = "/api/shopcarts"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestShopcartService(TestCase):
    """REST API Server Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Item).delete()
        db.session.query(Shopcart).delete()
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  P L A C E   T E S T   C A S E S   H E R E
    ######################################################################

    def test_index(self):
        """It should display the Shopcart administration page."""
        response = self.client.get("/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.mimetype, "text/html")

        page = response.get_data(as_text=True)

        self.assertIn("Shopcart Administration", page)
        self.assertIn('id="create-shopcart-form"', page)
        self.assertIn('id="customer-id"', page)
        self.assertIn('id="create-shopcart-btn"', page)
        self.assertIn('data-endpoint="/api/shopcarts"', page)
        self.assertIn("/static/shopcarts.js", page)

        # Add Item form for a retrieved shopcart
        self.assertIn('id="add-item-form"', page)
        self.assertIn('data-endpoint-template="/api/shopcarts/0/items"', page)
        for element_id in (
            "item-product-id",
            "item-name",
            "item-description",
            "item-price",
            "item-quantity",
            "add-item-btn",
            "add-item-message",
        ):
            self.assertIn(f'id="{element_id}"', page)

        # Description is optional; the other item inputs are required
        description_field = page[page.index('id="item-description"'):]
        description_field = description_field[: description_field.index(">")]
        self.assertNotIn("required", description_field)
        name_field = page[page.index('id="item-name"'):]
        name_field = name_field[: name_field.index(">")]
        self.assertIn("required", name_field)

        # The Add Item button starts disabled until a shopcart is retrieved
        add_item_button = page[page.index('id="add-item-btn"'):]
        add_item_button = add_item_button[: add_item_button.index(">")]
        self.assertIn("disabled", add_item_button)

    # ----------------------------------------------------------
    # TEST LIST SHOPCARTS
    # ----------------------------------------------------------

    def test_list_shopcarts_empty(self):
        """It should return an empty list when no Shopcarts exist"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(response.get_json(), [])

    def test_list_shopcarts(self):
        """It should list all shopcarts, including there items"""
        shopcarts = ShopcartFactory.create_batch(3)
        ItemFactory(shopcart=shopcarts[0])

        for shopcart in shopcarts:
            shopcart.create()
        response = self.client.get(BASE_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.mimetype, "application/json")

        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), len(shopcarts))

        expected = sorted(
            [shopcart.serialize() for shopcart in shopcarts],
            key=lambda shopcart: shopcart["id"],
        )
        actual = sorted(data, key=lambda shopcart: shopcart["id"])
        self.assertEqual(actual, expected)

    def test_query_shopcarts_by_customer_id(self):
        """It should return only the Shopcart for the given customer_id"""
        shopcarts = ShopcartFactory.create_batch(3)
        for shopcart in shopcarts:
            shopcart.create()
        target = shopcarts[1]

        response = self.client.get(
            BASE_URL, query_string=f"customer_id={target.customer_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], target.id)
        self.assertEqual(data[0]["customer_id"], target.customer_id)

    def test_query_shopcarts_by_customer_id_not_found(self):
        """It should return an empty list when no Shopcart matches the customer_id"""
        for shopcart in ShopcartFactory.create_batch(2):
            shopcart.create()

        response = self.client.get(BASE_URL, query_string="customer_id=0")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), [])

    def test_query_shopcarts_bad_customer_id(self):
        """It should return 400 when customer_id is not an integer"""
        for bad_id in ["abc", "", "-1", "1.5", "²", "2147483648"]:
            response = self.client.get(BASE_URL, query_string={"customer_id": bad_id})
            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
                f"customer_id={bad_id!r}",
            )

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_shopcart(self):
        """It should Create a new Shopcart"""
        test_shopcart = ShopcartFactory()
        logging.debug("Test Shopcart: %s", test_shopcart.serialize())
        response = self.client.post(BASE_URL, json=test_shopcart.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_shopcart = response.get_json()
        self.assertIsNotNone(new_shopcart["id"])
        self.assertEqual(new_shopcart["customer_id"], test_shopcart.customer_id)
        self.assertEqual(new_shopcart["items"], [])

        # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_shopcart = response.get_json()
        self.assertIsNotNone(new_shopcart["id"])
        self.assertEqual(new_shopcart["customer_id"], test_shopcart.customer_id)
        self.assertEqual(new_shopcart["items"], [])

    # ----------------------------------------------------------
    # TEST READ
    # ----------------------------------------------------------
    def test_read_shopcart(self):
        """It should Read the requested Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()
        other_shopcart = ShopcartFactory()
        other_shopcart.create()

        response = self.client.get(f"{BASE_URL}/{shopcart.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.mimetype, "application/json")

        data = response.get_json()
        self.assertEqual(data["id"], shopcart.id)
        self.assertEqual(data["customer_id"], shopcart.customer_id)

    def test_read_empty_shopcart(self):
        """It should Read an empty Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()

        response = self.client.get(f"{BASE_URL}/{shopcart.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.mimetype, "application/json")

        data = response.get_json()
        self.assertEqual(data["id"], shopcart.id)
        self.assertEqual(data["customer_id"], shopcart.customer_id)
        self.assertEqual(data["items"], [])

    def test_read_shopcart_not_found(self):
        """It should return 404 when the Shopcart does not exist"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.mimetype, "application/json")

        data = response.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn(
            "Shopcart with id '0' was not found",
            data["message"],
        )

    # ----------------------------------------------------------
    # TEST READ ITEM
    # ----------------------------------------------------------

    def test_read_item(self):
        """It should Read a specific item from a Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()

        item = ItemFactory(shopcart=shopcart)
        item.create()
        ItemFactory(shopcart=shopcart).create()

        response = self.client.get(f"{BASE_URL}/{shopcart.id}/items/{item.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(response.get_json(), item.serialize())

    def test_read_item_shopcart_not_found(self):
        """It should return 404 when the Shopcart does not exist"""
        response = self.client.get(f"{BASE_URL}/0/items/0")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.mimetype, "application/json")
        self.assertIn(
            "Shopcart with id '0' was not found",
            response.get_json()["message"],
        )

    def test_read_item_not_found(self):
        """It should return 404 when the item does not exist"""
        shopcart = ShopcartFactory()
        shopcart.create()

        response = self.client.get(f"{BASE_URL}/{shopcart.id}/items/0")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.mimetype, "application/json")
        self.assertIn(
            f"Item with id '0' was not found in shopcart '{shopcart.id}'",
            response.get_json()["message"],
        )

    def test_read_item_from_another_shopcart(self):
        """It should not Read an item from another Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()

        other_shopcart = ShopcartFactory()
        other_shopcart.create()
        item = ItemFactory(shopcart=other_shopcart)
        item.create()

        response = self.client.get(f"{BASE_URL}/{shopcart.id}/items/{item.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.mimetype, "application/json")

        data = response.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn(
            f"Item with id '{item.id}' was not found " f"in shopcart '{shopcart.id}'",
            data["message"],
        )
        self.assertNotIn("name", data)
        self.assertNotIn("price", data)

    # ----------------------------------------------------------
    # TEST LIST ITEMS
    # ----------------------------------------------------------
    def test_list_items(self):
        """It should List only items in the requested Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()

        item1 = ItemFactory(shopcart=shopcart)
        item1.create()
        item2 = ItemFactory(shopcart=shopcart)
        item2.create()

        other_shopcart = ShopcartFactory()
        other_shopcart.create()
        other_item = ItemFactory(shopcart=other_shopcart)
        other_item.create()

        response = self.client.get(f"{BASE_URL}/{shopcart.id}/items")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.mimetype, "application/json")

        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)

        expected = sorted(
            [item1.serialize(), item2.serialize()],
            key=lambda item: item["id"],
        )
        actual = sorted(data, key=lambda item: item["id"])
        self.assertEqual(actual, expected)

    def test_list_empty_shopcart(self):
        """It should return an empty list for an empty Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()

        response = self.client.get(f"{BASE_URL}/{shopcart.id}/items")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(response.get_json(), [])

    def test_list_items_shopcart_not_found(self):
        """It should return 404 when the Shopcart does not exist"""
        response = self.client.get(f"{BASE_URL}/0/items")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.mimetype, "application/json")

        data = response.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn(
            "Shopcart with id '0' was not found",
            data["message"],
        )

    # ----------------------------------------------------------
    # TEST DELETE ALL ITEMS
    # ----------------------------------------------------------
    def test_delete_all_items(self):
        """It should Delete all items in a Shopcart and keep the Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()
        for _ in range(3):
            ItemFactory(shopcart=shopcart).create()

        other_shopcart = ShopcartFactory()
        other_shopcart.create()
        other_item = ItemFactory(shopcart=other_shopcart)
        other_item.create()

        response = self.client.delete(f"{BASE_URL}/{shopcart.id}/items")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.data), 0)

        # the shopcart still exists but is empty
        response = self.client.get(f"{BASE_URL}/{shopcart.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["items"], [])

        # items in other shopcarts are untouched
        response = self.client.get(f"{BASE_URL}/{other_shopcart.id}/items")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), [other_item.serialize()])

    def test_delete_all_items_empty_shopcart(self):
        """It should return 204 when deleting items from an empty Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()

        response = self.client.delete(f"{BASE_URL}/{shopcart.id}/items")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_all_items_shopcart_not_found(self):
        """It should return 204 when deleting items from a missing Shopcart"""
        response = self.client.delete(f"{BASE_URL}/0/items")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.data), 0)

    # ----------------------------------------------------------
    # TEST DELETE SHOPCART
    # ----------------------------------------------------------
    def test_delete_shopcart(self):
        """It should Delete a Shopcart and its Items"""
        shopcart = ShopcartFactory()
        shopcart.create()
        item = ItemFactory(shopcart=shopcart)
        item.create()
        shopcart_id, item_id = shopcart.id, item.id

        other_shopcart = ShopcartFactory()
        other_shopcart.create()

        response = self.client.delete(f"{BASE_URL}/{shopcart_id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.data), 0)

        # the shopcart and its items are gone
        response = self.client.get(f"{BASE_URL}/{shopcart_id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIsNone(Item.find(item_id))

        # other shopcarts are untouched
        response = self.client.get(f"{BASE_URL}/{other_shopcart.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_shopcart_not_found(self):
        """It should return 204 when deleting a Shopcart that does not exist"""
        response = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.data), 0)

    # ----------------------------------------------------------
    # TEST ADD ITEM
    # ----------------------------------------------------------

    def test_add_item(self):
        """It should add an item to an existing Shopcart."""
        shopcart = ShopcartFactory()
        shopcart.create()

        item_data = {
            "product_id": "123",
            "name": "Test Product",
            "description": "A test product",
            "price": 10.0,
            "quantity": 2,
        }

        response = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items",
            json=item_data,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that the response contains the new item
        data = response.get_json()
        self.assertEqual(data["shopcart_id"], shopcart.id)
        self.assertEqual(data["product_id"], 123)
        self.assertEqual(data["name"], "Test Product")
        self.assertEqual(data["quantity"], 2)
        self.assertNotIn("items", data)

        # Check the Location header points to the new item
        location = response.headers.get("Location")
        self.assertIsNotNone(location)
        self.assertTrue(
            location.endswith(f"/shopcarts/{shopcart.id}/items/{data['id']}")
        )

        # Check that the item was saved
        saved_item = Item.find(data["id"])
        self.assertIsNotNone(saved_item)
        self.assertEqual(saved_item.shopcart_id, shopcart.id)

    def test_add_item_shopcart_not_found(self):
        """It should return 404 when the Shopcart does not exist."""
        item_data = {
            "product_id": "123",
            "name": "Test Product",
            "description": "A test product",
            "price": 10.0,
            "quantity": 2,
        }

        response = self.client.post(
            f"{BASE_URL}/0/items",
            json=item_data,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_item_missing_content_type(self):
        """It should return 415 when Content-Type is missing."""
        shopcart = ShopcartFactory()
        shopcart.create()

        response = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items",
            data='{"product_id": "123"}',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    # --------------------------------------------------------------------
    #  T E S T   U P D A T E
    # --------------------------------------------------------------------

    def test_update_shopcart(self):
        """It should update a shopcart and replace its items"""
        shopcart = ShopcartFactory()
        shopcart.create()

        old_item = {
            "product_id": 101,
            "name": "Old Product",
            "description": "Old description",
            "price": 5.0,
            "quantity": 1,
        }
        response = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items",
            json=old_item,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        new_item = {
            "product_id": 202,
            "name": "New Product",
            "description": "New description",
            "price": 10.0,
            "quantity": 2,
        }
        response = self.client.put(
            f"{BASE_URL}/{shopcart.id}",
            json={
                "customer_id": shopcart.customer_id,
                "items": [new_item],
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["id"], shopcart.id)
        self.assertEqual(data["customer_id"], shopcart.customer_id)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["product_id"], 202)
        self.assertEqual(data["items"][0]["name"], "New Product")
        self.assertEqual(data["items"][0]["quantity"], 2)

    def test_update_shopcart_clear_items(self):
        """It should clear all items and keep the shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()

        response = self.client.put(
            f"{BASE_URL}/{shopcart.id}",
            json={
                "customer_id": shopcart.customer_id,
                "items": [],
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["id"], shopcart.id)
        self.assertEqual(data["items"], [])

    def test_update_shopcart_not_found(self):
        """It should return 404 when the shopcart does not exist"""
        response = self.client.put(
            f"{BASE_URL}/999999",
            json={"customer_id": 123, "items": []},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_shopcart_invalid_items(self):
        """It should return 400 when items is not a list"""
        shopcart = ShopcartFactory()
        shopcart.create()

        response = self.client.put(
            f"{BASE_URL}/{shopcart.id}",
            json={
                "customer_id": shopcart.customer_id,
                "items": "not-a-list",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    ######################################################################
    #  T E S T   U P D A T E
    ######################################################################

    def test_delete_item(self):
        """It should remove an item from an existing Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()

        item_data = {
            "product_id": "123",
            "name": "Test Product",
            "description": "A test product",
            "price": 10.0,
            "quantity": 2,
        }

        response = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items",
            json=item_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item_id = response.get_json()["id"]

        response = self.client.delete(f"{BASE_URL}/{shopcart.id}/items/{item_id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, b"")

        response = self.client.get(f"{BASE_URL}/{shopcart.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["items"], [])

    def test_delete_item_shopcart_not_found(self):
        """It should return 204 when the Shopcart does not exist"""
        response = self.client.delete(f"{BASE_URL}/0/items/0")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, b"")

    def test_delete_item_not_found(self):
        """It should return 204 when the Item does not exist"""
        shopcart = ShopcartFactory()
        shopcart.create()

        response = self.client.delete(f"{BASE_URL}/{shopcart.id}/items/0")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, b"")

    def test_delete_item_from_another_shopcart(self):
        """It should not remove an item belonging to another Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()
        other_shopcart = ShopcartFactory()
        other_shopcart.create()

        item_data = {
            "product_id": "123",
            "name": "Test Product",
            "description": "A test product",
            "price": 10.0,
            "quantity": 2,
        }

        response = self.client.post(
            f"{BASE_URL}/{other_shopcart.id}/items",
            json=item_data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = response.get_json()

        response = self.client.delete(f"{BASE_URL}/{shopcart.id}/items/{item['id']}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(f"{BASE_URL}/{other_shopcart.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["items"], [item])

    # ----------------------------------------------------------
    # TEST SHOPCART TOTAL
    # ----------------------------------------------------------
    def test_get_shopcart_total(self):
        """It should calculate the total for only the requested Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()

        ItemFactory(
            shopcart=shopcart,
            price="10.25",
            quantity=2,
        ).create()
        ItemFactory(
            shopcart=shopcart,
            price="5.10",
            quantity=3,
        ).create()

        other_shopcart = ShopcartFactory()
        other_shopcart.create()
        ItemFactory(
            shopcart=other_shopcart,
            price="100.00",
            quantity=1,
        ).create()

        response = self.client.get(f"{BASE_URL}/{shopcart.id}/total")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.mimetype, "application/json")

        data = response.get_json()
        self.assertEqual(data["shopcart_id"], shopcart.id)
        self.assertEqual(data["total"], 35.80)

    def test_get_empty_shopcart_total(self):
        """It should return zero for an empty Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()

        response = self.client.get(f"{BASE_URL}/{shopcart.id}/total")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.mimetype, "application/json")

        data = response.get_json()
        self.assertEqual(data["shopcart_id"], shopcart.id)
        self.assertEqual(data["total"], 0)

    def test_get_shopcart_total_not_found(self):
        """It should return 404 when the Shopcart does not exist"""
        response = self.client.get(f"{BASE_URL}/0/total")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.mimetype, "application/json")
        self.assertIn(
            "Shopcart with id '0' was not found",
            response.get_json()["message"],
        )

    ######################################################################
    #  E R R O R   H A N D L E R   T E S T S
    ######################################################################

    def test_not_found(self):
        """It should return 404 for an unknown URL"""
        resp = self.client.get("/no-such-page")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp.get_json()["error"], "Not Found")

    def test_method_not_allowed(self):
        """It should return 405 for an unsupported method"""
        resp = self.client.delete("/")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_bad_request_handler(self):
        """It should return 400 for a DataValidationError"""
        _, code = error_handlers.request_validation_error(
            DataValidationError("bad data")
        )
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type_handler(self):
        """It should return 415 for an unsupported media type"""
        _, code = error_handlers.mediatype_not_supported("wrong content type")
        self.assertEqual(code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_api_error_other_http_exception(self):
        """It should use the exception's own name for unmapped HTTP errors"""
        body, code = error_handlers.api_error(Gone("no longer here"))
        self.assertEqual(code, status.HTTP_410_GONE)
        self.assertEqual(body["status"], status.HTTP_410_GONE)
        self.assertEqual(body["error"], "Gone")
        self.assertEqual(body["message"], "410 Gone: no longer here")

    def test_customer_id_type(self):
        """It should document customer_id as a bounded integer"""
        self.assertEqual(customer_id_type("42"), 42)
        for bad_id in ["abc", "", "-1", "1.5", "²", "2147483648"]:
            with self.assertRaises(ValueError):
                customer_id_type(bad_id)

    def test_internal_server_error_handler(self):
        """It should return 500 for an internal error"""
        _, code = error_handlers.internal_server_error("boom")
        self.assertEqual(code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_api_not_found_is_json(self):
        """It should return a JSON 404 with an error and message from the API"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.mimetype, "application/json")
        data = response.get_json()
        self.assertEqual(data["status"], status.HTTP_404_NOT_FOUND)
        self.assertEqual(data["error"], "Not Found")
        self.assertEqual(
            data["message"], "404 Not Found: Shopcart with id '0' was not found"
        )

    def test_non_integer_id_is_json_404(self):
        """It should return a JSON 404, not HTML, for a non-integer id"""
        response = self.client.get(f"{BASE_URL}/abc")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(response.get_json()["error"], "Not Found")

    def test_oversized_id_is_404(self):
        """It should return 404, not 500, for ids too big for the database"""
        too_big = 2**31
        for method, url in [
            ("get", f"{BASE_URL}/{too_big}"),
            ("delete", f"{BASE_URL}/{too_big}"),
            ("get", f"{BASE_URL}/{too_big}/total"),
            ("put", f"{BASE_URL}/{too_big}/checkout"),
            ("get", f"{BASE_URL}/{too_big}/items"),
            ("get", f"{BASE_URL}/1/items/{too_big}"),
        ]:
            response = getattr(self.client, method)(url)
            self.assertEqual(
                response.status_code, status.HTTP_404_NOT_FOUND, f"{method} {url}"
            )
            self.assertEqual(response.mimetype, "application/json")

    def test_api_method_not_allowed_is_json(self):
        """It should return a JSON 405 for an unsupported method on the API"""
        response = self.client.patch(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.mimetype, "application/json")
        data = response.get_json()
        self.assertEqual(data["status"], status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(data["error"], "Method not Allowed")
        self.assertTrue(data["message"].startswith("405 Method Not Allowed: "))

    def test_query_bad_customer_id_message(self):
        """It should explain why a customer_id query value was rejected"""
        response = self.client.get(BASE_URL, query_string={"customer_id": "abc"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.get_json(),
            {
                "status": status.HTTP_400_BAD_REQUEST,
                "error": "Bad Request",
                "message": "400 Bad Request: customer_id must be an integer, got 'abc'",
            },
        )

    def test_api_unhandled_exception_is_json_500(self):
        """It should return a JSON 500 for an unexpected error in the API"""
        with patch("service.routes.Shopcart.all", side_effect=RuntimeError("boom")):
            response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.get_json()
        self.assertEqual(data["status"], status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(data["error"], "Internal Server Error")

    ######################################################################
    #  S W A G G E R   D O C U M E N T A T I O N   T E S T S
    ######################################################################

    def test_swagger_ui(self):
        """It should serve the Swagger UI at /apidocs/"""
        response = self.client.get("/apidocs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.mimetype, "text/html")

    def test_swagger_json(self):
        """It should serve the Swagger specification at /api/swagger.json"""
        response = self.client.get("/api/swagger.json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        spec = response.get_json()
        self.assertEqual(spec["basePath"], "/api")
        for path in (
            "/shopcarts",
            "/shopcarts/{shopcart_id}",
            "/shopcarts/{shopcart_id}/total",
            "/shopcarts/{shopcart_id}/checkout",
            "/shopcarts/{shopcart_id}/items",
            "/shopcarts/{shopcart_id}/items/{item_id}",
        ):
            self.assertIn(path, spec["paths"])
        for model in ("Item", "ItemModel", "ShopcartCreate", "ShopcartUpdate",
                      "ShopcartModel", "Total"):
            self.assertIn(model, spec["definitions"])

    def test_health_outside_api(self):
        """It should keep the health check at the root, outside /api"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), {"status": "OK"})
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    ######################################################################
    #  B A D   D A T A   T E S T S  (never a 500)
    ######################################################################

    def _valid_item(self, **changes):
        """Returns a valid Item request body with some fields changed"""
        item = {"product_id": 1, "name": "widget", "price": 9.99, "quantity": 1}
        item.update(changes)
        return item

    def _create_shopcart_with_item(self):
        """Creates a Shopcart with one Item and returns their ids"""
        shopcart = ShopcartFactory()
        shopcart.create()
        item = ItemFactory(shopcart=shopcart)
        item.create()
        return shopcart.id, item.id

    def test_malformed_json_body(self):
        """It should return 400 for a body that is not valid JSON"""
        response = self.client.post(
            BASE_URL, data="{bad", content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.mimetype, "application/json")
        data = response.get_json()
        self.assertEqual(data["status"], status.HTTP_400_BAD_REQUEST)
        self.assertEqual(data["error"], "Bad Request")
        self.assertTrue(data["message"].startswith("400 Bad Request: "))

    def test_non_object_json_bodies(self):
        """It should return 400 when the JSON body is not an object"""
        shopcart_id, item_id = self._create_shopcart_with_item()
        endpoints = [
            ("post", BASE_URL),
            ("put", f"{BASE_URL}/{shopcart_id}"),
            ("post", f"{BASE_URL}/{shopcart_id}/items"),
            ("put", f"{BASE_URL}/{shopcart_id}/items/{item_id}"),
        ]
        for body in ("null", "[]", '"text"'):
            for method, url in endpoints:
                response = getattr(self.client, method)(
                    url, data=body, content_type="application/json"
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                    f"{method.upper()} {url} with {body}",
                )
                self.assertEqual(response.get_json()["error"], "Bad Request")

    def test_create_shopcart_customer_id_too_large(self):
        """It should return 400 for a customer_id that overflows the database"""
        response = self.client.post(BASE_URL, json={"customer_id": 99999999999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.get_json()["error"], "Bad Request")

    def test_create_shopcart_duplicate_customer_id(self):
        """It should return 400 for a customer_id that already has a Shopcart"""
        response = self.client.post(BASE_URL, json={"customer_id": 42})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(BASE_URL, json={"customer_id": 42})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.get_json()["error"], "Bad Request")

    def test_bad_item_fields(self):
        """It should return 400 for Item fields with bad values"""
        shopcart_id, item_id = self._create_shopcart_with_item()
        bad_values = [
            {"name": "x" * 100},
            {"price": "abc"},
            {"quantity": "2"},
            {"quantity": 0},
            {"product_id": "abc"},
        ]
        for changes in bad_values:
            body = self._valid_item(**changes)
            for method, url in [
                ("post", f"{BASE_URL}/{shopcart_id}/items"),
                ("put", f"{BASE_URL}/{shopcart_id}/items/{item_id}"),
            ]:
                response = getattr(self.client, method)(url, json=body)
                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                    f"{method.upper()} {url} with {changes}",
                )
                self.assertEqual(response.get_json()["error"], "Bad Request")

    def test_wrong_content_type(self):
        """It should return 415 for a text/plain body"""
        shopcart_id, item_id = self._create_shopcart_with_item()
        for method, url in [
            ("post", BASE_URL),
            ("put", f"{BASE_URL}/{shopcart_id}"),
            ("post", f"{BASE_URL}/{shopcart_id}/items"),
            ("put", f"{BASE_URL}/{shopcart_id}/items/{item_id}"),
        ]:
            response = getattr(self.client, method)(
                url, data="{}", content_type="text/plain"
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                f"{method.upper()} {url}",
            )
            data = response.get_json()
            self.assertEqual(data["status"], status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
            self.assertEqual(data["error"], "Unsupported media type")
            self.assertEqual(
                data["message"],
                "415 Unsupported Media Type: Content-Type must be application/json",
            )

    # ----------------------------------------------------------
    # TEST UPDATE ITEM
    # ----------------------------------------------------------

    def test_update_item(self):
        """It should update one item and leave other items unchanged."""
        shopcart = ShopcartFactory()
        shopcart.create()

        item = ItemFactory(shopcart=shopcart)
        item.create()
        other_item = ItemFactory(shopcart=shopcart)
        other_item.create()
        other_item_before = other_item.serialize()

        updated_data = {
            "product_id": 101,
            "name": "Updated Product",
            "description": "Updated description",
            "price": 10.0,
            "quantity": 3,
        }

        response = self.client.put(
            f"{BASE_URL}/{shopcart.id}/items/{item.id}",
            json=updated_data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.mimetype, "application/json")

        data = response.get_json()
        self.assertEqual(data["id"], item.id)
        self.assertEqual(data["shopcart_id"], shopcart.id)
        self.assertEqual(data["product_id"], 101)
        self.assertEqual(data["name"], "Updated Product")
        self.assertEqual(data["description"], "Updated description")
        self.assertEqual(data["price"], 10.0)
        self.assertEqual(data["quantity"], 3)

        # Check that the change was saved
        db.session.expire_all()
        saved_item = Item.find(item.id)
        self.assertEqual(saved_item.quantity, 3)
        self.assertEqual(saved_item.name, "Updated Product")

        # Check that the other item was not changed
        saved_other_item = Item.find(other_item.id)
        self.assertEqual(saved_other_item.serialize(), other_item_before)

    def test_update_item_shopcart_not_found(self):
        """It should return 404 when the shopcart does not exist."""
        response = self.client.put(
            f"{BASE_URL}/0/items/0",
            json={
                "product_id": 101,
                "name": "Product",
                "price": 10.0,
                "quantity": 1,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_item_not_found(self):
        """It should return 404 when the item does not exist."""
        shopcart = ShopcartFactory()
        shopcart.create()

        response = self.client.put(
            f"{BASE_URL}/{shopcart.id}/items/0",
            json={
                "product_id": 101,
                "name": "Product",
                "price": 10.0,
                "quantity": 1,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_item_from_another_shopcart(self):
        """It should not update an item from another shopcart."""
        shopcart = ShopcartFactory()
        shopcart.create()

        other_shopcart = ShopcartFactory()
        other_shopcart.create()

        item = ItemFactory(shopcart=other_shopcart)
        item.create()
        original_data = item.serialize()

        response = self.client.put(
            f"{BASE_URL}/{shopcart.id}/items/{item.id}",
            json={
                "product_id": 101,
                "name": "Changed Product",
                "price": 10.0,
                "quantity": 3,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        db.session.expire_all()
        self.assertEqual(Item.find(item.id).serialize(), original_data)

    def test_update_item_invalid_data(self):
        """It should reject invalid data without changing the item."""
        shopcart = ShopcartFactory()
        shopcart.create()

        item = ItemFactory(shopcart=shopcart)
        item.create()
        original_data = item.serialize()

        response = self.client.put(
            f"{BASE_URL}/{shopcart.id}/items/{item.id}",
            json={
                "product_id": 101,
                "name": "Changed Product",
                "price": 10.0,
                "quantity": 0,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        db.session.expire_all()
        self.assertEqual(Item.find(item.id).serialize(), original_data)

    def test_update_item_missing_content_type(self):
        """It should reject a request without a JSON content type."""
        shopcart = ShopcartFactory()
        shopcart.create()

        item = ItemFactory(shopcart=shopcart)
        item.create()

        response = self.client.put(
            f"{BASE_URL}/{shopcart.id}/items/{item.id}",
            data='{"quantity": 3}',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    # ----------------------------------------------------------
    # TEST HEALTH CHECK
    # ----------------------------------------------------------

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.mimetype, "application/json")

        self.assertEqual(response.get_json(), {"status": "OK"})

    # ----------------------------------------------------------
    # TEST CHECKOUT
    # ----------------------------------------------------------

    def _create_checked_out_shopcart(self):
        """Creates a Shopcart with one item and checks it out"""
        shopcart = ShopcartFactory()
        shopcart.create()
        item = ItemFactory(shopcart=shopcart)
        item.create()
        response = self.client.put(f"{BASE_URL}/{shopcart.id}/checkout")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return shopcart, item

    def test_checkout_shopcart(self):
        """It should checkout an active Shopcart that has items"""
        shopcart = ShopcartFactory()
        shopcart.create()
        item = ItemFactory(shopcart=shopcart)
        item.create()

        response = self.client.put(f"{BASE_URL}/{shopcart.id}/checkout")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["id"], shopcart.id)
        self.assertEqual(data["status"], STATUS_CHECKED_OUT)
        self.assertEqual(len(data["items"]), 1)

        # The new status is saved to the database
        response = self.client.get(f"{BASE_URL}/{shopcart.id}")
        self.assertEqual(response.get_json()["status"], STATUS_CHECKED_OUT)

    def test_checkout_shopcart_not_found(self):
        """It should return 404 when checking out a missing Shopcart"""
        response = self.client.put(f"{BASE_URL}/0/checkout")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("was not found", response.get_json()["message"])

    def test_checkout_empty_shopcart(self):
        """It should return 409 and stay active when the Shopcart is empty"""
        shopcart = ShopcartFactory()
        shopcart.create()

        response = self.client.put(f"{BASE_URL}/{shopcart.id}/checkout")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        data = response.get_json()
        self.assertEqual(data["error"], "Conflict")
        self.assertIn("no items", data["message"])

        response = self.client.get(f"{BASE_URL}/{shopcart.id}")
        self.assertEqual(response.get_json()["status"], STATUS_ACTIVE)

    def test_checkout_already_checked_out(self):
        """It should return 200 and change nothing on a repeat checkout"""
        shopcart, _ = self._create_checked_out_shopcart()
        before = self.client.get(f"{BASE_URL}/{shopcart.id}").get_json()

        response = self.client.put(f"{BASE_URL}/{shopcart.id}/checkout")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), before)

    def test_new_shopcart_is_active(self):
        """It should create Shopcarts with an active status"""
        response = self.client.post(BASE_URL, json={"customer_id": 1})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.get_json()["status"], STATUS_ACTIVE)

    def test_create_shopcart_ignores_status(self):
        """It should not let a client create a checked-out Shopcart"""
        response = self.client.post(
            BASE_URL, json={"customer_id": 1, "status": STATUS_CHECKED_OUT}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.get_json()["status"], STATUS_ACTIVE)

    def test_add_item_to_checked_out_shopcart(self):
        """It should not add items to a checked-out Shopcart"""
        shopcart, _ = self._create_checked_out_shopcart()
        new_item = ItemFactory()
        response = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items", json=new_item.serialize()
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("checked out", response.get_json()["message"])
        self.assertEqual(len(Shopcart.find(shopcart.id).items), 1)

    def test_update_checked_out_shopcart(self):
        """It should not update a checked-out Shopcart"""
        shopcart, _ = self._create_checked_out_shopcart()
        original_customer = shopcart.customer_id
        response = self.client.put(
            f"{BASE_URL}/{shopcart.id}", json={"customer_id": 99999, "items": []}
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        found = Shopcart.find(shopcart.id)
        self.assertEqual(found.customer_id, original_customer)
        self.assertEqual(len(found.items), 1)

    def test_update_item_in_checked_out_shopcart(self):
        """It should not update an item in a checked-out Shopcart"""
        shopcart, item = self._create_checked_out_shopcart()
        original_quantity = item.quantity
        data = item.serialize()
        data["quantity"] = original_quantity + 1
        response = self.client.put(
            f"{BASE_URL}/{shopcart.id}/items/{item.id}", json=data
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Item.find(item.id).quantity, original_quantity)

    def test_delete_item_from_checked_out_shopcart(self):
        """It should not delete an item from a checked-out Shopcart"""
        shopcart, item = self._create_checked_out_shopcart()
        response = self.client.delete(f"{BASE_URL}/{shopcart.id}/items/{item.id}")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIsNotNone(Item.find(item.id))

    def test_delete_all_items_from_checked_out_shopcart(self):
        """It should not delete all items from a checked-out Shopcart"""
        shopcart, _ = self._create_checked_out_shopcart()
        response = self.client.delete(f"{BASE_URL}/{shopcart.id}/items")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(len(Shopcart.find(shopcart.id).items), 1)

    def test_delete_checked_out_shopcart(self):
        """It should still allow a checked-out Shopcart to be deleted"""
        shopcart, _ = self._create_checked_out_shopcart()
        response = self.client.delete(f"{BASE_URL}/{shopcart.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(Shopcart.find(shopcart.id))
