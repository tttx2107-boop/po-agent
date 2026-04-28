# Multimodal Knowledge Graph System
多模态知识图谱系统

> 构建同时包含文本实体和视觉实体的多模态知识图谱

## 功能特性

### 核心能力
- **M1 图谱获取**：从PDF/文档/网页/上传多源采集图像
- **M2 图像标注**：AI辅助标注 + 手动标注，支持目标检测/OCR/关系抽取
- **M3 自学习**：反馈收集 + 增量学习 + 主动学习 + 质量评估
- **M4 图文融合**：文本→图像 + 图像→文本双向关联 + 冲突检测

### 文本KG（基于paper-to-knowledge-graph）
- Skill 1-9：实体/理论/变量/聚类/参数/实证映射/边界/外部链接/贡献提取
- Skill 10：多源知识融合
- Skill 11：质量审计
- Skill 12：可视化编译（Mermaid/D3/ECharts）

## 快速启动

### 1. 安装依赖
```bash
cd /root/multimodal-kg
pip install -r requirements.txt
```

### 2. 配置
编辑 `config.yaml` 设置：
- API密钥（OpenAI等）
- 存储路径
- 模型参数

### 3. 初始化数据库
```bash
python -c "from app.models.database import init_db; init_db()"
```

### 4. 启动服务
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 访问
- API文档：http://localhost:8000/docs
- 标注界面：http://localhost:8000/static/annotation/index.html
- 图谱查看器：http://localhost:8000/static/kg_viewer/index.html

## 项目结构

```
/root/multimodal-kg/
├── app/
│   ├── api/              # FastAPI路由
│   ├── core/             # 配置文件
│   ├── models/            # 数据库模型
│   ├── schemas/           # Pydantic模型
│   └── services/          # 业务逻辑
│       ├── acquisition_service.py  # M1 图谱获取
│       ├── annotation_engine.py     # M2 图像标注
│       ├── self_learning.py         # M3 自学习
│       ├── fusion_engine.py         # M4 图文融合
│       └── kg_generator.py          # 文本KG生成
├── data/                  # 数据存储
│   ├── images/           # 原始/标注/缩略图
│   ├── annotations/       # pending/verified/corrected
│   └── kg/               # text/image/multimodal
├── web/
│   ├── annotation/       # 标注界面
│   └── kg_viewer/         # 图谱可视化
├── scripts/              # 工具脚本
└── config.yaml           # 配置文件
```

## API 示例

### 上传图像
```bash
curl -X POST "http://localhost:8000/api/images/upload" \
  -F "file=@test.jpg" \
  -F "source=upload" \
  -F "image_type=facility"
```

### 标注图像
```bash
curl -X POST "http://localhost:8000/api/annotations/{image_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "objects": [{"id": "obj1", "type": "灭火器", "bbox": [100, 100, 200, 300]}],
    "scene": {"type": "消防设施", "confidence": 0.95}
  }'
```

### 生成文本KG
```bash
curl -X POST "http://localhost:8000/api/kg/generate" \
  -H "Content-Type: application/json" \
  -d '{"text": "火灾自动报警系统...", "name": "火灾报警KG"}'
```

### 图文融合
```bash
curl -X POST "http://localhost:8000/api/fusion/fuse" \
  -H "Content-Type: application/json" \
  -d '{"text_kg_id": "KG_XXXX", "image_ids": ["IMG_XXXX"]}'
```

## 数据模型

### Image
- `id`: 图像ID
- `storage_path`: 存储路径
- `source`: 来源（URL/文档/上传）
- `image_type`: 类型（facility/floor_plan/scene/standard/sign）

### ImageAnnotation
- `objects`: 检测对象列表 [{type, bbox, attributes}]
- `relationships`: 对象关系 [{source, target, type, spatial}]
- `ocr_text`: OCR识别文本
- `norm_reference`: 规范引用

### KGEntity
- `id`: 实体ID
- `name`: 实体名称
- `entity_type`: 类型（text/image）
- `cluster`: 聚类标签

### KGRelationship
- `source_id`: 源实体
- `target_id`: 目标实体
- `relation_type`: 关系类型
- `hypothesis_status`: 实证状态（supported/partial/rejected）

## 消防领域适配

系统预置了消防领域的标注类型：
- 灭火器、消火栓、防火门
- 疏散标志、喷淋头、火灾探测器
- 火灾报警控制器、消防泵

## 技术栈

- **后端**：FastAPI + SQLAlchemy + Pydantic
- **图像处理**：OpenCV + PIL + YOLO + PaddleOCR
- **向量检索**：ChromaDB
- **LLM**：OpenAI GPT-4o / Anthropic Claude
- **可视化**：Mermaid.js + D3.js

## License
MIT
