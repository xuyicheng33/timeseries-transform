# 数据库迁移指南

本项目使用 Alembic 进行数据库版本管理。

## 常用命令

### 1. 生成迁移脚本

当你修改了 `app/models/models.py` 中的模型后，运行：

```bash
cd backend
alembic revision --autogenerate -m "描述你的修改"
```

例如：
```bash
alembic revision --autogenerate -m "add user table"
alembic revision --autogenerate -m "add user_id to dataset"
```

### 2. 执行迁移

将数据库升级到最新版本：

```bash
alembic upgrade head
```

升级到指定版本：
```bash
alembic upgrade <revision_id>
```

### 3. 回滚迁移

回滚到上一个版本：
```bash
alembic downgrade -1
```

回滚到指定版本：
```bash
alembic downgrade <revision_id>
```

回滚所有迁移：
```bash
alembic downgrade base
```

### 4. 查看迁移状态

查看当前版本：
```bash
alembic current
```

查看迁移历史：
```bash
alembic history
```

查看待执行的迁移：
```bash
alembic history --indicate-current
```

### 5. 生成 SQL 脚本（不执行）

```bash
alembic upgrade head --sql > migration.sql
```

## 注意事项

1. **SQLite 限制**：SQLite 不支持 `ALTER COLUMN`，Alembic 会使用批量模式（创建新表、复制数据、删除旧表）

2. **首次使用**：如果数据库已存在但没有迁移记录，需要先标记当前状态：
   ```bash
   alembic stamp head
   ```

3. **冲突解决**：如果多人同时创建迁移，可能需要手动合并或重新生成

4. **生产环境**：建议先在测试环境验证迁移脚本，再应用到生产环境

## 目录结构

```
migrations/
├── env.py              # Alembic 环境配置
├── script.py.mako      # 迁移脚本模板
├── README.md           # 本文件
└── versions/           # 迁移脚本目录
    ├── 001_initial.py
    ├── 002_add_user.py
    └── ...
```

