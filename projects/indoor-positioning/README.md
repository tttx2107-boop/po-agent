# 室内定位系统

基于BLE+PDR融合的室内定位系统，信标与应急疏散标识集成。

## 项目结构

```
indoor-positioning/
├── src/                  # 源代码
│   ├── positioning_service.py  # 定位核心服务
│   ├── data_collector.py        # 数据采集
│   └── map_builder.py          # 地图构建
├── config/              # 配置文件
│   └── beacon_config.py        # 信标配置
├── tests/               # 测试
│   └── test_positioning.py
├── docs/                # 文档
└── README.md
```

## 快速开始

```bash
# 安装依赖
pip install numpy

# 运行测试
python tests/test_positioning.py
```

## 信标与应急标识集成

信标可与以下应急标识集成：
- 安全出口标识
- 疏散指示标识
- 灭火器标识
- 消火栓标识
- 手动报警器标识
