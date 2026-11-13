Feature: Update shopcarts through the administration page
  As an e-commerce administrator
  I want to edit an existing shopcart
  So that I can correct its details

  Background:
    Given I am on the administration page

  Scenario: Update a shopcart customer ID
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    When I enter the created shopcart ID for retrieval
    And I press "Retrieve"
    Then I should see a successful retrieval
    And the update form should show the current customer ID
    When I enter a new customer ID for update
    And I press "Update"
    Then I should see a successful update
    And the displayed shopcart should have the updated customer ID
    When I press "Retrieve"
    Then I should see a successful retrieval
    And the displayed shopcart should have the updated customer ID
    And the retrieved shopcart should contain 0 items

  Scenario: Show an error when the retrieved shopcart has been deleted
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    When I enter the created shopcart ID for retrieval
    And I press "Retrieve"
    Then I should see a successful retrieval
    When I enter the created shopcart ID for deletion
    And I press "Delete Shopcart"
    Then I should see a successful deletion
    When I enter a new customer ID for update
    And I press "Update"
    Then I should see an update shopcart not found message
    And the retrieved shopcart details should be hidden
