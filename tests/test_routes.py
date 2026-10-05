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

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)


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
        db.session.query(Item).delete()  # clean up the last tests
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
        _, code = error_handlers.request_validation_error(DataValidationError("bad data"))
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type_handler(self):
        """It should return 415 for an unsupported media type"""
        _, code = error_handlers.mediatype_not_supported("wrong content type")
        self.assertEqual(code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_internal_server_error_handler(self):
        """It should return 500 for an internal error"""
        _, code = error_handlers.internal_server_error("boom")
        self.assertEqual(code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Todo: Add your test cases here...
