"""
结果 API 单元测试
"""

import pytest
from httpx import AsyncClient

from app.models import Dataset, Result, User


class TestResultList:
    """结果列表测试"""

    @pytest.mark.asyncio
    async def test_list_results_empty(self, client: AsyncClient, auth_headers: dict):
        """测试空列表"""
        response = await client.get("/api/results", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_results_with_data(self, client: AsyncClient, auth_headers: dict, test_result: Result):
        """测试有数据的列表"""
        response = await client.get("/api/results", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Test Result"
        assert data["items"][0]["model_name"] == "TestModel"

    @pytest.mark.asyncio
    async def test_list_results_filter_by_dataset(
        self, client: AsyncClient, auth_headers: dict, test_result: Result, test_dataset: Dataset
    ):
        """测试按数据集筛选"""
        response = await client.get(f"/api/results?dataset_id={test_dataset.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        # 筛选不存在的数据集
        response = await client.get("/api/results?dataset_id=99999", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_list_results_filter_by_model(self, client: AsyncClient, auth_headers: dict, test_result: Result):
        """测试按模型名称筛选"""
        # 对外推荐使用 model_name 作为查询参数（algo_name 仍兼容）
        response = await client.get("/api/results?model_name=TestModel", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        # 筛选不存在的模型
        response = await client.get("/api/results?model_name=NonExistent", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0


class TestResultGet:
    """获取单个结果测试"""

    @pytest.mark.asyncio
    async def test_get_result_success(self, client: AsyncClient, auth_headers: dict, test_result: Result):
        """测试获取结果"""
        response = await client.get(f"/api/results/{test_result.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_result.id
        assert data["name"] == "Test Result"
        assert data["model_name"] == "TestModel"
        assert data["metrics"]["mse"] == 0.001
        assert data["metrics"]["r2"] == 0.95

    @pytest.mark.asyncio
    async def test_get_result_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试结果不存在"""
        response = await client.get("/api/results/99999", headers=auth_headers)

        assert response.status_code == 404


class TestResultUpload:
    """结果上传测试"""

    @pytest.mark.asyncio
    async def test_upload_result_success(
        self, client: AsyncClient, auth_headers: dict, test_dataset: Dataset, temp_result_csv: str
    ):
        """测试上传结果"""
        with open(temp_result_csv, "rb") as f:
            response = await client.post(
                "/api/results/upload",
                headers=auth_headers,
                files={"file": ("result.csv", f, "text/csv")},
                data={
                    "name": "Uploaded Result",
                    "dataset_id": str(test_dataset.id),
                    "model_name": "UploadedModel",
                    "model_version": "1.0.0",
                    "description": "Test upload",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Uploaded Result"
        assert data["model_name"] == "UploadedModel"
        assert data["model_version"] == "1.0.0"
        # 应该自动计算指标
        assert "metrics" in data
        assert "mse" in data["metrics"]
        assert "rmse" in data["metrics"]
        assert "mae" in data["metrics"]
        assert "r2" in data["metrics"]
        assert "mape" in data["metrics"]

    @pytest.mark.asyncio
    async def test_upload_result_missing_columns(
        self, client: AsyncClient, auth_headers: dict, test_dataset: Dataset, temp_csv_file: str
    ):
        """测试缺少必需列"""
        # temp_csv_file 没有 true_value 和 predicted_value 列
        with open(temp_csv_file, "rb") as f:
            response = await client.post(
                "/api/results/upload",
                headers=auth_headers,
                files={"file": ("result.csv", f, "text/csv")},
                data={"name": "Invalid Result", "dataset_id": str(test_dataset.id), "model_name": "TestModel"},
            )

        assert response.status_code == 400
        assert (
            "true_value" in response.json()["detail"].lower() or "predicted_value" in response.json()["detail"].lower()
        )

    @pytest.mark.asyncio
    async def test_upload_result_invalid_dataset(self, client: AsyncClient, auth_headers: dict, temp_result_csv: str):
        """测试无效数据集 ID"""
        with open(temp_result_csv, "rb") as f:
            response = await client.post(
                "/api/results/upload",
                headers=auth_headers,
                files={"file": ("result.csv", f, "text/csv")},
                data={"name": "Invalid Dataset Result", "dataset_id": "99999", "model_name": "TestModel"},
            )

        assert response.status_code == 404


class TestResultUpdate:
    """结果更新测试"""

    @pytest.mark.asyncio
    async def test_update_result_success(self, client: AsyncClient, auth_headers: dict, test_result: Result):
        """测试更新结果"""
        response = await client.put(
            f"/api/results/{test_result.id}",
            headers=auth_headers,
            json={"name": "Updated Result", "model_name": "UpdatedModel", "description": "Updated description"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Result"
        assert data["model_name"] == "UpdatedModel"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_result_partial(self, client: AsyncClient, auth_headers: dict, test_result: Result):
        """测试部分更新"""
        response = await client.put(
            f"/api/results/{test_result.id}", headers=auth_headers, json={"description": "Only description"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Result"  # 未变
        assert data["description"] == "Only description"

    @pytest.mark.asyncio
    async def test_update_result_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试更新不存在的结果"""
        response = await client.put("/api/results/99999", headers=auth_headers, json={"name": "New Name"})

        assert response.status_code == 404


class TestResultDelete:
    """结果删除测试"""

    @pytest.mark.asyncio
    async def test_delete_result_success(self, client: AsyncClient, auth_headers: dict, test_result: Result):
        """测试删除结果"""
        response = await client.delete(f"/api/results/{test_result.id}", headers=auth_headers)

        assert response.status_code == 200

        # 验证已删除
        get_response = await client.get(f"/api/results/{test_result.id}", headers=auth_headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_result_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试删除不存在的结果"""
        response = await client.delete("/api/results/99999", headers=auth_headers)

        assert response.status_code == 404


class TestResultMetrics:
    """结果指标测试"""

    @pytest.mark.asyncio
    async def test_get_metrics(self, client: AsyncClient, auth_headers: dict, test_result: Result):
        """测试获取指标"""
        response = await client.get(f"/api/results/{test_result.id}", headers=auth_headers)

        assert response.status_code == 200
        metrics = response.json()["metrics"]

        assert "mse" in metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert "r2" in metrics
        assert "mape" in metrics

        # 验证指标值
        assert metrics["mse"] == 0.001
        assert metrics["r2"] == 0.95


class TestResultModelNames:
    """模型名称列表测试"""

    @pytest.mark.asyncio
    async def test_get_model_names(self, client: AsyncClient, auth_headers: dict, test_result: Result):
        """测试获取模型名称列表"""
        response = await client.get("/api/results/model-names", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "TestModel" in data

    @pytest.mark.asyncio
    async def test_get_model_names_by_dataset(
        self, client: AsyncClient, auth_headers: dict, test_result: Result, test_dataset: Dataset
    ):
        """测试按数据集获取模型名称"""
        response = await client.get(f"/api/results/model-names?dataset_id={test_dataset.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "TestModel" in data


class TestResultPermissions:
    """结果权限测试"""

    @pytest.mark.asyncio
    async def test_access_own_result(self, client: AsyncClient, auth_headers: dict, test_result: Result):
        """测试访问自己的结果"""
        response = await client.get(f"/api/results/{test_result.id}", headers=auth_headers)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_access_other_user_result(self, client: AsyncClient, test_result: Result, test_session):
        """测试访问其他用户的结果"""
        from app.services.auth import get_password_hash

        # 创建另一个用户
        other_user = User(
            username="otheruser2",
            email="other2@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
        )
        test_session.add(other_user)
        await test_session.commit()

        # 登录另一个用户
        login_response = await client.post(
            "/api/auth/login", data={"username": "otheruser2", "password": "password123"}
        )
        other_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # 数据集/结果默认对所有登录用户可见（数据集强制公开）
        response = await client.get(f"/api/results/{test_result.id}", headers=other_headers)

        assert response.status_code == 200
