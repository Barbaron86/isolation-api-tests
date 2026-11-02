# Isolation API Tests

A educational project that demonstrates a **banking system built with a microservice architecture,**
asynchronous operation processing, and an API Gateway for external integrations.

The main goal of the project is to showcase:

- microservice-based design;
- HTTP & gRPC APIs;
- asynchronous processing with Kafka;
- clean separation of domains;
- Docker-based local infrastructure.

## Project Overview

The system simulates basic banking flows such as creating and processing financial operations.

It consists of **two core domains:**

- Gateway Service — a single entry point for external clients.
- Operations Service — asynchronous processing of banking operations.

Additional services (`users`, `cards`, `accounts`) are used as example downstream services behind the gateway.

## Architecture

### High-Level Architecture

![High-Level Architecture](./docs/architecture/core.png)

### Gateway Service

![Gateway Service](./docs/architecture/gateway.png)

### Operations Service

![Operations Service](./docs/architecture/operations.png)

## Tech Stack

- Python 3.12
- FastAPI (HTTP)
- gRPC
- Kafka
- PostgreSQL
- SQLAlchemy (async)
- Alembic
- Docker / Docker Compose

## Setup & Run

### Prerequisites

- Docker
- Docker Compose

### Build base image

```shell
docker build -t base-service .
```

### Run services

```shell
docker-compose up -d
```

## Available services

- Gateway HTTP: http://localhost:8001
- Gateway gRPC: localhost:9001
- Operations HTTP: http://localhost:8002
- Operations gRPC: localhost:9002
- Kafka UI: http://localhost:8081
- pgAdmin: http://localhost:5050

## Operations test data cleanup

Run from the repository root using the project's Python environment and a prepared
stand. The filter tests seed PostgreSQL directly. Each inserted row is registered
for deletion by primary key after that test, including setup or assertion failures:

```shell
python -m pytest tests/suites/http/test_operations.py tests/suites/grpc/test_operations.py -k filter
```

To keep a failing test's records for investigation, add:

```shell
python -m pytest tests/suites/http/test_operations.py tests/suites/grpc/test_operations.py -k filter --keep-test-data-on-failure
```

Passing and skipped tests still perform registered cleanup with this flag. When
cleanup is skipped, the registered actions and test nodeid are reported under
**Cleanup skipped**. These identifiers do not confirm that rows exist: an INSERT
may already have been rolled back. Database contents are not queried by reporting.
Use `-s` (already configured by this project) to view console logging; the Allure
attachment is available independently of console capture.
In PyCharm, put the flag in the pytest run configuration's **Additional Arguments**.
The decision uses setup/call results available when the cleanup fixture finishes;
later teardown failures cannot restore already deleted records. Retained rows
require explicit removal after investigation. Existing rows and Kafka-created
operations are outside this cleanup. A forcibly terminated process cannot guarantee
teardown execution.

The cleanup fixture delegates the retention decision to `should_keep_test_data`
and diagnostics to `report_test_data`. The whole reporting call is protected by
`try/finally`, so a reporting failure does not prevent required cleanup.
