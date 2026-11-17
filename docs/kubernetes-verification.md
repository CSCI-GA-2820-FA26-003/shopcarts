# Local Kubernetes Deployment Verification

Verification for Issue #64.

## Environment

- Host environment was macOS with Docker Desktop.
- k3d version was v5.9.0.
- Kubernetes version was v1.35.5+k3s1.
- Cluster name was `nyu-devops`.
- Namespace was `default`.
- Application source commit was `dedfa9a`.
- Application image was `cluster-registry:5000/shopcarts:1.0`.
- Ingress URL was `http://127.0.0.1:8080`.

## Deployment commands

The following commands completed successfully from the repository root.

```bash
make cluster
make build
make push
```

Before deployment, two local Kubernetes Secrets were created.

| Secret | Key | Purpose |
| --- | --- | --- |
| postgres-credentials | password | PostgreSQL password |
| shopcarts-db-connection | DATABASE_URI | Application database connection |

Both Secrets used the same generated password. The connection targeted
the `shopcarts` database on the `postgres` service at port `5432`,
using the `postgres` user and the `postgresql+psycopg` driver.
Secret values are omitted.

```bash
make deploy
```

PostgreSQL and Shopcarts rollouts completed successfully, and the
Shopcarts Ingress was created.

## Readiness and Ingress checks

```bash
kubectl --context k3d-nyu-devops get nodes
kubectl --context k3d-nyu-devops -n default get pods
kubectl --context k3d-nyu-devops -n default get ingress
make test-ingress
```

| Check | Expected | Observed |
| --- | --- | --- |
| Server and agent nodes | Ready | Both Ready |
| PostgreSQL pod | 1/1 Running | 1/1 Running, 0 restarts |
| Shopcarts pod | 1/1 Running | 1/1 Running, 0 restarts |
| Ingress | Routes to Shopcarts | Traefik Ingress created and smoke tests passed |
| GET /health | HTTP 200 and {"status":"OK"} | Passed |
| GET /shopcarts | HTTP 200 and JSON array | Passed |

## API integration verification

All requests were sent through the Ingress URL using a Python standard
library script. The script asserted response codes and JSON values and
used the shopcart ID returned by the create request.

| Operation | Expected | Observed |
| --- | --- | --- |
| POST /shopcarts | HTTP 201, generated ID, supplied customer ID | Passed, returned ID 1 |
| GET /shopcarts/1 | HTTP 200, matching ID and original customer ID | Passed |
| PUT /shopcarts/1 | HTTP 200, matching ID and updated customer ID | Passed |
| GET /shopcarts/1 | HTTP 200, saved updated customer ID | Passed |

The original customer ID was `1114223236`.
The updated customer ID was `1614223236`.
The item list was verified as empty before and after the update.

The successful create and subsequent reads verified application access
to PostgreSQL. The final read verified that the updated value was saved.

At verification completion, test shopcart `1` remained in the local
cluster for inspection.

## Setup issues

The manually started development container provided k3d and kubectl,
but its Docker CLI was unavailable. Verification was performed from
macOS using Docker Desktop, the existing kubectl installation, and k3d
installed with `brew install k3d`.

No deployment or API verification failures were observed after setup.
