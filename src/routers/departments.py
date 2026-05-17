from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.departments import (CreateEmployeeInDepartmentResponseSchema, RetrieveDepartmentResponseSchema,
                                     DepartmentDetailResponseSchema, ReassignDepartmentRequestSchema)
from src.repositories.departments_repo import DepartmentsRepo
from src.schemas.departments import (CreateDepartmentResponseSchema, CreateDepartmentRequestSchema,
                                     CreateEmployeeInDepartmentRequestSchema)
from src.service.departments_service import DepartmentsService
from src.db import get_db

router = APIRouter()


def department_service(db: AsyncSession = Depends(get_db)):
	repo = DepartmentsRepo(db)
	service = DepartmentsService(repo)
	return service


@router.post("/", response_model=CreateDepartmentResponseSchema)
async def create_departments(data: CreateDepartmentRequestSchema,
                             service: DepartmentsService = Depends(department_service)):
	return await service.create_department(data.name, data.department_id)


@router.post("/{department_id}/employees/", response_model=CreateEmployeeInDepartmentResponseSchema)
async def create_employee_in_department(
		department_id: int,
		data: CreateEmployeeInDepartmentRequestSchema,
		service: DepartmentsService = Depends(department_service)
):
	return await service.create_employeer_in_department(department_id, data)


@router.get("/{department_id}/", response_model=DepartmentDetailResponseSchema)
async def get_info_department(
		department_id: int,
		depth: Annotated[int, Query(ge=1, le=5)] = 1,
		include_employees: bool = True,
		service: DepartmentsService = Depends(department_service)
):
	return await service.full_info_department(department_id, depth, include_employees)


@router.patch("/{department_id}/", response_model=DepartmentDetailResponseSchema)
async def reassign_department(
		department_id: int,
		data: ReassignDepartmentRequestSchema,
		service: DepartmentsService = Depends(department_service)
):
	return await service.reassign_department(department_id, data)
