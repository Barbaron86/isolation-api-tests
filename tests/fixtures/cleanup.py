"""Политика очистки тестовых ресурсов и сохранения данных для расследования."""

from collections.abc import Generator

import allure
import pytest

from tests.tools.cleanup import CleanupManager
from tests.tools.logger import get_test_logger

TEST_REPORTS = pytest.StashKey[dict[str, pytest.TestReport]]()
logger = get_test_logger("TEST_DATA_CLEANUP")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Регистрирует режим сохранения данных при ошибке setup или call.

    Args:
        parser: Парсер параметров, предоставленный pytest.
    """
    parser.getgroup("test data").addoption(
        "--keep-test-data-on-failure",
        action="store_true",
        default=False,
        help="Keep registered test data when setup or test execution fails.",
    )


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Сохраняет отчёт этапа на item до принятия решения об очистке.

    Args:
        item: Выполняемый тест, хранящий отчёты в типизированном stash.
        call: Информация об этапе setup, call или teardown.

    Returns:
        Отчёт, созданный pytest и остальными реализациями хука.
    """
    report = yield
    reports = item.stash.setdefault(TEST_REPORTS, {})
    reports[report.when] = report
    return report


def should_keep_test_data(request: pytest.FixtureRequest) -> bool:
    """Определяет, нужно ли пропустить очистку для расследования ошибки.

    Учитывает только setup/call: отчёт teardown ещё не сформирован, пока
    выполняются финализаторы текущего теста.

    Args:
        request: Контекст текущего теста с параметрами и отчётами pytest.

    Returns:
        True, если передан флаг сохранения и setup или call завершился ошибкой.
        Для успеха, skip и отсутствующих отчётов возвращает False.
    """
    if not request.config.getoption("--keep-test-data-on-failure"):
        return False
    reports = request.node.stash.get(TEST_REPORTS, {})
    return any(reports[phase].failed for phase in ("setup", "call") if phase in reports)


def report_test_data(
    request: pytest.FixtureRequest,
    descriptions: tuple[str, ...],
    *,
    keep_data: bool,
) -> None:
    """Сообщает решение и зарегистрированные действия без обращения к БД.

    Регистрация удаления не подтверждает существование строки: INSERT мог
    быть отменён после flush. Отчёт также не подтверждает успешное удаление;
    результаты выполнения доступны в шагах удаления и ошибках teardown.

    Args:
        request: Контекст теста для привязки диагностики к nodeid и teardown.
        descriptions: Зарегистрированные действия и известные безопасные ID;
            до Kafka discovery вместо ID строк известна тройка владельца.
        keep_data: Пропущена ли очистка по выбранной политике.

    Raises:
        Exception: Если секция pytest, вложение Allure или логирование
            завершились ошибкой. Вызывающая фикстура обеспечивает очистку
            через finally независимо от результата диагностики.
    """
    decision = "Cleanup skipped" if keep_data else "Registered cleanup actions"
    actions = "\n".join(f"- {description}" for description in descriptions)
    details = (
        f"Test: {request.node.nodeid}\n\n"
        f"Registered cleanup actions:\n{actions}\n\n"
        "Row existence is not verified."
    )
    request.node.add_report_section("teardown", decision, details)
    allure.attach(details, name=decision, attachment_type=allure.attachment_type.TEXT)
    if keep_data:
        logger.info(f"🧹 [CLEANUP] {decision}\n{details}")


@pytest.fixture
def cleanup_manager(request: pytest.FixtureRequest) -> Generator[CleanupManager, None, None]:
    """Предоставляет отдельный реестр и завершает его после одного теста.

    С флагом сохранения пропускает удаления при ошибке setup/call. Последующие
    ошибки других teardown ещё неизвестны и не меняют принятое решение.
    Диагностика сообщает действия и известные идентификаторы без проверки строк.
    Ошибка формирования диагностики не препятствует обязательной очистке.

    Args:
        request: Контекст теста с параметрами запуска и отчётами этапов.

    Yields:
        Реестр действий для ресурсов, созданных текущим тестом.

    Raises:
        ExceptionGroup: Если очистка хотя бы одного ресурса не удалась.
            Pytest сообщает её как teardown error отдельно от ошибки теста.
        Exception: Если формирование диагностики завершилось ошибкой.
    """
    manager = CleanupManager()
    yield manager

    descriptions = manager.pending_descriptions
    if not descriptions:
        return
    keep_data = should_keep_test_data(request)
    try:
        report_test_data(request, descriptions, keep_data=keep_data)
    finally:
        if not keep_data:
            manager.cleanup()
