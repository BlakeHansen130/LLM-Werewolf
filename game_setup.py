# game_setup.py (修改版 - 颜色日志)
import json
import os
import random
from typing import List, Dict, Any, Optional

# 假设 terminal_colors.py 在项目根目录或者Python可以找到的路径下
try:
    from terminal_colors import (
        colorize, log_level_color, Colors, player_name_color,
        role_color, red, green, yellow, blue, magenta, cyan, grey, bold
    )
except ImportError:
    # Fallback if terminal_colors is not found
    def colorize(text: str, _color_code: str) -> str: return text
    def log_level_color(_level: str) -> str: return ""
    class Colors: RESET = ""; BOLD = ""; RED = ""; GREEN = ""; YELLOW = ""; BLUE = ""; MAGENTA = ""; CYAN = ""; BRIGHT_BLACK = ""; BRIGHT_YELLOW = ""
    def player_name_color(name: str, _player_data=None, _game_state=None) -> str: return name
    def role_color(name: str) -> str: return name
    def red(text: str) -> str: return text
    def green(text: str) -> str: return text
    def yellow(text: str) -> str: return text
    def blue(text: str) -> str: return text
    # (add other colors if needed by this file)


from game_state import GameState
from game_config import (
    CONFIG_FILENAME, ROLE_DISTRIBUTIONS, MIN_PLAYERS, ALL_POSSIBLE_ROLES,
    PHASE_START_GAME, PLAYER_STATUS_ALIVE,
    WITCH_HAS_SAVE_POTION_KEY, WITCH_HAS_POISON_POTION_KEY,
    HUNTER_CAN_SHOOT_KEY, PLAYER_IS_POISONED_KEY
)

MODULE_COLOR = Colors.CYAN # Setup 用青色

def _log_setup_event(message: str, level: str = "INFO"):
    level_colored = colorize(level, log_level_color(level))
    prefix_module = colorize("[Setup:", MODULE_COLOR)
    print(f"{prefix_module}{level_colored}] {message}")

def _get_colored_player_display_name_from_setup(game_state: GameState, player_config_name: Optional[str], show_role_to_gm: bool = False) -> str:
    """专门为本模块使用的玩家名上色函数"""
    if not player_config_name:
        return colorize("未知玩家", Colors.BRIGHT_BLACK)
    player_data = game_state.get_player_info(player_config_name)
    # 使用 game_state 的方法获取基础显示名，然后上色
    base_display_name = game_state.get_player_display_name(player_config_name, show_role_to_gm=show_role_to_gm, show_number=True)
    return player_name_color(base_display_name, player_data, game_state)


def _load_raw_player_configurations_from_file(filename: str = CONFIG_FILENAME) -> Optional[List[Dict[str, Any]]]:
    filename_colored = colorize(filename, Colors.BLUE)
    if not os.path.exists(filename):
        _log_setup_event(f"{red('错误')}: 配置文件 '{filename_colored}' 未找到。", "CRITICAL")
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            configs = json.load(f)
        if not isinstance(configs, list):
            _log_setup_event(f"{red('错误')}: 配置文件 '{filename_colored}' 的顶层必须是一个JSON数组 (列表)。", "CRITICAL")
            return None

        valid_configs = []
        seen_names = set()
        for i, p_config in enumerate(configs):
            p_name_val = p_config.get("name", "")
            if not p_name_val or not isinstance(p_name_val, str):
                _log_setup_event(f"{red('错误')}: 配置文件中第 {bold(str(i+1))} 个玩家缺少有效 'name' 字段。跳过此条目。", "ERROR")
                continue
            if p_name_val in seen_names:
                _log_setup_event(f"{red('错误')}: 配置文件中玩家名称 '{colorize(p_name_val, Colors.YELLOW)}' 重复。跳过第 {bold(str(i+1))} 个重复条目。", "ERROR")
                continue
            seen_names.add(p_name_val)
            valid_configs.append(p_config)

        if not valid_configs:
            _log_setup_event(f"{red('错误')}: 配置文件 '{filename_colored}' 中没有找到任何有效的玩家配置。", "CRITICAL")
            return None
        _log_setup_event(f"从 '{filename_colored}' 加载了 {bold(str(len(valid_configs)))} 条有效玩家配置。", "INFO")
        return valid_configs

    except json.JSONDecodeError:
        _log_setup_event(f"{red('错误')}: 配置文件 '{filename_colored}' 不是有效的JSON格式。", "CRITICAL")
        return None
    except Exception as e:
        _log_setup_event(f"{red('读取配置文件')} '{filename_colored}' {red('时发生未知错误')}: {e}", "CRITICAL")
        return None


def _assign_roles_and_populate_players_data(
    game_state: GameState,
    raw_player_configs: List[Dict[str, Any]]
) -> bool:
    num_actual_players = len(raw_player_configs)
    _log_setup_event(f"检测到 {bold(str(num_actual_players))} 名玩家。", "INFO")

    if num_actual_players not in ROLE_DISTRIBUTIONS:
        err_msg = (
            f"{red('错误')}: 未为 {bold(str(num_actual_players))} 名玩家精确定义角色配置。"
            f"请检查 game_config.py 中的 {colorize('ROLE_DISTRIBUTIONS', Colors.BLUE)}。"
        )
        _log_setup_event(err_msg, "CRITICAL")
        available_counts_colored = [colorize(str(k), Colors.GREEN) for k in sorted(ROLE_DISTRIBUTIONS.keys())]
        _log_setup_event(f"当前已定义的玩家数量配置有: {', '.join(available_counts_colored)}", "INFO")
        return False

    assigned_roles_list = ROLE_DISTRIBUTIONS[num_actual_players][:] # Create a copy
    roles_before_shuffle_colored = [role_color(r) for r in ROLE_DISTRIBUTIONS[num_actual_players]]
    random.shuffle(assigned_roles_list)
    _log_setup_event(
        f"为 {bold(str(num_actual_players))} 名玩家分配的角色池 (打乱前参考): {', '.join(roles_before_shuffle_colored)}",
        "DEBUG"
    )

    game_state.ai_player_config_names = [p_conf["name"] for p_conf in raw_player_configs]

    _log_setup_event(bold("--- 角色分配结果 (GM可见) ---"), "INFO")
    for i, player_config_entry in enumerate(raw_player_configs):
        config_name = player_config_entry["name"]
        assigned_role = assigned_roles_list[i]

        if assigned_role not in ALL_POSSIBLE_ROLES:
            warn_msg = (
                f"{colorize('警告', Colors.YELLOW)}: 角色 '{role_color(assigned_role)}' "
                f"分配给 {colorize(config_name, Colors.BRIGHT_YELLOW)} 但未在 "
                f"{colorize('ALL_POSSIBLE_ROLES', Colors.BLUE)} 中定义。"
            )
            _log_setup_event(warn_msg, "WARNING")

        game_state.players_data[config_name] = {
            "config_name": config_name,
            "player_number": i + 1,
            "role": assigned_role,
            "status": PLAYER_STATUS_ALIVE,
            "history": [],
            "api_endpoint": player_config_entry.get("api_endpoint"),
            "api_key": player_config_entry.get("api_key"),
            "model": player_config_entry.get("model"),
            "response_handler_type": player_config_entry.get("response_handler_type", "standard"),
            WITCH_HAS_SAVE_POTION_KEY: True if assigned_role == "女巫" else None,
            WITCH_HAS_POISON_POTION_KEY: True if assigned_role == "女巫" else None,
            HUNTER_CAN_SHOOT_KEY: True if assigned_role == "猎人" else None,
            PLAYER_IS_POISONED_KEY: False,
            "times_checked_by_prophet": 0,
            "is_confirmed_good_by_prophet": None,
        }
        # 使用辅助函数获取带颜色的玩家显示名
        player_display_colored = _get_colored_player_display_name_from_setup(game_state, config_name, True)
        _log_setup_event(f"{player_display_colored} (编号: {bold(str(i+1))})", "INFO")

    wolf_count = sum(1 for p_data in game_state.players_data.values() if p_data['role'] == '狼人')
    wolf_count_colored = bold(str(wolf_count))
    _log_setup_event(f"提示：当前配置中有 {wolf_count_colored} 名{role_color('狼人')}。", "INFO")
    return True


def initialize_game(game_state_instance: GameState) -> bool:
    _log_setup_event(bold("开始游戏初始化流程..."), "INFO")
    game_state_instance.current_game_phase = "GAME_SETUP_IN_PROGRESS"

    raw_player_configs = _load_raw_player_configurations_from_file()
    if not raw_player_configs:
        _log_setup_event(colorize("无法加载玩家配置，初始化失败。", Colors.RED), "CRITICAL")
        return False

    num_actual_players = len(raw_player_configs)

    if num_actual_players < MIN_PLAYERS:
        err_msg = (
            f"{red('错误')}: 玩家数量 ({bold(str(num_actual_players))}) 少于最小要求的 "
            f"{bold(str(MIN_PLAYERS))} 人。初始化失败。"
        )
        _log_setup_event(err_msg, "CRITICAL")
        return False

    if not _assign_roles_and_populate_players_data(game_state_instance, raw_player_configs):
        _log_setup_event(colorize("角色分配或玩家数据填充失败，初始化失败。", Colors.RED), "CRITICAL")
        return False

    game_state_instance.game_day = 0
    game_state_instance.current_game_phase = PHASE_START_GAME
    game_state_instance.human_gm_intervention_enabled = True
    # add_game_event_log 内部已经处理了颜色
    game_state_instance.add_game_event_log("SetupComplete", "游戏环境初始化成功。")

    _log_setup_event(green("游戏初始化成功完成。"), "INFO")
    return True

# --- 示例用法 (用于独立测试此模块) ---
if __name__ == "__main__":
    print(bold(blue("--- 测试 game_setup.py (已根据新需求调整) ---"))) # 主标题用蓝色粗体
    
    config_file_colored = colorize(CONFIG_FILENAME, Colors.BLUE)
    if not os.path.exists(CONFIG_FILENAME):
        print(yellow(f"创建示例配置文件: {config_file_colored}"))
        example_configs = [
            {"name": f"PlayerAI{i+1}", "model": "some-model"} for i in range(8) # 8人示例
        ]
        with open(CONFIG_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(example_configs, f, indent=2)
    else:
        print(green(f"使用已存在的配置文件: {config_file_colored}"))

    my_game_state = GameState()
    success = initialize_game(my_game_state)

    if success:
        print(bold(green("\n--- 初始化后的 GameState (部分摘要) ---")))
        print(f"游戏天数: {bold(str(my_game_state.game_day))}")
        print(f"当前阶段: {colorize(my_game_state.current_game_phase, Colors.MAGENTA)}")
        print(f"玩家配置名列表: {colorize(str(my_game_state.ai_player_config_names), Colors.CYAN)}")
        print(bold("\n部分玩家数据:"))
        for i, name in enumerate(my_game_state.ai_player_config_names):
            if i >= 3 and len(my_game_state.ai_player_config_names) > 3: # 限制只显示前3个
                print(grey("..."))
                break
            p_info = my_game_state.get_player_info(name)
            if p_info:
                # 使用辅助函数获取带颜色的玩家显示名
                display_name_colored = _get_colored_player_display_name_from_setup(my_game_state, name, True) # GM可见角色
                status_colored = colorize(p_info.get('status', 'N/A'), Colors.GREEN if p_info.get('status') == PLAYER_STATUS_ALIVE else Colors.RED)
                print(f"  玩家 {bold(str(p_info.get('player_number', 'N/A')))}: {display_name_colored}, 状态: {status_colored}")
                if p_info.get('role') == "女巫":
                    save_status = colorize("有", Colors.GREEN) if p_info.get(WITCH_HAS_SAVE_POTION_KEY) else colorize("无", Colors.RED)
                    poison_status = colorize("有", Colors.GREEN) if p_info.get(WITCH_HAS_POISON_POTION_KEY) else colorize("无", Colors.RED)
                    print(f"    {role_color('女巫')}药剂: 解药={save_status}, 夜晚能力药剂={poison_status}")
                if p_info.get('role') == "猎人":
                     shoot_status = colorize("可开枪", Colors.GREEN) if p_info.get(HUNTER_CAN_SHOOT_KEY) else colorize("不可开枪", Colors.RED)
                     print(f"    {role_color('猎人')}状态: {shoot_status}")
    else:
        print(red("游戏初始化失败。请检查日志输出。"))