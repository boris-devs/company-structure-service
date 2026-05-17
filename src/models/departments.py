from src.models import Base

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import ForeignKey, String, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
	from src.models.employees import Employees


class Departments(Base):
	__tablename__ = "departments"

	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(200), nullable=False)
	department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
	parent: Mapped["Departments"] = relationship("Departments", remote_side=[id])

	children: Mapped[List["Departments"]] = relationship(
		"Departments",
		back_populates="parent",
		lazy="selectin",
		cascade="all, delete-orphan",
		passive_deletes=True
	)
	employees: Mapped[List["Employees"]] = relationship(
		"Employees",
		back_populates="department",
		cascade="all, delete-orphan",
		passive_deletes=True
	)
	__table_args__ = (
		UniqueConstraint("department_id", "name", name="uq_department_parent_name"),
	)

	@property
	def safe_children(self) -> list["Departments"]:
		if "children" in self.__dict__:
			return self.children
		return []

	@property
	def safe_employees(self) -> list:
		if "employees" in self.__dict__:
			return self.employees
		return []
