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
docker compose -f docker-compose.yaml up -d
python scripts/wait_for_stand.py --compose-file docker-compose.yaml --timeout 180
```

Run the readiness command from the repository root using the project's Python
environment with the existing requirements installed. It checks successful
initialization/migrations, broker and consumer health, and HTTP/gRPC connectivity.
The consumer becomes healthy after partition assignment and initial positions are
known. Initialization normalizes CRLF while reading the script and requires no
package download or modification of the mounted source.

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
for deletion by primary key after that test, including setup or assertion failures.
Kafka fixtures also register cleanup before publishing. They snapshot existing
IDs for the test-owned user/card/account combination, discover new IDs after
processing, and delete only those exact keys:

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
require explicit removal after investigation. Existing rows are preserved.
Kafka tests must own their user/card/account combination exclusively; concurrent
publication with the same identifiers is unsupported. Discovery has a limited
waiting period. If processing or delivery completes later, an **Unresolved Kafka
Operations cleanup** attachment reports identifiers for investigation; complete
removal of late writes cannot be guaranteed. A forcibly terminated process cannot
guarantee teardown execution.

The cleanup fixture delegates the retention decision to `should_keep_test_data`
and diagnostics to `report_test_data`. The whole reporting call is protected by
`try/finally`, so a reporting failure does not prevent required cleanup.

## API response checks

The HTTP test clients' convenience methods check the exact status with
`assert_status_code` and `HTTPStatus.OK`, then parse the response with Pydantic.
Successful tests prepare data, call a convenience method and run domain assertions.
Raw `*_api` methods return the response for negative cases, such as an expected 404,
or explicit status/header checks.

Operations filter cases cover card/account filters, user-only selection, multiple
matching operations and an empty result while another user's operation exists.
ORM-backed HTTP/gRPC assertions compare the complete collection by operation ID,
including count, duplicate IDs and entity fields, without depending on result order.

## Kafka scenarios

```shell
python -m pytest tests/suites/http/test_operations.py tests/suites/grpc/test_operations.py -k operation_events
python -m pytest -m regression --alluredir=./allure-results
```

The producer's raw `produce` enqueues a message. `produce_and_wait` checks that
message's delivery callback and the remaining flush queue. Operations helpers
return the original event after confirmed delivery; they do not wait for a
database commit or publish the event again while waiting.

`wait_for_operations` explicitly waits for a result through HTTP or gRPC.
Both clients delegate the count/deadline loop to
[operations_waiter.py](tests/tools/operations_waiter.py), reading through their
existing `get_operations` facade. `get_operations` remains a single request and
accepts an optional timeout override. Only an incomplete operation count is
retried; extra rows and HTTP/schema/RPC errors fail immediately. Domain assertions
then compare all event fields, complete membership and unique operation IDs,
independently of response order. Controlled event pairs use `(user_id, card_id)`
for matching; this is test preparation, not a new operation identifier.

The twelve Kafka scenarios cover both purchase statuses, multiple events, user
isolation, and card/account filtering through HTTP and gRPC. Filter scenarios
confirm processing of all competing events before checking the final selection.

The following test settings can be overridden through the environment or `tests/.env`:

| Setting | Default | Responsibility |
| --- | --- | --- |
| `KAFKA_DELIVERY_TIMEOUT` | 10 seconds | Confirming broker delivery |
| `OPERATIONS_PROCESSING_TIMEOUT` | 10 seconds | Observing API results and reconciling one cleanup owner |
| `OPERATIONS_POLL_INTERVAL` | 0.25 seconds | Interval between incomplete reads |

Each RPC receives the remaining deadline. HTTPX limits individual network phases;
a late HTTP response is rejected, but a continuously arriving body can exceed
the observation deadline. PostgreSQL test connections additionally limit pool
checkout, connection setup and server statements to 5 seconds per phase by
default. Cleanup discovery sets a transaction-local statement timeout using its
remaining budget. These are phase limits, not a hard wall-clock guarantee for an
arbitrary network stall.

## Optional parallel execution

The default local and CI runs remain sequential. A prepared stand also supports
an explicit two-worker run using the pinned `pytest-xdist` dependency:

```shell
python -m pytest -m regression -n 2 -o addopts= -q --alluredir=./allure-results-parallel
```

The override replaces the default `-s -v` with captured, concise output for this
run. Prepare the stand once before starting workers. Each independent Operations
test owns its user ID, cleanup manager and lifecycle-bound clients. Sharing a
user across tests is unsafe even with different cards because user-only reads
can observe both tests' operations.

`Fake.uuid()` uses standard-library UUID4 independently of Faker's seed; other
generated values still use Faker. Fixed IDs can be passed explicitly in scenario
data. Keep producer/repository wrappers function-scoped while they refer to a
test's cleanup registry. More workers increase the stand's load; they do not
increase a single Kafka partition's processing capacity. Benchmark before
increasing the worker count.

## CI report environment

[write_allure_environment.py](scripts/write_allure_environment.py) creates
`allure-results/environment.properties` in the test runner environment.
The workflow runs it after dependency installation and before pytest.
`TEST_MARKER` and `TEST_COMPOSE_FILE` are defined once in the test job and shared
by the execution commands and report metadata. The existing results artifact
passes this file to the Allure report generator.

Before stopping the stand, CI runs `scripts/collect_stand_diagnostics.py`.
The separate `stand-diagnostics` artifact is retained for 3 days and contains
only `state.json` (service, process state, exit code and health) and
`collection.txt` (collection outcome, error type and any command exit code or
timeout). Container logs, environment variables and event payloads are not
collected. The snapshot can identify a stopped or unhealthy container; it does
not explain failures inside the application.

The previous `state.json` is removed before collection. Other files in a reused
output directory are preserved; CI uploads only the two named files.
Collection/upload failures do not prevent teardown or replace the test failure.

The two stand commands parse CLI arguments and delegate to [scripts/stand](scripts/stand/):
[compose.py](scripts/stand/compose.py) runs bounded Docker commands,
[readiness.py](scripts/stand/readiness.py) checks infrastructure and host-side APIs,
and [diagnostics.py](scripts/stand/diagnostics.py) writes the state snapshot and
collection result.
Readiness failures report the blocking service or API endpoint.
