# Project context: isolation-api-tests

Python 3.12 isolation tests for a banking microservice example, using pytest,
HTTPX, gRPC, Pydantic, PostgreSQL, Kafka and Allure. This repository contains both
the applications under test and their test framework. Reuse the existing layers;
ordinary test tasks do not include dependency, CI, database schema or application
contract changes unless the task requires them.

## Context pointers

Read only the pointers relevant to the task. Paths below are repository-relative.

| Context | Pointer and responsibility |
| --- | --- |
| Overview / environment | [README.md](README.md), [requirements.txt](requirements.txt), [docker-compose.yaml](docker-compose.yaml), [docker-compose.ci.yaml](docker-compose.ci.yaml). Applications and tests use separate Python environments and configuration. |
| Configuration | [config.py](config.py) loads application settings through `ENV_FILE`; [tests/config.py](tests/config.py) loads `tests/.env`. Inspect setting names without exposing credentials. |
| Applications / HTTP contract | [Gateway routes](services/gateway/app/api/http.py), [Operations routes](services/operations/app/api/http.py), [route prefixes](libs/routes.py), and each application's configured OpenAPI. Controllers and models explain implementation; they do not establish undocumented business requirements. |
| gRPC contract | [protos/contracts/](protos/contracts/) defines messages and RPCs; [protos/gen/](protos/gen/) contains generated code. Gateway and Operations are implemented here; Users, Accounts and Cards provide client contracts and mocks. |
| HTTP clients | [tests/clients/http/client.py](tests/clients/http/client.py) wraps HTTPX; [Gateway](tests/clients/http/gateway/client.py) and [Operations](tests/clients/http/operations/client.py) clients expose service operations. Application clients under `services/*/clients/` serve a different purpose. |
| gRPC clients | [tests/clients/grpc/client.py](tests/clients/grpc/client.py), [Gateway](tests/clients/grpc/gateway/client.py), [Operations](tests/clients/grpc/operations/client.py): channels, metadata and generated stubs. |
| Fixtures / data / schemas | [tests/conftest.py](tests/conftest.py) registers [tests/fixtures/](tests/fixtures/). [tests/schema/](tests/schema/), [tests/types/](tests/types/) and [tests/tools/fakers.py](tests/tools/fakers.py) define test data. Inspect scope, ownership and teardown before assuming isolation. |
| Assertions / examples | [tests/assertions/base.py](tests/assertions/base.py), domain helpers under [tests/assertions/](tests/assertions/), and suites under [tests/suites/](tests/suites/). Assertions compose response, aggregate and entity checks. |
| Mocks / scenarios | [tests/mock/](tests/mock/), [tests/context/base.py](tests/context/base.py), [tests/context/scenario.py](tests/context/scenario.py): JSON scenarios selected through `x-test-scenario`. [libs/context/](libs/context/) handles application-side context. |
| Kafka / PostgreSQL | [Kafka producer](tests/clients/kafka/producer.py), [operation events](tests/clients/kafka/operations/producer.py), [test repositories](tests/clients/postgres/), and [Operations infrastructure](services/operations/services/). Database initialization lives in [migrations/postgres/](migrations/postgres/); Alembic migrations in [services/operations/migrations/](services/operations/migrations/). |
| pytest / Allure / CI | [pytest.ini](pytest.ini), [tests/tools/allure.py](tests/tools/allure.py), and [isolation-tests.yml](.github/workflows/isolation-tests.yml): selection, reporting and CI commands. |

## Local conventions

- Tests live under `tests/suites/<protocol>/test_<service>.py`. Registered markers
  are `gateway`, `operations` and `regression`; reuse existing test classes,
  Allure features, stories, titles and steps.
- HTTP `*_api` methods return raw responses for status, headers and negative-case
  checks. Convenience methods validate successful responses and return test models.
  gRPC clients use generated protobuf messages; inspect their signatures rather
  than assuming HTTP response semantics.
- Keep tests focused on the scenario and operation under test. Put prerequisite
  data in fixtures/factories, transport in clients, and detailed comparisons in
  domain assertions. Do not hide the operation under test inside setup.
- When adding or changing test locals, use operation-specific names such as
  `get_operation_response`, `get_operation_response_data` and
  `get_operation_response_json` for HTTP response, parsed model and raw JSON.
  Keep existing public helper/fixture interfaces; avoid unrelated bulk renaming.
- Keep changes small and reviewable. Explain relevant data flow, library behavior
  and tradeoffs alongside the change; exhaustive walkthroughs are not a prerequisite
  for implementation.

## Test authoring and review rules

### Scenario data and expected results

- Reuse named scenarios, schema factories, generators and fixtures. Put boundary
  and invalid inputs in explicit named data or fixture variants. Random generation
  must preserve the condition the test intends to exercise.
- Derive expectations from the contract, sent inputs or independent setup state.
  A parsed response or the application's own mapper is not an independent oracle.
  Existing examples show conventions, not proof of a business rule.
- Put data-selection loops in data/fixture helpers and field/list comparisons in
  assertions. Keep the business sequence visible in the test.
- For list and filter cases, include matching and nonmatching records, including
  another card/account for the same user and another user where relevant.
- Existing Gateway mocks select responses by scenario and ignore requested IDs
  when choosing data. Such cases do not prove correct downstream ID propagation;
  add an observable request/identity check when that behavior is under test.
- Establish requirements before testing duplicate-event handling, idempotency,
  retry/DLQ policy or monetary restrictions. Supported enum values alone do not
  establish that every combination is a valid business scenario.

### Status, schema and domain assertions

- For HTTP tests, assert the expected status before parsing a successful response.
  `raise_for_status()` accepts successful status codes, not one exact expected code.
  Use raw `*_api` methods when the scenario needs protocol-level assertions.
- Pydantic validates declared types and constraints; domain assertions check
  expected identities, values, collection membership and required postconditions.
  Inspect raw JSON when exact wire types or missing/null distinctions matter.
- For negative HTTP/gRPC cases, assert the applicable status and meaningful error
  details. Reuse or extend focused domain helpers; do not parse errors as successful
  responses, or accept any exception as proof of the expected failure.
- Preserve specific business rejection reasons. Avoid brittle comparisons of
  framework/parser wording unless that wording is an explicit contract.
- Extend `tests/assertions/base.py` and the relevant protocol/domain module.
  Keep expected object construction and detailed comparisons out of test bodies;
  do not introduce a generic assertion framework or flag-heavy helpers.
- Compare unordered collections by stable identity when the contract does not
  guarantee order. A fixed mock order does not establish a general ordering rule.

### Resource ownership and asynchronous processing

- Inspect fixture scope and teardown explicitly. Current Operations fixtures commit
  prepared rows; they do not automatically delete them after a test. Unique IDs
  separate data but do not provide cleanup or transaction rollback for the test.
- When changing resource lifecycle, close clients/channels and clean only entities
  owned by the current test/run, including partial setup and failure paths.
  Preserve the original failure and useful diagnostics.
- Separate Kafka delivery confirmation from completion of application processing.
  Check delivery/flush outcomes and wait for a specific observable result with a
  bounded deadline; a fixed sleep is not evidence of completed processing.
- Do not republish an event while polling for its result. Avoid unrestricted
  retries that hide a delivery failure or service defect.
- Introduce locking or parallel execution only after identifying shared state and
  reproducing the relevant race. A thread lock does not isolate pytest processes,
  shared database records or messages in a Kafka topic.

### Review expectations

Review changed tests for defect-detection strength and these repository conventions.
Report concrete findings with file/line and distinguish functional defects from
structure/readability issues. A passing run does not establish that assertions
would detect the intended defect.

## Verification and side effects

Use the selected Python 3.12 virtual environment with dependencies from
`requirements.txt`. Run commands from the repository root.

```shell
# Validate Compose without starting services.
docker compose -f docker-compose.yaml config --quiet
docker compose -f docker-compose.ci.yaml config --quiet

# Focused and regression execution against a prepared test stand.
python -m pytest tests/suites/http/test_gateway.py -m gateway
python -m pytest -m regression --alluredir=./allure-results
```

- pytest does not start the stand. Check readiness of required APIs/mocks, Kafka,
  PostgreSQL and successful initialization/migrations before integration tests.
  Follow README for image building and stand startup within task authorization.
- Choose checks appropriate to the change. Documentation needs link/content/diff
  checks; Compose changes need configuration validation; behavioral changes need
  focused execution and the relevant regression scope. Do not run application tests
  solely for a documentation change.
- Report the actual commands, failures, skips and unverified behavior. Some
  Operations filter tests are skipped on Windows; do not count them as executed
  or remove the skip without investigating its cause.
- Test imports, collection and execution can create clients, logs and Allure output.
  Do not clear reports, install packages, migrate data or provision services during
  a read-only task.
- Preserve other Docker projects and persistent data. Stands using the same host
  ports run separately. Do not resolve conflicts by stopping, renaming or deleting
  another project's containers, or deleting shared volumes.
- Treat environment values, request/response logs and report attachments as
  potentially sensitive. Do not print whole env files or publish credentials.
- Edit protobuf sources and regenerate through `scripts/protos.sh` when required;
  inspect the script first. Do not hand-edit `protos/gen/`.

## Delivery and local guidance

- The current agreed delivery mode is direct work on `main`, without feature
  branches or PRs, unless the user changes it. Respect branch protections.
  Publish only completed changes covered by the task's authorization.
- Before Git mutations, inspect branch, index and working-tree state. Stage only
  task-owned paths/hunks, preserve unrelated changes, and use Conventional Commits.
  Write commit summaries and bodies in Russian; keep the type and optional scope
  in English. Keep this instruction file in English.
  After push, verify the published SHA on the intended remote branch.
- Discussion, explanation and preparation-only requests do not authorize publishing
  code. Follow narrower task instructions when present.
- Personal Markdown/Mermaid learning notes under `docs/learning/` remain local and
  Git-excluded; verify the exclusion before writing them. Missing private notes
  must not block work. Do not add them to commits or public artifacts.
- Local AQA context is a separate task; do not bootstrap it automatically.

Keep reusable AQA procedures in available Skills and personal rules in global
instructions. This file supplies repository context and conventions, not a separate
planning, debugging or review workflow.
