from src.models import Base

from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Departments(Base):
	__tablename__ = "departments"

	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(255), nullable=False)
	parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
	parent: Mapped["Departments"] = relationship("Departments", remote_side=[id])