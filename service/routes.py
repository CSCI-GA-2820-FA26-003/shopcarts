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
"""

from flask import request, url_for, abort
from flask import current_app as app  # Import Flask application
from service.models import Shopcart, Item
from service.common import status  # HTTP Status Codes


######################################################################
# GET INDEX
######################################################################
@app.route("/")
def index():
    """Root URL response"""
    return (
        "Reminder: return some useful information in json format about the service here",
        status.HTTP_200_OK,
    )


######################################################################
#  R E S T   A P I   E N D P O I N T S
######################################################################


######################################################################
# CREATE A NEW SHOPCART
######################################################################
@app.route("/shopcarts", methods=["POST"])
def create_shopcarts():
    """
    Create a Shopcart
    This endpoint will create a Shopcart based the data in the body that is posted
    """
    app.logger.info("Request to Create a shopcart...")
    check_content_type("application/json")

    shopcart = Shopcart()
    # Get the data from the request and deserialize it
    data = request.get_json()
    app.logger.info("Processing: %s", data)
    shopcart.deserialize(data)

    # Save the new shopcart to the database
    shopcart.create()
    app.logger.info("shopcart with new id [%s] saved!", shopcart.id)

    # Return the location of the new shopcart
    location_url = url_for("get_shopcarts", shopcart_id=shopcart.id, _external=True)
    return shopcart.serialize(), status.HTTP_201_CREATED, {"Location": location_url}


######################################################################
# GET A NEW SHOPCART
######################################################################
@app.route("/shopcarts/<int:shopcart_id>", methods=["GET"])
def get_shopcarts(shopcart_id):
    """
    Get a single Shopcart
    This endpoint will return a Shopcart based on its id
    """
    app.logger.info("Request to Read a shopcart with id [%s]", shopcart_id)
    shopcart = Shopcart.find(shopcart_id)
    if not shopcart:
        abort(
            status.HTTP_404_NOT_FOUND, f"Shopcart with id '{shopcart_id}' was not found"
        )
    return shopcart.serialize(), status.HTTP_200_OK

######################################################################
# ADD ITEM TO SHOPCART
######################################################################
@app.route("/shopcarts/<int:shopcart_id>/items", methods=["POST"])
def add_item(shopcart_id):
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

    # Get the item data from the request
    data = request.get_json()
    app.logger.info("Processing item: %s", data)

    # Create the new item
    item = Item()
    item.deserialize(data)

    # Add the item to the Shopcart and save
    shopcart.items.append(item)
    shopcart.update()

    app.logger.info("Item added to shopcart [%s]", shopcart_id)

    return shopcart.serialize(), status.HTTP_201_CREATED

######################################################################
# UPDATE A SHOPCART
######################################################################
@app.route("/shopcarts/<int:shopcart_id>", methods=["PUT"])
def update_shopcart(shopcart_id):
    """Update an existing Shopcart and replace its item list"""
    app.logger.info("Request to update shopcart [%s]", shopcart_id)
    check_content_type("application/json")

    # Find the existing Shopcart
    shopcart = Shopcart.find(shopcart_id)
    if not shopcart:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Shopcart with id '{shopcart_id}' was not found",
        )

    # Get the updated data
    data = request.get_json()
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


########################################################################
# Logs error messages before aborting
########################################################################
def error(status_code, reason):
    """Logs the error and then aborts"""
    app.logger.error(reason)
    abort(status_code, reason)
