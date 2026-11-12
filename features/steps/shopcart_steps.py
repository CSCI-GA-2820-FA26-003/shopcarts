"""Browser steps for the Shopcart administration page."""

from secrets import randbelow

from behave import given, then, when
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as conditions

FIELD_IDS = {
    "Customer ID": "customer-id",
    "Shopcart ID": "delete-shopcart-id",
    "Read Shopcart ID": "read-shopcart-id",
}

BUTTON_IDS = {
    "Create Shopcart": "create-shopcart-btn",
    "Retrieve": "read-shopcart-btn",
    "Delete Shopcart": "delete-shopcart-btn",
}


def wait_for_creation(context, expected_state):
    """Wait for a completed request and check its displayed result."""

    def request_finished(browser):
        message = browser.find_element(By.ID, "creation-message")
        button = browser.find_element(By.ID, "create-shopcart-btn")
        state = message.get_attribute("data-state")

        if state in ("success", "error") and button.is_enabled():
            return message

        return False

    message = context.wait.until(request_finished)
    actual_state = message.get_attribute("data-state")

    assert (
        actual_state == expected_state
    ), f"Expected {expected_state}, got {actual_state}: {message.text}"
    return message


@given("I am on the administration page")
def visit_administration_page(context):
    """Open the administration page."""
    context.browser.get(f"{context.base_url}/")
    context.wait.until(
        conditions.visibility_of_element_located((By.ID, "create-shopcart-form"))
    )


@then('I should see the heading "{heading}"')
def check_heading(context, heading):
    """Check the visible page heading."""
    element = context.wait.until(
        conditions.visibility_of_element_located((By.TAG_NAME, "h1"))
    )
    assert element.text == heading, element.text


@then('I should see the "{field}" field')
def check_field(context, field):
    """Check that a named input is visible."""
    context.wait.until(
        conditions.visibility_of_element_located((By.ID, FIELD_IDS[field]))
    )


@then('I should see the "{button}" button')
def check_button(context, button):
    """Check that a named button is visible."""
    element = context.wait.until(
        conditions.visibility_of_element_located((By.ID, BUTTON_IDS[button]))
    )
    assert element.text == button, element.text


@when("I enter a new test customer ID")
def enter_new_customer_id(context):
    """Enter a generated customer ID through the form."""
    previous_id = getattr(context, "customer_id", None)

    customer_id = 1_000_000_000 + randbelow(1_000_000_000)
    while customer_id == previous_id:
        customer_id = 1_000_000_000 + randbelow(1_000_000_000)

    context.customer_id = customer_id

    element = context.wait.until(
        conditions.element_to_be_clickable((By.ID, FIELD_IDS["Customer ID"]))
    )
    element.clear()
    element.send_keys(str(customer_id))


@when('I press "{button}"')
def press_button(context, button):
    """Click a named button."""
    element = context.wait.until(
        conditions.element_to_be_clickable((By.ID, BUTTON_IDS[button]))
    )
    element.click()


@then("I should see a successful creation")
def check_successful_creation(context):
    """Check the success message and returned shopcart ID."""
    message = wait_for_creation(context, "success")
    assert message.text == "Shopcart created successfully.", message.text

    context.wait.until(
        conditions.visibility_of_element_located((By.ID, "created-shopcart"))
    )

    shopcart_id = context.browser.find_element(By.ID, "result-shopcart-id").text

    assert shopcart_id.isdigit(), f"Expected a numeric shopcart ID, got {shopcart_id!r}"
    assert int(shopcart_id) > 0, shopcart_id


@then("the created shopcart should belong to the entered customer")
def check_created_customer(context):
    """Check the returned customer ID shown on the page."""
    customer_id = context.browser.find_element(By.ID, "result-customer-id").text

    assert customer_id == str(
        context.customer_id
    ), f"Expected customer {context.customer_id}, got {customer_id}"


@then("the created shopcart should contain {count:d} items")
def check_created_item_count(context, count):
    """Check the displayed item count."""
    item_count = context.browser.find_element(By.ID, "result-item-count").text

    assert item_count == str(count), f"Expected {count} items, got {item_count}"


@then("I should see a customer validation error")
def check_customer_validation_error(context):
    """Check a rejected creation and ensure old results are hidden."""
    message = wait_for_creation(context, "error")

    expected = (
        "Unable to create shopcart. Check the customer ID; "
        "the customer may already have a shopcart."
    )
    assert message.text == expected, message.text

    assert not context.browser.find_element(
        By.ID, "created-shopcart"
    ).is_displayed(), "A failed request must not display an old result."


@then('the "{button}" button should be enabled')
def check_button_enabled(context, button):
    """Check that the user can retry."""
    context.wait.until(conditions.element_to_be_clickable((By.ID, BUTTON_IDS[button])))


@when("I enter the created shopcart ID for deletion")
def enter_created_shopcart_id_for_deletion(context):
    """Enter the created shopcart ID in the delete form."""
    shopcart_id = context.browser.find_element(By.ID, "result-shopcart-id").text

    assert shopcart_id.isdigit(), f"Expected a numeric shopcart ID, got {shopcart_id!r}"

    context.shopcart_id = int(shopcart_id)

    element = context.wait.until(
        conditions.element_to_be_clickable((By.ID, FIELD_IDS["Shopcart ID"]))
    )
    element.clear()
    element.send_keys(shopcart_id)


@then("I should see a successful deletion")
def check_successful_deletion(context):
    """Check that the delete request completed successfully."""

    def deletion_finished(browser):
        message = browser.find_element(By.ID, "deletion-message")
        button = browser.find_element(By.ID, "delete-shopcart-btn")
        state = message.get_attribute("data-state")

        if state in ("success", "error") and button.is_enabled():
            return message

        return False

    message = context.wait.until(deletion_finished)

    assert message.get_attribute("data-state") == "success", message.text
    assert message.text == "Shopcart deleted successfully.", message.text


@then("the created shopcart should no longer be displayed")
def check_deleted_shopcart_not_displayed(context):
    """Check that the deleted shopcart result is hidden."""
    context.wait.until(
        conditions.invisibility_of_element_located((By.ID, "created-shopcart"))
    )


def wait_for_retrieval(context, expected_state):
    """Wait for retrieval to finish and check its displayed state."""

    def request_finished(browser):
        message = browser.find_element(By.ID, "read-message")
        button = browser.find_element(By.ID, "read-shopcart-btn")
        state = message.get_attribute("data-state")

        if state in ("success", "error") and button.is_enabled():
            return message

        return False

    message = context.wait.until(request_finished)
    actual_state = message.get_attribute("data-state")

    assert actual_state == expected_state, (
        f"Expected {expected_state}, got {actual_state}: {message.text}"
    )
    return message


@when("I enter the created shopcart ID for retrieval")
def enter_created_shopcart_id(context):
    """Copy the ID displayed by the creation form into the retrieval form."""
    shopcart_id = context.browser.find_element(
        By.ID, "result-shopcart-id"
    ).text

    assert shopcart_id.isdigit(), (
        f"Expected a numeric shopcart ID, got {shopcart_id!r}"
    )
    context.read_shopcart_id = shopcart_id

    element = context.wait.until(
        conditions.element_to_be_clickable((By.ID, "read-shopcart-id"))
    )
    element.clear()
    element.send_keys(shopcart_id)


@then("I should see a successful retrieval")
def check_successful_retrieval(context):
    """Check the retrieval success message and visible result."""
    message = wait_for_retrieval(context, "success")
    assert message.text == "Shopcart retrieved successfully.", message.text

    context.wait.until(
        conditions.visibility_of_element_located(
            (By.ID, "retrieved-shopcart")
        )
    )


@then("the retrieved shopcart should match the created shopcart")
def check_retrieved_shopcart(context):
    """Verify that the retrieved cart has the expected ID and customer."""
    shopcart_id = context.browser.find_element(
        By.ID, "read-result-shopcart-id"
    ).text
    customer_id = context.browser.find_element(
        By.ID, "read-result-customer-id"
    ).text

    assert shopcart_id == context.read_shopcart_id, (
        f"Expected shopcart {context.read_shopcart_id}, got {shopcart_id}"
    )
    assert customer_id == str(context.customer_id), (
        f"Expected customer {context.customer_id}, got {customer_id}"
    )


@then("the retrieved shopcart should contain {count:d} items")
def check_retrieved_item_count(context, count):
    """Check the retrieved cart's displayed item count."""
    item_count = context.browser.find_element(
        By.ID, "read-result-item-count"
    ).text

    assert item_count == str(count), (
        f"Expected {count} items, got {item_count}"
    )

    if count == 0:
        items = context.browser.find_element(
            By.ID, "read-result-items"
        ).text
        assert items == "[]", f"Expected an empty item list, got {items}"


@when("I enter a nonexistent shopcart ID for retrieval")
def enter_nonexistent_shopcart_id(context):
    """Enter an unused ID in the local test database."""
    element = context.wait.until(
        conditions.element_to_be_clickable((By.ID, "read-shopcart-id"))
    )
    element.clear()
    element.send_keys("2147483647")


@then("I should see a shopcart not found message")
def check_shopcart_not_found(context):
    """Check the message for a missing shopcart."""
    message = wait_for_retrieval(context, "error")
    assert message.text == "Shopcart not found.", message.text


@then("the retrieved shopcart details should be hidden")
def check_retrieved_details_hidden(context):
    """Check that a failed retrieval clears previous results."""
    panel = context.browser.find_element(By.ID, "retrieved-shopcart")
    assert not panel.is_displayed(), "Previous shopcart details are still visible."

    for field_id in (
        "read-result-shopcart-id",
        "read-result-customer-id",
        "read-result-item-count",
        "read-result-items",
    ):
        element = context.browser.find_element(By.ID, field_id)
        assert element.get_attribute("textContent") == "", (
            f"Previous content remains in {field_id}."
        )
