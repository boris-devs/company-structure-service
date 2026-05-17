import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.repositories.departments_repo import DepartmentsRepo
from src.schemas.departments import (
    CreateEmployeeInDepartmentRequestSchema,
    ReassignDepartmentRequestSchema,
)

logger = logging.getLogger(__name__)


class DepartmentsService:
    def __init__(self, depart_repo: DepartmentsRepo):
        self.depart_repo = depart_repo

    async def _commit(self, operation: str, **log_context) -> None:
        try:
            await self.depart_repo.db.commit()
        except SQLAlchemyError:
            await self.depart_repo.db.rollback()
            logger.exception(
                "%s failed; transaction rolled back", operation, extra=log_context
            )
            raise
        logger.info("%s committed", operation, extra=log_context)

    async def create_department(self, name: str, parent_id: int | None = None):
        logger.info("Creating department", extra={"parent_department_id": parent_id})

        if parent_id is not None:
            parent_exists = await self.depart_repo.get_department_by_id(parent_id)
            if not parent_exists:
                logger.warning(
                    "Department creation rejected: parent not found",
                    extra={"parent_department_id": parent_id},
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"The parent department with ID {parent_id} does not exist.",
                )

        existing_dept = await self.depart_repo.get_by_name_and_parent(name, parent_id)
        if existing_dept:
            logger.warning(
                "Department creation rejected: duplicate department under parent",
                extra={"parent_department_id": parent_id},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A department named '{name}' already exists under this parent.",
            )

        try:
            new_department = await self.depart_repo.create_department(name, parent_id)
            await self._commit(
                "Department creation",
                department_id=new_department.id,
                parent_department_id=parent_id,
            )
            return new_department
        except IntegrityError:
            await self.depart_repo.db.rollback()
            logger.exception(
                "Department creation failed due to integrity error",
                extra={"parent_department_id": parent_id},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Data integrity error. A department with this name may already exist.",
            )
        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while creating department.",
            )

    async def create_employeer_in_department(
        self, department_id: int, data: CreateEmployeeInDepartmentRequestSchema
    ):
        logger.info(
            "Creating employee in department", extra={"department_id": department_id}
        )
        exist_department = await self.depart_repo.get_department_by_id(department_id)
        if not exist_department:
            logger.warning(
                "Employee creation rejected: department not found",
                extra={"department_id": department_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department with ID {department_id} not found.",
            )
        try:
            new_employee = await self.depart_repo.create_employee(
                full_name=data.full_name,
                position=data.position,
                department_id=department_id,
                hired_at=data.hired_at,
            )
            await self._commit(
                "Employee creation",
                employee_id=new_employee.id,
                department_id=department_id,
            )
            return new_employee
        except IntegrityError:
            await self.depart_repo.db.rollback()
            logger.exception(
                "Employee creation failed due to integrity error",
                extra={"department_id": department_id},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Data integrity error. Something went wrong while creating the employee.",
            )
        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while creating employee.",
            )

    async def full_info_department(
        self, department_id: int, depth: int = 1, include_employees: bool = True
    ):
        logger.info(
            "Fetching department details",
            extra={
                "department_id": department_id,
                "depth": depth,
                "include_employees": include_employees,
            },
        )
        exist_department = await self.depart_repo.tree_children_departments(
            department_id=department_id,
            depth=depth,
            include_employees=include_employees,
        )
        if not exist_department:
            logger.warning(
                "Department details rejected: department not found",
                extra={"department_id": department_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found."
            )
        return exist_department

    async def reassign_department(
        self, department_id: int, data: ReassignDepartmentRequestSchema
    ):
        logger.info(
            "Reassigning department",
            extra={
                "department_id": department_id,
                "target_parent_department_id": data.parent_id,
                "renaming": data.name is not None,
            },
        )
        if data.parent_id == department_id:
            logger.warning(
                "Department reassignment rejected: target is self",
                extra={"department_id": department_id},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reassign a department to itself.",
            )

        exist_department = await self.depart_repo.get_department_by_id(department_id)
        if not exist_department:
            logger.warning(
                "Department reassignment rejected: department not found",
                extra={"department_id": department_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found."
            )

        if data.parent_id is not None:
            target_parent = await self.depart_repo.get_department_by_id(data.parent_id)
            if not target_parent:
                logger.warning(
                    "Department reassignment rejected: target parent not found",
                    extra={
                        "department_id": department_id,
                        "target_parent_department_id": data.parent_id,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Target parent department not found.",
                )

            ancestor_ids = await self.depart_repo.get_ancestor_ids(data.parent_id)
            if department_id in ancestor_ids:
                logger.warning(
                    "Department reassignment rejected: cycle detected",
                    extra={
                        "department_id": department_id,
                        "target_parent_department_id": data.parent_id,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot reassign a department to one of its own sub-departments (cycling detected).",
                )

        exist_department.department_id = data.parent_id
        if data.name is not None:
            exist_department.name = data.name
        try:
            await self._commit(
                "Department reassignment",
                department_id=department_id,
                target_parent_department_id=data.parent_id,
            )
            await self.depart_repo.db.refresh(exist_department)
        except IntegrityError:
            await self.depart_repo.db.rollback()
            logger.exception(
                "Department reassignment failed due to integrity error",
                extra={
                    "department_id": department_id,
                    "target_parent_department_id": data.parent_id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Data integrity error. A department with this name may already exist under the target parent.",
            )
        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while reassigning department.",
            )

        return exist_department

    async def delete_department(
        self, department_id: int, mode: str, reassign_to_id: int | None
    ):
        logger.info(
            "Deleting department",
            extra={
                "department_id": department_id,
                "mode": mode,
                "reassign_to_department_id": reassign_to_id,
            },
        )
        target_dept = await self.depart_repo.get_department_by_id(department_id)
        if not target_dept:
            logger.warning(
                "Department deletion rejected: department not found",
                extra={"department_id": department_id},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found."
            )

        try:
            if mode == "cascade":
                await self.depart_repo.delete_department(target_dept)

            elif mode == "reassign":
                new_home = await self.depart_repo.get_department_by_id(reassign_to_id)
                if not new_home:
                    logger.warning(
                        "Department deletion rejected: target reassign department not found",
                        extra={
                            "department_id": department_id,
                            "reassign_to_department_id": reassign_to_id,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Target reassign department not found.",
                    )

                await self.depart_repo.bulk_reassign_employees(
                    from_id=department_id, to_id=reassign_to_id
                )
                await self.depart_repo.bulk_move_child_departments(
                    from_parent_id=department_id, to_parent_id=reassign_to_id
                )
                await self.depart_repo.delete_department(target_dept)

            await self._commit(
                "Department deletion",
                department_id=department_id,
                mode=mode,
                reassign_to_department_id=reassign_to_id,
            )
        except HTTPException:
            raise
        except SQLAlchemyError:
            await self.depart_repo.db.rollback()
            logger.exception(
                "Department deletion failed; transaction rolled back",
                extra={
                    "department_id": department_id,
                    "mode": mode,
                    "reassign_to_department_id": reassign_to_id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while deleting department.",
            )
