######################################################################
# Test cases for Shopcart Model
######################################################################
# pylint: disable=duplicate-code
"""
Test cases for Shopcart Model
"""

import logging
import os
from unittest import TestCase
from unittest.mock import patch
from wsgi import app
from service.models import Shopcart, Item, DataValidationError, db
from tests.factories import ShopcartFactory, ItemFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#        S H O P C A R T   M O D E L   T E S T   C A S E S
######################################################################
class TestShopcart(TestCase):
    """Shopcart Model Test Cases"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Item).delete()  # clean up the last tests
        db.session.query(Shopcart).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_a_shopcart(self):
        """It should Create a Shopcart and assert that it exists"""
        fake_shopcart = ShopcartFactory()
        # pylint: disable=unexpected-keyword-arg
        shopcart = Shopcart(customer_id=fake_shopcart.customer_id)
        self.assertIsNotNone(shopcart)
        self.assertEqual(shopcart.id, None)
        self.assertEqual(shopcart.customer_id, fake_shopcart.customer_id)
        self.assertEqual(shopcart.items, [])

    def test_add_a_shopcart(self):
        """It should Create a Shopcart and add it to the database"""
        shopcarts = Shopcart.all()
        self.assertEqual(shopcarts, [])
        shopcart = ShopcartFactory()
        shopcart.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(shopcart.id)
        shopcarts = Shopcart.all()
        self.assertEqual(len(shopcarts), 1)

    @patch("service.models.db.session.commit")
    def test_add_shopcart_failed(self, exception_mock):
        """It should not create a Shopcart on database error"""
        exception_mock.side_effect = Exception()
        shopcart = ShopcartFactory()
        self.assertRaises(DataValidationError, shopcart.create)

    def test_read_shopcart(self):
        """It should Read a Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()

        # Read it back
        found = Shopcart.find(shopcart.id)
        self.assertEqual(found.id, shopcart.id)
        self.assertEqual(found.customer_id, shopcart.customer_id)
        self.assertEqual(found.items, [])

    def test_update_shopcart(self):
        """It should Update a Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()
        self.assertIsNotNone(shopcart.id)

        # Fetch it back and change the customer
        shopcart = Shopcart.find(shopcart.id)
        shopcart.customer_id = 99999
        shopcart.update()

        # Fetch it back again
        shopcart = Shopcart.find(shopcart.id)
        self.assertEqual(shopcart.customer_id, 99999)

    def test_update_shopcart_no_id(self):
        """It should not Update a Shopcart that has no id"""
        shopcart = ShopcartFactory()
        shopcart.id = None
        self.assertRaises(DataValidationError, shopcart.update)

    @patch("service.models.db.session.commit")
    def test_update_shopcart_failed(self, exception_mock):
        """It should not update a Shopcart on database error"""
        exception_mock.side_effect = Exception()
        shopcart = ShopcartFactory()
        self.assertRaises(DataValidationError, shopcart.update)

    def test_delete_a_shopcart(self):
        """It should Delete a Shopcart from the database"""
        shopcart = ShopcartFactory()
        shopcart.create()
        self.assertEqual(len(Shopcart.all()), 1)
        shopcart.delete()
        self.assertEqual(len(Shopcart.all()), 0)

    @patch("service.models.db.session.commit")
    def test_delete_shopcart_failed(self, exception_mock):
        """It should not delete a Shopcart on database error"""
        exception_mock.side_effect = Exception()
        shopcart = ShopcartFactory()
        self.assertRaises(DataValidationError, shopcart.delete)

    def test_delete_shopcart_deletes_items(self):
        """It should Delete all Items when their Shopcart is deleted"""
        shopcart = ShopcartFactory()
        ItemFactory(shopcart=shopcart)
        ItemFactory(shopcart=shopcart)
        shopcart.create()
        self.assertEqual(len(Item.all()), 2)

        shopcart = Shopcart.find(shopcart.id)
        shopcart.delete()
        self.assertEqual(len(Shopcart.all()), 0)
        self.assertEqual(len(Item.all()), 0)

    def test_list_all_shopcarts(self):
        """It should List all Shopcarts in the database"""
        self.assertEqual(Shopcart.all(), [])
        for shopcart in ShopcartFactory.create_batch(5):
            shopcart.create()
        self.assertEqual(len(Shopcart.all()), 5)

    def test_find_by_customer_id(self):
        """It should Find a Shopcart by customer_id"""
        shopcart = ShopcartFactory()
        shopcart.create()
        ShopcartFactory().create()  # another customer's shopcart

        found = Shopcart.find_by_customer_id(shopcart.customer_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, shopcart.id)
        self.assertEqual(found.customer_id, shopcart.customer_id)

    def test_find_by_customer_id_not_found(self):
        """It should return None when a customer has no Shopcart"""
        self.assertIsNone(Shopcart.find_by_customer_id(0))

    def test_one_shopcart_per_customer(self):
        """It should not allow two Shopcarts for the same customer"""
        shopcart = ShopcartFactory()
        shopcart.create()

        duplicate = ShopcartFactory(customer_id=shopcart.customer_id)
        self.assertRaises(DataValidationError, duplicate.create)
        self.assertEqual(len(Shopcart.all()), 1)

    def test_serialize_a_shopcart(self):
        """It should Serialize a Shopcart"""
        shopcart = ShopcartFactory()
        item = ItemFactory()
        shopcart.items.append(item)
        data = shopcart.serialize()
        self.assertEqual(data["id"], shopcart.id)
        self.assertEqual(data["customer_id"], shopcart.customer_id)
        self.assertEqual(len(data["items"]), 1)
        items = data["items"]
        self.assertEqual(items[0]["id"], item.id)
        self.assertEqual(items[0]["shopcart_id"], item.shopcart_id)
        self.assertEqual(items[0]["product_id"], item.product_id)
        self.assertEqual(items[0]["name"], item.name)
        self.assertEqual(items[0]["description"], item.description)
        self.assertEqual(items[0]["price"], float(item.price))
        self.assertEqual(items[0]["quantity"], item.quantity)

    def test_deserialize_a_shopcart(self):
        """It should Deserialize a Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.items.append(ItemFactory())
        shopcart.create()
        data = shopcart.serialize()
        new_shopcart = Shopcart()
        new_shopcart.deserialize(data)
        self.assertEqual(new_shopcart.customer_id, shopcart.customer_id)
        self.assertEqual(len(new_shopcart.items), 1)
        self.assertEqual(new_shopcart.items[0].name, shopcart.items[0].name)

    def test_deserialize_shopcart_without_items(self):
        """It should Deserialize a Shopcart that has no items key"""
        shopcart = Shopcart()
        shopcart.deserialize({"customer_id": 123})
        self.assertEqual(shopcart.customer_id, 123)
        self.assertEqual(shopcart.items, [])

    def test_deserialize_with_key_error(self):
        """It should not Deserialize a Shopcart with a KeyError"""
        shopcart = Shopcart()
        self.assertRaises(DataValidationError, shopcart.deserialize, {})

    def test_deserialize_with_type_error(self):
        """It should not Deserialize a Shopcart with a TypeError"""
        shopcart = Shopcart()
        self.assertRaises(DataValidationError, shopcart.deserialize, [])

    def test_deserialize_bad_customer_id(self):
        """It should not Deserialize a Shopcart with a non-integer customer_id"""
        shopcart = Shopcart()
        self.assertRaises(
            DataValidationError, shopcart.deserialize, {"customer_id": "abc"}
        )

    def test_repr(self):
        """It should have a readable repr"""
        shopcart = ShopcartFactory(customer_id=42)
        self.assertIn("customer=[42]", repr(shopcart))