# 「破」通用型想法实现智能体

> 让想法从"灵光一现"到"落地成真"的 AI 助理

## 核心理念

创新性和可行性都是动态的、相对的，需要定期重估。

## 架构设计

```
💭 想法录入 → ⚡快速评估 → 📋 想法库 → ⏰ 深度评估 → 📱 用户确认 
→ 🚀 执行追踪 → ⭐ 完成 → 🔄 定期复盘(循环)
```

## 技术栈

- **存储**：GitHub Gist
- **AI**：Claude/MiniMax
- **入口**：微信

## 快速开始

```bash
pip install -r requirements.txt
python main.py
```

## 项目结构

```
po-agent/
├── storage.py           # GitHub Gist 存储
├── quick_assessment.py   # 快速评估（分钟级）
├── deep_assessment.py    # 深度评估（周级）
├── main.py              # 主入口
├── config.py            # 配置
└── requirements.txt     # 依赖
```

## 设计文档

详见 [DESIGN.md](DESIGN.md)

## License

MIT
