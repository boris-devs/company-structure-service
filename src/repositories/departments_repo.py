from datetime import date
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, aliased

from src.models.employees import Employees
from src.models.departments import Departments


class DepartmentsRepo:
	def __init__(self, db: AsyncSession):
		self.db = db

	async def get_department_by_id(self, department_id: int, options: List | None = None) -> Optional[Departments]:
		query = select(Departments).where(Departments.id == department_id)
		if options:
			query = query.options(*options)
		result = await self.db.execute(query)
		return result.scalar_one_or_none()

	async def get_by_name_and_parent(self, name: str, department_id: Optional[int]) -> Optional[Departments]:
		"""
		Searches for a department by parent name and ID.
        Used for manual pre-validation of uniqueness.
		"""
		query = select(Departments).where(
			Departments.name == name,
			Departments.department_id == department_id
		)
		result = await self.db.execute(query)
		return result.scalar_one_or_none()

	async def create_department(self, name: str, department_id: Optional[int] = None) -> Departments:
		new_dept = Departments(name=name, department_id=department_id)
		self.db.add(new_dept)
		await self.db.flush()
		return new_dept

	async def create_employee(self, full_name: str, position: str, department_id: int, hired_at: date | None = None):
		new_employee = Employees(full_name=full_name, position=position, department_id=department_id, hired_at=hired_at)
		self.db.add(new_employee)
		await self.db.flush()
		return new_employee

	async def get_employees_in_department(self, department_id: int):
		employees = await self.db.execute(select(Employees).where(Employees.department_id == department_id))
		return employees.scalars().all()

	async def tree_children_departments(self, department_id: int, depth: int, include_employees: bool):
		options = []

		if depth > 0:
			current_load = selectinload(Departments.children)
			for _ in range(depth - 1):
				current_load = current_load.selectinload(Departments.children)
			options.append(current_load)

		if include_employees:
			options.append(selectinload(Departments.employees.order_by(Employees.full_name)))

		query = await self.get_department_by_id(department_id, options)
		return query

	async def get_ancestor_ids(self, department_id: int) -> list[int]:

		parent_cte = (
			select(Departments.id, Departments.department_id)
			.where(Departments.id == department_id)
			.cte(name="parent_tree", recursive=True)
		)

		parent_alias = aliased(Departments, name="p")
		cte_alias = aliased(parent_cte, name="c")

		parent_cte = parent_cte.union_all(
			select(parent_alias.id, parent_alias.department_id)
			.join(cte_alias, parent_alias.id == cte_alias.c.department_id)
		)

		query = select(parent_cte.c.id)
		result = await self.db.execute(query)

		return list(result.scalars().all())
