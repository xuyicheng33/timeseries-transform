# 权限矩阵文档

## 权限矩阵

### 数据集（Dataset）

| 操作 | 游客 | 普通用户 | 管理员 | 实现位置 |
|------|------|----------|--------|----------|
| 查看列表 | ❌ | ✅ 所有公开 | ✅ 所有 | `datasets.py:list_datasets` |
| 查看详情 | ❌ | ✅ 所有公开 | ✅ 所有 | `datasets.py:get_dataset` |
| 预览数据 | ❌ | ✅ 所有公开 | ✅ 所有 | `datasets.py:preview_dataset` |
| 下载 | ❌ | ✅ 所有公开 | ✅ 所有 | `datasets.py:download_dataset` |
| 上传 | ❌ | ❌ | ✅ | `datasets.py:upload_dataset` |
| 编辑 | ❌ | ❌ | ✅ | `datasets.py:update_dataset` |
| 删除 | ❌ | ❌ | ✅ | `datasets.py:delete_dataset` |

**说明**：
- 数据集默认强制公开（`is_public=True`）
- 由管理员统一管理，避免数据混乱

---

### 结果（Result）

| 操作 | 游客 | 普通用户 | 管理员 | 实现位置 |
|------|------|----------|--------|----------|
| 查看列表 | ❌ | ✅ 所有 | ✅ 所有 | `results.py:list_results` |
| 查看详情 | ❌ | ✅ 所有 | ✅ 所有 | `results.py:get_result` |
| 预览数据 | ❌ | ✅ 所有 | ✅ 所有 | `results.py:preview_result` |
| 下载 | ❌ | ✅ 所有 | ✅ 所有 | `results.py:download_result` |
| 上传 | ❌ | ✅ | ✅ | `results.py:upload_result` |
| 编辑 | ❌ | ✅ 所有者 | ✅ | `results.py:update_result` |
| 删除 | ❌ | ✅ 所有者 | ✅ | `results.py:delete_result` |

**说明**：
- 结果默认对所有登录用户可见（数据集公开）
- 编辑/删除仅限所有者或管理员
- 上传时自动关联当前用户（`user_id=current_user.id`）

---

### 配置（Configuration）

| 操作 | 游客 | 普通用户 | 管理员 | 实现位置 |
|------|------|----------|--------|----------|
| 查看列表 | ❌ | ✅ 所有 | ✅ 所有 | `configurations.py:list_configurations` |
| 查看详情 | ❌ | ✅ 所有 | ✅ 所有 | `configurations.py:get_configuration` |
| 创建 | ❌ | ✅ | ✅ | `configurations.py:create_configuration` |
| 编辑 | ❌ | ✅ 所有者 | ✅ | `configurations.py:update_configuration` |
| 删除 | ❌ | ✅ 所有者 | ✅ | `configurations.py:delete_configuration` |

---

### 实验（Experiment）

| 操作 | 游客 | 普通用户 | 管理员 | 实现位置 |
|------|------|----------|--------|----------|
| 查看列表 | ❌ | ✅ **仅本人** | ✅ **仅本人** | `experiments.py:list_experiments` |
| 查看详情 | ❌ | ✅ 所有者 | ✅ 所有者 | `experiments.py:get_experiment` |
| 创建 | ❌ | ✅ | ✅ | `experiments.py:create_experiment` |
| 编辑 | ❌ | ✅ 所有者 | ✅ 所有者 | `experiments.py:update_experiment` |
| 删除 | ❌ | ✅ 所有者 | ✅ 所有者 | `experiments.py:delete_experiment` |
| 导出 | ❌ | ✅ 所有者 | ✅ 所有者 | `experiments.py:export_experiment` |

**⚠️ 重要说明**：
- **实验默认仅本人可见**（包括管理员）
- 实现：`where Experiment.user_id == current_user.id`
- 这是**私有工作空间**的设计，与数据集/结果的"团队共享"不同
- 如需改为"全员可见"，需修改产品规则和代码

---

### 文件夹（Folder）

| 操作 | 游客 | 普通用户 | 管理员 | 实现位置 |
|------|------|----------|--------|----------|
| 查看 | ❌ | ✅ 所有 | ✅ 所有 | `folders.py:list_folders` |
| 创建 | ❌ | ❌ | ✅ | `folders.py:create_folder` |
| 编辑 | ❌ | ❌ | ✅ | `folders.py:update_folder` |
| 删除 | ❌ | ❌ | ✅ | `folders.py:delete_folder` |
| 排序 | ❌ | ❌ | ✅ | `folders.py:batch_update_sort` |

---

### 模型模板（ModelTemplate）

| 操作 | 游客 | 普通用户 | 管理员 | 实现位置 |
|------|------|----------|--------|----------|
| 查看列表 | ❌ | ✅ 系统+公开 | ✅ 所有 | `model_templates.py:list_templates` |
| 查看详情 | ❌ | ✅ 系统+公开+自己 | ✅ 所有 | `model_templates.py:get_template` |
| 创建 | ❌ | ✅ | ✅ | `model_templates.py:create_template` |
| 编辑 | ❌ | ✅ 所有者 | ✅ | `model_templates.py:update_template` |
| 删除 | ❌ | ✅ 所有者（非系统） | ✅ | `model_templates.py:delete_template` |

**说明**：
- 系统模板（`is_system=True`）不可删除
- 用户可创建私有模板或公开模板

---

## 数据隔离模式

通过环境变量 `ENABLE_DATA_ISOLATION` 控制：

### 模式对比

| 模式 | 配置值 | 数据集可见性 | 结果可见性 | 实验可见性 |
|------|--------|-------------|-----------|-----------|
| **团队共享**（默认） | `false` | 所有公开 | 所有 | 仅本人 |
| **用户隔离** | `true` | 自己+公开 | 自己 | 仅本人 |

### 实现位置

- `app/services/permissions.py:get_isolation_conditions()`
- 根据 `settings.ENABLE_DATA_ISOLATION` 动态添加过滤条件

---

## 权限检查函数

### 核心函数

```python
# app/services/permissions.py

def check_read_access(resource, current_user, resource_type, parent_dataset=None):
    """检查读取权限"""
    
def check_owner_or_admin(resource_user_id, current_user, action_name):
    """检查所有者或管理员权限"""
    
def can_access_result(result, dataset, current_user):
    """检查结果访问权限（考虑数据集公开性）"""
```

### 使用示例

```python
# 检查读取权限
check_read_access(dataset, current_user, ResourceType.DATASET)

# 检查编辑权限
check_owner_or_admin(result.user_id, current_user, "编辑结果")

# 检查结果访问（考虑数据集）
if not can_access_result(result, dataset, current_user):
    raise HTTPException(status_code=403, detail="无权访问")
```

---

## 测试覆盖

### 关键测试用例

- ✅ `test_datasets.py`: 数据集权限（管理员/普通用户）
- ✅ `test_results.py`: 结果权限（所有者/其他用户）
- ✅ `test_auth.py`: 认证和授权
- ✅ `test_folders.py`: 文件夹权限

### 运行测试

```bash
cd backend
pytest tests/ -v -k "permission or access or auth"
```

---

## 变更历史

- **2026-01-26**: 创建权限矩阵文档
- **2026-01-26**: 明确实验为"仅本人可见"

---

## 相关文档

- [API 规范](./API_SPECIFICATION.md)
- [架构文档](./ARCHITECTURE.md)
- [贡献指南](./CONTRIBUTING.md)

