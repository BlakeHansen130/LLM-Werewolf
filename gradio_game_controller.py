# gradio_game_controller.py (最终完整版)
import threading
import traceback
import re
from typing import Optional, Callable, Dict, Any, List

from gradio_interface import GradioGameInterface
from ui_adapter import GradioUIAdapter, GMApprovalResult, set_current_ui_adapter
from game_state import GameState
from game_setup import initialize_game
from game_flow_manager import run_game_loop
from assets_base64 import format_gm_action_message
import game_config

def strip_ansi_codes(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

class GradioGameController:
    # ... __init__, _setup_ui_adapter, create_interface, start_game 保持不变 ...
    def __init__(self):
        self.interface = GradioGameInterface()
        self.game_state: Optional[GameState] = None
        self.ui_adapter: Optional[GradioUIAdapter] = None
        self.game_running = False
        self._setup_ui_adapter()
    
    def _setup_ui_adapter(self):
        self.ui_adapter = GradioUIAdapterImpl(self)
        set_current_ui_adapter(self.ui_adapter)
        self.interface.set_ui_adapter(self.ui_adapter)
    
    def create_interface(self):
        return self.interface.create_interface()
    
    def start_game(self):
        if self.game_running: return
        try:
            self.game_state = GameState()
            success = initialize_game(self.game_state)
            if not success:
                self.ui_adapter.broadcast_message("❌ 游戏初始化失败！请检查配置文件。", "system")
                return
            self.interface.set_game_state(self.game_state)
            self.ui_adapter.set_game_state(self.game_state)
            self.game_running = True
            self.ui_adapter.broadcast_message("🎮 游戏已开始！", "system")
            run_game_loop(self.game_state, ui_adapter=self.ui_adapter)
        except Exception as e:
            error_msg = f"游戏主线程发生错误: {str(e)}"
            self.ui_adapter.broadcast_message(f"💥 {error_msg}", "system")
            print(f"Game thread error: {e}\n{traceback.format_exc()}")
        finally:
            self.game_running = False
            self.ui_adapter.broadcast_message("🏁 游戏已结束。", "system")


class GradioUIAdapterImpl(GradioUIAdapter):
    # ... __init__, broadcast_message, get_gm_approval 保持不变 ...
    def __init__(self, controller: GradioGameController):
        super().__init__()
        self.controller = controller
        self.interface = controller.interface
        self.message_history = []
        self.start_game_callback: Optional[Callable] = self.controller.start_game
    
    def broadcast_message(self, message: str, message_type: str = "info") -> None:
        try:
            clean_message = strip_ansi_codes(message)
            if message_type == "ai_speech":
                if ":" in clean_message and self.game_state:
                    parts = clean_message.split(":", 1)
                    speaker_name, content = parts[0].strip(), parts[1].strip()
                    self.message_history.append((f"**{speaker_name}**: {content}", None))
                else:
                    self.message_history.append((None, f"*{clean_message}*"))
            elif message_type.startswith("gm"):
                self.message_history.append((None, f"**GM**: {clean_message}"))
            else:
                self.message_history.append((None, f"*{clean_message}*"))
        except Exception as e:
            print(f"Error broadcasting message: {e}\n{traceback.format_exc()}")

    def get_gm_approval(self, player_config_name: str, ai_response: str,
                       action_type: str, validation_error: Optional[str] = None,
                       parsed_value: Any = None, valid_choices: Optional[List[str]] = None) -> GMApprovalResult:
        try:
            clean_ai_response = strip_ansi_codes(ai_response)
            clean_validation_error = strip_ansi_codes(validation_error) if validation_error else None
            clean_parsed_value = strip_ansi_codes(parsed_value) if parsed_value is not None else None
            
            if self.game_state:
                player_display = self.game_state.get_player_display_name(player_config_name)
                self.message_history.append((f"**{player_display}** (响应): {clean_ai_response}", None))

            result = self.interface.show_gm_approval(player_config_name, clean_ai_response, action_type, clean_validation_error, clean_parsed_value, valid_choices)
            
            action_msg = format_gm_action_message(result.action, self.game_state.get_player_display_name(player_config_name) if self.game_state else player_config_name)
            self.broadcast_message(action_msg, "gm_action")
            return result
        except Exception as e:
            print(f"Error in get_gm_approval: {e}\n{traceback.format_exc()}")
            return GMApprovalResult("accept")
    
    def show_player_status(self, players_data: Dict[str, Dict[str, Any]], show_gm_view: bool = True) -> None:
        pass
    def show_game_log(self, game_log: List[Dict[str, Any]], count: int = 20) -> None:
        pass
    def show_player_history(self, player_config_name: str, player_info: Dict[str, Any]) -> None:
        pass
    def show_current_votes(self, votes_data: Dict[str, str]) -> None:
        pass
    def get_user_input(self, prompt: str, input_type: str = "text") -> str:
        return "y"
    
    def log_flow_event(self, message: str, level: str = "INFO", day: Optional[int] = None, phase: Optional[str] = None) -> None:
        try:
            prefix = f"[第{day}天 {phase}] " if day is not None and phase else ""
            self.broadcast_message(f"{prefix}{message}", "system")
        except Exception as e:
            print(f"Error logging flow event: {e}\n{traceback.format_exc()}")

    # --- 新增的方法实现 ---
    def wait_for_continue(self, prompt: str) -> None:
        """通知UI层显示“继续”按钮，并阻塞等待点击信号。"""
        if self.interface and hasattr(self.interface, 'wait_for_ui_continue'):
            self.interface.wait_for_ui_continue(prompt)
        else:
            # 如果UI没有实现这个方法，为了防止游戏卡死，我们只在终端打印并自动继续
            print(f"WARN: UI does not support wait_for_continue. Auto-continuing after 3s. Prompt was: {prompt}")
            import time
            time.sleep(3)


def create_gradio_controller() -> GradioGameController:
    return GradioGameController()