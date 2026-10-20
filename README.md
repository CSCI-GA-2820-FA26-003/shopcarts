# Shopcarts Service

A RESTful shopping-cart microservice developed for NYU's DevOps and Agile Methodologies course. It manages shopping carts belonging to customers and the products stored within each cart.

## Features

- Create and retrieve customer shopping carts.
- List all shopping carts.
- Update a cart's customer ID or replace its items.
- Add, list, remove, and clear items within a cart.
- Persist carts and items in PostgreSQL through SQLAlchemy.

A `Shopcart` has a unique integer `customer_id`, and each item includes its product ID, name, optional description, price, and quantity.

## Technology Stack

- Python 3.12
- Flask 3.1.3 and Flask-SQLAlchemy 3.1.1
- PostgreSQL (PostgreSQL 15 in the supplied Dev Container setup)
- Pipenv for dependency management
- Gunicorn and Honcho for running the service
- Pytest for testing; Flake8 and Pylint for code-quality checks

## Getting Started

### Recommended: VS Code Dev Container

The repository includes a Dev Container configuration that defines an application container and a PostgreSQL database container.

**Prerequisites:** Git, Docker, VS Code, and the VS Code **Dev Containers** extension.

1. Clone and open the repository:

   ```bash
   git clone https://github.com/CSCI-GA-2820-FA26-003/shopcarts.git
   cd shopcarts
   code .
   ```

2. In VS Code, run **Dev Containers: Reopen in Container** from the Command Palette. The provided Docker Compose configuration starts the development environment and its PostgreSQL dependency.
3. Open a terminal **inside the container** and start the application:

   ```bash
   make run
   ```

4. The service is configured to listen on port **8080**. VS Code forwards port 8080 from the container; visit `http://localhost:8080/` or run:

   ```bash
   curl http://localhost:8080/
   ```

The repository's `Makefile` implements `make run` using `honcho start`, and its `Procfile` launches Gunicorn with the Flask WSGI application at `wsgi:app`.

### Alternative: Local Python Environment

You can also run the service outside the Dev Container, provided that Python 3.12, Pipenv and a reachable PostgreSQL instance are installed.

```bash
git clone https://github.com/CSCI-GA-2820-FA26-003/shopcarts.git
cd shopcarts
pipenv install --dev
```

Configure the database connection before starting the service. For example, set `DATABASE_URI` to the connection string for **your own running PostgreSQL database**:

```bash
export DATABASE_URI='postgresql+psycopg://USER:PASSWORD@localhost:5432/DBNAME'
export PORT=8080
pipenv run honcho start
```

Do not commit real database passwords or secrets to Git. The application creates database tables on startup; the database server and target database must already be available.

## API Reference

Base URL for local development: `http://localhost:8080`

| Method | Path | Description | Typical success status |
| --- | --- | --- | --- |
| `GET` | `/` | Service information | `200 OK` |
| `GET` | `/shopcarts` | List all shopping carts | `200 OK` |
| `POST` | `/shopcarts` | Create a shopping cart | `201 Created` |
| `GET` | `/shopcarts/{shopcart_id}` | Retrieve one shopping cart | `200 OK` |
| `PUT` | `/shopcarts/{shopcart_id}` | Update a cart's customer ID and/or replace its items | `200 OK` |
| `POST` | `/shopcarts/{shopcart_id}/items` | Add an item to a cart | `201 Created` |
| `GET` | `/shopcarts/{shopcart_id}/items` | List items in a cart | `200 OK` |
| `DELETE` | `/shopcarts/{shopcart_id}/items` | Remove all items, keeping the cart | `204 No Content` |
| `DELETE` | `/shopcarts/{shopcart_id}/items/{item_id}` | Remove an item from a cart | `204 No Content` |

These are the endpoints defined in `service/routes.py` on the `master` branch at the time this README was drafted. A delete-cart endpoint is **not currently defined** in that file.

### Data Fields

**Shopcart**

| Field | Type | Description |
| --- | --- | --- |
| `id` | integer | Server-generated cart ID |
| `customer_id` | integer | Required customer ID; unique across carts |
| `items` | array | Items in the cart; optional when creating a cart |

**Item**

| Field | Type | Description |
| --- | --- | --- |
| `id` | integer | Server-generated item ID |
| `shopcart_id` | integer | Parent cart ID |
| `product_id` | integer | Required product ID |
| `name` | string | Required product name (up to 64 characters) |
| `description` | string or null | Optional description (up to 256 characters) |
| `price` | number | Required item price, stored with two decimal places |
| `quantity` | integer | Required positive quantity |

### Request Inputs and Responses

All `{shopcart_id}` and `{item_id}` path parameters are **integer IDs** returned by the service, not customer IDs or product IDs. The API uses JSON for request bodies and responses. For `POST` and `PUT`, send exactly `Content-Type: application/json`.

| Method and endpoint | Required input | Optional input | Success response |
| --- | --- | --- | --- |
| `GET /` | None | None | `200` JSON object with service name, version, and a link to the cart collection |
| `GET /shopcarts` | None | None | `200` JSON array of carts (possibly empty) |
| `POST /shopcarts` | JSON body with integer `customer_id` | `items`: array of item objects | `201` serialized cart JSON and `Location` header |
| `GET /shopcarts/{shopcart_id}` | Integer `shopcart_id` in URL | None | `200` serialized cart JSON |
| `PUT /shopcarts/{shopcart_id}` | Integer `shopcart_id` in URL; JSON object body | `customer_id` (integer) and/or `items` (array); omitting either retains its existing value | `200` updated cart JSON |
| `POST /shopcarts/{shopcart_id}/items` | Integer `shopcart_id` in URL; JSON item with `product_id`, `name`, `price`, `quantity` | `description` | `201` serialized **cart** including the new item |
| `GET /shopcarts/{shopcart_id}/items` | Integer `shopcart_id` in URL | None | `200` JSON array of items |
| `DELETE /shopcarts/{shopcart_id}/items` | Integer `shopcart_id` in URL | None | `204` empty body (the cart itself remains) |
| `DELETE /shopcarts/{shopcart_id}/items/{item_id}` | Integer `shopcart_id` and `item_id` in URL | None | `204` empty body |

When replacing items using `PUT`, every object in the `items` array must supply `product_id`, `name`, `price`, and `quantity`; `description` is optional. Supplying `items: []` clears the cart's items. Updating only `customer_id` leaves the items unchanged. The implementation permits a JSON object with neither update field, which leaves the cart unchanged.

**Important constraints:** `customer_id` must be an integer and is unique across shopcarts; `quantity` must be a positive integer. An item's `name` and `description` columns have maximum lengths of 64 and 256 characters respectively, and `price` is stored as a two-decimal-place numeric value. Database constraints may also reject incompatible values. IDs are generated by the database; do not supply `id` as a replacement for `customer_id` or `product_id`.

### Example Requests and Responses

Examples assume the app is running at `http://localhost:8080` and that the database assigns cart ID `1` and item ID `2`. **Actual IDs and output values may differ.** Use the IDs returned by your own requests.

**1. Check service information**

```bash
curl -i http://localhost:8080/
```

The response is `200 OK` with a JSON object containing `name`, `version`, and `paths` (an absolute URL for `/shopcarts`).

**2. Create a cart (POST)**

```bash
curl -i -X POST http://localhost:8080/shopcarts \
  -H 'Content-Type: application/json' \
  -d '{"customer_id": 1001}'
```

Expected: `201 Created`, a `Location` header pointing to the new cart, and JSON with `id`, `customer_id`, and `items`, for example:

```json
{"id": 1, "customer_id": 1001, "items": []}
```

Alternatively, include initial `items` in the creation payload:

```json
{
  "customer_id": 1001,
  "items": [
    {"product_id": 42, "name": "Notebook", "description": "A5 notebook", "price": 7.50, "quantity": 2}
  ]
}
```

Use a different `customer_id` when trying both examples: the model requires unique customer IDs.

**3. List carts and read one cart (GET)**

```bash
curl -i http://localhost:8080/shopcarts
curl -i http://localhost:8080/shopcarts/1
```

Each returns `200 OK`; the first body is an array of serialized carts, the second is one serialized cart. A nonexistent cart returns `404 Not Found`.

**4. Add an item (POST)**

```bash
curl -i -X POST http://localhost:8080/shopcarts/1/items \
  -H 'Content-Type: application/json' \
  -d '{"product_id": 42, "name": "Notebook", "description": "A5 notebook", "price": 7.50, "quantity": 2}'
```

Expected: `201 Created` and the **whole updated cart** in JSON, including its `items` array. This is not an item-only response.

**5. List a cart's items (GET)**

```bash
curl -i http://localhost:8080/shopcarts/1/items
```

Expected: `200 OK` and an array of item objects such as:

```json
[
  {"id": 2, "shopcart_id": 1, "product_id": 42, "name": "Notebook", "description": "A5 notebook", "price": 7.5, "quantity": 2}
]
```

**6. Update a cart (PUT)**

Change the customer without replacing the items:

```bash
curl -i -X PUT http://localhost:8080/shopcarts/1 \
  -H 'Content-Type: application/json' \
  -d '{"customer_id": 1002}'
```

Or replace the entire item list while keeping the existing customer:

```bash
curl -i -X PUT http://localhost:8080/shopcarts/1 \
  -H 'Content-Type: application/json' \
  -d '{"items": [{"product_id": 77, "name": "Pen", "price": 1.25, "quantity": 3}]}'
```

Expected: `200 OK` and updated cart JSON. **Replacing** `items` removes the previous items; this is not a partial item update.

**7. Remove one item (DELETE)**

```bash
curl -i -X DELETE http://localhost:8080/shopcarts/1/items/2
```

Expected: `204 No Content` with no response body. Replace `2` with an item ID currently associated with the cart (especially if you performed the PUT replacement above).

**8. Clear all items (DELETE)**

```bash
curl -i -X DELETE http://localhost:8080/shopcarts/1/items
```

Expected: `204 No Content` with no response body. The cart itself still exists.

### Error Cases and HTTP Status Codes

| Case | Expected behavior |
| --- | --- |
| Cart ID not found for read, update, or item operations | `404 Not Found` |
| Item ID not found, or item belongs to another cart, when deleting a single item | `404 Not Found` |
| `POST`/`PUT` missing `Content-Type: application/json` or using another content type | `415 Unsupported Media Type` |
| `PUT /shopcarts/{id}` receives a non-object JSON body, invalid `customer_id` type, or non-array `items` | `400 Bad Request` |
| Invalid or missing creation/item fields | Validation error; exact status/body depend on the application's error handler and database constraints |

For instance, a bad content type can be tested with:

```bash
curl -i -X POST http://localhost:8080/shopcarts \
  -H 'Content-Type: text/plain' -d 'customer_id=1001'
```

A nonexistent cart can be tested using `GET /shopcarts/999999` (assuming no cart has that ID). Some database-related failures, such as duplicate `customer_id` values, may follow database error handling rather than a dedicated API validation response; do not depend on a particular status for those cases without checking the implementation and tests.

**Not implemented in this version:** `DELETE /shopcarts/{shopcart_id}` (delete the entire cart). The routes documented above are the ones currently defined in `service/routes.py`.

## Development Commands

Inside the configured development environment:

```bash
make run     # Run the service (Honcho/Gunicorn)
make test    # Run pytest with coverage checks (fails below 95%)
make lint    # Run Flake8 and Pylint
make help    # List Makefile targets
```

`make test` invokes `pytest --pspec --cov=service --cov-fail-under=95 --disable-warnings` (with `RETRY_COUNT=1` set by the Makefile). The coverage tool measures how much of `service/` is exercised by the tests; the course target is **at least 95%**. The documented command enforces the threshold, but this README does **not** claim the tests have been run successfully on every commit. The tests live in `tests/`, including model and route tests; they are written with PyUnit-style test classes and run by pytest. `make lint` runs Flake8 and Pylint; note the current Makefile prefixes the linter commands with `-`, so its shell target may finish even when a linter reports findings. Inspect the linter output rather than relying only on the exit code.

For a Pipenv-based local environment, activate it using `pipenv shell` (if available) or run tools using `pipenv run`, for example:

```bash
pipenv run pytest
```

## Project Structure

```text
shopcarts/
├── .devcontainer/       # Container-based development configuration
├── config/              # Additional project configuration
├── service/
│   ├── __init__.py      # Flask application factory
│   ├── config.py        # Database and application settings
│   ├── models/          # Shopcart and Item models
│   ├── routes.py        # REST endpoints
│   └── common/          # Shared helpers
├── tests/               # Automated tests
├── Makefile             # Development commands
├── Pipfile              # Python dependencies
├── Procfile             # Gunicorn start command
├── wsgi.py              # WSGI entry point
└── README.md
```

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).

## Project Context

This repository is used for the NYU CSCI-GA.2820 DevOps and Agile Methodologies course.
