from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from fastapi import status

from src.repositories.departments_repo import DepartmentsRepo


class DepartmentsService:
	def __init__(self, depart_repo: DepartmentsRepo):
		self.depart_repo = depart_repo


	async def create_department(self, name: str, parent_id: int | None = None):
		try:
			new_departament = await self.depart_repo.create(name, parent_id)
			await self.depart_repo.db.commit()
			return new_departament
		except IntegrityError:
			await self.depart_repo.db.rollback()
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail="Data integrity error. A department with this name may already exist."
			)