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
# cspell: ignore= backref
"""
Shopcart Model
"""

import logging
from .persistent_base import db, PersistentBase, DataValidationError
from .item import Item

logger = logging.getLogger("flask.app")


######################################################################
#  S H O P C A R T   M O D E L
######################################################################
class Shopcart(db.Model, PersistentBase):
    """
    Class that represents a Shopcart
    """

    # Table Schema
    id = db.Column(db.Integer, primary_key=True)
    # unique=True: the database refuses a second shopcart for the same customer
    customer_id = db.Column(db.Integer, nullable=False, unique=True)
    items = db.relationship("Item", backref="shopcart", passive_deletes=True)

    def __repr__(self):
        return f"<Shopcart customer=[{self.customer_id}] id=[{self.id}]>"

    def serialize(self) -> dict:
        """Converts a Shopcart into a dictionary"""
        shopcart = {
            "id": self.id,
            "customer_id": self.customer_id,
            "items": [],
        }
        for item in self.items:
            shopcart["items"].append(item.serialize())
        return shopcart

    def deserialize(self, data: dict):
        """
        Populates a Shopcart from a dictionary

        Args:
            data (dict): A dictionary containing the resource data
        """
        try:
            if not isinstance(data["customer_id"], int):
                raise DataValidationError(
                    "Invalid Shopcart: customer_id must be an integer"
                )
            self.customer_id = data["customer_id"]
            # handle inner list of items (optional; a new cart can be empty)
            item_list = data.get("items", [])
            for json_item in item_list:
                item = Item()
                item.deserialize(json_item)
                self.items.append(item)
        except AttributeError as error:
            raise DataValidationError("Invalid attribute: " + error.args[0]) from error
        except KeyError as error:
            raise DataValidationError(
                "Invalid Shopcart: missing " + error.args[0]
            ) from error
        except TypeError as error:
            raise DataValidationError(
                "Invalid Shopcart: body of request contained bad or no data "
                + str(error)
            ) from error
        return self

    @classmethod
    def find_by_customer_id(cls, customer_id: int):
        """Returns the Shopcart for the given customer, or None

        Args:
            customer_id (int): the id of the customer who owns the shopcart
        """
        logger.info("Processing customer_id query for %s ...", customer_id)
        return cls.query.filter(cls.customer_id == customer_id).first()