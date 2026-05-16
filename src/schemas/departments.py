from pydantic import BaseModel, Field


class CreateDepartmentRequestSchema(BaseModel):
	name: str = Field(min_length=1, max_length=200, str_strip_whitespace=True)
	department_id: int | None = None


class CreateDepartmentResponseSchema(BaseModel):
	id: int
	name: str
	department_id: int | None = None


class CreateEmployeeInDepartmentRequestSchema(BaseModel):
	full_name: str
	position: str
	hire_date: str | None = None


class CreateEmployeeInDepartmentResponseSchema(BaseModel):
	id: int
	full_name: str
	position: str
	hire_date: str | None = None
	department_id: int
