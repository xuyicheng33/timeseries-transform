# API 规范文档

## 字段命名规范

### 模型名称和版本字段

#### 规范说明

| 场景 | 字段名 | 说明 |
|------|--------|------|
| **数据库存储** | `algo_name`, `algo_version` | 内部字段，历史原因保留 |
| **API 请求参数** | `model_name`, `model_version` | 对外统一使用（主要） |
| **API 请求参数** | `algo_name`, `algo_version` | 兼容别名（逐步废弃） |
| **API 响应输出** | `model_name`, `model_version` | 对外统一使用 |
| **查询参数** | `model_name` | 筛选时使用（主要） |
| **查询参数** | `algo_name` | 兼容别名（逐步废弃） |

#### 实现方式（Pydantic v2）

**响应 Schema（输出新字段名）**：
```python
from pydantic import BaseModel, Field, ConfigDict

class ResultResponse(BaseModel):
    id: int
    name: str
    # 数据库字段是 algo_name，但序列化时输出为 model_name
    algo_name: str = Field(..., serialization_alias="model_name")
    algo_version: str = Field(default="", serialization_alias="model_version")
    
    model_config = ConfigDict(
        from_attributes=True,  # 允许从 ORM 对象创建
        populate_by_name=True,  # 允许使用原字段名或别名访问
    )
```

**请求 Schema（接受两种参数）**：
```python
class ResultCreate(BaseModel):
    name: str
    # 主字段名用新的，但通过 validation_alias 兼容旧字段名
    model_name: str = Field(..., validation_alias="algo_name")
    model_version: str = Field(default="", validation_alias="algo_version")
    
    model_config = ConfigDict(
        populate_by_name=True,  # 同时接受 model_name 和 algo_name
    )
```

**查询参数（路由层兼容）**：
```python
@router.get("/results")
async def list_results(
    model_name: Optional[str] = None,  # 新参数名
    algo_name: Optional[str] = None,   # 兼容旧参数名
    db: AsyncSession = Depends(get_db),
):
    # 优先使用新参数，兼容旧参数
    effective_model_name = model_name or algo_name
    if effective_model_name:
        query = query.where(Result.algo_name == effective_model_name)
```

**当前状态**：
- ✅ 后端响应已使用 `serialization_alias` 输出 `model_name`
- ✅ 后端测试已全部通过
- ⚠️ 前端查询参数仍在使用 `algo_name`（需迁移）

---

## 兼容性策略

### 请求参数兼容
- **当前版本（v1.1）**：同时接受 `model_name` 和 `algo_name`
- **下一版本（v1.2，3个月后）**：标记 `algo_name` 为 deprecated
- **未来版本（v2.0，6个月后）**：移除 `algo_name` 支持

### 响应字段统一
- **当前版本（v1.1）**：统一输出 `model_name`
- **不再输出** `algo_name`（通过 `serialization_alias` 实现）

### 前端迁移计划

#### 步骤 1：更新 API 调用
```typescript
// src/api/results.ts
export const getResults = (params: {
  dataset_id?: number
  model_name?: string  // ✅ 使用新字段
  page?: number
  page_size?: number
}) => {
  return request.get<PaginatedResponse<Result>>('/results', { params })
}
```

#### 步骤 2：更新类型定义
```typescript
// src/types/result.ts
export interface Result {
  id: number
  name: string
  model_name: string  // ✅ 使用新字段
  model_version: string
  dataset_id: number
  // ...
}
```

#### 步骤 3：更新组件
```typescript
// 全局搜索替换：algo_name -> model_name
// 保留兼容性处理（如果有旧数据）
const modelName = result.model_name || result.algo_name
```

---

## 验收标准

- [ ] API 文档明确说明字段规范
- [ ] 后端所有响应使用 `model_name`
- [ ] 前端代码不再出现新的 `algo_name` 使用
- [ ] 单元测试覆盖字段映射
- [ ] 兼容性测试通过（旧参数仍可用）

---

## 相关文档

- [权限矩阵](./PERMISSIONS.md)
- [架构文档](./ARCHITECTURE.md)
- [贡献指南](./CONTRIBUTING.md)

---

**文档版本**：v1.0  
**创建日期**：2026-01-26  
**最后更新**：2026-01-26

