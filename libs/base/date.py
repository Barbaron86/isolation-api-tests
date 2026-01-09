from datetime import datetime


def to_proto_datetime(value: datetime) -> str:
    return value.strftime('%Y-%m-%d %H:%M:%S')
