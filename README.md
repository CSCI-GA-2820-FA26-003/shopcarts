# Shopcarts

Shopcart service for NYU CSCI-GA.2820-003, DevOps and Agile Methodologies. Each customer has a shopping cart that holds the products they plan to buy.

Built with Flask, SQLAlchemy, and PostgreSQL.

### Continuous Integration
[![CI](https://github.com/CSCI-GA-2820-FA26-003/shopcarts/actions/workflows/ci.yml/badge.svg)](https://github.com/CSCI-GA-2820-FA26-003/shopcarts/actions/workflows/ci.yml)
[![codecov](https://codecov.io/github/CSCI-GA-2820-FA26-003/shopcarts/graph/badge.svg?token=6SS68Z8251)](https://codecov.io/github/CSCI-GA-2820-FA26-003/shopcarts)

## Local Setup

You will need Git, Docker Desktop, and VS Code with the Dev Containers extension.

1. Start Docker Desktop.
2. Clone the repository:

```bash
   git clone https://github.com/CSCI-GA-2820-FA26-003/shopcarts.git
   cd shopcarts
```

3. Open the `shopcarts` folder in VS Code.
4. Open the Command Palette and select **Dev Containers: Reopen in Container**.
5. Wait for the container setup to finish, then open a terminal in VS Code.

The setup installs the Python dependencies and starts PostgreSQL in a separate container. Run the commands below in the development container's terminal.

## Running the Service

```bash
make run
```

Open <http://localhost:8080/> for the Shopcart administration page, or <http://localhost:8080/apidocs/> for the interactive Swagger API documentation. If VS Code forwards a different local port, use the address in the Ports tab. Stop the server with `Ctrl+C`.

## Tests and Code Checks

Run all tests:

```bash
make test
```

Tests must pass with at least 95% coverage. They clear Shopcart and Item records in the configured database, so only run them against a development or test database.

Run the code checks:

```bash
make lint
```

This runs Flake8 and Pylint. Check the output for errors and warnings, even if the command finishes.

After `make deploy`, check that the Traefik Ingress routes traffic to the service:

```bash
make test-ingress
```

This sends `GET /health` and `GET /api/shopcarts` to `http://127.0.0.1:8080` (override with `BASE_URL=...`). It retries each check up to 10 times while the Ingress comes up, and exits nonzero if either check fails.

## Database

The service uses two tables in PostgreSQL, defined in `service/models/`.

```text
shopcart (1) ──────< (many) item
```

**shopcart**

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | Integer | Primary key |
| `customer_id` | Integer | Not null, unique |

**item**

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | Integer | Primary key |
| `shopcart_id` | Integer | Foreign key to `shopcart.id`, not null, `ON DELETE CASCADE` |
| `product_id` | Integer | Not null |
| `name` | String(64) | Not null |
| `description` | String(256) | Optional |
| `price` | Numeric(10, 2) | Not null |
| `quantity` | Integer | Not null, default 1 |

Notes:

- `customer_id` is unique, so the database itself prevents a second shopcart for the same customer.
- Deleting a shopcart deletes all of its items (cascade).
- `price` is stored as a fixed-point decimal to avoid floating-point rounding errors.
- `quantity` must be a positive integer. This is enforced when a request is deserialized, not by a database constraint.
## API

The REST API is served under `/api`, so the shopcart collection is at `/api/shopcarts`. Interactive Swagger documentation, with every endpoint, model and response code, is at [`/apidocs/`](http://localhost:8080/apidocs/), and the OpenAPI (Swagger 2.0) specification is at `/api/swagger.json`. The administration page (`/`) and the health check (`/health`) stay at the root, outside `/api`.

Every response with a body is JSON; `DELETE` returns `204 No Content` with an empty body. `POST` and `PUT` requests must send `Content-Type: application/json`, except `PUT /api/shopcarts/{id}/checkout`, which takes no body.

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/` | Shopcart administration page (HTML) | `200 OK` |
| GET | `/health` | Health check | `200 OK` |
| GET | `/apidocs/` | Swagger API documentation (HTML) | `200 OK` |
| GET | `/api/shopcarts` | List all shopcarts, or `?customer_id=N` for one customer's shopcart | `200 OK` |
| POST | `/api/shopcarts` | Create a shopcart | `201 Created` + `Location` header |
| GET | `/api/shopcarts/{id}` | Read one shopcart with its items | `200 OK` |
| PUT | `/api/shopcarts/{id}` | Update a shopcart's customer and/or replace its items | `200 OK` |
| DELETE | `/api/shopcarts/{id}` | Delete a shopcart and its items | `204 No Content` |
| GET | `/api/shopcarts/{id}/total` | Total price of a shopcart's items | `200 OK` |
| POST | `/api/shopcarts/{id}/items` | Add an item to a shopcart | `201 Created` + `Location` header |
| GET | `/api/shopcarts/{id}/items` | List the items in a shopcart | `200 OK` |
| DELETE | `/api/shopcarts/{id}/items` | Remove all items, keeping the shopcart | `204 No Content` |
| GET | `/api/shopcarts/{id}/items/{item_id}` | Read one item in a shopcart | `200 OK` |
| PUT | `/api/shopcarts/{id}/items/{item_id}` | Update one item in a shopcart | `200 OK` |
| DELETE | `/api/shopcarts/{id}/items/{item_id}` | Remove one item from a shopcart | `204 No Content` |
| PUT | `/api/shopcarts/{id}/checkout` | Check out a shopcart so it can no longer be modified | `200 OK` |

`{id}` is the shopcart id returned by the service, not the customer id. `{item_id}` is the item id, not the product id.

### Shopcart JSON

```json
{
  "customer_id": 1001,
  "id": 1,
  "status": "active",
  "items": [
    {
      "description": "A5 notebook",
      "id": 2,
      "name": "Notebook",
      "price": 7.5,
      "product_id": 42,
      "quantity": 2,
      "shopcart_id": 1
    }
  ]
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `id` | Integer | Generated by the database. Never read from a request body. |
| `customer_id` | Integer | Required. Identifies the customer. Each customer can have only one shopcart. |
| `items` | Array | Items in the shopcart. Optional when creating a shopcart. |
| `status` | String | `active` or `checked_out`. New shopcarts are `active`. Only the checkout endpoint changes it; a `status` in a request body is ignored. |

### Item JSON

| Field | Type | Notes |
| --- | --- | --- |
| `id` | Integer | Generated by the database. |
| `shopcart_id` | Integer | The shopcart the item belongs to. |
| `product_id` | Integer | Required. |
| `name` | String | Required. At most 64 characters. |
| `description` | String | Optional. At most 256 characters. |
| `price` | Number | Required. Stored with two decimal places. |
| `quantity` | Integer | Required. Must be positive. |

### GET /

Returns the Shopcart administration page (HTML). The page calls the REST API under `/api`.

```bash
curl -i http://localhost:8080/
```

### GET /api/shopcarts

Returns a JSON array of all shopcarts, each in the format above. Returns `[]` when there are none.

```bash
curl -i http://localhost:8080/api/shopcarts
```

### POST /api/shopcarts

Creates a shopcart. The body needs `customer_id`. `items` may be omitted or sent as a list of items.

```bash
curl -i -X POST http://localhost:8080/api/shopcarts \
  -H 'Content-Type: application/json' \
  -d '{"customer_id": 1001}'
```

Returns `201 Created` with the new shopcart in the body and a `Location` header pointing to it, for example `http://localhost:8080/api/shopcarts/1`.

- `400 Bad Request`: missing or invalid fields.
- `415 Unsupported Media Type`: the request is not JSON.

### GET /api/shopcarts/{id}

```bash
curl -i http://localhost:8080/api/shopcarts/1
```

Returns `200 OK` with the shopcart and its items.

- `404 Not Found`: no shopcart with that id.

### PUT /api/shopcarts/{id}

Updates `customer_id` and/or `items`. A field that is left out keeps its current value. If `items` is sent, it replaces the whole item list, and `[]` clears it. An `id` in the body is ignored.

```bash
curl -i -X PUT http://localhost:8080/api/shopcarts/1 \
  -H 'Content-Type: application/json' \
  -d '{"customer_id": 1002}'
```

```bash
curl -i -X PUT http://localhost:8080/api/shopcarts/1 \
  -H 'Content-Type: application/json' \
  -d '{"items": [{"product_id": 77, "name": "Pen", "price": 1.25, "quantity": 3}]}'
```

Returns `200 OK` with the updated shopcart.

- `400 Bad Request`: the body is not a JSON object, `customer_id` is not an integer, `items` is not a list, or an item is invalid.
- `404 Not Found`: no shopcart with that id.
- `415 Unsupported Media Type`: the request is not JSON.

### DELETE /api/shopcarts/{id}

```bash
curl -i -X DELETE http://localhost:8080/api/shopcarts/1
```

Returns `204 No Content` with an empty body and deletes the shopcart's items with it. Deleting an id that does not exist also returns `204`, so the call is idempotent.

### POST /api/shopcarts/{id}/items

Adds one item. The body needs `product_id`, `name`, `price` and `quantity`. `description` is optional.

```bash
curl -i -X POST http://localhost:8080/api/shopcarts/1/items \
  -H 'Content-Type: application/json' \
  -d '{"product_id": 42, "name": "Notebook", "description": "A5 notebook", "price": 7.50, "quantity": 2}'
```

Returns `201 Created` with the whole updated shopcart, not just the new item.

- `400 Bad Request`: missing or invalid item fields.
- `404 Not Found`: no shopcart with that id.
- `415 Unsupported Media Type`: the request is not JSON.

### GET /api/shopcarts/{id}/items

```bash
curl -i http://localhost:8080/api/shopcarts/1/items
```

Returns `200 OK` with a JSON array of the shopcart's items.

- `404 Not Found`: no shopcart with that id.

### DELETE /api/shopcarts/{id}/items

```bash
curl -i -X DELETE http://localhost:8080/api/shopcarts/1/items
```

Returns `204 No Content` with an empty body. The shopcart itself stays.

- `404 Not Found`: no shopcart with that id.

### DELETE /api/shopcarts/{id}/items/{item_id}

```bash
curl -i -X DELETE http://localhost:8080/api/shopcarts/1/items/2
```

Returns `204 No Content` with an empty body.

- `404 Not Found`: no shopcart with that id, or the item does not exist in that shopcart.

### PUT /api/shopcarts/{id}/checkout

Finalizes a shopcart by changing its `status` from `active` to `checked_out`. No payment is processed and no order is created.

```bash
curl -i -X PUT http://localhost:8080/api/shopcarts/1/checkout
```

Returns `200 OK` with the checked-out shopcart. Checking out a shopcart that is already checked out also returns `200` and changes nothing.

- `404 Not Found`: no shopcart with that id.
- `409 Conflict`: the shopcart has no items. It stays `active`.

Once a shopcart is checked out, these requests return `409 Conflict` and change nothing: `PUT /api/shopcarts/{id}`, `POST /api/shopcarts/{id}/items`, `PUT /api/shopcarts/{id}/items/{item_id}`, `DELETE /api/shopcarts/{id}/items` and `DELETE /api/shopcarts/{id}/items/{item_id}`. `DELETE /api/shopcarts/{id}` still works, so a customer can start a new shopcart.

### Errors

Every error is returned as JSON in this format, never as HTML:

```json
{"status": 404, "error": "Not Found", "message": "404 Not Found: Shopcart with id '7' was not found"}
```

`status` repeats the HTTP status code. `message` starts with the code and its standard name, except for invalid data rejected by the models, whose `400` message is the plain validation error. The `error` labels are:

| Code | `error` |
| --- | --- |
| 400 | `Bad Request` |
| 404 | `Not Found` |
| 405 | `Method not Allowed` |
| 409 | `Conflict` |
| 415 | `Unsupported media type` |
| 500 | `Internal Server Error` |

## Project Layout

| Path | Contents |
| --- | --- |
| `service/models/` | Shopcart and Item models |
| `service/routes.py` | Flask-RESTX API resources and Swagger models |
| `service/common/` | Error handlers, logging, status codes and CLI commands |
| `tests/` | Model and API tests, test data factories |
| `.devcontainer/` | Development container and PostgreSQL configuration |
| `Makefile` | Development commands |

## License

Copyright (c) 2016, 2025 [John Rofrano](https://www.linkedin.com/in/JohnRofrano/). All rights reserved.

Licensed under the Apache License. See [LICENSE](LICENSE)

This repository is part of the New York University (NYU) masters class: **CSCI-GA.2820-003 DevOps and Agile Methodologies** created and taught by [John Rofrano](https://cs.nyu.edu/~rofrano/), Adjunct Instructor, NYU Courant Institute, Graduate Division, Computer Science, and NYU Stern School of Business.
