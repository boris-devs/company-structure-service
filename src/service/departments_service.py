from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from fastapi import status

from src.schemas.departments import CreateEmployeeInDepartmentRequestSchema
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

	async def create_employeer_in_department(self, department_id: int, data: CreateEmployeeInDepartmentRequestSchema):
		exist_department = await self.depart_repo.get_department_by_id(department_id)
		if not exist_department:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail=f"Department with ID {department_id} not found."
			)
		try:
			new_employee = await self.depart_repo.create_employee(
				full_name=data.full_name,
				position=data.position,
				department_id=department_id,
				hired_at=data.hired_at)
			await self.depart_repo.db.commit()
			return new_employee
		except IntegrityError:
			await self.depart_repo.db.rollback()
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail="Data integrity error. Something went wrong while creating the employee."
			)
