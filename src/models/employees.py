from src.models import Base

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class Employees(Base):
	__tablename__ = "employees"

	id: Mapped[int] = mapped_column(primary_key=True)
	department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
	full_name: Mapped[str] = mapped_column(String(255), nullable=False)
	position: Mapped[str] = mapped_column(String(255), nullable=False)
	hire_date: Mapped[Optional[str]] = mapped_column(String(255), nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
