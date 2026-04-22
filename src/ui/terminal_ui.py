"""
增强型 Terminal UI 模块
支持彩色输出、进度条、表格、交互式输入
"""
import sys
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

# 颜色代码
class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # 前景色
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # 亮色
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # 背景色
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"


class Theme:
    """UI 主题配置"""
    
    # 默认主题
    DEFAULT = {
        "title": Color.BRIGHT_CYAN + Color.BOLD,
        "header": Color.BRIGHT_BLUE + Color.BOLD,
        "success": Color.BRIGHT_GREEN,
        "warning": Color.BRIGHT_YELLOW,
        "error": Color.BRIGHT_RED,
        "info": Color.BRIGHT_CYAN,
        "muted": Color.DIM,
        "highlight": Color.BRIGHT_MAGENTA,
        "reset": Color.RESET
    }
    
    # 简洁主题（减少颜色）
    MINIMAL = {
        "title": Color.BOLD,
        "header": Color.BOLD,
        "success": "",
        "warning": "",
        "error": "",
        "info": "",
        "muted": Color.DIM,
        "highlight": "",
        "reset": ""
    }


@dataclass
class TableStyle:
    """表格样式"""
    border_char: str = "─"
    corner_char: str = "┼"
    header_char: str = "─"
    vertical_char: str = "│"


class TerminalUI:
    """增强型终端UI"""
    
    def __init__(self, theme: Dict = None, width: int = 80, table_style: TableStyle = None):
        self.theme = theme or Theme.DEFAULT
        self.width = width
        self.table_style = table_style or TableStyle()
        self._progress_bars: Dict[str, 'ProgressBar'] = {}
    
    # ==================== 基础输出 ====================
    
    def print(self, text: str = "", style: str = "info", newline: bool = True):
        """打印带样式的文本"""
        style_code = self.theme.get(style, "")
        reset = self.theme.get("reset", Color.RESET)
        end = "\n" if newline else ""
        print(f"{style_code}{text}{reset}", end=end, flush=True)
    
    def print_line(self, char: str = "─", width: int = None):
        """打印分隔线"""
        w = width or self.width
        print(char * w)
    
    def print_title(self, text: str, subtitle: str = None):
        """打印标题"""
        self.print_line("═")
        self.print(f"  {text}", style="title")
        if subtitle:
            self.print(f"  {subtitle}", style="muted")
        self.print_line("═")
    
    def print_header(self, text: str):
        """打印表头"""
        self.print(f"\n{text}", style="header")
        self.print_line("─")
    
    def print_success(self, text: str):
        self.print(f"✅ {text}", style="success")
    
    def print_warning(self, text: str):
        self.print(f"⚠️  {text}", style="warning")
    
    def print_error(self, text: str):
        self.print(f"❌ {text}", style="error")
    
    def print_info(self, text: str):
        self.print(f"ℹ️  {text}", style="info")
    
    def print_muted(self, text: str):
        self.print(text, style="muted")
    
    def blank(self, lines: int = 1):
        """打印空行"""
        print("\n" * (lines - 1) if lines > 1 else "")
    
    # ==================== 表格 ====================
    
    def print_table(self, headers: List[str], rows: List[List[str]], 
                    max_widths: List[int] = None, align: str = "left"):
        """
        打印表格
        
        Args:
            headers: 表头
            rows: 数据行
            max_widths: 每列最大宽度
            align: 对齐方式 ('left', 'center', 'right')
        """
        if not rows:
            self.print_muted("暂无数据")
            return
        
        # 计算列宽
        num_cols = len(headers)
        col_widths = max_widths or [len(h) for h in headers]
        
        for row in rows:
            for i, cell in enumerate(row):
                if i < num_cols:
                    col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # 限制总宽度
        total_width = sum(col_widths) + num_cols * 3 + 1
        if total_width > self.width:
            scale = (self.width - num_cols * 3 - 1) / sum(col_widths)
            col_widths = [max(10, int(w * scale)) for w in col_widths]
        
        # 对齐函数
        def align_cell(text: str, width: int) -> str:
            text = str(text)
            padding = width - len(text)
            if align == "right":
                return " " * padding + text
            elif align == "center":
                return " " * (padding // 2) + text + " " * (padding - padding // 2)
            else:
                return text + " " * padding
        
        # 打印表头
        header_line = "┌" + "┬".join("─" * (w + 2) for w in col_widths) + "┐"
        self.print(header_line)
        
        header_cells = "│" + "│".join(f" {align_cell(h, col_widths[i])} " 
                                        for i, h in enumerate(headers)) + "│"
        self.print(header_cells, style="header")
        
        # 打印分隔线
        separator = "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤"
        self.print(separator)
        
        # 打印数据行
        for row in rows:
            cells = "│" + "│".join(f" {align_cell(str(row[i]) if i < len(row) else '', col_widths[i])} "
                                    for i in range(num_cols)) + "│"
            self.print(cells)
        
        # 打印底部
        footer_line = "└" + "┴".join("─" * (w + 2) for w in col_widths) + "┘"
        self.print(footer_line)
    
    def print_table_simple(self, headers: List[str], rows: List[List[str]]):
        """简化表格（无边框）"""
        if not rows:
            return
        
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # 打印表头
        header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
        self.print(header_line, style="header")
        self.print("  ".join("─" * w for w in col_widths))
        
        # 打印数据
        for row in rows:
            line = "  ".join(str(row[i]).ljust(col_widths[i]) 
                           for i in range(min(len(row), len(col_widths))))
            self.print(line)
    
    # ==================== 进度条 ====================
    
    def progress_start(self, task_id: str, description: str, total: int = 100):
        """开始一个进度任务"""
        self._progress_bars[task_id] = ProgressBar(
            task_id=task_id,
            description=description,
            total=total,
            width=min(40, self.width - 50),
            ui=self
        )
        self._progress_bars[task_id].render()
    
    def progress_update(self, task_id: str, current: int = None, description: str = None):
        """更新进度"""
        if task_id in self._progress_bars:
            self._progress_bars[task_id].update(current, description)
    
    def progress_complete(self, task_id: str, message: str = "完成"):
        """完成进度"""
        if task_id in self._progress_bars:
            self._progress_bars[task_id].complete(message)
            del self._progress_bars[task_id]
    
    def progress_cancel(self, task_id: str):
        """取消进度"""
        if task_id in self._progress_bars:
            self._progress_bars[task_id].cancel()
            del self._progress_bars[task_id]
    
    # ==================== 列表选择 ====================
    
    def choose(self, prompt: str, options: List[str], 
               allow_custom: bool = False, custom_prompt: str = "自定义: ") -> Optional[str]:
        """
        让用户从列表中选择
        
        Args:
            prompt: 提示文字
            options: 选项列表
            allow_custom: 是否允许自定义输入
            custom_prompt: 自定义输入提示
        
        Returns:
            选择的选项或自定义输入，None表示取消
        """
        self.print(f"\n{prompt}")
        self.print("━" * min(40, self.width))
        
        for i, option in enumerate(options, 1):
            self.print(f"  {i}. {option}")
        
        if allow_custom:
            self.print(f"  0. {custom_prompt}")
        
        self.print("━" * min(40, self.width))
        self.print(f"请输入编号 (1-{len(options)})", style="muted")
        
        while True:
            try:
                choice = input(f"{Color.BRIGHT_CYAN}➜ {Color.RESET}").strip()
                
                if not choice:
                    continue
                
                if choice.isdigit():
                    num = int(choice)
                    if 1 <= num <= len(options):
                        return options[num - 1]
                    elif choice == "0" and allow_custom:
                        custom = input(f"{custom_prompt}").strip()
                        return custom if custom else None
                
                self.print_error(f"请输入 1-{len(options)} 之间的数字")
            except (ValueError, KeyboardInterrupt):
                self.print_warning("已取消")
                return None
    
    def confirm(self, prompt: str, default: bool = None) -> bool:
        """
        确认提示
        
        Args:
            prompt: 提示文字
            default: 默认选择 (True/False/None)
        
        Returns:
            用户选择
        """
        if default is True:
            suffix = " [Y/n]"
            default_val = "y"
        elif default is False:
            suffix = " [y/N]"
            default_val = "n"
        else:
            suffix = " [y/n]"
            default_val = None
        
        while True:
            response = input(f"{prompt}{suffix}: ").strip().lower()
            
            if not response and default_val:
                return default_val == "y"
            
            if response in ("y", "yes", "是", "ok", "好"):
                return True
            elif response in ("n", "no", "否", "不", "算了"):
                return False
            
            self.print_warning("请输入 y 或 n")
    
    def input_text(self, prompt: str, default: str = None, 
                   validator: Callable[[str], bool] = None) -> Optional[str]:
        """
        输入文本
        
        Args:
            prompt: 提示文字
            default: 默认值
            validator: 验证函数
        
        Returns:
            输入的文本，None表示取消
        """
        default_hint = f" (默认: {default})" if default else ""
        full_prompt = f"{prompt}{default_hint}: "
        
        while True:
            try:
                response = input(f"{full_prompt}").strip()
                
                if not response and default:
                    return default
                
                if not response:
                    self.print_warning("输入不能为空")
                    continue
                
                if validator:
                    if validator(response):
                        return response
                    else:
                        self.print_error("输入格式不正确，请重新输入")
                else:
                    return response
                    
            except KeyboardInterrupt:
                self.print_warning("已取消")
                return None
    
    def input_password(self, prompt: str = "密码") -> Optional[str]:
        """输入密码（不回显）"""
        import getpass
        try:
            return getpass.getpass(f"{prompt}: ")
        except KeyboardInterrupt:
            return None
    
    # ==================== 状态显示 ====================
    
    def print_status_list(self, items: List[Dict[str, Any]], 
                          status_field: str = "status",
                          name_field: str = "name",
                          id_field: str = "id"):
        """
        打印状态列表
        
        Args:
            items: 项目列表
            status_field: 状态字段名
            name_field: 名称字段名
            id_field: ID字段名
        """
        if not items:
            self.print_muted("暂无数据")
            return
        
        status_icons = {
            "NEW": ("🆕 新", Color.BRIGHT_BLUE),
            "ASSESSING": ("⏳ 评估中", Color.BRIGHT_YELLOW),
            "CONFIRMED": ("✅ 已确认", Color.BRIGHT_GREEN),
            "DEFERRED": ("⏸️ 暂缓", Color.BRIGHT_MAGENTA),
            "REJECTED": ("❌ 已否决", Color.BRIGHT_RED),
            "IN_PROGRESS": ("🔄 进行中", Color.BRIGHT_CYAN),
            "COMPLETED": ("⭐ 已完成", Color.BRIGHT_GREEN),
        }
        
        for item in items:
            status = item.get(status_field, "UNKNOWN")
            icon, color = status_icons.get(status, ("❓", Color.DIM))
            name = item.get(name_field, "未命名")
            item_id = item.get(id_field, "")
            
            id_hint = f"[{item_id[:8]}]" if item_id else ""
            print(f"{color}{icon}{Color.RESET} {name} {Color.DIM}{id_hint}{Color.RESET}")
    
    def print_summary(self, data: Dict[str, Any], title: str = None):
        """
        打印摘要信息
        
        Args:
            data: 键值对数据
            title: 标题
        """
        if title:
            self.print_header(title)
        
        max_key_len = max(len(str(k)) for k in data.keys()) if data else 10
        
        for key, value in data.items():
            key_str = str(key)
            value_str = str(value) if value is not None else "-"
            
            self.print(f"  {key_str.ljust(max_key_len)} : {value_str}")
    
    # ==================== 等待动画 ====================
    
    def spinner(self, text: str = "处理中", duration: float = None):
        """
        显示旋转动画
        
        Args:
            text: 提示文字
            duration: 持续时间(秒)，None表示一直显示直到调用stop
        
        Returns:
            stop函数
        """
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        
        def stop():
            print(f"\r{' ' * (len(text) + 20)}\r", end="\r")
        
        if duration:
            end_time = time.time() + duration
            while time.time() < end_time:
                char = spinner_chars[i % len(spinner_chars)]
                print(f"\r{Color.BRIGHT_CYAN}{char}{Color.RESET} {text}", end="", flush=True)
                time.sleep(0.1)
                i += 1
            stop()
            return None
        else:
            # 返回一个可以更新的生成器
            def generator():
                i = 0
                while True:
                    char = spinner_chars[i % len(spinner_chars)]
                    yield f"\r{Color.BRIGHT_CYAN}{char}{Color.RESET} {text}"
                    i += 1
            return generator()
    
    def wait(self, text: str = "请稍候", steps: int = None):
        """
        等待动画
        
        Args:
            text: 提示文字
            steps: 步数，None表示无限
        
        Yields:
            更新回调函数
        """
        dots = ["", ".", "..", "..."]
        i = 0
        
        if steps:
            for step in range(steps):
                print(f"\r{text}{dots[step % 4]}", end="", flush=True)
                time.sleep(0.3)
            print(f"\r{' ' * (len(text) + 4)}\r", end="\r")
        else:
            while True:
                print(f"\r{text}{dots[i % 4]}", end="", flush=True)
                time.sleep(0.3)
                i += 1
                yield
    
    # ==================== 帮助信息 ====================
    
    def print_help(self, commands: List[Dict[str, str]]):
        """
        打印帮助信息
        
        Args:
            commands: 命令列表 [{"cmd": "命令", "desc": "描述"}, ...]
        """
        self.print_header("可用命令")
        
        max_cmd_len = max(len(c.get("cmd", "")) for c in commands) if commands else 10
        
        for cmd in commands:
            command = cmd.get("cmd", "").ljust(max_cmd_len)
            desc = cmd.get("desc", "")
            alias = cmd.get("alias", "")
            
            line = f"  {command}"
            if alias:
                line += f" ({alias})"
            line += f"  {desc}"
            
            self.print(line)
        
        self.blank()


class ProgressBar:
    """进度条组件"""
    
    def __init__(self, task_id: str, description: str, total: int, width: int, ui: TerminalUI):
        self.task_id = task_id
        self.description = description
        self.total = total
        self.current = 0
        self.width = width
        self.ui = ui
        self.start_time = time.time()
    
    def update(self, current: int = None, description: str = None):
        """更新进度"""
        if current is not None:
            self.current = min(current, self.total)
        if description:
            self.description = description
        
        self.render()
    
    def render(self):
        """渲染进度条"""
        filled = int(self.width * self.current / max(self.total, 1))
        bar = "█" * filled + "░" * (self.width - filled)
        percent = int(100 * self.current / max(self.total, 1))
        
        elapsed = time.time() - self.start_time
        if self.current > 0:
            rate = self.current / elapsed
            remaining = (self.total - self.current) / rate if rate > 0 else 0
            time_str = f" {int(remaining)}s"
        else:
            time_str = ""
        
        line = f"\r{Color.BRIGHT_CYAN}█{Color.RESET} {self.description[:30]} |{bar}| {percent}%{time_str}"
        print(line, end="", flush=True)
    
    def complete(self, message: str = "完成"):
        """完成进度"""
        filled = self.width
        bar = "█" * filled
        print(f"\r{Color.BRIGHT_GREEN}✓{Color.RESET} {self.description} |{bar}| 100% {message}")
    
    def cancel(self):
        """取消进度"""
        print(f"\r{Color.BRIGHT_YELLOW}✗{Color.RESET} {self.description} 已取消" + " " * 30)


# ==================== 全局实例 ====================

# 默认UI实例
default_ui = TerminalUI()


def get_ui() -> TerminalUI:
    """获取默认UI实例"""
    return default_ui
