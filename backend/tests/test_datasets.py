"""
数据集 API 单元测试
"""
import pytest
from httpx import AsyncClient

from app.models import User, Dataset


class TestDatasetList:
    """数据集列表测试"""
    
    @pytest.mark.asyncio
    async def test_list_datasets_empty(self, client: AsyncClient, auth_headers: dict):
        """测试空列表"""
        response = await client.get("/api/datasets", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_list_datasets_with_data(self, client: AsyncClient, auth_headers: dict, test_dataset: Dataset):
        """测试有数据的列表"""
        response = await client.get("/api/datasets", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Test Dataset"
    
    @pytest.mark.asyncio
    async def test_list_datasets_pagination(self, client: AsyncClient, auth_headers: dict, test_session, test_user: User):
        """测试分页"""
        # 创建多个数据集
        for i in range(15):
            dataset = Dataset(
                name=f"Dataset {i}",
                filename=f"data_{i}.csv",
                filepath=f"/tmp/data_{i}.csv",
                file_size=1024,
                row_count=100,
                column_count=5,
                columns=["col1", "col2", "col3", "col4", "col5"],
                user_id=test_user.id
            )
            test_session.add(dataset)
        await test_session.commit()
        
        # 测试第一页
        response = await client.get("/api/datasets?page=1&page_size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 15
        assert len(data["items"]) == 10
        assert data["page"] == 1
        
        # 测试第二页
        response = await client.get("/api/datasets?page=2&page_size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["page"] == 2
    
    @pytest.mark.asyncio
    async def test_list_datasets_unauthorized(self, client: AsyncClient):
        """测试未认证访问"""
        response = await client.get("/api/datasets")
        
        assert response.status_code == 401


class TestDatasetGet:
    """获取单个数据集测试"""
    
    @pytest.mark.asyncio
    async def test_get_dataset_success(self, client: AsyncClient, auth_headers: dict, test_dataset: Dataset):
        """测试获取数据集"""
        response = await client.get(f"/api/datasets/{test_dataset.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_dataset.id
        assert data["name"] == "Test Dataset"
        assert data["row_count"] == 100
        assert data["column_count"] == 5
    
    @pytest.mark.asyncio
    async def test_get_dataset_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试数据集不存在"""
        response = await client.get("/api/datasets/99999", headers=auth_headers)
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_dataset_no_permission(self, client: AsyncClient, test_dataset: Dataset, test_session, admin_auth_headers: dict):
        """测试无权限访问（非公开数据集）"""
        # admin_user 尝试访问 test_user 的私有数据集
        # 注意：管理员可能有权限，这里测试普通用户
        # 创建另一个用户
        from app.services.auth import get_password_hash
        other_user = User(
            username="otheruser",
            email="other@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True
        )
        test_session.add(other_user)
        await test_session.commit()
        
        # 登录另一个用户
        login_response = await client.post("/api/auth/login", data={
            "username": "otheruser",
            "password": "password123"
        })
        other_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        
        # 尝试访问
        response = await client.get(f"/api/datasets/{test_dataset.id}", headers=other_headers)
        
        assert response.status_code == 403


class TestDatasetUpload:
    """数据集上传测试"""
    
    @pytest.mark.asyncio
    async def test_upload_dataset_success(self, client: AsyncClient, auth_headers: dict, temp_csv_file: str):
        """测试上传数据集"""
        with open(temp_csv_file, 'rb') as f:
            response = await client.post(
                "/api/datasets/upload",
                headers=auth_headers,
                files={"file": ("test.csv", f, "text/csv")},
                data={"name": "Uploaded Dataset", "description": "Test upload"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Uploaded Dataset"
        assert data["description"] == "Test upload"
        assert data["row_count"] == 100
        assert data["column_count"] == 3
    
    @pytest.mark.asyncio
    async def test_upload_dataset_no_file(self, client: AsyncClient, auth_headers: dict):
        """测试未提供文件"""
        response = await client.post(
            "/api/datasets/upload",
            headers=auth_headers,
            data={"name": "No File Dataset"}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_upload_dataset_invalid_type(self, client: AsyncClient, auth_headers: dict):
        """测试无效文件类型"""
        response = await client.post(
            "/api/datasets/upload",
            headers=auth_headers,
            files={"file": ("test.txt", b"not a csv", "text/plain")},
            data={"name": "Invalid File"}
        )
        
        assert response.status_code == 400


class TestDatasetUpdate:
    """数据集更新测试"""
    
    @pytest.mark.asyncio
    async def test_update_dataset_success(self, client: AsyncClient, auth_headers: dict, test_dataset: Dataset):
        """测试更新数据集"""
        response = await client.put(
            f"/api/datasets/{test_dataset.id}",
            headers=auth_headers,
            json={"name": "Updated Name", "description": "Updated description"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
    
    @pytest.mark.asyncio
    async def test_update_dataset_partial(self, client: AsyncClient, auth_headers: dict, test_dataset: Dataset):
        """测试部分更新"""
        response = await client.put(
            f"/api/datasets/{test_dataset.id}",
            headers=auth_headers,
            json={"description": "Only description updated"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Dataset"  # 未变
        assert data["description"] == "Only description updated"
    
    @pytest.mark.asyncio
    async def test_update_dataset_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试更新不存在的数据集"""
        response = await client.put(
            "/api/datasets/99999",
            headers=auth_headers,
            json={"name": "New Name"}
        )
        
        assert response.status_code == 404


class TestDatasetDelete:
    """数据集删除测试"""
    
    @pytest.mark.asyncio
    async def test_delete_dataset_success(self, client: AsyncClient, auth_headers: dict, test_dataset: Dataset):
        """测试删除数据集"""
        response = await client.delete(f"/api/datasets/{test_dataset.id}", headers=auth_headers)
        
        assert response.status_code == 200
        
        # 验证已删除
        get_response = await client.get(f"/api/datasets/{test_dataset.id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_dataset_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试删除不存在的数据集"""
        response = await client.delete("/api/datasets/99999", headers=auth_headers)
        
        assert response.status_code == 404


class TestDatasetPreview:
    """数据集预览测试"""
    
    @pytest.mark.asyncio
    async def test_preview_dataset(self, client: AsyncClient, auth_headers: dict, test_dataset: Dataset, temp_csv_file: str):
        """测试预览数据集"""
        # 先上传一个真实的数据集
        with open(temp_csv_file, 'rb') as f:
            upload_response = await client.post(
                "/api/datasets/upload",
                headers=auth_headers,
                files={"file": ("test.csv", f, "text/csv")},
                data={"name": "Preview Test"}
            )
        
        dataset_id = upload_response.json()["id"]
        
        # 预览
        response = await client.get(
            f"/api/datasets/{dataset_id}/preview?rows=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "columns" in data
        assert "data" in data
        assert len(data["data"]) <= 10


class TestDatasetPublic:
    """数据集公开/私有测试"""
    
    @pytest.mark.asyncio
    async def test_make_dataset_public(self, client: AsyncClient, auth_headers: dict, test_dataset: Dataset):
        """测试设置数据集为公开"""
        response = await client.put(
            f"/api/datasets/{test_dataset.id}",
            headers=auth_headers,
            json={"is_public": True}
        )
        
        assert response.status_code == 200
        assert response.json()["is_public"] == True
    
    @pytest.mark.asyncio
    async def test_access_public_dataset(self, client: AsyncClient, test_dataset: Dataset, test_session, auth_headers: dict):
        """测试其他用户访问公开数据集"""
        # 先设置为公开
        await client.put(
            f"/api/datasets/{test_dataset.id}",
            headers=auth_headers,
            json={"is_public": True}
        )
        
        # 创建另一个用户
        from app.services.auth import get_password_hash
        other_user = User(
            username="publicuser",
            email="public@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True
        )
        test_session.add(other_user)
        await test_session.commit()
        
        # 登录另一个用户
        login_response = await client.post("/api/auth/login", data={
            "username": "publicuser",
            "password": "password123"
        })
        other_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        
        # 访问公开数据集
        response = await client.get(f"/api/datasets/{test_dataset.id}", headers=other_headers)
        
        assert response.status_code == 200

