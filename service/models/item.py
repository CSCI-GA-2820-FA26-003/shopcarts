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
Item Model (a product inside a Shopcart)
"""

import logging
from decimal import Decimal, InvalidOperation
from .persistent_base import db, PersistentBase, DataValidationError

logger = logging.getLogger("flask.app")


######################################################################
#  I T E M   M O D E L
######################################################################
class Item(db.Model, PersistentBase):
    """
    Class that represents an Item in a Shopcart
    """

    # Table Schema
    id = db.Column(db.Integer, primary_key=True)
    shopcart_id = db.Column(
        db.Integer, db.ForeignKey("shopcart.id", ondelete="CASCADE"), nullable=False
    )
    product_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(256))
    price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    def __repr__(self):
        return f"<Item {self.name} id=[{self.id}] shopcart[{self.shopcart_id}]>"

    def __str__(self):
        return f"{self.name}: {self.quantity} x ${self.price}"

    def serialize(self) -> dict:
        """Converts an Item into a dictionary"""
        return {
            "id": self.id,
            "shopcart_id": self.shopcart_id,
            "product_id": self.product_id,
            "name": self.name,
            "description": self.description,
            "price": float(self.price) if self.price is not None else None,
            "quantity": self.quantity,
        }

    def deserialize(self, data: dict):
        """
        Populates an Item from a dictionary

        Args:
            data (dict): A dictionary containing the resource data
        """
        try:
            # shopcart_id is optional here: when an item is created inside a
            # shopcart, SQLAlchemy fills it in through the relationship
            self.shopcart_id = data.get("shopcart_id")
            self.product_id = data["product_id"]
            self.name = data["name"]
            self.description = data.get("description")
            self.price = Decimal(str(data["price"]))
            self.quantity = data["quantity"]
            if not isinstance(self.quantity, int) or self.quantity < 1:
                raise DataValidationError(
                    "Invalid Item: quantity must be a positive integer"
                )
        except InvalidOperation as error:
            raise DataValidationError("Invalid Item: price must be a number") from error
        except AttributeError as error:
            raise DataValidationError("Invalid attribute: " + error.args[0]) from error
        except KeyError as error:
            raise DataValidationError(
                "Invalid Item: missing " + error.args[0]
            ) from error
        except TypeError as error:
            raise DataValidationError(
                "Invalid Item: body of request contained bad or no data " + str(error)
            ) from error
        return self