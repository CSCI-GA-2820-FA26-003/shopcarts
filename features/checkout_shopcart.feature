Feature: Checkout shopcarts through the administration page
  As a user
  I need the ability to checkout my shopping cart
  So that I can finalize my shopping cart and prevent further modifications

  Background:
    Given I am on the administration page

  Scenario: Successfully checkout a shopcart with items
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    When I enter the created shopcart ID for retrieval
    And I press "Retrieve"
    Then I should see a successful retrieval
    And the retrieved shopcart should have status "active"
    And the "Add Item" button should be enabled
    When I add an item through the administration page
    Then I should see a successful item addition
    And the retrieved shopcart should contain 1 items
    When I press "Checkout"
    Then I should see a successful checkout
    And the retrieved shopcart should have status "checked_out"
    And the retrieved shopcart should contain 1 items
    And the "Add Item" button should be disabled
    And the "Update" button should be disabled
    When I press "Retrieve"
    Then I should see a successful retrieval
    And the retrieved shopcart should have status "checked_out"
    And the retrieved shopcart should contain 1 items
    And the "Add Item" button should be disabled
    And the "Update" button should be disabled

  Scenario: Checking out an already checked-out shopcart changes nothing
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    When I enter the created shopcart ID for retrieval
    And I press "Retrieve"
    Then I should see a successful retrieval
    When I add an item through the administration page
    Then I should see a successful item addition
    And the retrieved shopcart should contain 1 items
    When I press "Checkout"
    Then I should see a successful checkout
    And the retrieved shopcart should have status "checked_out"
    And the "Checkout" button should be enabled
    When I press "Checkout"
    Then I should see a successful checkout
    And the retrieved shopcart should have status "checked_out"
    And the retrieved shopcart should contain 1 items
    And the "Add Item" button should be disabled
    And the "Update" button should be disabled
    When I press "Retrieve"
    Then I should see a successful retrieval
    And the retrieved shopcart should have status "checked_out"
    And the retrieved shopcart should contain 1 items
    And the "Add Item" button should be disabled
    And the "Update" button should be disabled

  Scenario: Reject checkout of an empty shopcart
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    When I enter the created shopcart ID for retrieval
    And I press "Retrieve"
    Then I should see a successful retrieval
    And the retrieved shopcart should contain 0 items
    When I press "Checkout"
    Then I should see an empty shopcart checkout error
    And the retrieved shopcart should have status "active"
    And the "Add Item" button should be enabled
    When I press "Retrieve"
    Then I should see a successful retrieval
    And the retrieved shopcart should have status "active"

  Scenario: Show an error when checking out a deleted shopcart
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    When I enter the created shopcart ID for retrieval
    And I press "Retrieve"
    Then I should see a successful retrieval
    When I enter the created shopcart ID for deletion
    And I press "Delete Shopcart"
    Then I should see a successful deletion
    When I press "Checkout"
    Then I should see a checkout shopcart not found message
    And the retrieved shopcart details should be hidden
    And the "Add Item" button should be disabled
    And the "Update" button should be disabled
