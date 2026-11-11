Feature: Create shopcarts through the administration page
  As an e-commerce manager
  I want to create a shopcart through the administration page
  So that I can begin preparing an order for a customer

  Background:
    Given I am on the administration page

  Scenario: Display the creation form
    Then I should see the heading "Shopcart Administration"
    And I should see the "Customer ID" field
    And I should see the "Create Shopcart" button

  Scenario: Create an empty shopcart
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    And the created shopcart should belong to the entered customer
    And the created shopcart should contain 0 items

  Scenario: Retry after submitting a duplicate customer ID
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    And the created shopcart should belong to the entered customer
    When I press "Create Shopcart"
    Then I should see a customer validation error
    And the "Create Shopcart" button should be enabled
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    And the created shopcart should belong to the entered customer
    And the created shopcart should contain 0 items

  Scenario: Delete a shopcart
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    When I enter the created shopcart ID for deletion
    And I press "Delete Shopcart"
    Then I should see a successful deletion
    And the created shopcart should no longer be displayed