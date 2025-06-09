# ui_adapter.py (最终完整版)
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, Union
from enum import Enum

# 导入现有的颜色模块和游戏模块
try:
    from terminal_colors import (
        colorize, log_level_color, game_phase_color, Colors,
        gm_broadcast_color, player_name_color, role_color,
        red, green, yellow, blue, magenta, cyan, grey, bold
    )
except ImportError:
    # Fallback if terminal_colors is not found
    def colorize(text: str, _color_code: str) -> str: return text
    def log_level_color(_level: str) -> str: return ""
    class Colors: RESET = ""; BOLD = ""; RED = ""; GREEN = ""; YELLOW = ""; BLUE = ""; MAGENTA = ""; CYAN = ""; BRIGHT_BLACK = ""; BRIGHT_YELLOW = ""; BRIGHT_CYAN = ""; BRIGHT_RED = ""
    def game_phase_color(text: str) -> str: return text
    def gm_broadcast_color(text: str) -> str: return text
    def player_name_color(name: str, _player_data=None, _game_state=None) -> str: return name
    def role_color(name: str) -> str: return name
    def red(text: str) -> str: return text
    def green(text: str) -> str: return text
    def yellow(text: str) -> str: return text
    def blue(text: str) -> str: return text
    def magenta(text: str) -> str: return text
    def cyan(text: str) -> str: return text
    def grey(text: str) -> str: return text
    def bold(text: str) -> str: return text

from assets_base64 import format_gm_action_message

class UIMode(Enum):
    """UI模式枚举"""
    TERMINAL = "terminal"
    GRADIO = "gradio"

class GMApprovalResult:
    """GM审核结果"""
    def __init__(self, action: str, content: Optional[str] = None):
        self.action = action  # 'accept', 'retry', 'manual', 'skip', 'accept_invalid'
        self.content = content  # 如果是manual，这里是手动输入的内容

class UIAdapter(ABC):
    """UI适配器抽象基类"""
    
    def __init__(self, mode: UIMode):
        self.mode = mode
        self.game_state = None  # 会在初始化时设置
    
    def set_game_state(self, game_state):
        """设置游戏状态引用"""
        self.game_state = game_state
    
    @abstractmethod
    def broadcast_message(self, message: str, message_type: str = "info") -> None:
        """
        广播消息给所有玩家
        
        Args:
            message: 消息内容
            message_type: 消息类型 ('info', 'warning', 'error', 'gm_broadcast')
        """
        pass
    
    @abstractmethod
    def get_gm_approval(self, player_config_name: str, ai_response: str, 
                       action_type: str, validation_error: Optional[str] = None,
                       parsed_value: Any = None, valid_choices: Optional[List[str]] = None) -> GMApprovalResult: # 添加 valid_choices
        """
        获取GM对AI响应的审核结果
        
        Args:
            player_config_name: 玩家配置名
            ai_response: AI的原始响应
            action_type: 行动类型
            validation_error: 验证错误信息（如果有）
            parsed_value: 解析后的值（如果验证通过）
            valid_choices: 当验证失败时，提供的有效选项列表
        
        Returns:
            GM审核结果
        """
        pass
    
    @abstractmethod
    def show_player_status(self, players_data: Dict[str, Dict[str, Any]], 
                          show_gm_view: bool = True) -> None:
        """
        显示玩家状态
        
        Args:
            players_data: 玩家数据字典
            show_gm_view: 是否GM视角（显示角色等隐藏信息）
        """
        pass
    
    @abstractmethod
    def get_user_input(self, prompt: str, input_type: str = "text") -> str:
        """
        获取用户输入
        
        Args:
            prompt: 提示信息
            input_type: 输入类型 ('text', 'choice', 'confirm')
        
        Returns:
            用户输入的内容
        """
        pass
    
    @abstractmethod
    def show_game_log(self, game_log: List[Dict[str, Any]], count: int = 20) -> None:
        """
        显示游戏日志
        
        Args:
            game_log: 游戏日志列表
            count: 显示条数
        """
        pass
    
    @abstractmethod
    def show_player_history(self, player_config_name: str, 
                           player_info: Dict[str, Any]) -> None:
        """
        显示玩家历史记录
        
        Args:
            player_config_name: 玩家配置名
            player_info: 玩家信息
        """
        pass
    
    @abstractmethod
    def show_current_votes(self, votes_data: Dict[str, str]) -> None:
        """
        显示当前投票情况
        
        Args:
            votes_data: 投票数据
        """
        pass
    
    @abstractmethod
    def log_flow_event(self, message: str, level: str = "INFO", 
                      day: Optional[int] = None, phase: Optional[str] = None) -> None:
        """
        记录游戏流程事件
        
        Args:
            message: 消息内容
            level: 日志级别
            day: 游戏天数
            phase: 游戏阶段
        """
        pass

    @abstractmethod
    def wait_for_continue(self, prompt: str) -> None:
        """
        暂停游戏，等待用户通过UI发出继续指令。
        
        Args:
            prompt: 向用户显示的提示信息，例如“按键进入下一夜”。
        """
        pass


class TerminalUIAdapter(UIAdapter):
    """终端UI适配器 - 包装现有的终端逻辑，保持完全兼容"""
    
    def __init__(self):
        super().__init__(UIMode.TERMINAL)
    
    def broadcast_message(self, message: str, message_type: str = "info") -> None:
        if message_type == "gm_broadcast":
            colored_message = gm_broadcast_color(f"GM广播: {message}")
            print(colored_message)
        else:
            print(message)
    
    def get_gm_approval(self, player_config_name: str, ai_response: str,
                       action_type: str, validation_error: Optional[str] = None,
                       parsed_value: Any = None, valid_choices: Optional[List[str]] = None) -> GMApprovalResult:
        if self.game_state:
            player_data = self.game_state.get_player_info(player_config_name)
            player_display = player_name_color(
                self.game_state.get_player_display_name(player_config_name), 
                player_data, self.game_state
            )
        else:
            player_display = colorize(player_config_name, Colors.BRIGHT_MAGENTA)
        
        action_type_colored = colorize(action_type, Colors.YELLOW)
        
        print(colorize(f"\n--- GM审核点: {player_display} (行动: {action_type_colored}) ---", Colors.BOLD + Colors.MAGENTA))
        print(f"AI响应原文:\n```\n{ai_response}\n```")
        
        if validation_error:
            print(colorize(f"AI响应内容校验失败: {validation_error}", Colors.RED))
            choice = input(
                f"请选择操作: [{bold('R')}]让AI重试(提供修正), [{bold('M')}]手动输入, "
                f"[{bold('A')}]接受此原始响应(风险自负), [{bold('S')}]跳过: "
            ).strip().upper()
            
            if choice == 'R': return GMApprovalResult("retry")
            elif choice == 'M':
                manual_input = input(f"请输入 {player_display} 的 {action_type_colored} 内容: ").strip()
                return GMApprovalResult("manual", manual_input)
            elif choice == 'A': return GMApprovalResult("accept_invalid")
            else: return GMApprovalResult("skip")
        else:
            parsed_value_display = colorize(str(parsed_value)[:100], Colors.BRIGHT_WHITE) + (grey('...') if len(str(parsed_value)) > 100 else '')
            print(f"{green('AI响应有效')}。解析后的行动值: '{parsed_value_display}'")
            choice = input(f"请选择操作: [{bold('Y')}]确认采纳, [{bold('R')}]让AI重试(不满意), [{bold('M')}]手动修改/覆盖: ").strip().upper()
            
            if choice == 'Y': return GMApprovalResult("accept")
            elif choice == 'R': return GMApprovalResult("retry")
            elif choice == 'M':
                manual_input = input(f"当前AI建议为: '{parsed_value_display}'\n请输入你修改后的 {player_display} 的 {action_type_colored} 内容: ").strip()
                return GMApprovalResult("manual", manual_input)
            else: return GMApprovalResult("accept")
    
    def show_player_status(self, players_data: Dict[str, Dict[str, Any]], show_gm_view: bool = True) -> None:
        from gm_tools import display_all_player_statuses
        if self.game_state:
            display_all_player_statuses(self.game_state)
    
    def get_user_input(self, prompt: str, input_type: str = "text") -> str:
        return input(cyan(prompt)).strip()
    
    def show_game_log(self, game_log: List[Dict[str, Any]], count: int = 20) -> None:
        from gm_tools import display_game_log
        if self.game_state:
            display_game_log(self.game_state, count)
    
    def show_player_history(self, player_config_name: str, player_info: Dict[str, Any]) -> None:
        from gm_tools import view_player_game_history
        if self.game_state:
            view_player_game_history(self.game_state, player_config_name)
    
    def show_current_votes(self, votes_data: Dict[str, str]) -> None:
        from gm_tools import display_current_votes
        if self.game_state:
            display_current_votes(self.game_state)
    
    def log_flow_event(self, message: str, level: str = "INFO", day: Optional[int] = None, phase: Optional[str] = None) -> None:
        level_colored = colorize(level, log_level_color(level))
        prefix_module = colorize("[FlowManager:", Colors.GREEN)
        prefix = f"\n{prefix_module}{level_colored}]"
        if day is not None:
            prefix += f" [{colorize('Day ' + str(day), Colors.BOLD)}]"
        if phase:
            prefix += f" [{game_phase_color(phase)}]"
        print(f"{prefix} {message}")

    def wait_for_continue(self, prompt: str) -> None:
        """终端模式下，使用input()来阻塞和等待。"""
        input(cyan(prompt)).strip().lower()


class GradioUIAdapter(UIAdapter):
    """Gradio UI适配器 - 接口定义，具体实现在gradio_game_controller.py中"""
    
    def __init__(self):
        super().__init__(UIMode.GRADIO)
        self.interface = None
        self.message_history = []
        self.status_callback = None
        self.approval_callback = None
    
    def set_interface_callbacks(self, interface, status_callback: Callable, approval_callback: Callable):
        self.interface = interface
        self.status_callback = status_callback
        self.approval_callback = approval_callback
    
    def broadcast_message(self, message: str, message_type: str = "info") -> None:
        pass # 具体实现在GradioUIAdapterImpl中
    
    def get_gm_approval(self, player_config_name: str, ai_response: str,
                       action_type: str, validation_error: Optional[str] = None,
                       parsed_value: Any = None, valid_choices: Optional[List[str]] = None) -> GMApprovalResult:
        if self.approval_callback:
            result = self.approval_callback(player_config_name, ai_response, action_type, validation_error, parsed_value, valid_choices)
            action_msg = format_gm_action_message(result.action, player_config_name)
            self.broadcast_message(action_msg, "gm_action")
            return result
        else:
            return GMApprovalResult("accept")
    
    def show_player_status(self, players_data: Dict[str, Dict[str, Any]], show_gm_view: bool = True) -> None:
        pass
    
    def get_user_input(self, prompt: str, input_type: str = "text") -> str:
        return ""
    
    def show_game_log(self, game_log: List[Dict[str, Any]], count: int = 20) -> None:
        pass
    
    def show_player_history(self, player_config_name: str, player_info: Dict[str, Any]) -> None:
        pass
    
    def show_current_votes(self, votes_data: Dict[str, str]) -> None:
        pass
    
    def log_flow_event(self, message: str, level: str = "INFO", day: Optional[int] = None, phase: Optional[str] = None) -> None:
        pass

    def wait_for_continue(self, prompt: str) -> None:
        """Gradio模式下，此方法将被GradioUIAdapterImpl覆盖。"""
        pass


def create_ui_adapter(mode: str) -> UIAdapter:
    if mode == "terminal":
        return TerminalUIAdapter()
    elif mode == "gradio":
        # 返回基类，具体实现将在controller中被注入
        return GradioUIAdapter()
    else:
        raise ValueError(f"不支持的UI模式: {mode}")

_current_ui_adapter: Optional[UIAdapter] = None

def set_current_ui_adapter(adapter: UIAdapter) -> None:
    global _current_ui_adapter
    _current_ui_adapter = adapter

def get_current_ui_adapter() -> Optional[UIAdapter]:
    return _current_ui_adapter

def is_gradio_mode() -> bool:
    return _current_ui_adapter and _current_ui_adapter.mode == UIMode.GRADIO

def is_terminal_mode() -> bool:
    return not is_gradio_mode() # 简化