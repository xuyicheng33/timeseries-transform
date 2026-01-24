import pytest
from httpx import AsyncClient

from app.models import Dataset


class TestFolderAPI:
    @pytest.mark.asyncio
    async def test_create_folder_forbidden_for_normal_user(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.post(
            "/api/folders",
            json={"name": "Root", "description": "", "parent_id": None},
            headers=auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_root_folder_success(self, client: AsyncClient, admin_auth_headers: dict):
        response = await client.post(
            "/api/folders",
            json={"name": "Root", "description": "Root folder", "parent_id": None},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Root"
        assert data["parent_id"] is None
        assert data["description"] == "Root folder"

    @pytest.mark.asyncio
    async def test_folder_description_allows_newlines_and_tabs(
        self, client: AsyncClient, admin_auth_headers: dict
    ):
        description = "Line1\n\tLine2"
        response = await client.post(
            "/api/folders",
            json={"name": "Root", "description": description, "parent_id": None},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["description"] == description

    @pytest.mark.asyncio
    async def test_create_subfolder_success(self, client: AsyncClient, admin_auth_headers: dict):
        root_resp = await client.post(
            "/api/folders",
            json={"name": "Root", "description": "", "parent_id": None},
            headers=admin_auth_headers,
        )
        assert root_resp.status_code == 200
        root_id = root_resp.json()["id"]

        child_resp = await client.post(
            "/api/folders",
            json={"name": "Child", "description": "", "parent_id": root_id},
            headers=admin_auth_headers,
        )
        assert child_resp.status_code == 200
        data = child_resp.json()
        assert data["name"] == "Child"
        assert data["parent_id"] == root_id

    @pytest.mark.asyncio
    async def test_create_third_level_folder_rejected(self, client: AsyncClient, admin_auth_headers: dict):
        root_resp = await client.post(
            "/api/folders",
            json={"name": "Root", "description": "", "parent_id": None},
            headers=admin_auth_headers,
        )
        assert root_resp.status_code == 200
        root_id = root_resp.json()["id"]

        child_resp = await client.post(
            "/api/folders",
            json={"name": "Child", "description": "", "parent_id": root_id},
            headers=admin_auth_headers,
        )
        assert child_resp.status_code == 200
        child_id = child_resp.json()["id"]

        grandchild_resp = await client.post(
            "/api/folders",
            json={"name": "Grandchild", "description": "", "parent_id": child_id},
            headers=admin_auth_headers,
        )
        assert grandchild_resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_folders_contains_two_levels(self, client: AsyncClient, admin_auth_headers: dict):
        root_resp = await client.post(
            "/api/folders",
            json={"name": "Root", "description": "", "parent_id": None},
            headers=admin_auth_headers,
        )
        assert root_resp.status_code == 200
        root_id = root_resp.json()["id"]

        child_resp = await client.post(
            "/api/folders",
            json={"name": "Child", "description": "", "parent_id": root_id},
            headers=admin_auth_headers,
        )
        assert child_resp.status_code == 200
        child_id = child_resp.json()["id"]

        list_resp = await client.get("/api/folders", headers=admin_auth_headers)
        assert list_resp.status_code == 200
        data = list_resp.json()
        ids = {item["id"] for item in data["items"]}
        assert root_id in ids
        assert child_id in ids

    @pytest.mark.asyncio
    async def test_folder_dataset_count_and_subfolder_folder_id_supported(
        self, client: AsyncClient, admin_auth_headers: dict, admin_dataset: Dataset
    ):
        root_resp = await client.post(
            "/api/folders",
            json={"name": "Root", "description": "", "parent_id": None},
            headers=admin_auth_headers,
        )
        assert root_resp.status_code == 200
        root_id = root_resp.json()["id"]

        child_resp = await client.post(
            "/api/folders",
            json={"name": "Child", "description": "", "parent_id": root_id},
            headers=admin_auth_headers,
        )
        assert child_resp.status_code == 200
        child_id = child_resp.json()["id"]

        move_resp = await client.post(
            "/api/datasets/batch-move",
            json={"dataset_ids": [admin_dataset.id], "folder_id": child_id},
            headers=admin_auth_headers,
        )
        assert move_resp.status_code == 200

        list_folders_resp = await client.get("/api/folders", headers=admin_auth_headers)
        assert list_folders_resp.status_code == 200
        folders = list_folders_resp.json()["items"]
        folder_counts = {folder["id"]: folder["dataset_count"] for folder in folders}
        assert folder_counts[root_id] == 0
        assert folder_counts[child_id] == 1
        assert list_folders_resp.json()["root_dataset_count"] == 0

        list_datasets_resp = await client.get(
            f"/api/datasets?folder_id={child_id}", headers=admin_auth_headers
        )
        assert list_datasets_resp.status_code == 200
        dataset_items = list_datasets_resp.json()["items"]
        assert len(dataset_items) == 1
        assert dataset_items[0]["id"] == admin_dataset.id

    @pytest.mark.asyncio
    async def test_reorder_folders_route_and_sort_order_persisted(
        self, client: AsyncClient, admin_auth_headers: dict
    ):
        first_resp = await client.post(
            "/api/folders",
            json={"name": "First", "description": "", "parent_id": None},
            headers=admin_auth_headers,
        )
        assert first_resp.status_code == 200
        first_id = first_resp.json()["id"]

        second_resp = await client.post(
            "/api/folders",
            json={"name": "Second", "description": "", "parent_id": None},
            headers=admin_auth_headers,
        )
        assert second_resp.status_code == 200
        second_id = second_resp.json()["id"]

        reorder_resp = await client.put(
            "/api/folders/reorder",
            json={
                "orders": [
                    {"id": first_id, "sort_order": 1},
                    {"id": second_id, "sort_order": 0},
                ]
            },
            headers=admin_auth_headers,
        )
        assert reorder_resp.status_code == 200

        list_resp = await client.get(
            "/api/folders?sort_by=manual&order=asc", headers=admin_auth_headers
        )
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        root_ids = [item["id"] for item in items if item["parent_id"] is None]
        assert root_ids.index(second_id) < root_ids.index(first_id)
