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

### Example Requests

**Create an empty cart**

```bash
curl -i -X POST http://localhost:8080/shopcarts \
  -H 'Content-Type: application/json' \
  -d '{"customer_id": 1001}'
```

**Add an item to cart 1** (replace `1` with the ID returned by the create request):

```bash
curl -i -X POST http://localhost:8080/shopcarts/1/items \
  -H 'Content-Type: application/json' \
  -d '{"product_id": 42, "name": "Notebook", "description": "A5 notebook", "price": 7.50, "quantity": 2}'
```

**Read the cart and its items**

```bash
curl -i http://localhost:8080/shopcarts/1
curl -i http://localhost:8080/shopcarts/1/items
```

**Update customer ID of cart 1**

```bash
curl -i -X PUT http://localhost:8080/shopcarts/1 \
  -H 'Content-Type: application/json' \
  -d '{"customer_id": 1002}'
```

**Remove an item** (replace `2` with an actual item ID):

```bash
curl -i -X DELETE http://localhost:8080/shopcarts/1/items/2
```

**Clear all items from a cart**

```bash
curl -i -X DELETE http://localhost:8080/shopcarts/1/items
```

JSON-writing endpoints expect the `Content-Type: application/json` header. Requests for carts or items that do not exist return `404 Not Found`.

## Development Commands

Inside the configured development environment:

```bash
make run     # Run the service (Honcho/Gunicorn)
make test    # Run pytest with coverage checks (95% threshold)
make lint    # Run Flake8 and Pylint
make help    # List Makefile targets
```

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
