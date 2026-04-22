# 「破」通用型想法实现智能体

> 让想法从"灵光一现"到"落地成真"的 AI 助理

## 核心理念

创新性和可行性都是动态的、相对的，需要定期重估。

## 核心功能

| 功能 | 描述 |
|------|------|
| 💡 **想法管理** | 快速记录、自动评估、智能分类 |
| 📊 **评估体系** | 5维度快速评估 + 4维度深度评审 |
| 🔨 **任务拆解** | AI 自动将想法拆解为可执行任务 |
| 📈 **进度追踪** | 任务状态、甘特图、里程碑管理 |
| 🔔 **智能提醒** | 定时评估、进度预警、复盘提醒 |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 GitHub Token

# 运行
python main.py
```

## 项目状态

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1-7 | 核心架构/评估/任务/API/CLI/Web UI/定时任务 | ✅ 完成 |
| Phase 8 | 执行引擎 | 🔄 开发中 |
| Phase 9 | UI界面 | 📋 待开发 |
| Phase 10 | 持久化存储 | 📋 待开发 |

**当前规模：** 54个Python文件，约3900+行代码

## 测试状态

```bash
# 运行所有测试
pytest tests/ -v

# 查看覆盖率
pytest tests/ --cov=src --cov-report=term
```

当前测试覆盖率：**52%+**

## 目录结构

```
po-agent/
├── src/
│   ├── models/          # 数据模型
│   ├── core/            # 核心逻辑
│   ├── services/        # 服务层
│   ├── storage/         # 存储层
│   └── entry/           # 入口点
├── tests/               # 单元测试
└── main.py              # 主入口
```

## License

MIT
