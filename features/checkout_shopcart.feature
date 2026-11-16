Feature: Checkout shopcarts through the administration page
  As a user
  I need the ability to checkout my shopping cart
  So that I can finalize my shopping cart and prevent further modifications

  Background:
    Given I am on the administration page

  Scenario: Display the checkout form
    Then I should see the "Checkout Shopcart ID" field
    And I should see the "Checkout" button

  Scenario: Successfully checkout a shopcart with items
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    When the created shopcart contains an item
    And I enter the created shopcart ID for checkout
    And I press "Checkout"
    Then I should see a successful checkout
    And the checked-out shopcart should match the created shopcart
    And the checked-out shopcart should contain 1 items
    And the checked-out shopcart should have status "checked_out"
    When I enter the created shopcart ID for retrieval
    And I press "Retrieve"
    Then I should see a successful retrieval
    And the retrieved shopcart should have status "checked_out"
    And the "Update" button should be disabled

  Scenario: Checkout a nonexistent shopcart
    When I enter a nonexistent shopcart ID for checkout
    And I press "Checkout"
    Then I should see a checkout shopcart not found message
    And the checked-out shopcart details should be hidden

  Scenario: Reject checkout of an empty shopcart
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    When I enter the created shopcart ID for checkout
    And I press "Checkout"
    Then I should see an empty shopcart checkout error
    And the checked-out shopcart details should be hidden
    When I enter the created shopcart ID for retrieval
    And I press "Retrieve"
    Then I should see a successful retrieval
    And the retrieved shopcart should have status "active"

  Scenario: Checking out an already checked-out shopcart changes nothing
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    When the created shopcart contains an item
    And I enter the created shopcart ID for checkout
    And I press "Checkout"
    Then I should see a successful checkout
    When I press "Checkout"
    Then I should see a successful checkout
    And the checked-out shopcart should contain 1 items
    And the checked-out shopcart should have status "checked_out"
