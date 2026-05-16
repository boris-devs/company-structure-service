from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.departments_repo import DepartmentsRepo
from src.schemas.departments import CreateDepartmentResponseSchema, CreateDepartmentRequestSchema
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
