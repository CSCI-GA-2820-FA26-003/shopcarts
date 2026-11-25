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
Shopcart Service

This service implements a REST API that allows you to Create, Read, Update
and Delete Shopcart and Item

Paths:
------
GET /api/shopcarts - Returns a list all of the Shopcarts
POST /api/shopcarts - Creates a new Shopcart record in the database
GET /api/shopcarts/{id} - Returns the Shopcart with a given id number
PUT /api/shopcarts/{id} - Updates a Shopcart record in the database
DELETE /api/shopcarts/{id} - Deletes a Shopcart record in the database
GET /api/shopcarts/{id}/total - Returns the total price of a Shopcart
PUT /api/shopcarts/{id}/checkout - Checks out a Shopcart
GET /api/shopcarts/{id}/items - Returns the Items in a Shopcart
POST /api/shopcarts/{id}/items - Adds an Item to a Shopcart
DELETE /api/shopcarts/{id}/items - Deletes all Items in a Shopcart
GET /api/shopcarts/{id}/items/{item_id} - Returns an Item in a Shopcart
PUT /api/shopcarts/{id}/items/{item_id} - Updates an Item in a Shopcart
DELETE /api/shopcarts/{id}/items/{item_id} - Deletes an Item from a Shopcart
"""

from flask import jsonify, request, render_template
from flask import abort as flask_abort
from flask import current_app as app  # Import Flask application
from flask_restx import Api, Resource, fields, reqparse
from service.models import Shopcart, Item, DataValidationError
from service.models import STATUS_ACTIVE, STATUS_CHECKED_OUT
from service.common import status  # HTTP Status Codes

# Largest value a PostgreSQL INTEGER column can hold
MAX_CUSTOMER_ID = 2**31 - 1

# URL converter for ids in the path. Ids larger than a PostgreSQL INTEGER
# overflow the lookup query, so they do not match the route and get a 404.
ID = f"int(max={MAX_CUSTOMER_ID})"


######################################################################
# GET HEALTH CHECK
######################################################################
@app.route("/health", methods=["GET"])
def health_check():
    """Returns service health status"""
    return jsonify(status="OK"), status.HTTP_200_OK


######################################################################
# GET INDEX
######################################################################
@app.route("/", methods=["GET"])
def index():
    """Display the Shopcart administration page."""
    app.logger.info("Request for Shopcart administration page")
    # The UI calls the REST API, so hand it the /api URLs. The "0" ids are
    # placeholders that shopcarts.js replaces with the real ids.
    return (
        render_template(
            "index.html",
            max_customer_id=MAX_CUSTOMER_ID,
            shopcarts_url=api.url_for(ShopcartCollection),
            shopcart_url=api.url_for(ShopcartResource, shopcart_id=0),
            items_url=api.url_for(ItemCollection, shopcart_id=0),
            checkout_url=api.url_for(CheckoutResource, shopcart_id=0),
        ),
        status.HTTP_200_OK,
    )


######################################################################
# Configure Swagger before initializing it
######################################################################
api = Api(
    app,
    version="1.0.0",
    title="Shopcart REST API Service",
    description="Create, read, update, delete and check out Shopcarts and their Items.",
    default="shopcarts",
    default_label="Shopcart operations",
    doc="/apidocs/",
    prefix="/api",
)


# Define the Item model used for creating and updating Items
item_create_model = api.model(
    "Item",
    {
        "product_id": fields.Integer(
            required=True, description="The id of the product being purchased"
        ),
        "name": fields.String(
            required=True, max_length=64, description="The name of the product"
        ),
        "description": fields.String(
            max_length=256, description="An optional description of the product"
        ),
        "price": fields.Float(required=True, description="The price of one unit"),
        "quantity": fields.Integer(
            required=True, min=1, description="How many units are in the Shopcart"
        ),
    },
)

item_model = api.inherit(
    "ItemModel",
    item_create_model,
    {
        "id": fields.Integer(
            readonly=True, description="The unique id assigned internally by service"
        ),
        "shopcart_id": fields.Integer(
            readonly=True, description="The id of the Shopcart that owns this Item"
        ),
    },
)

# Define the Shopcart models
create_model = api.model(
    "ShopcartCreate",
    {
        "customer_id": fields.Integer(
            required=True, description="The id of the customer who owns the Shopcart"
        ),
        "items": fields.List(
            fields.Nested(item_create_model),
            description="Optional Items to put in the new Shopcart",
        ),
    },
)

update_model = api.model(
    "ShopcartUpdate",
    {
        "customer_id": fields.Integer(
            description="A new customer id for the Shopcart (left unchanged if omitted)"
        ),
        "items": fields.List(
            fields.Nested(item_create_model),
            description="Replaces every Item in the Shopcart (left unchanged if omitted)",
        ),
    },
)

shopcart_model = api.model(
    "ShopcartModel",
    {
        "id": fields.Integer(
            readonly=True, description="The unique id assigned internally by service"
        ),
        "customer_id": fields.Integer(
            required=True, description="The id of the customer who owns the Shopcart"
        ),
        "status": fields.String(
            readonly=True,
            enum=[STATUS_ACTIVE, STATUS_CHECKED_OUT],
            description="Whether the Shopcart is active or has been checked out",
        ),
        "items": fields.List(
            fields.Nested(item_model), description="The Items in the Shopcart"
        ),
    },
)

total_model = api.model(
    "Total",
    {
        "shopcart_id": fields.Integer(description="The id of the Shopcart"),
        "total": fields.Float(
            description="The sum of price x quantity for every Item in the Shopcart"
        ),
    },
)

error_model = api.model(
    "ErrorResponse",
    {
        "status": fields.Integer(
            required=True, description="HTTP status code", example=404
        ),
        "error": fields.String(
            required=True, description="Error name", example="Not Found"
        ),
        "message": fields.String(
            required=True,
            description="Details about the failed request",
            example="Shopcart with id '7' was not found",
        ),
    },
)

created_location_headers = {
    "Location": {
        "type": "string",
        "description": "URL of the newly created resource.",
    }
}


def customer_id_type(value):
    """Validates customer_id query values"""
    # isascii() rejects Unicode digits like "²"; the upper bound keeps
    # values that overflow PostgreSQL's INTEGER column out of the query
    if not (value.isascii() and value.isdigit()) or int(value) > MAX_CUSTOMER_ID:
        raise ValueError(f"customer_id must be an integer, got '{value}'")
    return int(value)


customer_id_type.__schema__ = {
    "type": "integer",
    "minimum": 0,
    "maximum": MAX_CUSTOMER_ID,
}

# query string arguments
shopcart_args = reqparse.RequestParser()
shopcart_args.add_argument(
    "customer_id",
    type=customer_id_type,
    location="args",
    required=False,
    help="Only list the Shopcart owned by this customer.",
)


######################################################################
#  R E S T   A P I   E N D P O I N T S
######################################################################


######################################################################
#  PATH: /shopcarts/{shopcart_id}
######################################################################
@api.route(f"/shopcarts/<{ID}:shopcart_id>")
@api.param("shopcart_id", "The Shopcart identifier")
class ShopcartResource(Resource):
    """
    ShopcartResource class

    Allows the manipulation of a single Shopcart
    GET /shopcarts/{id} - Returns a Shopcart with the id
    PUT /shopcarts/{id} - Update a Shopcart with the id
    DELETE /shopcarts/{id} -  Deletes a Shopcart with the id
    """

    # ------------------------------------------------------------------
    # RETRIEVE A SHOPCART
    # ------------------------------------------------------------------
    @api.doc("get_shopcarts")
    @api.response(404, "Shopcart not found", error_model)
    @api.marshal_with(shopcart_model)
    def get(self, shopcart_id):
        """
        Get a single Shopcart
        This endpoint will return a Shopcart based on its id
        """
        app.logger.info("Request to Read a shopcart with id [%s]", shopcart_id)
        shopcart = Shopcart.find(shopcart_id)
        if not shopcart:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Shopcart with id '{shopcart_id}' was not found",
            )
        return shopcart.serialize(), status.HTTP_200_OK

    # ------------------------------------------------------------------
    # UPDATE AN EXISTING SHOPCART
    # ------------------------------------------------------------------
    @api.doc("update_shopcarts")
    @api.response(400, "The posted Shopcart data was not valid", error_model)
    @api.response(404, "Shopcart not found", error_model)
    @api.response(409, "The Shopcart has been checked out", error_model)
    @api.response(415, "Content-Type must be application/json", error_model)
    @api.expect(update_model)
    @api.marshal_with(shopcart_model)
    def put(self, shopcart_id):
        """
        Update a Shopcart
        Updates the customer_id and/or replaces the entire item list
        of an existing Shopcart. Fields that are omitted are left unchanged.
        """
        app.logger.info("Request to update shopcart [%s]", shopcart_id)
        check_content_type("application/json")

        # Find the existing Shopcart
        shopcart = Shopcart.find(shopcart_id)
        if not shopcart:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Shopcart with id '{shopcart_id}' was not found",
            )
        check_not_checked_out(shopcart)

        # Get the updated data
        data = api.payload
        if not isinstance(data, dict):
            abort(status.HTTP_400_BAD_REQUEST, "Request body must be a JSON object")

        # Update customer_id if provided
        if "customer_id" in data:
            if not isinstance(data["customer_id"], int):
                abort(
                    status.HTTP_400_BAD_REQUEST,
                    "customer_id must be an integer",
                )
            shopcart.customer_id = data["customer_id"]

        # Replace the entire item list if provided
        if "items" in data:
            if not isinstance(data["items"], list):
                abort(
                    status.HTTP_400_BAD_REQUEST,
                    "items must be a list",
                )

            # Delete all existing items
            for item in list(shopcart.items):
                item.delete()

            # Add the new items
            for item_data in data["items"]:
                item = Item()
                item.deserialize(item_data)
                shopcart.items.append(item)

        # Save the changes
        shopcart.update()

        app.logger.info("Shopcart [%s] updated", shopcart_id)
        return shopcart.serialize(), status.HTTP_200_OK

    # ------------------------------------------------------------------
    # DELETE A SHOPCART
    # ------------------------------------------------------------------
    @api.doc("delete_shopcarts")
    @api.response(204, "Shopcart deleted")
    def delete(self, shopcart_id):
        """
        Delete a Shopcart
        This endpoint will delete a Shopcart and all of its Items
        """
        app.logger.info("Request to Delete a shopcart with id [%s]", shopcart_id)

        shopcart = Shopcart.find(shopcart_id)
        if shopcart:
            shopcart.delete()
            app.logger.info("Shopcart with id [%s] deleted", shopcart_id)

        return "", status.HTTP_204_NO_CONTENT


######################################################################
#  PATH: /shopcarts
######################################################################
@api.route("/shopcarts", strict_slashes=False)
class ShopcartCollection(Resource):
    """
    Handles all interactions with collections of Shopcarts
    GET /shopcarts - Returns all Shopcarts, optionally filtered by customer_id
    POST /shopcarts - Creates a new Shopcart
    """

    # ------------------------------------------------------------------
    # LIST ALL SHOPCARTS
    # ------------------------------------------------------------------
    @api.doc("list_shopcarts")
    @api.response(400, "customer_id must be a non-negative integer", error_model)
    @api.expect(shopcart_args, validate=True)
    @api.marshal_list_with(shopcart_model)
    def get(self):
        """Returns all of the Shopcarts, optionally filtered by customer_id"""
        app.logger.info("Request for shopcarts list")

        # shopcart_args documents customer_id in Swagger. The value is checked
        # here, rather than with parse_args(), to keep this error message.
        customer_id = request.args.get("customer_id")
        if customer_id is not None:
            # isascii() rejects Unicode digits like "²"; the upper bound keeps
            # values that overflow PostgreSQL's INTEGER column out of the query
            if (
                not (customer_id.isascii() and customer_id.isdigit())
                or int(customer_id) > MAX_CUSTOMER_ID
            ):
                abort(
                    status.HTTP_400_BAD_REQUEST,
                    f"customer_id must be an integer, got '{customer_id}'",
                )
            app.logger.info("Filtering by customer_id: %s", customer_id)
            # customer_id is unique, so there is at most one matching shopcart
            shopcart = Shopcart.find_by_customer_id(int(customer_id))
            shopcarts = [shopcart] if shopcart else []
        else:
            # Return all of the Shopcarts
            shopcarts = Shopcart.all()

        results = [shopcart.serialize() for shopcart in shopcarts]
        app.logger.info("Returning %d shopcarts", len(results))
        return results, status.HTTP_200_OK

    # ------------------------------------------------------------------
    # ADD A NEW SHOPCART
    # ------------------------------------------------------------------
    @api.doc("create_shopcarts")
    @api.response(400, "The posted data was not valid", error_model)
    @api.response(415, "Content-Type must be application/json", error_model)
    @api.response(
        "201",
        "Shopcart created",
        shopcart_model,
        headers=created_location_headers,
    )
    @api.expect(create_model)
    @api.marshal_with(shopcart_model, code=201)
    def post(self):
        """
        Create a Shopcart
        This endpoint will create a Shopcart based the data in the body that is posted
        """
        app.logger.info("Request to Create a shopcart...")
        check_content_type("application/json")

        shopcart = Shopcart()
        # Get the data from the request and deserialize it
        data = api.payload
        app.logger.info("Processing: %s", data)
        shopcart.deserialize(data)

        # Save the new shopcart to the database
        shopcart.create()
        app.logger.info("shopcart with new id [%s] saved!", shopcart.id)

        # Return the location of the new shopcart
        location_url = api.url_for(
            ShopcartResource, shopcart_id=shopcart.id, _external=True
        )
        return (
            shopcart.serialize(),
            status.HTTP_201_CREATED,
            {"Location": location_url},
        )


######################################################################
#  PATH: /shopcarts/{shopcart_id}/total
######################################################################
@api.route(f"/shopcarts/<{ID}:shopcart_id>/total")
@api.param("shopcart_id", "The Shopcart identifier")
class ShopcartTotalResource(Resource):
    """
    ShopcartTotalResource class

    GET /shopcarts/{id}/total - Returns the total price of a Shopcart
    """

    @api.doc("get_shopcart_total")
    @api.response(404, "Shopcart not found", error_model)
    @api.marshal_with(total_model)
    def get(self, shopcart_id):
        """Returns the total price of a Shopcart"""
        app.logger.info("Request for total of shopcart [%s]", shopcart_id)

        shopcart = Shopcart.find(shopcart_id)
        if not shopcart:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Shopcart with id '{shopcart_id}' was not found",
            )

        return {
            "shopcart_id": shopcart.id,
            "total": float(shopcart.calculate_total()),
        }, status.HTTP_200_OK


######################################################################
#  PATH: /shopcarts/{shopcart_id}/checkout
######################################################################
@api.route(f"/shopcarts/<{ID}:shopcart_id>/checkout")
@api.param("shopcart_id", "The Shopcart identifier")
class CheckoutResource(Resource):
    """
    CheckoutResource class

    PUT /shopcarts/{id}/checkout - Checks out a Shopcart
    """

    @api.doc("checkout_shopcarts")
    @api.response(404, "Shopcart not found", error_model)
    @api.response(
        409, "The Shopcart has no items and cannot be checked out", error_model
    )
    @api.marshal_with(shopcart_model)
    def put(self, shopcart_id):
        """
        Checkout a Shopcart
        Marks an active, non-empty Shopcart as checked_out so it can no longer be
        modified. Checking out an already checked-out Shopcart changes nothing.
        """
        app.logger.info("Request to checkout shopcart [%s]", shopcart_id)

        shopcart = Shopcart.find(shopcart_id)
        if not shopcart:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Shopcart with id '{shopcart_id}' was not found",
            )

        try:
            changed = shopcart.checkout()
        except DataValidationError as err:
            abort(status.HTTP_409_CONFLICT, str(err))

        if changed:
            app.logger.info("Shopcart [%s] checked out", shopcart_id)
        else:
            app.logger.info("Shopcart [%s] was already checked out", shopcart_id)

        return shopcart.serialize(), status.HTTP_200_OK


######################################################################
#  PATH: /shopcarts/{shopcart_id}/items/{item_id}
######################################################################
@api.route(f"/shopcarts/<{ID}:shopcart_id>/items/<{ID}:item_id>")
@api.param("shopcart_id", "The Shopcart identifier")
@api.param("item_id", "The Item identifier")
class ItemResource(Resource):
    """
    ItemResource class

    Allows the manipulation of a single Item in a Shopcart
    GET /shopcarts/{id}/items/{item_id} - Returns the Item with the item_id
    PUT /shopcarts/{id}/items/{item_id} - Updates the Item with the item_id
    DELETE /shopcarts/{id}/items/{item_id} - Deletes the Item with the item_id
    """

    # ------------------------------------------------------------------
    # RETRIEVE AN ITEM
    # ------------------------------------------------------------------
    @api.doc("get_items")
    @api.response(404, "Shopcart or Item not found", error_model)
    @api.marshal_with(item_model)
    def get(self, shopcart_id, item_id):
        """Returns a specific item from a Shopcart"""
        app.logger.info(
            "Request to Read item [%s] in shopcart [%s]",
            item_id,
            shopcart_id,
        )

        shopcart = Shopcart.find(shopcart_id)
        if not shopcart:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Shopcart with id '{shopcart_id}' was not found",
            )

        item = Item.find(item_id)
        if not item or item.shopcart_id != shopcart_id:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Item with id '{item_id}' was not found in shopcart '{shopcart_id}'",
            )

        return item.serialize(), status.HTTP_200_OK

    # ------------------------------------------------------------------
    # UPDATE AN ITEM
    # ------------------------------------------------------------------
    @api.doc("update_items")
    @api.response(400, "The posted Item data was not valid", error_model)
    @api.response(404, "Shopcart or Item not found", error_model)
    @api.response(409, "The Shopcart has been checked out", error_model)
    @api.response(415, "Content-Type must be application/json", error_model)
    @api.expect(item_create_model)
    @api.marshal_with(item_model)
    def put(self, shopcart_id, item_id):
        """Update an existing item in a shopcart."""
        app.logger.info(
            "Request to update item [%s] in shopcart [%s]", item_id, shopcart_id
        )
        check_content_type("application/json")

        # Find the shopcart
        shopcart = Shopcart.find(shopcart_id)
        if not shopcart:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Shopcart with id '{shopcart_id}' was not found",
            )
        check_not_checked_out(shopcart)

        # Find the item and check that it belongs to this shopcart
        item = Item.find(item_id)
        if not item or item.shopcart_id != shopcart_id:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Item with id '{item_id}' was not found in shopcart '{shopcart_id}'",
            )

        # Validate the request using a temporary item
        data = api.payload
        if not isinstance(data, dict):
            abort(status.HTTP_400_BAD_REQUEST, "Request body must be a JSON object")

        # The URL determines which shopcart owns the item
        data = dict(data)
        data.pop("shopcart_id", None)

        updated_item = Item()
        updated_item.deserialize(data)

        # Copy the validated values to the existing item
        item.product_id = updated_item.product_id
        item.name = updated_item.name
        item.description = updated_item.description
        item.price = updated_item.price
        item.quantity = updated_item.quantity
        item.update()
        app.logger.info("Item [%s] updated", item_id)

        return item.serialize(), status.HTTP_200_OK

    # ------------------------------------------------------------------
    # DELETE AN ITEM
    # ------------------------------------------------------------------
    @api.doc("delete_items")
    @api.response(204, "Item deleted")
    @api.response(409, "The Shopcart has been checked out", error_model)
    def delete(self, shopcart_id, item_id):
        """Remove an item from a shopcart."""
        app.logger.info(
            "Request to Delete item [%s] from shopcart [%s]", item_id, shopcart_id
        )

        shopcart = Shopcart.find(shopcart_id)
        if shopcart:
            check_not_checked_out(shopcart)

        item = Item.find(item_id)
        if item and item.shopcart_id == shopcart_id:
            item.delete()
            app.logger.info(
                "Item [%s] deleted from shopcart [%s]", item_id, shopcart_id
            )

        return "", status.HTTP_204_NO_CONTENT


######################################################################
#  PATH: /shopcarts/{shopcart_id}/items
######################################################################
@api.route(f"/shopcarts/<{ID}:shopcart_id>/items", strict_slashes=False)
@api.param("shopcart_id", "The Shopcart identifier")
class ItemCollection(Resource):
    """
    Handles all interactions with the collection of Items in a Shopcart
    GET /shopcarts/{id}/items - Returns all Items in the Shopcart
    POST /shopcarts/{id}/items - Adds a new Item to the Shopcart
    DELETE /shopcarts/{id}/items - Deletes all Items in the Shopcart
    """

    # ------------------------------------------------------------------
    # LIST ALL ITEMS
    # ------------------------------------------------------------------
    @api.doc("list_items")
    @api.response(404, "Shopcart not found", error_model)
    @api.marshal_list_with(item_model)
    def get(self, shopcart_id):
        """Returns all items in the specified Shopcart"""
        app.logger.info("Request to List items in shopcart [%s]", shopcart_id)

        shopcart = Shopcart.find(shopcart_id)
        if not shopcart:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Shopcart with id '{shopcart_id}' was not found",
            )

        items = [item.serialize() for item in shopcart.items]
        return items, status.HTTP_200_OK

    # ------------------------------------------------------------------
    # ADD AN ITEM
    # ------------------------------------------------------------------
    @api.doc("create_items")
    @api.response(400, "The posted Item data was not valid", error_model)
    @api.response(404, "Shopcart not found", error_model)
    @api.response(409, "The Shopcart has been checked out", error_model)
    @api.response(415, "Content-Type must be application/json", error_model)
    @api.response(
        "201",
        "Item created",
        item_model,
        headers=created_location_headers,
    )
    @api.expect(item_create_model)
    @api.marshal_with(item_model, code=201)
    def post(self, shopcart_id):
        """
        Add an item to a Shopcart
        This endpoint will add an item to an existing Shopcart
        """
        app.logger.info("Request to add an item to shopcart [%s]", shopcart_id)
        check_content_type("application/json")

        # Find the existing Shopcart
        shopcart = Shopcart.find(shopcart_id)
        if not shopcart:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Shopcart with id '{shopcart_id}' was not found",
            )
        check_not_checked_out(shopcart)

        # Get the item data from the request
        data = api.payload
        app.logger.info("Processing item: %s", data)

        # Create the new item
        item = Item()
        item.deserialize(data)

        # Add the item to the Shopcart and save
        shopcart.items.append(item)
        shopcart.update()

        app.logger.info("Item added to shopcart [%s]", shopcart_id)

        location_url = api.url_for(
            ItemResource,
            shopcart_id=shopcart_id,
            item_id=item.id,
            _external=True,
        )
        return item.serialize(), status.HTTP_201_CREATED, {"Location": location_url}

    # ------------------------------------------------------------------
    # DELETE ALL ITEMS
    # ------------------------------------------------------------------
    @api.doc("delete_all_items")
    @api.response(204, "All Items deleted")
    @api.response(409, "The Shopcart has been checked out", error_model)
    def delete(self, shopcart_id):
        """Deletes all items in the specified Shopcart but keeps the Shopcart"""
        app.logger.info("Request to Delete all items in shopcart [%s]", shopcart_id)

        shopcart = Shopcart.find(shopcart_id)
        if shopcart:
            check_not_checked_out(shopcart)
            for item in list(shopcart.items):
                item.delete()
            app.logger.info("All items in shopcart [%s] deleted", shopcart_id)

        return "", status.HTTP_204_NO_CONTENT


######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################


######################################################################
# Logs error messages before aborting
######################################################################
def abort(error_code: int, message: str):
    """Logs errors before aborting"""
    app.logger.error(message)
    flask_abort(error_code, message)


######################################################################
# Checks the ContentType of a request
######################################################################
def check_content_type(content_type) -> None:
    """Checks that the media type is correct"""
    if "Content-Type" not in request.headers:
        app.logger.error("No Content-Type specified.")
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )

    if request.headers["Content-Type"] == content_type:
        return

    app.logger.error("Invalid Content-Type: %s", request.headers["Content-Type"])
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Content-Type must be {content_type}",
    )


######################################################################
# Rejects changes to a checked-out Shopcart
######################################################################
def check_not_checked_out(shopcart) -> None:
    """Aborts with 409 Conflict if the Shopcart has been checked out"""
    if shopcart.is_checked_out:
        abort(
            status.HTTP_409_CONFLICT,
            f"Shopcart with id '{shopcart.id}' has been checked out "
            "and cannot be modified",
        )
