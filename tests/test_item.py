######################################################################
# Test cases for Item Model
######################################################################
# pylint: disable=duplicate-code
"""
Test cases for Item Model
"""

import logging
import os
from decimal import Decimal
from unittest import TestCase
from wsgi import app
from service.models import Shopcart, Item, DataValidationError, db
from tests.factories import ShopcartFactory, ItemFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#        I T E M   M O D E L   T E S T   C A S E S
######################################################################
class TestItem(TestCase):
    """Item Model Test Cases"""

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

    def test_add_shopcart_item(self):
        """It should Create a Shopcart with an Item and add it to the database"""
        self.assertEqual(Shopcart.all(), [])
        shopcart = ShopcartFactory()
        item = ItemFactory(shopcart=shopcart)
        shopcart.create()
        self.assertIsNotNone(shopcart.id)
        self.assertEqual(len(Shopcart.all()), 1)

        # All product fields should be stored
        new_shopcart = Shopcart.find(shopcart.id)
        stored = new_shopcart.items[0]
        self.assertEqual(stored.shopcart_id, shopcart.id)
        self.assertEqual(stored.product_id, item.product_id)
        self.assertEqual(stored.name, item.name)
        self.assertEqual(stored.description, item.description)
        self.assertEqual(stored.price, item.price)
        self.assertEqual(stored.quantity, item.quantity)

        # A shopcart can contain multiple products
        item2 = ItemFactory(shopcart=shopcart)
        shopcart.items.append(item2)
        shopcart.update()

        new_shopcart = Shopcart.find(shopcart.id)
        self.assertEqual(len(new_shopcart.items), 2)
        self.assertEqual(new_shopcart.items[1].name, item2.name)

    def test_read_item(self):
        """It should Read an Item by its id"""
        shopcart = ShopcartFactory()
        item = ItemFactory(shopcart=shopcart)
        shopcart.create()

        found = Item.find(item.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, item.id)
        self.assertEqual(found.shopcart_id, shopcart.id)
        self.assertEqual(found.name, item.name)

    def test_update_shopcart_item(self):
        """It should Update an Item in a Shopcart"""
        shopcart = ShopcartFactory()
        ItemFactory(shopcart=shopcart, quantity=1)
        shopcart.create()

        # Fetch it back and change the quantity
        shopcart = Shopcart.find(shopcart.id)
        old_item = shopcart.items[0]
        self.assertEqual(old_item.quantity, 1)
        old_item.quantity = 5
        shopcart.update()

        # Fetch it back again
        shopcart = Shopcart.find(shopcart.id)
        self.assertEqual(shopcart.items[0].quantity, 5)

    def test_delete_shopcart_item(self):
        """It should Delete an Item from a Shopcart"""
        shopcart = ShopcartFactory()
        ItemFactory(shopcart=shopcart)
        shopcart.create()

        shopcart = Shopcart.find(shopcart.id)
        item = shopcart.items[0]
        item.delete()
        shopcart.update()

        shopcart = Shopcart.find(shopcart.id)
        self.assertEqual(len(shopcart.items), 0)
        self.assertEqual(len(Shopcart.all()), 1)  # the shopcart itself remains

    def test_list_all_items(self):
        """It should List all Items in the database"""
        shopcart = ShopcartFactory()
        for _ in range(3):
            ItemFactory(shopcart=shopcart)
        shopcart.create()
        self.assertEqual(len(Item.all()), 3)

    def test_serialize_an_item(self):
        """It should Serialize an Item"""
        item = ItemFactory()
        data = item.serialize()
        self.assertEqual(data["id"], item.id)
        self.assertEqual(data["shopcart_id"], item.shopcart_id)
        self.assertEqual(data["product_id"], item.product_id)
        self.assertEqual(data["name"], item.name)
        self.assertEqual(data["description"], item.description)
        self.assertEqual(data["price"], float(item.price))
        self.assertEqual(data["quantity"], item.quantity)

    def test_deserialize_an_item(self):
        """It should Deserialize an Item"""
        item = ItemFactory()
        item.create()
        new_item = Item()
        new_item.deserialize(item.serialize())
        self.assertEqual(new_item.shopcart_id, item.shopcart_id)
        self.assertEqual(new_item.product_id, item.product_id)
        self.assertEqual(new_item.name, item.name)
        self.assertEqual(new_item.description, item.description)
        self.assertEqual(new_item.price, item.price)
        self.assertEqual(new_item.quantity, item.quantity)

    def test_deserialize_keeps_shopcart_id(self):
        """It should keep the existing shopcart_id when the data has none"""
        item = Item()
        item.shopcart_id = 7
        item.deserialize(
            {"product_id": 1, "name": "pen", "price": 1.25, "quantity": 2}
        )
        self.assertEqual(item.shopcart_id, 7)
        self.assertEqual(item.price, Decimal("1.25"))
        self.assertIsNone(item.description)  # description is optional

    def test_deserialize_item_key_error(self):
        """It should not Deserialize an Item with a KeyError"""
        item = Item()
        self.assertRaises(DataValidationError, item.deserialize, {})

    def test_deserialize_item_type_error(self):
        """It should not Deserialize an Item with a TypeError"""
        item = Item()
        self.assertRaises(DataValidationError, item.deserialize, [])

    def test_deserialize_item_bad_price(self):
        """It should not Deserialize an Item with a price that is not a number"""
        item = Item()
        data = {"product_id": 1, "name": "pen", "price": "abc", "quantity": 1}
        self.assertRaises(DataValidationError, item.deserialize, data)

    def test_deserialize_item_bad_quantity(self):
        """It should not Deserialize an Item with a quantity that is not a positive integer"""
        item = Item()
        for bad in [0, -1, "2"]:
            data = {"product_id": 1, "name": "pen", "price": 1, "quantity": bad}
            self.assertRaises(DataValidationError, item.deserialize, data)

    def test_repr_and_str(self):
        """It should have a readable repr and str"""
        item = ItemFactory(name="pen", quantity=2, price=Decimal("1.50"))
        self.assertIn("pen", repr(item))
        self.assertEqual(str(item), "pen: 2 x $1.50")