"""Юнит-тесты политики сохранения ресурсов и отчёта об очистке."""

from unittest.mock import Mock

import pytest

from tests.fixtures import cleanup


TEST_NODE_ID = "tests/suites/test_example.py::test_example"
OWNED_RECORD_DESCRIPTION = "Operations row id=operation-42"


def make_request(*, keep_on_failure: bool, outcomes: dict[str, str]) -> Mock:
    """Подготавливает запрос pytest с заданным флагом и отчётами этапов.

    Args:
        keep_on_failure: Значение флага сохранения ресурсов.
        outcomes: Исходы известных этапов pytest.

    Returns:
        Запрос с настоящим pytest stash и тестовыми отчётами.
    """
    request = Mock()
    request.config.getoption.return_value = keep_on_failure
    request.node.nodeid = TEST_NODE_ID
    request.node.stash = pytest.Stash()
    if outcomes:
        request.node.stash[cleanup.TEST_REPORTS] = {
            phase: pytest.TestReport(
                nodeid=TEST_NODE_ID,
                location=("test_example.py", 0, "test_example"),
                keywords={},
                outcome=outcome,
                longrepr=None,
                when=phase,
            )
            for phase, outcome in outcomes.items()
        }
    return request


@pytest.mark.parametrize(
    "keep_on_failure, outcomes, expected",
    [
        pytest.param(False, {"call": "failed"}, False, id="flag-off"),
        pytest.param(True, {"setup": "failed"}, True, id="setup-failed"),
        pytest.param(True, {"setup": "passed", "call": "failed"}, True, id="call-failed"),
        pytest.param(True, {"setup": "passed", "call": "passed"}, False, id="passed"),
        pytest.param(True, {"call": "skipped"}, False, id="skipped"),
        pytest.param(True, {"call": "passed", "teardown": "failed"}, False, id="teardown-failed"),
        pytest.param(True, {}, False, id="no-reports"),
    ],
)
def test_retention_requires_flag_and_a_setup_or_call_failure(
    keep_on_failure: bool, outcomes: dict[str, str], expected: bool,
) -> None:
    """Сохраняет ресурсы при ошибке подготовки или теста с включённым флагом.

    Args:
        keep_on_failure: Значение флага сохранения.
        outcomes: Исходы этапов теста.
        expected: Решение сохранить зарегистрированные ресурсы.
    """
    request = make_request(keep_on_failure=keep_on_failure, outcomes=outcomes)

    assert cleanup.should_keep_test_data(request) is expected
    request.config.getoption.assert_called_once_with("--keep-test-data-on-failure")


@pytest.mark.parametrize(
    "keep_data, expected_title",
    [
        pytest.param(False, "Registered cleanup actions", id="cleanup"),
        pytest.param(True, "Cleanup skipped", id="retention"),
    ],
)
def test_report_describes_registered_resources_and_the_cleanup_decision(
    monkeypatch: pytest.MonkeyPatch, keep_data: bool, expected_title: str,
) -> None:
    """Включает идентификаторы и пределы проверки в pytest и Allure.

    Args:
        monkeypatch: Фикстура для перехвата вложения Allure.
        keep_data: Решение сохранить зарегистрированные ресурсы.
        expected_title: Название секции отчёта и вложения.
    """
    request = make_request(keep_on_failure=keep_data, outcomes={})
    attach = Mock()
    monkeypatch.setattr(cleanup.allure, "attach", attach)

    cleanup.report_test_data(request, (OWNED_RECORD_DESCRIPTION,), keep_data=keep_data)

    request.node.add_report_section.assert_called_once()
    phase, title, report = request.node.add_report_section.call_args.args
    assert phase == "teardown"
    assert title == expected_title
    assert f"Test: {TEST_NODE_ID}" in report
    assert f"- {OWNED_RECORD_DESCRIPTION}" in report
    assert "Row existence is not verified." in report
    attach.assert_called_once_with(report, name=expected_title, attachment_type=cleanup.allure.attachment_type.TEXT)


@pytest.mark.parametrize(
    "keep_data, expected_delete_count, expected_pending",
    [
        pytest.param(False, 1, (), id="cleanup-required"),
        pytest.param(True, 0, (OWNED_RECORD_DESCRIPTION,), id="retention-enabled"),
    ],
)
def test_diagnostic_failure_preserves_the_cleanup_decision(
    monkeypatch: pytest.MonkeyPatch,
    keep_data: bool,
    expected_delete_count: int,
    expected_pending: tuple[str, ...],
) -> None:
    """Применяет решение об очистке, даже если сформировать отчёт не удалось.

    Args:
        monkeypatch: Фикстура для имитации отказа диагностики.
        keep_data: Решение, заданное флагом при упавшем тесте.
        expected_delete_count: Число вызовов удаления.
        expected_pending: Ресурсы, оставшиеся в реестре после teardown.
    """
    request = make_request(keep_on_failure=keep_data, outcomes={"call": "failed"})
    report_error = RuntimeError("diagnostics failed")
    report_test_data = Mock(side_effect=report_error)
    monkeypatch.setattr(cleanup, "report_test_data", report_test_data)
    lifecycle = cleanup.cleanup_manager.__wrapped__(request)
    manager = next(lifecycle)
    delete_record = Mock()
    manager.add(delete_record, description=OWNED_RECORD_DESCRIPTION)

    with pytest.raises(RuntimeError) as failure:
        next(lifecycle)

    assert failure.value is report_error
    report_test_data.assert_called_once_with(request, (OWNED_RECORD_DESCRIPTION,), keep_data=keep_data)
    assert delete_record.call_count == expected_delete_count
    assert manager.pending_descriptions == expected_pending
