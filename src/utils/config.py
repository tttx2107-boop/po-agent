"""配置管理"""
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class Config:
    """配置类"""
    # GitHub
    github_token: str = ""
    github_user: str = "tttx2107-boop"
    gist_id: str = "9cac7883a1c961951baa5d0234fd335c"
    
    # 评估参数
    eval_trigger_count: int = 5
    eval_schedule_day: int = 6  # 周六
    eval_schedule_hour: int = 6
    max_daily_assessments: int = 3
    
    # 存储
    data_file: str = "data/ideas.json"
    tasks_file: str = "data/tasks.json"
    activities_file: str = "data/activities.json"
    log_file: str = "logs/activity.log"
    
    # 微信
    wechat_webhook_url: str = ""
    
    # 项目路径
    project_root: Path = None

    def __post_init__(self):
        if self.project_root is None:
            self.project_root = Path(__file__).parent.parent.parent
        # 确保路径是绝对路径
        if not Path(self.data_file).is_absolute():
            self.data_file = str(self.project_root / self.data_file)
        if not Path(self.tasks_file).is_absolute():
            self.tasks_file = str(self.project_root / self.tasks_file)
        if not Path(self.activities_file).is_absolute():
            self.activities_file = str(self.project_root / self.activities_file)
        if not Path(self.log_file).is_absolute():
            self.log_file = str(self.project_root / self.log_file)


def load_config() -> Config:
    """加载配置"""
    config = Config()
    
    # 从环境变量读取
    config.github_token = os.environ.get("GITHUB_TOKEN", config.github_token)
    config.github_user = os.environ.get("GITHUB_USER", config.github_user)
    config.gist_id = os.environ.get("GIST_ID", config.gist_id)
    config.wechat_webhook_url = os.environ.get("WECHAT_WEBHOOK_URL", config.wechat_webhook_url)
    
    # 解析数值参数
    if os.environ.get("EVAL_TRIGGER_COUNT"):
        config.eval_trigger_count = int(os.environ["EVAL_TRIGGER_COUNT"])
    if os.environ.get("MAX_DAILY_ASSESSMENTS"):
        config.max_daily_assessments = int(os.environ["MAX_DAILY_ASSESSMENTS"])
    
    return config


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取配置实例"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config():
    """重新加载配置"""
    global _config
    _config = load_config()
