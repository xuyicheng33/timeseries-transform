"""
认证 API 单元测试
"""

import pytest
from httpx import AsyncClient

from app.models import User


class TestAuthRegister:
    """用户注册测试"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """测试正常注册"""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User",
            },
        )

        assert response.status_code == 201  # 注册成功返回 201 Created
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "hashed_password" not in data  # 不应返回密码

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, test_user: User):
        """测试重复用户名"""
        response = await client.post(
            "/api/auth/register",
            json={"username": "testuser", "email": "another@example.com", "password": "password123"},  # 已存在
        )

        assert response.status_code == 400
        assert "用户名已存在" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        """测试重复邮箱"""
        response = await client.post(
            "/api/auth/register",
            json={"username": "anotheruser", "email": "test@example.com", "password": "password123"},  # 已存在
        )

        assert response.status_code == 400
        assert "邮箱已被注册" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """测试无效邮箱格式"""
        response = await client.post(
            "/api/auth/register", json={"username": "newuser", "email": "invalid-email", "password": "password123"}
        )

        # 使用 EmailStr 校验后返回 422
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        """测试密码太短"""
        response = await client.post(
            "/api/auth/register",
            json={"username": "newuser", "email": "newuser@example.com", "password": "123"},  # 太短
        )

        assert response.status_code == 422


class TestAuthLogin:
    """用户登录测试"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """测试正常登录"""
        response = await client.post("/api/auth/login", data={"username": "testuser", "password": "testpassword123"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """测试密码错误"""
        response = await client.post("/api/auth/login", data={"username": "testuser", "password": "wrongpassword"})

        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """测试用户不存在"""
        response = await client.post("/api/auth/login", data={"username": "nonexistent", "password": "password123"})

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_with_email(self, client: AsyncClient, test_user: User):
        """测试使用邮箱登录"""
        response = await client.post(
            "/api/auth/login", data={"username": "test@example.com", "password": "testpassword123"}  # 使用邮箱
        )

        assert response.status_code == 200
        assert "access_token" in response.json()


class TestAuthMe:
    """获取当前用户信息测试"""

    @pytest.mark.asyncio
    async def test_get_me_success(self, client: AsyncClient, auth_headers: dict):
        """测试获取当前用户信息"""
        response = await client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, client: AsyncClient):
        """测试未认证访问"""
        response = await client.get("/api/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_invalid_token(self, client: AsyncClient):
        """测试无效 token"""
        response = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_token"})

        assert response.status_code == 401


class TestAuthRefresh:
    """Token 刷新测试"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, test_user: User):
        """测试刷新 token"""
        # 先登录获取 refresh_token
        login_response = await client.post(
            "/api/auth/login", data={"username": "testuser", "password": "testpassword123"}
        )
        refresh_token = login_response.json()["refresh_token"]

        # 刷新 token
        response = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """测试无效 refresh_token"""
        response = await client.post("/api/auth/refresh", json={"refresh_token": "invalid_refresh_token"})

        assert response.status_code == 401


class TestAuthUpdateProfile:
    """更新用户信息测试"""

    @pytest.mark.asyncio
    async def test_update_profile_success(self, client: AsyncClient, auth_headers: dict):
        """测试更新用户信息"""
        response = await client.put("/api/auth/me", headers=auth_headers, json={"full_name": "Updated Name"})

        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_profile_unauthorized(self, client: AsyncClient):
        """测试未认证更新"""
        response = await client.put("/api/auth/me", json={"full_name": "Updated Name"})

        assert response.status_code == 401


class TestAuthChangePassword:
    """修改密码测试"""

    @pytest.mark.asyncio
    async def test_change_password_success(self, client: AsyncClient, auth_headers: dict):
        """测试修改密码"""
        # 正确的接口是 PUT /api/auth/me/password
        response = await client.put(
            "/api/auth/me/password",
            headers=auth_headers,
            json={"old_password": "testpassword123", "new_password": "newpassword456"},
        )

        assert response.status_code == 200

        # 验证新密码可以登录
        login_response = await client.post(
            "/api/auth/login", data={"username": "testuser", "password": "newpassword456"}
        )
        assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, client: AsyncClient, auth_headers: dict):
        """测试当前密码错误"""
        response = await client.put(
            "/api/auth/me/password",
            headers=auth_headers,
            json={"old_password": "wrongpassword", "new_password": "newpassword456"},
        )

        assert response.status_code == 400
        assert "原密码错误" in response.json()["detail"]
