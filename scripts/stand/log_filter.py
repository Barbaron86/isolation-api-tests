"""Распознаёт технические сообщения сервисов без сохранения произвольных логов."""

import re

_DOCKER_TIMESTAMP = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z"
_APPLICATION_TIMESTAMP = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}"
_TOPIC = r"[A-Za-z0-9_.-]{1,249}"
_CONSUMER_PREFIX = rf"(?:{_APPLICATION_TIMESTAMP} - OPERATIONS_KAFKA_CONSUMER_CLIENT - INFO - )?"
_CONSUMER_ERROR_PREFIX = rf"(?:{_APPLICATION_TIMESTAMP} - OPERATIONS_KAFKA_CONSUMER_CLIENT - ERROR - )?"
_ADMIN_PREFIX = rf"(?:{_APPLICATION_TIMESTAMP} - OPERATIONS_KAFKA_ADMIN_CLIENT - INFO - )?"
_ADMIN_ERROR_PREFIX = rf"(?:{_APPLICATION_TIMESTAMP} - OPERATIONS_KAFKA_ADMIN_CLIENT - ERROR - )?"
_POSTGRES_PREFIX = r"(?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} (?:UTC|[+-]\d{2}) \[\d+\] (?:LOG|FATAL):  )?"
_ALEMBIC_PREFIX = r"(?:INFO  \[alembic\.runtime\.migration\] )?"

_RULES = {
    "kafka-operations": (
        (_CONSUMER_PREFIX + r"Kafka consumer ready partitions=(\d+)", r"Kafka consumer ready partitions=\1"),
        (_CONSUMER_PREFIX + rf"Kafka consumer started topic=({_TOPIC})", r"Kafka consumer started topic=\1"),
        (_CONSUMER_PREFIX + r"Kafka consumer stopped", "Kafka consumer stopped"),
        (
            _CONSUMER_ERROR_PREFIX + r"Kafka consumer stop failed error_type=[A-Za-z_][A-Za-z0-9_]{0,63}",
            "Kafka consumer stop failed",
        ),
        (
            _CONSUMER_PREFIX + rf"(Received|Processed) Kafka record topic=({_TOPIC}) partition=(\d+) offset=(\d+)",
            r"\1 Kafka record topic=\2 partition=\3 offset=\4",
        ),
        (_ADMIN_PREFIX + rf"Kafka topic '({_TOPIC})' created", r"Kafka topic '\1' created"),
        (_ADMIN_PREFIX + rf"Topic '({_TOPIC})' already exists", r"Topic '\1' already exists"),
        (
            _ADMIN_ERROR_PREFIX + rf"Kafka topic creation failed topic=({_TOPIC}) code=(-?\d+)",
            r"Kafka topic creation failed topic=\1 code=\2",
        ),
    ),
    "postgres": (
        (
            _POSTGRES_PREFIX + r"database system is (ready to accept connections|shut down|starting up)",
            r"database system is \1",
        ),
    ),
    "postgres-init": (
        (r"Initialization complete\.", "Initialization complete."),
    ),
    "postgres-migrator-operations": (
        (
            _ALEMBIC_PREFIX + r"Running upgrade ([A-Za-z0-9_]{0,64}) -> ([A-Za-z0-9_]{1,64})(?:, [^\r\n]*)?",
            r"Running upgrade \1 -> \2",
        ),
    ),
    "kafka": (
        (r"Kafka Server started", "Kafka Server started"),
        (
            r"\[" + _APPLICATION_TIMESTAMP + r"\] INFO \[KafkaServer id=(\d+)\] started \(kafka\.server\.KafkaServer\)",
            r"Kafka Server started broker_id=\1",
        ),
    ),
}


def filter_logs(service: str, output: str) -> str:
    """Оставляет разрешённые поля из целиком распознанных сообщений.

    Args:
        service: Сервис Compose, чьи логи получены без префикса контейнера.
        output: Ограниченный вывод логов с необязательными метками времени Docker.

    Returns:
        Технические сообщения либо пустая строка, если все строки отброшены.
    """
    lines = []
    for line in output.splitlines():
        timestamp = re.fullmatch(rf"({_DOCKER_TIMESTAMP}) (.*)", line)
        message = timestamp[2] if timestamp else line
        for pattern, replacement in _RULES.get(service, ()):
            match = re.fullmatch(pattern, message)
            if match is not None:
                prefix = f"{timestamp[1]} " if timestamp else ""
                lines.append(prefix + match.expand(replacement))
                break
    return "\n".join(lines) + ("\n" if lines else "")
