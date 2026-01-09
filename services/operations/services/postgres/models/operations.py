import uuid
from datetime import datetime

from sqlalchemy import Column, UUID, DateTime, Float, String
from sqlalchemy.orm import Mapped

from libs.postgres.mixin_model import MixinModel


class OperationsModel(MixinModel):
    __tablename__ = "operations"

    id: Mapped[uuid.UUID] = Column(UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = Column(String(length=50), nullable=False)
    status: Mapped[str] = Column(String(length=50), nullable=False)
    amount: Mapped[float] = Column(Float, nullable=False)
    user_id: Mapped[uuid.UUID] = Column(UUID, nullable=False)
    card_id: Mapped[uuid.UUID] = Column(UUID, nullable=False)
    category: Mapped[str] = Column(String(length=50), nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, nullable=False)
    account_id: Mapped[uuid.UUID] = Column(UUID, nullable=False)
