"""
统一权限检查模块

将 datasets/configurations/results/visualization 中分散的权限检查逻辑
抽取到此模块，便于维护和后续扩展（如添加组织/项目/角色等）。

使用方式：
    from app.services.permissions import (
        check_read_access, check_write_access, check_dataset_write_access,
        check_owner_or_admin,  # 新增：严格的所有者或管理员检查
        build_dataset_query, build_result_query, build_config_query,
        get_isolation_conditions, can_access_result
    )

权限模型：
    - 团队共享模式 (ENABLE_DATA_ISOLATION=False)：所有登录用户可读，所有者/管理员可写
    - 用户隔离模式 (ENABLE_DATA_ISOLATION=True)：只能访问自己的或公开的资源

新增权限规则（2025-01更新）：
    - 数据集：仅管理员可上传/编辑/删除
    - 配置/结果/模型模板：本人或管理员可编辑/删除（user_id=NULL 时仅管理员可写）
"""

from typing import Any, TypeVar

from fastapi import HTTPException
from sqlalchemy import or_, select

from app.config import settings
from app.models import Configuration, Dataset, Result, User

# 泛型类型，用于类型提示
T = TypeVar("T")


class ResourceType:
    """资源类型常量"""

    DATASET = "数据集"
    RESULT = "结果"
    CONFIGURATION = "配置"


class ActionType:
    """操作类型常量"""

    READ = "访问"
    PREVIEW = "预览"
    DOWNLOAD = "下载"
    WRITE = "修改"
    DELETE = "删除"
    CREATE = "创建"


def is_owner(resource, user: User) -> bool:
    """检查用户是否是资源的所有者"""
    if hasattr(resource, "user_id"):
        return resource.user_id == user.id
    return False


def is_public(resource) -> bool:
    """检查资源是否公开"""
    if hasattr(resource, "is_public"):
        return resource.is_public
    return False


def check_owner_or_admin(resource_user_id: int | None, current_user: User, resource_name: str = "资源") -> None:
    """
    严格的所有者或管理员权限检查

    用于：结果/配置/模型模板的编辑和删除操作

    权限规则：
    - 管理员：可操作任意资源
    - 资源所有者：可操作自己的资源
    - user_id=NULL：仅管理员可操作（历史数据或用户已删除）

    注意：此函数不考虑 parent_dataset 的权限，是"严格"的所有者检查

    Args:
        resource_user_id: 资源的 user_id（可能为 None）
        current_user: 当前登录用户
        resource_name: 资源名称（用于错误提示）

    Raises:
        HTTPException 403: 非本人且非管理员
    """
    # 管理员有所有权限
    if current_user.is_admin:
        return

    # user_id 为 NULL 时，仅管理员可操作
    if resource_user_id is None:
        raise HTTPException(status_code=403, detail=f"此{resource_name}的所有者未知，仅管理员可操作")

    # 检查是否为本人
    if resource_user_id == current_user.id:
        return

    # 非本人且非管理员
    raise HTTPException(status_code=403, detail=f"只能操作自己的{resource_name}，或需要管理员权限")


def check_read_access(resource, user: User, resource_type: str = "资源", parent_dataset: Dataset | None = None) -> None:
    """
    检查用户对资源的读取权限

    读取操作包括：访问、预览、下载

    权限规则：
    - 管理员：可访问所有资源
    - 团队共享模式：所有登录用户可访问
    - 用户隔离模式：
        - 可访问自己的资源
        - 可访问公开的资源
        - 可访问自己数据集下的资源（如结果、配置）

    Args:
        resource: 要检查的资源对象
        user: 当前登录用户
        resource_type: 资源类型名称（用于错误提示）
        parent_dataset: 父数据集（用于检查结果/配置的权限）

    Raises:
        HTTPException: 无权限时抛出 403
    """
    # 管理员有所有权限
    if user.is_admin:
        return

    # 团队共享模式：所有登录用户可访问
    if not settings.ENABLE_DATA_ISOLATION:
        return

    # 用户隔离模式下的读取权限检查

    # 1. 资源所有者可以访问
    if is_owner(resource, user):
        return

    # 2. 公开资源允许登录用户访问
    if is_public(resource):
        return

    # 3. 对于结果/配置，检查父数据集的权限
    if parent_dataset is not None:
        # 父数据集所有者可以访问
        if is_owner(parent_dataset, user):
            return
        # 父数据集公开时允许访问
        if is_public(parent_dataset):
            return

    raise HTTPException(status_code=403, detail=f"无权访问此{resource_type}")


def check_write_access(
    resource,
    user: User,
    action: str = ActionType.WRITE,
    resource_type: str = "资源",
    parent_dataset: Dataset | None = None,
) -> None:
    """
    检查用户对资源的写入权限

    写入操作包括：修改、删除

    权限规则（无论是否开启数据隔离）：
    - 管理员：可操作所有资源
    - 资源所有者：可操作自己的资源
    - 父数据集所有者：可操作其数据集下的资源（如结果、配置）

    Args:
        resource: 要检查的资源对象
        user: 当前登录用户
        action: 操作类型（用于错误提示）
        resource_type: 资源类型名称（用于错误提示）
        parent_dataset: 父数据集（用于检查结果/配置的权限）

    Raises:
        HTTPException: 无权限时抛出 403
    """
    # 管理员有所有权限
    if user.is_admin:
        return

    # 资源所有者可以操作
    if is_owner(resource, user):
        return

    # 对于结果/配置，父数据集所有者也可以操作
    if parent_dataset is not None and is_owner(parent_dataset, user):
        return

    # 根据是否有父数据集生成不同的错误信息
    if parent_dataset is not None:
        raise HTTPException(
            status_code=403, detail=f"无权{action}此{resource_type}，只有{resource_type}所有者或数据集所有者可以操作"
        )
    else:
        raise HTTPException(status_code=403, detail=f"无权{action}此{resource_type}，只有{resource_type}所有者可以操作")


def check_dataset_write_access(dataset: Dataset, user: User, action: str = "写入") -> None:
    """
    检查用户是否有权向数据集写入（上传结果、创建配置等）

    无论是否开启数据隔离，写入操作都只允许：
    - 数据集所有者
    - 管理员

    Args:
        dataset: 数据集对象
        user: 当前登录用户
        action: 操作描述（用于错误提示）

    Raises:
        HTTPException: 无权限时抛出 403
    """
    # 管理员有所有权限
    if user.is_admin:
        return

    # 只有数据集所有者可以写入
    if is_owner(dataset, user):
        return

    raise HTTPException(status_code=403, detail=f"无权向此数据集{action}，只有数据集所有者可以操作")


def build_dataset_query(user: User, base_query=None):
    """
    构建数据集查询，根据数据隔离配置过滤

    Args:
        user: 当前登录用户
        base_query: 基础查询（可选）

    Returns:
        过滤后的查询
    """
    if base_query is None:
        base_query = select(Dataset)

    if settings.ENABLE_DATA_ISOLATION:
        if not user.is_admin:
            # 普通用户只能看到自己的数据或公开数据
            base_query = base_query.where(or_(Dataset.user_id == user.id, Dataset.is_public.is_(True)))
        # 管理员不做过滤
    # 团队共享模式：不过滤

    return base_query


def build_result_query(user: User, base_query=None):
    """
    构建结果查询，根据数据隔离配置过滤

    Args:
        user: 当前登录用户
        base_query: 基础查询（可选）

    Returns:
        过滤后的查询（需要 join Dataset）
    """
    if base_query is None:
        base_query = select(Result)

    if settings.ENABLE_DATA_ISOLATION:
        if not user.is_admin:
            # 普通用户只能看到自己的结果、自己数据集的结果、或公开数据集的结果
            base_query = base_query.join(Dataset).where(
                or_(Result.user_id == user.id, Dataset.user_id == user.id, Dataset.is_public.is_(True))
            )
        # 管理员不做过滤

    return base_query


def build_config_query(user: User, base_query=None):
    """
    构建配置查询，根据数据隔离配置过滤

    Args:
        user: 当前登录用户
        base_query: 基础查询（可选）

    Returns:
        过滤后的查询（需要 join Dataset）
    """
    if base_query is None:
        base_query = select(Configuration)

    if settings.ENABLE_DATA_ISOLATION:
        if not user.is_admin:
            # 普通用户只能看到自己的数据集或公开数据集的配置
            base_query = base_query.join(Dataset).where(or_(Dataset.user_id == user.id, Dataset.is_public.is_(True)))
        # 管理员不做过滤

    return base_query


def get_isolation_conditions(user: User, model_class: type[T]) -> tuple[list[Any], bool]:
    """
    获取数据隔离的查询条件列表

    用于需要手动构建查询的场景（如分页查询）

    Args:
        user: 当前登录用户
        model_class: 模型类（Dataset, Result, Configuration）

    Returns:
        (conditions: list, need_join: bool) - 条件列表和是否需要 join Dataset
    """
    conditions: list[Any] = []
    need_join = False

    if not settings.ENABLE_DATA_ISOLATION:
        return conditions, need_join

    if user.is_admin:
        return conditions, need_join

    if model_class == Dataset:
        conditions.append(or_(Dataset.user_id == user.id, Dataset.is_public.is_(True)))
    elif model_class == Result:
        need_join = True
        conditions.append(or_(Result.user_id == user.id, Dataset.user_id == user.id, Dataset.is_public.is_(True)))
    elif model_class == Configuration:
        need_join = True
        conditions.append(or_(Dataset.user_id == user.id, Dataset.is_public.is_(True)))

    return conditions, need_join


def can_access_result(result: Result, dataset: Dataset | None, user: User) -> bool:
    """
    检查用户是否有权访问结果（返回布尔值，不抛异常）

    用于批量检查场景（如可视化对比）

    Args:
        result: 结果对象
        dataset: 关联的数据集（可选）
        user: 当前登录用户

    Returns:
        True 表示有权访问，False 表示无权
    """
    if not settings.ENABLE_DATA_ISOLATION:
        return True

    # 公开数据集的结果允许登录用户访问
    if dataset and is_public(dataset):
        return True

    if user.is_admin:
        return True

    if is_owner(result, user):
        return True

    if dataset and is_owner(dataset, user):
        return True

    return False
