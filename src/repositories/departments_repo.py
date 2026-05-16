from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from src.models.departments import Departments


class DepartmentsRepo:
	def __init__(self, db: AsyncSession):
		self.db = db


	async def get_department_by_id(self, department_id: int) -> Optional[Departments]:
		query = select(Departments).where(Departments.id == department_id)
		result = await self.db.execute(query)
		return result.scalar_one_or_none()

	async def get_by_name_and_parent(self, name: str, parent_id: Optional[int]) -> Optional[Departments]:
		"""
		Searches for a department by parent name and ID.
        Used for manual pre-validation of uniqueness.
		"""
		query = select(Departments).where(
			Departments.name == name,
			Departments.parent_id == parent_id
		)
		result = await self.db.execute(query)
		return result.scalar_one_or_none()

	async def create(self, name: str, parent_id: Optional[int] = None) -> Departments:
		if parent_id is not None:
			parent_exists = await self.get_department_by_id(parent_id)
			if not parent_exists:
				raise HTTPException(
					status_code=status.HTTP_400_BAD_REQUEST,
					detail=f"The parent department with ID {parent_id} does not exist."
				)
			
		existing_dept = await self.get_by_name_and_parent(name, parent_id)
		if existing_dept:
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail=f"A department named ‘{name}’ already exists under this parent."
			)

		new_dept = Departments(name=name, parent_id=parent_id)
		self.db.add(new_dept)
		await self.db.flush()
		return new_dept
