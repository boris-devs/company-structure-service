import logging
from datetime import date
from typing import Optional, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, aliased

from src.models.employees import Employees
from src.models.departments import Departments

logger = logging.getLogger(__name__)


class DepartmentsRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_department_by_id(
        self, department_id: int, options: List | None = None
    ) -> Optional[Departments]:
        logger.debug(
            "Fetching department by id",
            extra={"department_id": department_id, "with_options": bool(options)},
        )
        query = select(Departments).where(Departments.id == department_id)
        if options:
            query = query.options(*options)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name_and_parent(
        self, name: str, department_id: Optional[int]
    ) -> Optional[Departments]:
        """
                Searches for a department by parent name and ID.
        Used for manual pre-validation of uniqueness.
        """
        logger.debug(
            "Checking department uniqueness",
            extra={"parent_department_id": department_id},
        )
        query = select(Departments).where(
            Departments.name == name, Departments.department_id == department_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_department(
        self, name: str, department_id: Optional[int] = None
    ) -> Departments:
        logger.debug(
            "Adding department to session",
            extra={"parent_department_id": department_id},
        )
        new_dept = Departments(name=name, department_id=department_id)
        self.db.add(new_dept)
        await self.db.flush()
        logger.info(
            "Department flushed",
            extra={"department_id": new_dept.id, "parent_department_id": department_id},
        )
        return new_dept

    async def create_employee(
        self,
        full_name: str,
        position: str,
        department_id: int,
        hired_at: date | None = None,
    ):
        logger.debug(
            "Adding employee to session",
            extra={
                "department_id": department_id,
                "has_hired_at": hired_at is not None,
            },
        )
        new_employee = Employees(
            full_name=full_name,
            position=position,
            department_id=department_id,
            hired_at=hired_at,
        )
        self.db.add(new_employee)
        await self.db.flush()
        logger.info(
            "Employee flushed",
            extra={"employee_id": new_employee.id, "department_id": department_id},
        )
        return new_employee

    async def get_employees_in_department(self, department_id: int):
        logger.debug(
            "Fetching employees in department", extra={"department_id": department_id}
        )
        employees = await self.db.execute(
            select(Employees).where(Employees.department_id == department_id)
        )
        return employees.scalars().all()

    async def tree_children_departments(
        self, department_id: int, depth: int, include_employees: bool
    ):
        """
        Retrieves the hierarchical structure of departments starting from a given
        department ID up to a specified depth. Optionally includes employees
        associated with the departments.

        The method allows for dynamically preloading the children and employee
        relationships of the departments for optimized querying.

        :param department_id: The unique identifier of the department from which
            to start the hierarchy traversal.
        :type department_id: int
        :param depth: The depth of the hierarchical traversal for loading child
            departments. A value of 0 indicates no further depth beyond the
            given department.
        :type depth: int
        :param include_employees: A flag indicating whether the employees
            associated with each department should be included in the result.
        :type include_employees: bool
        :return: An instance of the department with its hierarchical children
            and optionally its employee list if `include_employees` is specified.
        :rtype: Optional[Departments]
        """
        logger.debug(
            "Fetching department tree",
            extra={
                "department_id": department_id,
                "depth": depth,
                "include_employees": include_employees,
            },
        )
        options = []

        if depth > 0:
            current_load = selectinload(Departments.children)
            for _ in range(depth - 1):
                current_load = current_load.selectinload(Departments.children)
            options.append(current_load)

        if include_employees:
            options.append(selectinload(Departments.employees))

        query = await self.get_department_by_id(department_id, options)
        if query and include_employees:
            query.employees.sort(key=lambda emp: emp.full_name)
        return query

    async def get_ancestor_ids(self, department_id: int) -> list[int]:
        """
        Fetches the ancestor department IDs for a given department in a hierarchical organization
        structure using a Common Table Expression (CTE). This method retrieves all ancestor IDs
        starting from the provided department ID until the root-level department.

        :param department_id: The ID of the department whose ancestor hierarchy is to be fetched.
        :type department_id: int
        :return: A list of ancestor department IDs in the hierarchy.
        :rtype: list[int]
        """
        logger.debug(
            "Fetching department ancestors", extra={"department_id": department_id}
        )
        parent_cte = (
            select(Departments.id, Departments.department_id)
            .where(Departments.id == department_id)
            .cte(name="parent_tree", recursive=True)
        )

        parent_alias = aliased(Departments, name="p")
        cte_alias = aliased(parent_cte, name="c")

        parent_cte = parent_cte.union_all(
            select(parent_alias.id, parent_alias.department_id).join(
                cte_alias, parent_alias.id == cte_alias.c.department_id
            )
        )

        query = select(parent_cte.c.id)
        result = await self.db.execute(query)

        return list(result.scalars().all())

    async def bulk_reassign_employees(self, from_id: int, to_id: int):
        """
        Reassigns all employees from one department to another in the database.

        This method updates the department of all employees who are currently assigned
        to the specified source department (`from_id`), reassigning them to the
        specified target department (`to_id`).

        :param from_id: The ID of the source department from which employees are being reassigned.
        :param to_id: The ID of the target department to which employees will be reassigned.
        :return: None
        """
        logger.info(
            "Bulk reassigning employees",
            extra={"from_department_id": from_id, "to_department_id": to_id},
        )
        query = (
            update(Employees)
            .where(Employees.department_id == from_id)
            .values(department_id=to_id)
        )
        result = await self.db.execute(query)
        logger.info(
            "Employees reassigned",
            extra={
                "from_department_id": from_id,
                "to_department_id": to_id,
                "row_count": result.rowcount,
            },
        )

    async def bulk_move_child_departments(
        self, from_parent_id: int, to_parent_id: int
    ) -> None:
        """
        Bulk moves child departments from one parent department to another by updating
        their parent ID in the database. This operation is executed asynchronously.

        :param from_parent_id: The ID of the parent department from which child
            departments will be moved.
        :type from_parent_id: int
        :param to_parent_id: The ID of the parent department to which child
            departments will be moved.
        :type to_parent_id: int
        :return: None
        :rtype: None
        """
        logger.info(
            "Bulk moving child departments",
            extra={
                "from_parent_department_id": from_parent_id,
                "to_parent_department_id": to_parent_id,
            },
        )
        query = (
            update(Departments)
            .where(Departments.department_id == from_parent_id)
            .values(department_id=to_parent_id)
        )
        result = await self.db.execute(query)
        logger.info(
            "Child departments moved",
            extra={
                "from_parent_department_id": from_parent_id,
                "to_parent_department_id": to_parent_id,
                "row_count": result.rowcount,
            },
        )

    async def delete_department(self, department: Departments) -> None:
        """
                Removes the department object from the session.
        Because cascade="all, delete-orphan" is configured in the model,
        when this deletion is committed, SQLAlchemy will automatically remove
        all associated employees and nested subdepartments (if cascade mode is enabled).
        """
        logger.info(
            "Deleting department from session", extra={"department_id": department.id}
        )
        await self.db.delete(department)
