Feature: Read shopcarts through the administration page
  As an e-commerce administrator
  I want to retrieve a shopcart by its ID
  So that I can view its current details

  Background:
    Given I am on the administration page

  Scenario: Display the retrieval form
    Then I should see the "Shopcart ID" field
    And I should see the "Retrieve" button

  Scenario: Retrieve an existing shopcart
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    When I enter the created shopcart ID for retrieval
    And I press "Retrieve"
    Then I should see a successful retrieval
    And the retrieved shopcart should match the created shopcart
    And the retrieved shopcart should contain 0 items

  Scenario: Clear previous details when a shopcart is not found
    When I enter a new test customer ID
    And I press "Create Shopcart"
    Then I should see a successful creation
    When I enter the created shopcart ID for retrieval
    And I press "Retrieve"
    Then I should see a successful retrieval
    When I enter a nonexistent shopcart ID for retrieval
    And I press "Retrieve"
    Then I should see a shopcart not found message
    And the retrieved shopcart details should be hidden
    And the "Retrieve" button should be enabled
    When I enter the created shopcart ID for retrieval
    And I press "Retrieve"
    Then I should see a successful retrieval
    And the retrieved shopcart should match the created shopcart
