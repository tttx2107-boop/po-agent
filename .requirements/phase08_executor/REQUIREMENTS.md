# Phase 8: 执行引擎 - 需求文档

> 创建时间：2026-04-22  
> 状态：进行中  
> TDD 驱动

## 1. As Is（当前状态）

### 已有代码
| 文件 | 行数 | 状态 |
|------|------|------|
| `executor.py` | 628 | 骨架完成，测试通过 |
| `execution_storage.py` | 595 | 已实现持久化 |
| `test_executor.py` | 284 | 20个测试全通过 |

### 已具备能力
- ✅ ExecutionContext / ExecutionResult 数据模型
- ✅ Executor 核心类（execute/pause/resume/cancel/retry）
- ✅ 串行/并行/条件执行模式
- ✅ 钩子系统（before_execute/after_execute/on_error/on_progress/on_complete）
- ✅ 检查点创建（create_checkpoint）
- ✅ 执行历史记录

### 已具备测试
- ✅ 20个测试覆盖基础功能

---

## 2. To Be（目标状态）

**Phase 8 执行引擎应支持：**

1. **任务执行器**：从 Task 到 ExecutionResult 的完整执行流程
2. **子任务调度**：基于 Task.subtasks 的自动拆解执行
3. **并行/串行控制**：支持依赖感知的并行执行
4. **执行状态持久化**：与 execution_storage.py 集成，支持中断恢复
5. **回滚机制**：执行失败时的安全回滚

---

## 3. Requirements（功能需求）

### R1: 任务执行器核心
- [x] **R1.1** `execute()` 方法完整执行 Task
- [x] **R1.2** `_default_steps()` 根据 Task.subtasks 生成步骤
- [x] **R1.3** 执行超时控制（基于 estimated_hours）
- [x] **R1.4** 执行进度实时更新

### R2: 子任务调度
- [x] **R2.1** 从 Task.subtasks 自动生成执行步骤
- [x] **R2.2** 子任务依赖解析（blocked_by）
- [x] **R2.3** 依赖前置检查
- [x] **R2.4** 依赖失败处理策略

### R3: 并行/串行执行
- [x] **R3.1** 串行执行（按依赖顺序）
- [x] **R3.2** 并行执行（无依赖任务同时执行）
- [x] **R3.3** 并发数控制（max_concurrent）
- [x] **R3.4** 依赖感知的并行分组

### R4: 状态持久化集成
- [x] **R4.1** 与 ExecutionStorage 集成
- [x] **R4.2** 执行状态自动保存
- [x] **R4.3** 检查点保存与恢复
- [x] **R4.4** 执行中断后恢复

### R5: 回滚机制
- [x] **R5.1** 执行失败时触发回滚
- [x] **R5.2** 按执行顺序逆序回滚
- [x] **R5.3** 回滚状态通知

---

## 4. Acceptance Criteria（验收标准）

### AC1: 基础执行
```
GIVEN 一个 Task 包含 3 个 subtasks
WHEN 执行该 Task
THEN 所有 3 个 subtask 都被执行
AND ExecutionResult 包含 3 个步骤的结果
```

### AC2: 依赖调度
```
GIVEN Task A 依赖 Task B，Task B 依赖 Task C
WHEN 按串行模式执行
THEN 执行顺序为 C → B → A
AND 如果 C 失败，B 和 A 不会执行
```

### AC3: 并行执行
```
GIVEN 4 个独立 Task（无依赖）
WHEN 使用并行模式，max_concurrent=2
THEN 2+2 分批执行
AND 等待前一批完成后开始后一批
```

### AC4: 中断恢复
```
GIVEN 一个正在执行的任务
WHEN 调用 pause() 并保存状态
AND 重新创建 Executor 并调用 resume()
THEN 从中断点恢复执行
```

### AC5: 回滚
```
GIVEN 执行过程中某个步骤失败
WHEN 触发回滚
THEN 已完成的步骤按逆序回滚
AND 回滚结果包含在 ExecutionResult 中
```

---

## 5. Testing Plan（测试策略）

### 单元测试
1. `test_executor_execute_with_subtasks` - 子任务执行
2. `test_executor_sequential_with_dependencies` - 依赖调度
3. `test_executor_parallel_grouping` - 并行分组
4. `test_executor_pause_resume` - 中断恢复
5. `test_executor_rollback_on_failure` - 失败回滚
6. `test_executor_timeout_handling` - 超时处理

### 集成测试
1. `test_full_task_execution_flow` - 完整流程
2. `test_storage_integration` - 存储集成

---

## 6. Implementation Plan（实现计划）

### Step 1: 修复现有 TODO（🔴 RED → 🟢 GREEN）
1. 实现 `execute_from_context()` 方法
2. 实现依赖检查逻辑
3. 实现回滚机制

### Step 2: 子任务调度（🟢 GREEN → 🔵 REFACTOR）
1. 实现 `_default_steps()` 生成逻辑
2. 实现 `_resolve_dependencies()` 依赖解析
3. 添加子任务执行测试

### Step 3: 并行执行（🟢 GREEN → 🔵 REFACTOR）
1. 完善 `execute_parallel()` 依赖分组
2. 添加 `max_concurrent` 控制
3. 添加并行执行测试

### Step 4: 状态持久化集成（🟢 GREEN → 🔵 REFACTOR）
1. 集成 ExecutionStorage
2. 实现检查点保存/恢复
3. 添加集成测试

---

## 7. Technical Notes（技术要点）

### 检查点数据结构
```python
Checkpoint {
    checkpoint_id: str
    execution_id: str
    task_id: str
    step_id: str  # 下一步要执行的步骤索引
    context_snapshot: ExecutionContext
    created_at: datetime
}
```

### 依赖图
```
Task A ──depends on──> Task B ──depends on──> Task C

串行执行顺序: C → B → A
并行分组:
  - Group 1: C
  - Group 2: B (等待 C 完成)
  - Group 3: A (等待 B 完成)
```

### 回滚策略
- 回滚粒度：按步骤回滚
- 回滚顺序：从后向前
- 回滚操作：由 ExecutionStep.rollback() 定义
