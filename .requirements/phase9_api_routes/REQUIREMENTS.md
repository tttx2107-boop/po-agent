# Phase 9: API 路由与数据操作 - 需求文档

## As Is (当前状态)
- Web UI 已有基础的 HTML 页面（/ui/app）
- 已有 risk_warning 路由
- 但缺少想法/任务的 CRUD API 路由
- WebSocket 仅支持 ping/subscribe

## To Be (目标状态)
- 完整的想法 CRUD API（增删改查）
- 任务 CRUD API
- 评估触发 API
- WebSocket 实时推送想法更新
- 所有 API 有对应的单元测试

## Requirements

### R1: 想法 CRUD API
- [ ] POST /api/ideas - 创建想法
- [ ] GET /api/ideas - 列表查询
- [ ] GET /api/ideas/{id} - 详情
- [ ] PUT /api/ideas/{id} - 更新
- [ ] DELETE /api/ideas/{id} - 删除

### R2: 任务 CRUD API
- [ ] POST /api/ideas/{idea_id}/tasks - 创建任务
- [ ] GET /api/ideas/{idea_id}/tasks - 列表
- [ ] PUT /api/tasks/{id} - 更新任务
- [ ] DELETE /api/tasks/{id} - 删除任务

### R3: 评估 API
- [ ] POST /api/ideas/{id}/assess - 触发评估
- [ ] GET /api/ideas/{id}/assess - 获取评估结果

### R4: WebSocket 增强
- [ ] 想法创建时广播
- [ ] 想法更新时广播
- [ ] 任务状态变更时广播

### R5: 错误处理
- [ ] 404 处理（找不到资源）
- [ ] 400 处理（参数错误）
- [ ] 500 处理（服务器错误）

## Acceptance Criteria

1. 所有 API 返回正确的 HTTP 状态码
2. 数据验证失败返回明确的错误信息
3. WebSocket 连接稳定，断开自动清理
4. 所有 API 有对应的 pytest 测试

## Testing Plan

| API | 测试用例 |
|-----|----------|
| POST /api/ideas | 正常创建、参数验证、重复创建 |
| GET /api/ideas | 空列表、有数据、分页 |
| GET /api/ideas/{id} | 存在、不存在 |
| PUT /api/ideas/{id} | 正常更新、不存在 |
| DELETE /api/ideas/{id} | 正常删除、不存在 |
| WebSocket | 连接、广播消息、断开 |

## Implementation Plan

1. 创建 `src/routers/ideas.py` - 想法路由
2. 创建 `src/routers/tasks.py` - 任务路由  
3. 创建 `src/routers/assessment.py` - 评估路由
4. 更新 `web_server.py` 注册新路由
5. 编写测试 `tests/test_api_routes.py`
6. 增强 WebSocket 广播逻辑
