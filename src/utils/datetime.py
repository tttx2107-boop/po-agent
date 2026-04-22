"""日期时间工具"""
from datetime import datetime, timedelta
from typing import Optional


def now() -> str:
    """返回当前时间 ISO 格式"""
    return datetime.now().isoformat()


def today() -> str:
    """返回今天的日期"""
    return datetime.now().strftime("%Y-%m-%d")


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """解析 ISO 格式时间字符串"""
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    """格式化日期"""
    return dt.strftime(fmt)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """格式化日期时间"""
    return dt.strftime(fmt)


def days_ago(dt_str: str) -> int:
    """计算距离今天多少天"""
    dt = parse_datetime(dt_str)
    if dt:
        return (datetime.now() - dt).days
    return 0


def is_weekend() -> bool:
    """是否周末"""
    return datetime.now().weekday() >= 5


def is_saturday() -> bool:
    """是否周六"""
    return datetime.now().weekday() == 5


def days_until_weekday(target_weekday: int) -> int:
    """
    计算距离目标星期几还有多少天
    
    Args:
        target_weekday: 0=周一, 6=周日
    """
    current = datetime.now().weekday()
    diff = target_weekday - current
    if diff <= 0:
        diff += 7
    return diff


def next_scheduled_time(schedule_day: int = 5, schedule_hour: int = 6) -> datetime:
    """
    计算下次调度时间
    
    Args:
        schedule_day: 0=周一, 6=周日
        schedule_hour: 小时 (0-23)
    """
    now = datetime.now()
    
    # 计算目标日期
    days = days_until_weekday(schedule_day)
    target_date = now + timedelta(days=days)
    
    # 设置时间
    return target_date.replace(hour=schedule_hour, minute=0, second=0, microsecond=0)


def format_duration(hours: float) -> str:
    """格式化时长"""
    if hours < 1:
        return f"{int(hours * 60)}分钟"
    elif hours < 24:
        return f"{hours:.1f}小时"
    else:
        days = hours / 24
        return f"{days:.1f}天"
