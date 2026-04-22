# Phase 10: SQLite 持久化存储 - 需求文档

## As Is (当前状态)
- 项目使用 GistStorage (GitHub Gist) 作为主要存储
- 有 LocalStorage (JSON文件) 作为备用
- 无结构化数据库支持，无法进行复杂查询

## To Be (期望状态)
- 新增 SQLiteStorage 实现，支持结构化存储
- 支持 SQL 查询、索引、事务
- 向后兼容现有 GistStorage/LocalStorage
- 支持数据迁移 (JSON → SQLite)

---

## Requirements (功能需求)

### R1: SQLiteStorage 实现
- [x] 实现 BaseStorage 接口
- [x] 支持 ideas 表 (id, content, tags, status, quick_assessment, deep_assessment, created_at, updated_at)
- [x] 支持 tasks 表 (id, idea_id, content, status, priority, progress, created_at, updated_at)
- [x] 支持 activities 表 (id, type, content, timestamp)

### R2: 数据迁移
- [x] 提供 migrate_from_json(from_dir: str) 方法
- [x] 提供 migrate_from_gist(token: str, gist_id: str) 方法
- [x] 迁移过程有进度反馈

### R3: 高级查询
- [x] 按状态查询想法
- [x] 按标签查询想法
- [x] 按时间范围查询
- [x] 支持分页查询

### R4: 向后兼容
- [x] get_storage() 函数保持现有签名
- [x] 支持通过环境变量配置存储类型
- [x] GistStorage 和 LocalStorage 不受影响

### R5: 测试覆盖
- [x] 单元测试: SQLiteStorage CRUD 操作
- [x] 单元测试: 数据迁移
- [x] 集成测试: 与 IdeaManager 配合

---

## Acceptance Criteria (验收标准)

1. **存储创建**: `SQLiteStorage("data/po_agent.db")` 能成功创建数据库和表
2. **想法CRUD**: save_ideas/load_ideas 能正确保存和加载想法数据
3. **数据迁移**: 从 JSON 文件迁移后数据完整性 100%
4. **查询功能**: 按状态查询返回正确结果
5. **向后兼容**: 现有代码无需修改即可切换到 SQLite

---

## Testing Plan (测试策略)

### 单元测试
1. `test_sqlite_storage_init`: 测试数据库初始化和表创建
2. `test_sqlite_save_load_ideas`: 测试想法的保存和加载
3. `test_sqlite_save_load_tasks`: 测试任务的保存和加载
4. `test_sqlite_activities`: 测试活动日志
5. `test_sqlite_advanced_queries`: 测试高级查询

### 迁移测试
6. `test_migrate_from_json`: 测试从 JSON 迁移
7. `test_migrate_preserves_data`: 测试数据完整性

### 集成测试
8. `test_idea_manager_with_sqlite`: 测试与 IdeaManager 集成

---

## Implementation Plan (实施计划)

### 阶段 1: 测试基础设施 (TDD-RED)
- [ ] 创建 `tests/test_sqlite_storage.py`
- [ ] 编写表创建测试 (预期失败)
- [ ] 编写 CRUD 测试框架

### 阶段 2: SQLiteStorage 核心 (TDD-GREEN)
- [ ] 实现 SQLiteStorage 类
- [ ] 实现表创建逻辑
- [ ] 实现 ideas CRUD
- [ ] 实现 tasks CRUD
- [ ] 实现 activities

### 阶段 3: 高级查询 (TDD-GREEN)
- [ ] 实现按状态/标签查询
- [ ] 实现分页查询

### 阶段 4: 数据迁移 (TDD-GREEN)
- [ ] 实现 migrate_from_json
- [ ] 实现 migrate_from_gist

### 阶段 5: 集成与重构 (REFACTOR)
- [ ] 更新 storage/__init__.py
- [ ] 更新配置支持
- [ ] 运行完整测试套件

---

## 技术约束
- 使用 Python 标准库 sqlite3
- 不引入额外依赖
- 数据库文件放在项目 data/ 目录
- 支持多进程安全 (使用 WAL 模式)
