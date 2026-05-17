from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from main import app
from src.routers.departments import department_service


class FakeDepartmentsService:
    def __init__(self):
        self.calls = []

    async def create_department(self, name: str, parent_id: int | None = None):
        self.calls.append(("create_department", name, parent_id))
        return SimpleNamespace(id=1, name=name, department_id=parent_id)

    async def create_employeer_in_department(self, department_id: int, data):
        self.calls.append(
            (
                "create_employeer_in_department",
                department_id,
                data.full_name,
                data.position,
                data.hired_at,
            )
        )
        return SimpleNamespace(
            id=10,
            full_name=data.full_name,
            position=data.position,
            hired_at=data.hired_at,
            department_id=department_id,
        )

    async def full_info_department(
        self, department_id: int, depth: int = 1, include_employees: bool = True
    ):
        self.calls.append(
            ("full_info_department", department_id, depth, include_employees)
        )
        return department_detail(
            department_id=department_id,
            name="Engineering",
            parent_id=None,
        )

    async def reassign_department(self, department_id: int, data):
        self.calls.append(
            ("reassign_department", department_id, data.name, data.parent_id)
        )
        return department_detail(
            department_id=department_id,
            name=data.name or "Engineering",
            parent_id=data.parent_id,
        )

    async def delete_department(
        self, department_id: int, mode: str, reassign_to_id: int | None
    ):
        self.calls.append(("delete_department", department_id, mode, reassign_to_id))


class RaisingDepartmentsService(FakeDepartmentsService):
    async def create_department(self, name: str, parent_id: int | None = None):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A department named 'Engineering' already exists under this parent.",
        )


def department_detail(department_id: int, name: str, parent_id: int | None):
    return SimpleNamespace(
        id=department_id,
        name=name,
        department_id=parent_id,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        safe_employees=[],
        safe_children=[],
    )


@pytest.fixture
def fake_service():
    service = FakeDepartmentsService()
    app.dependency_overrides[department_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.fixture
def client(fake_service):
    return TestClient(app)


def test_create_department_calls_service_and_returns_created_department(
    client, fake_service
):
    response = client.post(
        "/api/v1/departments/",
        json={"name": "Engineering", "department_id": 7},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": 1,
        "name": "Engineering",
        "department_id": 7,
    }
    assert fake_service.calls == [("create_department", "Engineering", 7)]


def test_create_department_returns_service_business_error():
    app.dependency_overrides[department_service] = lambda: RaisingDepartmentsService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/departments/",
        json={"name": "Engineering", "department_id": None},
    )

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == (
        "A department named 'Engineering' already exists under this parent."
    )


def test_create_employee_in_department_calls_service(client, fake_service):
    response = client.post(
        "/api/v1/departments/3/employees/",
        json={
            "full_name": "Ada Lovelace",
            "position": "Engineer",
            "hired_at": "2026-01-15",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": 10,
        "full_name": "Ada Lovelace",
        "position": "Engineer",
        "hired_at": "2026-01-15",
        "department_id": 3,
    }
    assert fake_service.calls == [
        (
            "create_employeer_in_department",
            3,
            "Ada Lovelace",
            "Engineer",
            datetime(2026, 1, 15).date(),
        )
    ]


def test_get_department_details_passes_depth_and_employee_flag(
    client, fake_service
):
    response = client.get(
        "/api/v1/departments/5/",
        params={"depth": 3, "include_employees": "false"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == 5
    assert response.json()["employees"] == []
    assert response.json()["children"] == []
    assert fake_service.calls == [("full_info_department", 5, 3, False)]


def test_get_department_details_rejects_invalid_depth(client, fake_service):
    response = client.get("/api/v1/departments/5/", params={"depth": 6})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert fake_service.calls == []


def test_reassign_department_calls_service(client, fake_service):
    response = client.patch(
        "/api/v1/departments/5/",
        json={"name": "Platform", "parent_id": 2},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Platform"
    assert response.json()["department_id"] == 2
    assert fake_service.calls == [("reassign_department", 5, "Platform", 2)]


def test_delete_reassign_requires_target_department(client, fake_service):
    response = client.delete("/api/v1/departments/5/", params={"mode": "reassign"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == (
        "The 'reassign_to_department_id' parameter is required if the "
        "'reassign' mode is selected."
    )
    assert fake_service.calls == []


def test_delete_reassign_rejects_same_department_target(client, fake_service):
    response = client.delete(
        "/api/v1/departments/5/",
        params={"mode": "reassign", "reassign_to_department_id": 5},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == (
        "Employees cannot be transferred to the same department that is being "
        "eliminated."
    )
    assert fake_service.calls == []


def test_delete_cascade_calls_service(client, fake_service):
    response = client.delete("/api/v1/departments/5/", params={"mode": "cascade"})

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert fake_service.calls == [("delete_department", 5, "cascade", None)]


def test_delete_reassign_calls_service(client, fake_service):
    response = client.delete(
        "/api/v1/departments/5/",
        params={"mode": "reassign", "reassign_to_department_id": 8},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert fake_service.calls == [("delete_department", 5, "reassign", 8)]
