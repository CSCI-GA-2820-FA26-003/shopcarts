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

# pylint: disable=duplicate-code
import os
import logging
from unittest import TestCase
from wsgi import app
from service.common import status
from service.models import db, Shopcart, Item, DataValidationError
from service.common import error_handlers
from .factories import ShopcartFactory, ItemFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)
BASE_URL = "/shopcarts"


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
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

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

    def test_internal_server_error_handler(self):
        """It should return 500 for an internal error"""
        _, code = error_handlers.internal_server_error("boom")
        self.assertEqual(code, status.HTTP_500_INTERNAL_SERVER_ERROR)

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
