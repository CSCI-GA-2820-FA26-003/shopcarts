"use strict";

const form = document.getElementById("create-shopcart-form");
const customerInput = document.getElementById("customer-id");
const createButton = document.getElementById("create-shopcart-btn");
const message = document.getElementById("creation-message");

const resultPanel = document.getElementById("created-shopcart");
const resultShopcartId = document.getElementById("result-shopcart-id");
const resultCustomerId = document.getElementById("result-customer-id");
const resultItemCount = document.getElementById("result-item-count");

const deleteForm = document.getElementById("delete-shopcart-form");
const deleteInput = document.getElementById("delete-shopcart-id");
const deleteButton = document.getElementById("delete-shopcart-btn");
const deletionMessage = document.getElementById("deletion-message");

function showMessage(text, state) {
  message.textContent = text;
  message.dataset.state = state;
}

function showDeletionMessage(text, state) {
  deletionMessage.textContent = text;
  deletionMessage.dataset.state = state;
}

function clearResult() {
  resultPanel.hidden = true;
  resultShopcartId.textContent = "";
  resultCustomerId.textContent = "";
  resultItemCount.textContent = "";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (createButton.disabled || !form.reportValidity()) {
    return;
  }

  const customerId = Number(customerInput.value);

  clearResult();
  createButton.disabled = true;
  showMessage("Creating shopcart...", "pending");

  try {
    const response = await fetch(form.dataset.endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        customer_id: customerId,
        items: []
      })
    });

    if (response.status === 400 || response.status === 409) {
      showMessage(
        "Unable to create shopcart. Check the customer ID; " +
        "the customer may already have a shopcart.",
        "error"
      );
      return;
    }

    if (response.status !== 201) {
      showMessage(
        "The service could not create the shopcart. Please try again.",
        "error"
      );
      return;
    }

    const shopcart = await response.json();

    if (
      !Number.isInteger(shopcart.id) ||
      shopcart.id <= 0 ||
      shopcart.customer_id !== customerId ||
      !Array.isArray(shopcart.items)
    ) {
      showMessage(
        "The service returned an unexpected response. " +
        "Check whether the shopcart was created before trying again.",
        "error"
      );
      return;
    }

    resultShopcartId.textContent = String(shopcart.id);
    resultCustomerId.textContent = String(shopcart.customer_id);
    resultItemCount.textContent = String(shopcart.items.length);
    resultPanel.hidden = false;

    showMessage("Shopcart created successfully.", "success");
  } catch {
    showMessage(
      "Unable to confirm creation. Check your connection and " +
      "whether the shopcart was created before trying again.",
      "error"
    );
  } finally {
    createButton.disabled = false;
  }
});

deleteForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (deleteButton.disabled || !deleteForm.reportValidity()) {
    return;
  }

  const shopcartId = Number(deleteInput.value);

  deleteButton.disabled = true;
  showDeletionMessage("Deleting shopcart...", "pending");

  try {
    const response = await fetch(
      `${deleteForm.dataset.endpoint}/${shopcartId}`,
      {
        method: "DELETE"
      }
    );

    if (response.status !== 204) {
      showDeletionMessage(
        "The service could not delete the shopcart. Please try again.",
        "error"
      );
      return;
    }

    if (resultShopcartId.textContent === String(shopcartId)) {
      clearResult();
    }

    deleteInput.value = "";
    showDeletionMessage("Shopcart deleted successfully.", "success");
  } catch {
    showDeletionMessage(
      "Unable to delete the shopcart. Check your connection and try again.",
      "error"
    );
  } finally {
    deleteButton.disabled = false;
  }
});

// Enable buttons after their submit handlers have been installed.
createButton.disabled = false;
deleteButton.disabled = false;

const readForm = document.getElementById("read-shopcart-form");
const readInput = document.getElementById("read-shopcart-id");
const readButton = document.getElementById("read-shopcart-btn");
const readMessage = document.getElementById("read-message");

const readPanel = document.getElementById("retrieved-shopcart");
const readResultId = document.getElementById("read-result-shopcart-id");
const readResultCustomer = document.getElementById("read-result-customer-id");
const readResultCount = document.getElementById("read-result-item-count");
const readResultItems = document.getElementById("read-result-items");

function showReadMessage(text, state) {
  readMessage.textContent = text;
  readMessage.dataset.state = state;
}

function clearReadResult() {
  readPanel.hidden = true;
  readResultId.textContent = "";
  readResultCustomer.textContent = "";
  readResultCount.textContent = "";
  readResultItems.textContent = "";
}

readForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (readButton.disabled || !readForm.reportValidity()) {
    return;
  }

  const shopcartId = Number(readInput.value);
  const endpoint = readForm.dataset.endpointTemplate.replace(
    /\/0$/,
    `/${shopcartId}`
  );

  clearReadResult();
  readButton.disabled = true;
  showReadMessage("Retrieving shopcart...", "pending");

  try {
    const response = await fetch(endpoint, {
      headers: {
        "Accept": "application/json"
      }
    });

    if (response.status === 404) {
      showReadMessage("Shopcart not found.", "error");
      return;
    }

    if (response.status !== 200) {
      showReadMessage(
        "The service could not retrieve the shopcart. Please try again.",
        "error"
      );
      return;
    }

    const shopcart = await response.json();

    if (
      shopcart.id !== shopcartId ||
      !Number.isInteger(shopcart.customer_id) ||
      !Array.isArray(shopcart.items)
    ) {
      showReadMessage(
        "The service returned an unexpected response. Please try again.",
        "error"
      );
      return;
    }

    readResultId.textContent = String(shopcart.id);
    readResultCustomer.textContent = String(shopcart.customer_id);
    readResultCount.textContent = String(shopcart.items.length);
    readResultItems.textContent = JSON.stringify(shopcart.items, null, 2);
    readPanel.hidden = false;

    showReadMessage("Shopcart retrieved successfully.", "success");
  } catch {
    showReadMessage(
      "Unable to retrieve the shopcart. Check your connection and try again.",
      "error"
    );
  } finally {
    readButton.disabled = false;
  }
});

readButton.disabled = false;

const queryForm = document.getElementById("query-shopcart-form");
const queryInput = document.getElementById("query-customer-id");
const queryButton = document.getElementById("query-shopcart-btn");
const queryMessage = document.getElementById("query-message");
const queryResults = document.getElementById("query-results");
const queryResultsBody = document.getElementById("query-results-body");

function showQueryMessage(text, state) {
  queryMessage.textContent = text;
  queryMessage.dataset.state = state;
}

function clearQueryResults() {
  queryResults.hidden = true;
  queryResultsBody.replaceChildren();
}

function displayQueryResults(shopcarts) {
  queryResultsBody.replaceChildren();

  for (const shopcart of shopcarts) {
    const row = document.createElement("tr");

    const shopcartId = document.createElement("td");
    shopcartId.textContent = String(shopcart.id);

    const customerId = document.createElement("td");
    customerId.textContent = String(shopcart.customer_id);

    const itemCount = document.createElement("td");
    itemCount.textContent = String(shopcart.items.length);

    row.append(shopcartId, customerId, itemCount);
    queryResultsBody.appendChild(row);
  }

  queryResults.hidden = false;
}

queryForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (queryButton.disabled || !queryForm.reportValidity()) {
    return;
  }

  const customerId = Number(queryInput.value);
  const endpoint = new URL(queryForm.dataset.endpoint, window.location.origin);
  endpoint.searchParams.set("customer_id", String(customerId));

  clearQueryResults();
  queryButton.disabled = true;
  showQueryMessage("Searching for shopcarts...", "pending");

  try {
    const response = await fetch(endpoint, {
      headers: {
        "Accept": "application/json"
      }
    });

    if (response.status !== 200) {
      showQueryMessage(
        "The service could not search for shopcarts. Please try again.",
        "error"
      );
      return;
    }

    const shopcarts = await response.json();

    if (
      !Array.isArray(shopcarts) ||
      shopcarts.some(
        (shopcart) =>
          !Number.isInteger(shopcart.id) ||
          shopcart.customer_id !== customerId ||
          !Array.isArray(shopcart.items)
      )
    ) {
      showQueryMessage(
        "The service returned an unexpected response. Please try again.",
        "error"
      );
      return;
    }

    if (shopcarts.length === 0) {
      showQueryMessage("No shopcarts found.", "success");
      return;
    }

    displayQueryResults(shopcarts);
    showQueryMessage("Shopcarts found successfully.", "success");
  } catch {
    showQueryMessage(
      "Unable to search for shopcarts. Check your connection and try again.",
      "error"
    );
  } finally {
    queryButton.disabled = false;
  }
});

queryButton.disabled = false;