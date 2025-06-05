# gm_tools.py (修改版 - 颜色日志)
from typing import Optional, List

# 假设 terminal_colors.py 在项目根目录或者Python可以找到的路径下
try:
    from terminal_colors import (
        colorize, log_level_color, Colors, player_name_color,
        role_color, red, green, yellow, blue, magenta, cyan, grey, bold,
        underline
    )
except ImportError:
    # Fallback if terminal_colors is not found
    def colorize(text: str, _color_code: str) -> str: return text
    def log_level_color(_level: str) -> str: return ""
    class Colors: RESET = ""; BOLD = ""; RED = ""; GREEN = ""; YELLOW = ""; BLUE = ""; MAGENTA = ""; CYAN = ""; BRIGHT_BLACK = ""; BRIGHT_YELLOW = ""; BRIGHT_MAGENTA = ""; UNDERLINE = "" # Add more if needed
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
    def underline(text: str) -> str: return text


from game_state import GameState, PLAYER_STATUS_ALIVE, PLAYER_STATUS_DEAD
import game_config # For role list, VOTE_SKIP etc.

MODULE_COLOR = Colors.BRIGHT_YELLOW # GMTool 用亮黄色

def _log_gm_tool(message: str, level: str = "INFO", game_state_ref: Optional[GameState] = None): # game_state_ref for context
    level_colored = colorize(level, log_level_color(level))
    prefix_module = colorize("[GMTool:", MODULE_COLOR)
    print(f"{prefix_module}{level_colored}] {message}")

def _get_colored_player_display_name_from_gm(game_state: GameState, player_config_name: Optional[str], show_role: bool = False) -> str:
    if not player_config_name:
        return colorize("未知玩家", Colors.BRIGHT_BLACK)
    player_data = game_state.get_player_info(player_config_name)
    base_display_name = game_state.get_player_display_name(player_config_name, show_role_to_gm=show_role, show_number=True)
    return player_name_color(base_display_name, player_data, game_state)


def display_all_player_statuses(game_state: GameState):
    _log_gm_tool(bold(underline("--- 所有玩家状态 (GM视角) ---")), game_state_ref=game_state)
    if not game_state.players_data:
        _log_gm_tool(yellow("没有玩家数据可显示。"), "WARN", game_state_ref=game_state)
        return

    sorted_players = sorted(game_state.players_data.values(), key=lambda p: p.get("player_number", 0))

    for player_data in sorted_players:
        player_name_colored = _get_colored_player_display_name_from_gm(game_state, player_data["config_name"], False) # Role will be colored separately
        role_colored = role_color(player_data.get("role", "未知"))
        status_colored = colorize(player_data.get("status", "未知"), Colors.GREEN if player_data.get("status") == PLAYER_STATUS_ALIVE else Colors.RED)
        player_num = bold(str(player_data.get("player_number", "N/A")))

        details_parts = []
        role = player_data.get("role")
        if role == "女巫":
            save = player_data.get(game_config.WITCH_HAS_SAVE_POTION_KEY, False)
            poison = player_data.get(game_config.WITCH_HAS_POISON_POTION_KEY, False)
            details_parts.append(f"解药:{green('有') if save else red('无')}")
            details_parts.append(f"夜晚能力药剂:{green('有') if poison else red('无')}")
        if role == "猎人":
            can_shoot = player_data.get(game_config.HUNTER_CAN_SHOOT_KEY, False)
            details_parts.append(f"可行动:{green('是') if can_shoot else red('否')}")
        
        detail_str_colored = colorize(f" ({', '.join(details_parts)})", Colors.BRIGHT_BLACK) if details_parts else ""
        
        _log_gm_tool(f"玩家 {player_num}: {player_name_colored} - 身份: {role_colored}, 状态: {status_colored}{detail_str_colored}", game_state_ref=game_state)

def view_player_game_history(game_state: GameState, player_config_name: str):
    player_info = game_state.get_player_info(player_config_name)
    player_display_colored = _get_colored_player_display_name_from_gm(game_state, player_config_name, True)

    if not player_info:
        _log_gm_tool(red(f"未找到玩家 {player_display_colored} 的信息。"), "ERROR", game_state_ref=game_state)
        return

    _log_gm_tool(bold(underline(f"--- 玩家 {player_display_colored} 的消息历史 ---")), game_state_ref=game_state)
    history = player_info.get("history", [])
    if not history:
        _log_gm_tool(yellow("该玩家没有历史记录。"), "INFO", game_state_ref=game_state)
        return

    for i, entry in enumerate(history):
        msg_role = entry.get("role", "unknown_role")
        content_preview = entry.get("content", "")[:200] + (grey('...') if len(entry.get("content", "")) > 200 else '')
        
        msg_role_colored = colorize(msg_role.upper(), Colors.BOLD + (Colors.GREEN if msg_role == 'user' else Colors.CYAN if msg_role == 'assistant' else Colors.BLUE))
        
        meta_info_colored = []
        if "_meta" in entry:
            meta = entry["_meta"]
            if meta.get("action_type"): meta_info_colored.append(f"{colorize('action', Colors.BLUE)}:{colorize(meta['action_type'], Colors.YELLOW)}")
            if meta.get("is_error_response"): meta_info_colored.append(red("ERR_RESP"))
            if meta.get("is_accepted_invalid"): meta_info_colored.append(yellow("ACCEPT_INVALID"))
            if meta.get("is_gm_override"): meta_info_colored.append(colorize("GM_OVERRIDE", Colors.MAGENTA))
        
        meta_str_colored = colorize(f" ({', '.join(meta_info_colored)})", Colors.BRIGHT_BLACK) if meta_info_colored else ""
        
        _log_gm_tool(f"  [{bold(str(i+1))}] {msg_role_colored}{meta_str_colored}: {content_preview}", game_state_ref=game_state)

def display_game_log(game_state: GameState, count: int = 20):
    _log_gm_tool(bold(underline(f"--- 最新 {bold(str(count))} 条游戏事件日志 ---")), game_state_ref=game_state)
    if not game_state.game_log:
        _log_gm_tool(yellow("游戏日志为空。"), "INFO", game_state_ref=game_state)
        return
    
    start_index = max(0, len(game_state.game_log) - count)
    for i, log_entry in enumerate(game_state.game_log[start_index:], start=start_index):
        timestamp_colored = colorize(log_entry.get("timestamp", "未知时间"), Colors.BRIGHT_BLACK)
        event_type_colored = colorize(log_entry.get("event_type", "未知事件"), Colors.MAGENTA) # GameLog event types in magenta
        message = log_entry.get("message", "") # Message content can be complex, color sparingly or based on keywords
        details = log_entry.get("details", {})
        details_str_colored = colorize(f" (详情: {details})", Colors.GREY) if details else "" # Details in grey
        
        _log_gm_tool(f"[{bold(str(i+1))}] {timestamp_colored} [{event_type_colored}]: {message}{details_str_colored}", game_state_ref=game_state)

def gm_manual_set_player_status(game_state: GameState, player_config_name: str, new_status: str, reason: str = "GM手动设置"):
    player_display_colored = _get_colored_player_display_name_from_gm(game_state, player_config_name, True)
    if new_status not in [PLAYER_STATUS_ALIVE, PLAYER_STATUS_DEAD]:
        err_msg = (
            f"{red('错误')}：无效的状态 '{colorize(new_status, Colors.YELLOW)}'。"
            f"只能是 '{green(PLAYER_STATUS_ALIVE)}' 或 '{red(PLAYER_STATUS_DEAD)}'。"
        )
        _log_gm_tool(err_msg, "ERROR", game_state_ref=game_state)
        return
    
    player_info = game_state.get_player_info(player_config_name)
    if not player_info:
        _log_gm_tool(red(f"未找到玩家 {player_display_colored}。"), "ERROR", game_state_ref=game_state)
        return

    old_status_colored = colorize(player_info["status"], Colors.GREEN if player_info["status"] == PLAYER_STATUS_ALIVE else Colors.RED)
    new_status_colored = colorize(new_status, Colors.GREEN if new_status == PLAYER_STATUS_ALIVE else Colors.RED)
    
    success = game_state.update_player_status(player_config_name, new_status, reason=f"GM手动: {reason}") # update_player_status logs internally
    
    if success:
        _log_gm_tool(
            yellow(f"GM已将玩家 {player_display_colored} 的状态从 {old_status_colored} 修改为 {new_status_colored} (原因: {reason})。"),
            "WARN", game_state_ref=game_state
        )
    else: # Should ideally not happen if above checks pass, but as a fallback
        _log_gm_tool(red(f"GM尝试修改玩家 {player_display_colored} 状态失败。"), "ERROR", game_state_ref=game_state)

def display_current_votes(game_state: GameState):
    _log_gm_tool(bold(underline("--- 当前轮次投票情况 ---")), game_state_ref=game_state)
    if not game_state.votes_current_round:
        _log_gm_tool(yellow("尚未开始投票或没有投票数据。"), "INFO", game_state_ref=game_state)
        return
    for voter, target in game_state.votes_current_round.items():
        voter_display_colored = _get_colored_player_display_name_from_gm(game_state, voter, True)
        target_display_colored = colorize("弃票", Colors.GREEN) if target == game_config.VOTE_SKIP else _get_colored_player_display_name_from_gm(game_state, target, True)
        _log_gm_tool(f"{voter_display_colored} 投给了 --> {target_display_colored}", game_state_ref=game_state)