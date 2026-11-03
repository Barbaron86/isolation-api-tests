import uuid
from datetime import datetime

from faker import Faker
from faker.providers.python import TEnum


class Fake:
    """
    Централизованный генератор тестовых данных.

    Этот класс используется как единая точка генерации
    случайных доменных значений для автотестов:
    идентификаторов, enum'ов, сумм, дат и категорий.

    Тесты не работают напрямую с библиотекой генерации,
    а используют этот фасад.
    """

    def __init__(self, faker: Faker):
        """Принимает генератор доменных значений, кроме идентификаторов.

        Args:
            faker: Генератор сумм, категорий, enum и дат тестовых данных.
        """
        self.faker = faker

    def uuid(self) -> uuid.UUID:
        """Создаёт UUID4 независимо от seed и состояния Faker.

        Одинаковый Faker seed в разных workers не должен повторять ID владельцев
        тестовых записей. Для сценария с фиксированным ID его передают явно при
        подготовке данных; seed управляет остальными значениями генератора.

        Returns:
            UUID версии 4 из стандартной библиотеки, а не строка.
        """
        return uuid.uuid4()

    def enum(self, value: type[TEnum]) -> TEnum:
        """
        Возвращает случайное значение из переданного enum'а.

        Используется вместе с тестовыми доменными enum'ами
        (OperationTestType, CardTestStatus и т.д.),
        чтобы генерировать валидные доменные значения.
        """
        return self.faker.enum(value)

    def category(self) -> str:
        """
        Генерирует категорию операции или платежа.

        Категории заданы явно, чтобы:
        - контролировать доменное пространство значений
        - не зависеть от случайных строк
        - использовать реалистичные бизнес-категории
        """
        return self.faker.random_element([
            "gas",
            "taxi",
            "tolls",
            "water",
            "beauty",
            "mobile",
            "travel",
            "parking",
            "catalog",
            "internet",
            "satellite",
            "education",
            "government",
            "healthcare",
            "restaurants",
            "electricity",
            "supermarkets",
        ])

    def float(self, start: int = 1, end: int = 100) -> float:
        """
        Генерирует числовое значение с плавающей точкой
        в заданном диапазоне.

        Используется как базовый метод для генерации
        числовых доменных значений.
        """
        return self.faker.pyfloat(min_value=start, max_value=end, right_digits=2)

    def amount(self) -> float:
        """
        Генерирует денежную сумму операции.

        Это семантическая обертка над float(),
        чтобы в тестах было явно видно,
        что речь идет именно о сумме денег.
        """
        return self.float(1, 1000)

    def date_time(self) -> datetime:
        """
        Генерирует дату и время доменного события.

        Используется для:
        - времени операции
        - времени создания сущности
        - временных полей в API-запросах и ответах
        """
        return self.faker.date_time()


# Единый экземпляр генератора для всего тестового проекта.
# Импортируется и используется напрямую в тестах и фабриках.
fake = Fake(faker=Faker())
