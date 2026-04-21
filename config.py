"""配置文件"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# GitHub 配置 - 从环境变量读取
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER = os.environ.get("GITHUB_USER", "tttx2107-boop")
GIST_ID = os.environ.get("GIST_ID", "9cac7883a1c961951baa5d0234fd335c")

# 评估触发条件
EVAL_TRIGGER_COUNT = 5  # 每积累 5 个想法触发评估
EVAL_SCHEDULE_DAY = 6   # 每周六 (0=周一, 6=周日)
EVAL_SCHEDULE_HOUR = 6  # 凌晨 6:00

# 评估参数
MAX_DAILY_ASSESSMENTS = 3  # 每日最多深度评估数量
ASSESSMENT_QUEUE_LIMIT = 10  # 评估队列上限

# 数据存储
DATA_FILE = PROJECT_ROOT / "data" / "ideas.json"
LOG_FILE = PROJECT_ROOT / "logs" / "activity.log"

# 确保目录存在
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
