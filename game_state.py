# game_state.py (修改版 - 颜色日志 + 为日志添加day/phase)
import time
from typing import List, Dict, Any, Optional, Tuple

# 假设 terminal_colors.py 在项目根目录或者Python可以找到的路径下
try:
    from terminal_colors import colorize, Colors, grey, log_level_color, player_name_color, red, green
except ImportError:
    # Fallback if terminal_colors is not found
    def colorize(text: str, _color_code: str) -> str: return text
    class Colors: RESET = ""; BRIGHT_BLACK = ""; RED = ""; GREEN = ""; YELLOW = "" # Add more if needed for this file
    def grey(text: str) -> str: return text
    def log_level_color(_level: str) -> str: return ""
    def player_name_color(name: str, _player_data=None, _game_state=None) -> str: return name
    def red(text: str) -> str: return text
    def green(text: str) -> str: return text


# 确保从 game_config 引入了所有需要的常量
from game_config import (
    PHASE_GAME_SETUP, PLAYER_STATUS_ALIVE, PLAYER_STATUS_DEAD,
    WITCH_HAS_SAVE_POTION_KEY, WITCH_HAS_POISON_POTION_KEY,
    HUNTER_CAN_SHOOT_KEY, PLAYER_IS_POISONED_KEY, VOTE_SKIP
)

MODULE_COLOR_GAMELOG = Colors.BRIGHT_BLACK # GameLog 用灰色

class GameState:
    def __init__(self):
        self.players_data: Dict[str, Dict[str, Any]] = {}
        self.ai_player_config_names: List[str] = []
        self.game_day: int = 0
        self.current_game_phase: str = PHASE_GAME_SETUP

        self.last_night_events: Dict[str, Any] = {}
        self.wolf_nominations_this_night: Dict[str, Optional[str]] = {} # 确保在 reset_nightly_events 前定义

        self.speech_order_current_round: List[str] = []
        self.votes_current_round: Dict[str, str] = {}
        self.round_speeches_log: List[Dict[str,str]] = []

        self.players_to_give_last_words: List[str] = [] # 这个变量目前在流程中没有被直接使用
        self.current_round_deaths: List[str] = []

        self.last_round_final_speaker: Optional[str] = None

        self.human_gm_intervention_enabled: bool = True
        self.game_log: List[Dict[str, Any]] = []
        
        self.game_winner_message: Optional[str] = None # 用于存储游戏结果消息

        self.reset_nightly_events() # 在所有相关属性定义后调用

    def reset_nightly_events(self):
        """重置每晚的事件记录。"""
        self.last_night_events = {
            "wolf_intended_kill_target": None,
            "witch_informed_of_kill_target": None,
            "witch_used_save_on": None,
            "witch_used_poison_on": None,
            "prophet_selected_target": None,
            "prophet_check_result_is_wolf": None,
            "final_deaths_this_night": [],
            "hunter_triggered_by_night_death": None
        }
        self.wolf_nominations_this_night.clear() # 使用 clear() 更安全

    def reset_daily_round_data(self):
        """重置每个白天发言/投票回合开始前的数据。"""
        self.speech_order_current_round = []
        self.votes_current_round.clear()
        self.round_speeches_log = []

    def add_game_event_log(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """向游戏日志中添加一条事件。"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_entry: Dict[str, Any] = {"timestamp": timestamp, "event_type": event_type, "message": message}
        
        # 自动添加 day 和 phase 到 details (如果外部没有提供)
        current_details = details.copy() if details else {}
        if "day" not in current_details:
            current_details["day"] = self.game_day
        if "phase" not in current_details:
            current_details["phase"] = self.current_game_phase
        
        log_entry["details"] = current_details # 使用更新后的 details

        self.game_log.append(log_entry)
        
        # 为终端输出上色
        event_type_colored = colorize(event_type, log_level_color(event_type.upper())) # 尝试用日志级别颜色
        details_print_str = f" {grey(str(current_details))}" if current_details else ""
        print(f"{colorize('[GameLog', MODULE_COLOR_GAMELOG)}|{event_type_colored}|{colorize(timestamp, Colors.BRIGHT_BLACK)}] {message}{details_print_str}")


    def get_player_info(self, player_config_name: str) -> Optional[Dict[str, Any]]:
        return self.players_data.get(player_config_name)

    def get_player_role(self, player_config_name: str) -> Optional[str]:
        player_info = self.get_player_info(player_config_name)
        return player_info.get("role") if player_info else None

    def get_player_status(self, player_config_name: str) -> Optional[str]:
        player_info = self.get_player_info(player_config_name)
        return player_info.get("status") if player_info else None

    def update_player_status(self, player_config_name: str, new_status: str, reason: Optional[str] = "unknown") -> bool:
        player_display_for_log = self.get_player_display_name(player_config_name) # 获取基础名用于日志
        if new_status not in [PLAYER_STATUS_ALIVE, PLAYER_STATUS_DEAD]:
            self.add_game_event_log("Error", f"尝试将玩家 {player_display_for_log} 设置为无效状态: {new_status}")
            return False

        player_info = self.get_player_info(player_config_name)
        if not player_info:
            self.add_game_event_log("Error", f"尝试更新不存在的玩家状态: {player_config_name}")
            return False

        old_status = player_info.get("status")
        if old_status == new_status:
            return True

        player_info["status"] = new_status
        log_message = f"玩家 {player_display_for_log} 状态从 {old_status} 更新为 {new_status} (原因: {reason})"
        self.add_game_event_log(
            "StatusUpdate",
            log_message,
            {
                "player": player_config_name,
                "new_status": new_status,
                "old_status": old_status,
                "reason": reason,
                "day": self.game_day,      # <-- 确保添加 day
                "phase": self.current_game_phase # <-- 确保添加 phase
            }
        )

        if new_status == PLAYER_STATUS_DEAD and old_status == PLAYER_STATUS_ALIVE:
            if player_config_name not in self.current_round_deaths:
                self.current_round_deaths.append(player_config_name)
        return True

    def get_alive_players(self, exclude_self_config_name: Optional[str] = None) -> List[str]:
        alive = [name for name, data in self.players_data.items() if data.get("status") == PLAYER_STATUS_ALIVE]
        if exclude_self_config_name and exclude_self_config_name in alive:
            alive.remove(exclude_self_config_name)
        return alive

    def get_player_display_name(self, player_config_name: Optional[str], show_role_to_gm: bool = False, show_number: bool = True) -> str:
        if not player_config_name:
            return "未知玩家"
        player_info = self.get_player_info(player_config_name)
        if not player_info:
            return player_config_name

        parts = []
        if show_number and "player_number" in player_info:
            parts.append(f"玩家{player_info['player_number']}")
        parts.append(player_config_name)
        if show_role_to_gm and "role" in player_info:
            parts.append(f"[{player_info['role']}]")
        return " ".join(parts)

    def add_player_message_to_history(
        self, player_config_name: str, content: str, role: str,
        action_type: Optional[str] = None, is_error: bool = False,
        is_accepted_invalid: bool = False, is_gm_override: bool = False
    ):
        player_info = self.get_player_info(player_config_name)
        if player_info:
            if "history" not in player_info or not isinstance(player_info["history"], list):
                player_info["history"] = []
            history_entry: Dict[str, Any] = {"role": role, "content": content}
            meta: Dict[str, Any] = {}
            if action_type: meta["action_type"] = action_type
            if is_error: meta["is_error_response"] = True
            if is_accepted_invalid: meta["is_accepted_invalid"] = True
            if is_gm_override: meta["is_gm_override"] = True
            if meta: history_entry["_meta"] = meta
            player_info["history"].append(history_entry)
            
            log_details = {
                "player": player_config_name,
                "role": role,
                "content_preview": content[:70]+"...",
                "action_type": action_type or "N/A", # 将 action_type 也加入 details
                "day": self.game_day,
                "phase": self.current_game_phase
            }
            if is_gm_override: log_details["gm_override"] = True

            self.add_game_event_log(
                "PlayerMessageLog",
                f"消息记录到 {self.get_player_display_name(player_config_name)} 历史 (Role: {role}, Action: {action_type or 'N/A'})",
                log_details
            )

    def get_player_history(self, player_config_name: str) -> List[Dict[str, str]]:
        player_info = self.get_player_info(player_config_name)
        if player_info and "history" in player_info and isinstance(player_info["history"], list):
            return [{"role": entry["role"], "content": entry["content"]} for entry in player_info["history"] if "role" in entry and "content" in entry]
        return []

    def use_witch_potion(self, witch_config_name: str, potion_type: str, target_player_name: Optional[str] = None): # 添加 target_player_name
        witch_info = self.get_player_info(witch_config_name)
        witch_display_name = self.get_player_display_name(witch_config_name)
        if witch_info and witch_info["role"] == "女巫":
            key_to_set_false = WITCH_HAS_SAVE_POTION_KEY if potion_type == "save" else WITCH_HAS_POISON_POTION_KEY if potion_type == "poison" else None
            if key_to_set_false and witch_info.get(key_to_set_false, False):
                witch_info[key_to_set_false] = False
                
                log_details = {
                    "player": witch_config_name,
                    "potion_type": potion_type,
                    "day": self.game_day,
                    "phase": self.current_game_phase
                }
                if target_player_name: # 如果有目标，也记录到 details
                    log_details["target"] = target_player_name
                message = f"女巫 {witch_display_name} 使用了 {potion_type} 药剂"
                if target_player_name:
                    message += f" 于玩家 {self.get_player_display_name(target_player_name)}"
                message += "."
                self.add_game_event_log("PotionUsed", message, log_details)
            else:
                self.add_game_event_log(
                    "PotionError",
                    f"女巫 {witch_display_name} 尝试使用无效或已用尽的 {potion_type} 药剂。",
                    {"player": witch_config_name, "potion_type": potion_type, "day": self.game_day, "phase": self.current_game_phase}
                )

    def can_witch_use_potion(self, witch_config_name: str, potion_type: str) -> bool:
        witch_info = self.get_player_info(witch_config_name)
        if witch_info and witch_info["role"] == "女巫":
            key_to_check = WITCH_HAS_SAVE_POTION_KEY if potion_type == "save" else WITCH_HAS_POISON_POTION_KEY if potion_type == "poison" else None
            return witch_info.get(key_to_check, False) if key_to_check else False
        return False

    def can_hunter_shoot(self, hunter_config_name: str) -> bool:
        hunter_info = self.get_player_info(hunter_config_name)
        if not hunter_info or hunter_info.get("role") != "猎人": return False
        return hunter_info.get("status") == PLAYER_STATUS_DEAD and \
               not self.is_player_poisoned_this_round(hunter_config_name) and \
               hunter_info.get(HUNTER_CAN_SHOOT_KEY, False)

    def hunter_uses_shot(self, hunter_config_name: str, target_player_name: Optional[str] = None): # 添加 target_player_name
        hunter_info = self.get_player_info(hunter_config_name)
        hunter_display_name = self.get_player_display_name(hunter_config_name)
        if hunter_info and hunter_info["role"] == "猎人":
            if hunter_info.get(HUNTER_CAN_SHOOT_KEY, False):
                hunter_info[HUNTER_CAN_SHOOT_KEY] = False
                log_details = {
                    "player": hunter_config_name,
                    "day": self.game_day,
                    "phase": self.current_game_phase
                }
                message = f"猎人 {hunter_display_name} 已使用其特殊能力"
                if target_player_name:
                    log_details["target"] = target_player_name
                    message += f" 指向玩家 {self.get_player_display_name(target_player_name)}"
                message += "."
                self.add_game_event_log("HunterAbilityUsed", message, log_details)
            else:
                self.add_game_event_log(
                    "HunterAbilityError",
                    f"猎人 {hunter_display_name} 尝试使用已用尽或无效的特殊能力。",
                    {"player": hunter_config_name, "day": self.game_day, "phase": self.current_game_phase}
                )

    def set_player_poisoned_status(self, player_config_name: Optional[str], is_poisoned: bool):
        log_details_base = {"day": self.game_day, "phase": self.current_game_phase}
        if player_config_name is None:
            for p_name_iter in list(self.players_data.keys()):
                p_info_iter = self.get_player_info(p_name_iter)
                if p_info_iter and p_info_iter.get(PLAYER_IS_POISONED_KEY, False):
                    p_info_iter[PLAYER_IS_POISONED_KEY] = False
                    details = log_details_base.copy()
                    details["player"] = p_name_iter
                    details["poisoned"] = False
                    self.add_game_event_log("SpecialConditionUpdate", f"清除了玩家 {self.get_player_display_name(p_name_iter)} 的中毒标记。", details)
            return

        player_info = self.get_player_info(player_config_name)
        if player_info:
            player_info[PLAYER_IS_POISONED_KEY] = is_poisoned
            if is_poisoned:
                details = log_details_base.copy()
                details["player"] = player_config_name
                details["poisoned"] = True
                self.add_game_event_log("SpecialConditionUpdate", f"玩家 {self.get_player_display_name(player_config_name)} 被标记为本轮中毒。", details)

    def is_player_poisoned_this_round(self, player_config_name: str) -> bool:
        player_info = self.get_player_info(player_config_name)
        return player_info.get(PLAYER_IS_POISONED_KEY, False) if player_info else False