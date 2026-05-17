import logging
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.repositories.departments_repo import DepartmentsRepo
from src.schemas.departments import (
    CreateDepartmentRequestSchema,
    CreateDepartmentResponseSchema,
    CreateEmployeeInDepartmentRequestSchema,
    CreateEmployeeInDepartmentResponseSchema,
    DepartmentDetailResponseSchema,
    ReassignDepartmentRequestSchema,
)
from src.service.departments_service import DepartmentsService

router = APIRouter()
logger = logging.getLogger(__name__)


def department_service(db: AsyncSession = Depends(get_db)):
    repo = DepartmentsRepo(db)
    service = DepartmentsService(repo)
    return service


@router.post(
    "/",
    response_model=CreateDepartmentResponseSchema,
    summary="Create department",
    description="Creates a new department. The department can be either a root department or a child of another department.",
    response_description="Department successfully created",
)
async def create_departments(
    data: CreateDepartmentRequestSchema,
    service: DepartmentsService = Depends(department_service),
):
    logger.info(
        "Create department endpoint called",
        extra={"parent_department_id": data.department_id},
    )
    return await service.create_department(data.name, data.department_id)


@router.post(
    "/{department_id}/employees/",
    response_model=CreateEmployeeInDepartmentResponseSchema,
    summary="Create employee in department",
    description="Creates a new employee and assigns the employee to the department specified by department_id.",
    response_description="Employee successfully created and assigned to the department",
)
async def create_employee_in_department(
    department_id: int,
    data: CreateEmployeeInDepartmentRequestSchema,
    service: DepartmentsService = Depends(department_service),
):
    logger.info(
        "Create employee endpoint called", extra={"department_id": department_id}
    )
    return await service.create_employeer_in_department(department_id, data)


@router.get(
    "/{department_id}/",
    response_model=DepartmentDetailResponseSchema,
    summary="Get department details",
    description=(
        "Returns detailed information about a department. "
        "The response can include nested child departments up to the specified depth "
        "and optionally include employees."
    ),
    response_description="Department details successfully retrieved",
)
async def get_info_department(
    department_id: int,
    depth: Annotated[
        int,
        Query(
            ge=1,
            le=5,
            description="Depth of nested child departments to include. Allowed range: 1 to 5.",
        ),
    ] = 1,
    include_employees: bool = Query(
        True, description="Whether to include employees in the response."
    ),
    service: DepartmentsService = Depends(department_service),
):
    logger.info(
        "Department details endpoint called",
        extra={
            "department_id": department_id,
            "depth": depth,
            "include_employees": include_employees,
        },
    )
    return await service.full_info_department(department_id, depth, include_employees)


@router.patch(
    "/{department_id}/",
    response_model=DepartmentDetailResponseSchema,
    summary="Reassign department",
    description="Changes the parent department of the specified department.",
    response_description="Department successfully reassigned",
)
async def reassign_department(
    department_id: int,
    data: ReassignDepartmentRequestSchema,
    service: DepartmentsService = Depends(department_service),
):
    logger.info(
        "Reassign department endpoint called",
        extra={
            "department_id": department_id,
            "target_parent_department_id": data.parent_id,
            "renaming": data.name is not None,
        },
    )
    return await service.reassign_department(department_id, data)


@router.delete(
    "/{department_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete department",
    description=(
        "Deletes a department using one of two modes: "
        "`cascade` removes the department together with related employees; "
        "`reassign` transfers employees to another department before deleting the department. "
        "When using `reassign`, the `reassign_to_department_id` query parameter is required."
    ),
    response_description="Department successfully deleted",
)
async def delete_department(
    department_id: int,
    mode: Literal["cascade", "reassign"] = Query(
        description="Delete mode. Use `cascade` to remove related employees or `reassign` to transfer them."
    ),
    reassign_to_department_id: Optional[int] = Query(
        None,
        description="Department that should receive employees when mode is `reassign`.",
    ),
    service: DepartmentsService = Depends(department_service),
):
    if mode == "reassign":
        if reassign_to_department_id is None:
            logger.warning(
                "Delete department rejected: missing reassign target",
                extra={"department_id": department_id},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The 'reassign_to_department_id' parameter is required if the 'reassign' mode is selected.",
            )
        if reassign_to_department_id == department_id:
            logger.warning(
                "Delete department rejected: reassign target is same department",
                extra={
                    "department_id": department_id,
                    "reassign_to_department_id": reassign_to_department_id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employees cannot be transferred to the same department that is being eliminated.",
            )

    logger.info(
        "Delete department endpoint called",
        extra={
            "department_id": department_id,
            "mode": mode,
            "reassign_to_department_id": reassign_to_department_id,
        },
    )
    await service.delete_department(
        department_id=department_id, mode=mode, reassign_to_id=reassign_to_department_id
    )
