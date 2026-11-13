# Isolation API Tests

**English** · [Русский](README.ru.md)

[![CI](https://github.com/Barbaron86/isolation-api-tests/actions/workflows/isolation-tests.yml/badge.svg?branch=main)](https://github.com/Barbaron86/isolation-api-tests/actions/workflows/isolation-tests.yml)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB)
![pytest](https://img.shields.io/badge/pytest-test%20runner-0A9EDC)
![HTTP and gRPC](https://img.shields.io/badge/API-HTTP%20%2B%20gRPC-226B65)
![Allure](https://img.shields.io/badge/Allure-reporting-orange)

API test automation for a sample banking system. The suites exercise **Gateway**
with controlled Users, Accounts and Cards dependencies, and **Operations** with
real PostgreSQL and Kafka. Both services run locally in Docker Compose. pytest
runs on the host and records test steps, assertions and logs in Allure.

[Allure Report](https://barbaron86.github.io/isolation-api-tests/) ·
[GitHub Actions](https://github.com/Barbaron86/isolation-api-tests/actions/workflows/isolation-tests.yml)

## 📑 Contents

[Quick Start](#-quick-start) · [Tech Stack](#-tech-stack) ·
[Test Scenarios](#-test-scenarios) · [Architecture](#-architecture) ·
[Project Structure](#-project-structure) · [Running Tests](#-running-tests) ·
[Reports](#-reports) · [CI/CD](#-cicd)

## 🚀 Quick Start

Install **Python 3.12** and start **Docker with Compose v2** in Linux container
mode. Clone the repository and run the commands from its root.

```shell
git clone https://github.com/Barbaron86/isolation-api-tests.git
cd isolation-api-tests
```

<details>
<summary>Create a Python 3.12 virtual environment</summary>

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux or macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

</details>

```shell
python -m pip install -r requirements.txt
docker build -t base-service .
docker compose -f docker-compose.yaml up -d
python scripts/wait_for_stand.py --compose-file docker-compose.yaml --timeout 180
python -m pytest -m regression
```

The repository includes local stand settings in `.env` and test client settings
in `tests/.env`. The readiness script checks PostgreSQL initialization and
migrations, Redis, the Kafka broker and consumer, and HTTP/gRPC connectivity.
Stop the local stand with `docker compose -f docker-compose.yaml down`.

| Component | Local address |
| --- | --- |
| Gateway | HTTP `localhost:8001` · gRPC `localhost:9001` |
| Operations | HTTP `localhost:8002` · gRPC `localhost:9002` |
| Mock Service | [HTTP Swagger UI](http://127.0.0.1:8003/docs) · gRPC `localhost:9003` |
| Stand tools | [Kafka UI](http://localhost:8081) · [pgAdmin](http://localhost:5050) |

## 🧰 Tech Stack

| Tool | Role in the project |
| --- | --- |
| **Python 3.12** | Language for the services, mocks and test framework. |
| **pytest / pytest-xdist** | Fixtures, parametrization, test selection by markers and optional parallel execution. |
| **HTTPX** | HTTP clients for tests and downstream service calls. |
| **gRPC / Protocol Buffers** | Typed RPC contracts, generated stubs and request metadata. |
| **Pydantic / Pydantic Settings** | Typed request and response models, API field aliases and settings from environment variables. |
| **Faker / UUID4** | Synthetic test data and identifiers for independent test resources. |
| **FastAPI / Uvicorn** | HTTP APIs for the applications and mock service. |
| **PostgreSQL / SQLAlchemy / Alembic** | Operations persistence, test data setup and cleanup, and database migrations. |
| **Kafka / confluent-kafka / aiokafka** | Event broker, test producer and Operations consumer. |
| **Redis / redis-py** | Shared, TTL-backed scenario storage for HTTP and gRPC mocks. |
| **Python logging** | HTTP/gRPC calls, assertions and cleanup diagnostics. |
| **Allure / allure-pytest** | Test steps, logs, environment metadata and report history. |
| **Docker Compose** | Local and CI test stands with readiness checks. |
| **GitHub Actions / GitHub Pages** | Separate unit and API jobs and publication of the Allure report. |

Python dependencies are pinned in [requirements.txt](requirements.txt). Container
images and service settings are declared in the [local Compose file](docker-compose.yaml)
and the [CI Compose file](docker-compose.ci.yaml).

## 🧪 Test Scenarios

| Suite | Data setup | What the tests verify |
| --- | --- | --- |
| Gateway HTTP and gRPC | Built-in mock scenarios | User/account aggregates, exact accounts and cards, empty collections, missing entities, and propagation of dependency errors. |
| Dynamic Gateway HTTP | Test-owned records registered through the Mock Admin API | User and account aggregates, accounts and cards for the requested entity, and a missing account with prepared cards. |
| Dynamic Gateway gRPC | The same Admin API and Redis store | User and account aggregates, accounts and cards for the requested entity, and `NOT_FOUND` from Accounts when the account is absent. |
| Operations HTTP and gRPC | Rows inserted through the test repository | Lookup by ID, missing operations, user/card/account filters, combined card and account filters, and exact result membership. |
| Operations through Kafka | Test events published to the Operations topic | Processing of `IN_PROGRESS` and `COMPLETED` purchases, several events for one user, and filtering after all competing events have been processed. |
| Unit tests | Controlled dependencies in the pytest process | Cleanup ordering and failure handling, repository timeout budgets, scenario resolution and storage, and Redis serialization, TTL configuration and error handling. |
| Mock integration | Isolated mock with in-memory scenario storage | Admin lifecycle, scenario isolation and responses from the mock's own HTTP and gRPC endpoints. |

## 🏗 Architecture

The application diagrams show the service boundaries. On the test stand,
Gateway's downstream clients connect directly to the matching HTTP or gRPC mock
routes. Both Operations suites cover direct PostgreSQL setup and Kafka-driven
processing.

![High-level banking service architecture](docs/architecture/core.png)

<details>
<summary>Gateway service architecture</summary>

![Gateway service architecture](docs/architecture/gateway.png)

</details>

<details>
<summary>Operations service architecture</summary>

![Operations service architecture](docs/architecture/operations.png)

</details>

### Test Execution Flow

pytest fixtures prepare test data and provide typed clients. Successful HTTP
calls check the expected status before parsing the response with Pydantic. Negative
cases use raw responses to check the status and error details. gRPC calls use
generated protobuf stubs. Domain assertions compare responses with expectations
built from the prepared data.

#### Gateway and its dependencies

Built-in scenarios are selected through `X-Test-Scenario` in HTTP or
`x-test-scenario` metadata in gRPC. For dynamic HTTP tests, the same header carries
the ID returned by the Admin API. Each dependency route selects the scenario
and uses the requested entity ID to find or filter the data.

**Static `GetAccountDetails`**

```mermaid
sequenceDiagram
    participant T as pytest
    participant G as HTTP Gateway
    participant M as HTTP mock

    T->>G: Request account details with the built-in scenario name
    G->>M: Request cards by accountId with the same scenario header
    M->>M: Read the cards JSON and filter by accountId
    M-->>G: Return cards for this account
    G->>M: Request the account by ID with the same scenario header
    M->>M: Read the account JSON and check its ID
    M-->>G: Return the account
    G-->>T: Return the account and its cards
    T->>T: Check the account fields and cards
```

The test passes `USER_WITH_ACTIVE_DEBIT_CARD_ACCOUNT` as the scenario and gets
the requested account ID from a fixture. The mock selects a JSON file for each
operation. [Static Gateway test](tests/suites/http/test_gateway.py#L143)

**Dynamic `GetAccountDetails`**

```mermaid
sequenceDiagram
    participant T as Test and fixture
    participant G as HTTP Gateway
    participant M as HTTP mock
    participant R as Redis

    T->>M: POST /__admin/scenarios with accounts and cards
    M->>R: Save the scenario
    M-->>T: Return the scenario ID

    T->>G: Request account details with X-Test-Scenario
    G->>M: Request cards by accountId with the same header
    M->>R: Load the scenario by ID
    M-->>G: Return cards for this account
    G->>M: Request the account by ID with the same header
    M->>R: Load the same scenario
    M-->>G: Return the account
    G-->>T: Return the account and its cards

    T->>T: Check account fields and exact card membership
    T->>M: Fixture deletes the scenario through Admin API
    M->>R: Delete the scenario key
```

The account-details test registers cards for two accounts, then calls Gateway
and checks the requested account and its exact set of cards.
[Gateway test](tests/suites/http/test_gateway.py#L367)

`X-Test-Scenario` selects the dataset. The account ID selects the account and
its cards within that dataset.

The gRPC variant registers data through the same HTTP Admin API and sends the
returned ID as `x-test-scenario` metadata. The gRPC mock reads the same Redis
key for `GetUser`, `GetAccounts`, `GetCards` and `GetAccount` and returns
protobuf messages. `GetCard` uses built-in scenarios. A deleted or expired ID
returns `NOT_FOUND` for the dynamic RPCs. A Redis connection error or timeout
returns `UNAVAILABLE`.

#### Operations with PostgreSQL or Kafka

```mermaid
sequenceDiagram
    participant T as Test
    participant K as Kafka
    participant C as Operations consumer
    participant DB as PostgreSQL
    participant API as Operations API

    T->>K: Publish a purchase event
    par Consumer processes the event
        K-->>C: Deliver the event
        C->>DB: Insert the operation and commit
    and Test waits for the result
        K-->>T: Confirm broker delivery
        loop Until the expected count is visible or the deadline expires
            T->>API: Request the user's operations
            API->>DB: Read committed operations
            DB-->>API: Return matching rows
            API-->>T: Return the operations list
        end
    end

    T->>T: Check the exact set and fields of the operations
```

The test starts reading the HTTP or gRPC API after Kafka confirms delivery.
The consumer commits independently. Only a successful response with too few
operations is retried. Extra operations fail the check immediately. If the
expected count is still missing at the deadline, the test raises `TimeoutError`.

**Direct database setup** · The test repository inserts rows into PostgreSQL.
The test then calls the Operations API once and checks the response.

The card-filter test publishes two events for the same user, waits until both
operations are visible, then filters by card and checks that only the matching
operation is returned. [Operations test](tests/suites/http/test_operations.py#L288)

Cleanup removes test-owned rows by primary key. For Kafka events, it records
existing IDs before publication and finds new IDs for the test's
`(user_id, card_id, account_id)` combination. Late writes outside the cleanup
deadline may require manual investigation.

## 📁 Project Structure

```text
services/           Gateway and Operations, plus downstream client contracts
libs/               Shared application clients, context and configuration
protos/             Protobuf contracts and generated gRPC code
tests/
  suites/           HTTP and gRPC API suites
  unit/             Cleanup, mock scenario and Redis unit tests
  integration/mock/ Direct HTTP and gRPC mock integration tests
  clients/          HTTP, gRPC, Kafka and PostgreSQL test access
  fixtures/         Test setup and resource cleanup
  schema/           Pydantic test models
  assertions/       Protocol and domain assertions
  mock/             HTTP and gRPC mocks and scenario data
scripts/            Stand readiness, diagnostics and Allure metadata
```

## ▶️ Running Tests

Run Gateway and Operations API commands against a ready stand. The unit suite
and mock integration suite run without Docker or a running stand.

| Scope | Command |
| --- | --- |
| Unit tests | `python -m pytest tests/unit --noconftest -o addopts= -q` |
| Mock integration | `python -m pytest tests/integration/mock -o addopts= -q` |
| Full API regression | `python -m pytest -m regression` |
| Gateway over HTTP and gRPC | `python -m pytest -m gateway` |
| Dynamic HTTP Gateway | `python -m pytest tests/suites/http/test_gateway.py::TestDynamicGatewayHTTP` |
| Dynamic gRPC Gateway | `python -m pytest tests/suites/grpc/test_gateway.py::TestDynamicGatewayGRPC` |
| Operations over HTTP and gRPC | `python -m pytest -m operations` |
| Kafka-backed Operations | `python -m pytest -m operations -k operation_events` |

<details>
<summary>Parallel execution, debugging and timeout settings</summary>

The default run is sequential. To run the API regression with two pytest workers,
prepare the stand once and run:

```shell
python -m pytest -m regression -n 2 -o addopts= -q --alluredir=./allure-results-parallel
```

Use separate user IDs across independent Operations tests because user-only reads
can see every operation for that user.

To inspect Operations data after a setup or test failure, add
`--keep-test-data-on-failure`. The **Cleanup skipped** attachment lists the
registered actions and test ID. Use PostgreSQL to confirm which rows exist
and remove retained rows after debugging. Dynamic Gateway scenarios have their
own teardown.

| Setting | Default | Purpose |
| --- | --- | --- |
| `KAFKA_DELIVERY_TIMEOUT` | `10s` | Confirm delivery to the broker. |
| `OPERATIONS_PROCESSING_TIMEOUT` | `10s` | Wait for the API result and bound cleanup discovery for one owner. |
| `OPERATIONS_POLL_INTERVAL` | `0.25s` | Interval between incomplete reads. |

Override these through the environment or `tests/.env`. Network phases have
their own transport limits. The polling deadline bounds accepted results and
retry scheduling.

</details>

## 📊 Reports

### Allure

The [published report](https://barbaron86.github.io/isolation-api-tests/) contains
API test results, individual steps, logs, environment metadata and run history.

To generate and open a local report, use [Allure Commandline](https://allurereport.org/docs/v2/install/).

```
python -m pytest -m regression --alluredir=./allure-results
allure serve ./allure-results
```

## 🔄 CI/CD

The [Isolation Tests workflow](.github/workflows/isolation-tests.yml) runs on
pull requests to `main` and pushes to `main`.

| Job | What it does |
| --- | --- |
| `unit-tests` | Installs dependencies and runs the unit suite separately. |
| `run-tests` | Builds the image, starts the Compose stand, waits for readiness and runs the API regression with Allure results. |
| `publish-report` | Generates the API report with history and publishes it to [GitHub Pages](https://barbaron86.github.io/isolation-api-tests/). |

The API job also uploads a separate `stand-diagnostics` artifact with Compose
state and the collection outcome for failed-stand investigation.
