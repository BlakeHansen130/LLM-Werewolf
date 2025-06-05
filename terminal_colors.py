# terminal_colors.py
from typing import Optional

# ANSI 转义码
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    # 前景色 (文本颜色)
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BRIGHT_BLACK = '\033[90m'  # Grey
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

    # 背景色
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    BG_BRIGHT_BLACK = '\033[100m'
    # ... 其他背景色

# 辅助函数，用于包裹文本
def colorize(text: str, color_code: str) -> str:
    """用指定的颜色代码包裹文本。"""
    return f"{color_code}{text}{Colors.RESET}"

# 常用颜色组合的便捷函数
def red(text: str) -> str: return colorize(text, Colors.RED)
def green(text: str) -> str: return colorize(text, Colors.GREEN)
def yellow(text: str) -> str: return colorize(text, Colors.YELLOW)
def blue(text: str) -> str: return colorize(text, Colors.BLUE)
def magenta(text: str) -> str: return colorize(text, Colors.MAGENTA)
def cyan(text: str) -> str: return colorize(text, Colors.CYAN)
def white(text: str) -> str: return colorize(text, Colors.WHITE) # 如果默认不是白色
def grey(text: str) -> str: return colorize(text, Colors.BRIGHT_BLACK) # Grey

def bold(text: str) -> str: return colorize(text, Colors.BOLD)
def underline(text: str) -> str: return colorize(text, Colors.UNDERLINE)

# 特定用途的颜色
def log_level_color(level: str) -> str:
    if level == "CRITICAL": return Colors.BOLD + Colors.RED
    if level == "ERROR": return Colors.RED
    if level == "WARN" or level == "WARNING": return Colors.YELLOW
    if level == "INFO": return Colors.GREEN # 或者 Colors.CYAN
    if level == "DEBUG": return Colors.BLUE
    if level == "TRACE": return Colors.BRIGHT_BLACK # Grey
    return Colors.WHITE # 默认

def player_name_color(player_name: str, player_data: Optional[dict] = None, game_state: Optional['GameState'] = None) -> str: # 避免循环导入，GameState 用字符串
    # 可以根据玩家角色或其他状态赋予不同颜色
    # 例如：狼人用红色，神职用亮色，平民用普通色
    if player_data:
        role = player_data.get("role")
        if role == "狼人":
            return colorize(player_name, Colors.BOLD + Colors.RED)
        elif role in ["预言家", "女巫", "猎人"]:
            return colorize(player_name, Colors.BOLD + Colors.CYAN) # 神用亮青色
        elif role == "平民":
            return colorize(player_name, Colors.WHITE) # 平民用白色
    return colorize(player_name, Colors.BRIGHT_WHITE) # 默认亮白色

def role_color(role_name: str) -> str:
    if role_name == "狼人": return colorize(role_name, Colors.RED)
    if role_name in ["预言家", "女巫", "猎人"]: return colorize(role_name, Colors.CYAN)
    if role_name == "平民": return colorize(role_name, Colors.WHITE)
    return role_name

def game_phase_color(phase_name: str) -> str:
    return colorize(phase_name, Colors.BOLD + Colors.MAGENTA)

def gm_tool_color(text: str) -> str:
    return colorize(text, Colors.BRIGHT_YELLOW)

def gm_broadcast_color(text: str) -> str:
    return colorize(text, Colors.BRIGHT_CYAN)

def ai_response_color(text: str) -> str: # AI的实际回复
    return colorize(text, Colors.WHITE) # 或者一个浅色

def system_message_color(text: str) -> str: # 比如系统提示或规则
    return colorize(text, Colors.BRIGHT_BLACK) # 灰色