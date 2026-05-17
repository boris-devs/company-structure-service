from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, model_validator
from sqlalchemy import inspect


class CreateDepartmentRequestSchema(BaseModel):
	name: str = Field(min_length=1, max_length=200, str_strip_whitespace=True)
	department_id: int | None = None


class CreateDepartmentResponseSchema(BaseModel):
	id: int
	name: str
	department_id: int | None = None

	model_config = ConfigDict(from_attributes=True)


class CreateEmployeeInDepartmentRequestSchema(BaseModel):
	full_name: str
	position: str
	hired_at: date | None = None


class CreateEmployeeInDepartmentResponseSchema(BaseModel):
	id: int
	full_name: str
	position: str
	hired_at: date | None = None
	department_id: int

	model_config = ConfigDict(from_attributes=True)


class RetrieveDepartmentResponseSchema(BaseModel):
	id: int
	name: str
	department_id: int | None = None

	model_config = ConfigDict(from_attributes=True)


class DepartmentParentTreeResponse(BaseModel):
	id: int
	name: str
	department_id: Optional[int]
	children: List["DepartmentParentTreeResponse"] = Field(validation_alias="safe_children",
	                                                       serialization_alias="children", default=[])

	model_config = ConfigDict(from_attributes=True)


class EmployeeResponseSchema(BaseModel):
	id: int
	full_name: str
	position: str
	hired_at: Optional[date]
	created_at: datetime

	model_config = ConfigDict(from_attributes=True)


class DepartmentDetailResponseSchema(BaseModel):
	id: int
	name: str
	department_id: Optional[int]
	created_at: datetime
	employees: List[EmployeeResponseSchema] = Field(validation_alias="safe_employees", serialization_alias="employees",
	                                                default=[])
	children: List["DepartmentParentTreeResponse"] = Field(validation_alias="safe_children",
	                                                       serialization_alias="children", default=[])

	model_config = ConfigDict(from_attributes=True)
