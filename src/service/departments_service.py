from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from fastapi import status

from src.schemas.departments import CreateEmployeeInDepartmentRequestSchema, ReassignDepartmentRequestSchema
from src.repositories.departments_repo import DepartmentsRepo


class DepartmentsService:
	def __init__(self, depart_repo: DepartmentsRepo):
		self.depart_repo = depart_repo

	async def create_department(self, name: str, parent_id: int | None = None):

		if parent_id is not None:
			parent_exists = await self.depart_repo.get_department_by_id(parent_id)
			if not parent_exists:
				raise HTTPException(
					status_code=status.HTTP_400_BAD_REQUEST,
					detail=f"The parent department with ID {parent_id} does not exist."
				)

		existing_dept = await self.depart_repo.get_by_name_and_parent(name, parent_id)
		if existing_dept:
			raise HTTPException(
				status_code=status.HTTP_409_CONFLICT,
				detail=f"A department named ‘{name}’ already exists under this parent."
			)

		try:
			new_departament = await self.depart_repo.create_department(name, parent_id)
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

	async def full_info_department(self, department_id: int, depth: int = 1, include_employees: bool = True):
		exist_department = await self.depart_repo.tree_children_departments(department_id=department_id, depth=depth,
		                                                                    include_employees=include_employees)
		if not exist_department:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
		return exist_department

	async def reassign_department(self, department_id: int, data: ReassignDepartmentRequestSchema):
		if data.parent_id == department_id:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="Cannot reassign a department to itself."
			)

		exist_department = await self.depart_repo.get_department_by_id(department_id)
		if not exist_department:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Department not found."
			)

		if data.parent_id is not None:
			target_parent = await self.depart_repo.get_department_by_id(data.parent_id)
			if not target_parent:
				raise HTTPException(
					status_code=status.HTTP_404_NOT_FOUND,
					detail="Target parent department not found."
				)

			ancestor_ids = await self.depart_repo.get_ancestor_ids(data.parent_id)

			if department_id in ancestor_ids:
				raise HTTPException(
					status_code=status.HTTP_400_BAD_REQUEST,
					detail="Cannot reassign a department to one of its own sub-departments (cycling detected)."
				)

		exist_department.department_id = data.parent_id
		if data.name is not None:
			exist_department.name = data.name
		await self.depart_repo.db.commit()
		await self.depart_repo.db.refresh(exist_department)

		return exist_department

	async def delete_department(self, department_id: int, mode: str, reassign_to_id: int | None):
		"""
		Deletes a department from the repository based on the given mode of operation.

		Summary:
		This coroutine handles the deletion of a department identified by its ID. The action performed depends on the mode
		parameter, which can either trigger a cascade delete or reassign employees and child departments to another
		department. The method ensures proper validation, including that the specified department exists and that,
		in reassign mode, the target reassign department is valid. If the operation is successful, changes are committed
		to the database.

		:param department_id: The ID of the department to be deleted.
		:type department_id: int
		:param mode: Determines the mode of deletion. Accepted values are "cascade" for direct deletion and "reassign"
		             for reassigning employees and child departments before deletion.
		:type mode: str
		:param reassign_to_id: The ID of the target department to which employees and child departments are reassigned.
		                       Must be provided if mode is "reassign". Defaults to None.
		:type reassign_to_id: int | None
		:return: None
		:rtype: None
		:raises HTTPException: Raises an exception with a 404 status code if the specified department or target
		                       reassign department is not found.
		"""
		target_dept = await self.depart_repo.get_department_by_id(department_id)
		if not target_dept:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

		if mode == "cascade":
			await self.depart_repo.delete_department(target_dept)

		elif mode == "reassign":

			new_home = await self.depart_repo.get_department_by_id(reassign_to_id)
			if not new_home:
				raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
				                    detail="Target reassign department not found.")


			await self.depart_repo.bulk_reassign_employees(
				from_id=department_id,
				to_id=reassign_to_id
			)


			await self.depart_repo.bulk_move_child_departments(
				from_parent_id=department_id,
				to_parent_id=reassign_to_id
			)

			await self.depart_repo.delete_department(target_dept)

		await self.depart_repo.db.commit()