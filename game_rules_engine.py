# game_rules_engine.py (修改版 - 颜色日志)
import random
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple

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
    def magenta(text: str) -> str: return text
    def cyan(text: str) -> str: return text
    def grey(text: str) -> str: return text
    def bold(text: str) -> str: return text

from game_state import GameState
from game_config import (
    PLAYER_STATUS_ALIVE, PLAYER_STATUS_DEAD,
    ALL_POSSIBLE_ROLES,
    VOTE_SKIP
)

MODULE_COLOR = Colors.YELLOW # RulesEngine 用黄色

def _log_rules_event(message: str, level: str = "INFO", game_state_ref: Optional[GameState] = None): # game_state_ref for context if needed
    level_colored = colorize(level, log_level_color(level))
    prefix_module = colorize("[RulesEngine:", MODULE_COLOR)
    print(f"{prefix_module}{level_colored}] {message}")

def _get_colored_player_display_name_from_rules(game_state: GameState, player_config_name: Optional[str], show_role: bool = False) -> str:
    if not player_config_name:
        return colorize("未知玩家", Colors.BRIGHT_BLACK)
    player_data = game_state.get_player_info(player_config_name)
    display_name = game_state.get_player_display_name(player_config_name, show_role_to_gm=show_role, show_number=True)
    return player_name_color(display_name, player_data, game_state)


def check_for_win_conditions(game_state: GameState) -> Optional[str]:
    alive_players_data = [p_data for p_data in game_state.players_data.values() if p_data["status"] == PLAYER_STATUS_ALIVE]
    if not alive_players_data:
        _log_rules_event(colorize("所有玩家都已出局，游戏平局或出现异常。", Colors.RED), "WARN", game_state_ref=game_state)
        game_state.game_winner_message = "异常平局：所有玩家都已出局" # Store for report
        return "异常平局"

    num_alive_wolves = sum(1 for p in alive_players_data if p["role"] == "狼人")
    num_alive_prophets = sum(1 for p in alive_players_data if p["role"] == "预言家")
    num_alive_witches = sum(1 for p in alive_players_data if p["role"] == "女巫")
    num_alive_hunters = sum(1 for p in alive_players_data if p["role"] == "猎人")
    num_alive_villagers = sum(1 for p in alive_players_data if p["role"] == "平民")

    num_alive_gods = num_alive_prophets + num_alive_witches + num_alive_hunters
    num_alive_good_guys = num_alive_gods + num_alive_villagers

    log_msg = (
        f"胜利条件检查: {role_color('狼人')}-{bold(str(num_alive_wolves))}, "
        f"神-{bold(str(num_alive_gods))} ({role_color('预言家')}{bold(str(num_alive_prophets))},"
        f"{role_color('女巫')}{bold(str(num_alive_witches))},{role_color('猎人')}{bold(str(num_alive_hunters))}), "
        f"{role_color('平民')}-{bold(str(num_alive_villagers))}, "
        f"总好人-{bold(str(num_alive_good_guys))}, 总存活-{bold(str(len(alive_players_data)))}"
    )
    _log_rules_event(log_msg, "DEBUG", game_state_ref=game_state)

    winner_message = None
    if num_alive_wolves == 0 and num_alive_good_guys > 0:
        winner_message = green("好人阵营胜利！(所有狼人出局)")
        _log_rules_event(winner_message, "INFO", game_state_ref=game_state)
        game_state.game_winner_message = "好人胜利"
        return "好人胜利"

    if num_alive_wolves > 0:
        if num_alive_wolves >= num_alive_good_guys:
            winner_message = red("狼人阵营胜利！(人数压制)")
            _log_rules_event(winner_message, "INFO", game_state_ref=game_state)
            game_state.game_winner_message = "狼人胜利"
            return "狼人胜利"
        if num_alive_gods == 0 and num_alive_villagers > 0:
            winner_message = red("狼人阵营胜利！(屠神边)")
            _log_rules_event(winner_message, "INFO", game_state_ref=game_state)
            game_state.game_winner_message = "狼人胜利"
            return "狼人胜利"
        if num_alive_villagers == 0 and num_alive_gods > 0:
            winner_message = red("狼人阵营胜利！(屠民边)")
            _log_rules_event(winner_message, "INFO", game_state_ref=game_state)
            game_state.game_winner_message = "狼人胜利"
            return "狼人胜利"
    return None


def determine_speech_order(game_state: GameState, last_night_dead_player: Optional[str] = None) -> List[str]:
    alive_player_config_names = game_state.get_alive_players()
    if not alive_player_config_names: return []
    sorted_alive_players = sorted(alive_player_config_names, key=lambda name: game_state.players_data[name]["player_number"])
    if not sorted_alive_players: return []

    start_player_config_name = None
    start_player_display = ""

    if last_night_dead_player:
        dead_player_info = game_state.get_player_info(last_night_dead_player)
        dead_player_display = _get_colored_player_display_name_from_rules(game_state, last_night_dead_player)
        if dead_player_info:
            dead_player_number = dead_player_info["player_number"]
            potential_starters = [p for p in sorted_alive_players if game_state.players_data[p]["player_number"] > dead_player_number]
            if potential_starters: start_player_config_name = potential_starters[0]
            else: start_player_config_name = sorted_alive_players[0]
            start_player_display = _get_colored_player_display_name_from_rules(game_state, start_player_config_name)
            _log_rules_event(f"昨夜死者为 {dead_player_display}。从其下一位 {start_player_display} 开始发言。", "DEBUG", game_state_ref=game_state)
        else:
            _log_rules_event(colorize(f"警告: 昨夜死者 {dead_player_display} 信息未找到，按平安夜规则决定发言顺序。", Colors.YELLOW), "WARN", game_state_ref=game_state)
            last_night_dead_player = None

    if not last_night_dead_player: # 平安夜逻辑
        if game_state.game_day == 1:
            start_player_config_name = sorted_alive_players[0]
            start_player_display = _get_colored_player_display_name_from_rules(game_state, start_player_config_name)
            _log_rules_event(f"第一天平安夜，从玩家 {start_player_display} 开始发言。", "DEBUG", game_state_ref=game_state)
        else:
            last_speaker_config_name = getattr(game_state, "last_round_final_speaker", None)
            if last_speaker_config_name and last_speaker_config_name in sorted_alive_players:
                try:
                    last_speaker_index = sorted_alive_players.index(last_speaker_config_name)
                    next_speaker_index = (last_speaker_index + 1) % len(sorted_alive_players)
                    start_player_config_name = sorted_alive_players[next_speaker_index]
                    last_speaker_display = _get_colored_player_display_name_from_rules(game_state, last_speaker_config_name)
                    start_player_display = _get_colored_player_display_name_from_rules(game_state, start_player_config_name)
                    _log_rules_event(f"后续平安夜，从上一轮最后发言者 {last_speaker_display} 的下一位 {start_player_display} 开始发言。", "DEBUG", game_state_ref=game_state)
                except ValueError:
                    start_player_config_name = sorted_alive_players[0]
                    start_player_display = _get_colored_player_display_name_from_rules(game_state, start_player_config_name)
                    _log_rules_event(colorize(f"后续平安夜，上一轮最后发言者已死亡或无效，从 {start_player_display} 开始发言。", Colors.YELLOW), "DEBUG", game_state_ref=game_state)
            else:
                start_player_config_name = sorted_alive_players[0]
                start_player_display = _get_colored_player_display_name_from_rules(game_state, start_player_config_name)
                _log_rules_event(colorize(f"后续平安夜，无法确定上一轮最后发言者，从 {start_player_display} 开始发言。", Colors.YELLOW), "DEBUG", game_state_ref=game_state)

    if not start_player_config_name:
        start_player_config_name = sorted_alive_players[0]
        start_player_display = _get_colored_player_display_name_from_rules(game_state, start_player_config_name)
        _log_rules_event(colorize(f"无法确定发言起点，默认从 {start_player_display} 开始。", Colors.YELLOW), "WARN", game_state_ref=game_state)

    try:
        start_index = sorted_alive_players.index(start_player_config_name)
    except ValueError:
        start_player_display = _get_colored_player_display_name_from_rules(game_state, start_player_config_name) # May fail if not in list
        _log_rules_event(colorize(f"错误: 起始发言玩家 {start_player_display} 不在当前存活玩家列表中！将从列表头开始。", Colors.RED), "ERROR", game_state_ref=game_state)
        start_index = 0
        
    speech_order = sorted_alive_players[start_index:] + sorted_alive_players[:start_index]
    game_state.speech_order_current_round = speech_order
    speech_order_display_colored = [_get_colored_player_display_name_from_rules(game_state, p) for p in speech_order]
    _log_rules_event(f"本轮发言顺序: {', '.join(speech_order_display_colored)}", "INFO", game_state_ref=game_state)
    return speech_order


def tally_votes_and_handle_ties(
    game_state: GameState,
    votes_this_round: Dict[str, str]
) -> Tuple[Optional[str], bool]:
    if not votes_this_round:
        _log_rules_event(colorize("没有收到任何投票。", Colors.YELLOW), "INFO", game_state_ref=game_state)
        return None, False

    vote_counts = Counter()
    num_actual_votes = 0
    _log_rules_event(bold("--- 本轮投票详情 ---"), "DEBUG", game_state_ref=game_state)
    for voter, target in votes_this_round.items():
        voter_display_colored = _get_colored_player_display_name_from_rules(game_state, voter)
        target_display_colored = colorize("弃票", Colors.GREEN) if target == VOTE_SKIP else _get_colored_player_display_name_from_rules(game_state, target)
        _log_rules_event(f"{voter_display_colored} 投给了 --> {target_display_colored}", "DEBUG", game_state_ref=game_state)
        if target != VOTE_SKIP and target in game_state.players_data and game_state.players_data[target]["status"] == PLAYER_STATUS_ALIVE:
            vote_counts[target] += 1
            num_actual_votes +=1
        elif target == VOTE_SKIP: pass
        else:
             _log_rules_event(colorize(f"警告: 玩家 {voter_display_colored} 的投票目标 '{target}' 无效 (可能已死亡或不存在)，此票作废。", Colors.YELLOW), "WARN", game_state_ref=game_state)

    if num_actual_votes == 0:
        _log_rules_event(colorize("所有有效投票均为弃票，本轮无人出局。", Colors.GREEN), "INFO", game_state_ref=game_state)
        return None, False

    vote_counts_display = { _get_colored_player_display_name_from_rules(game_state, k) : bold(str(v)) for k,v in vote_counts.items() }
    _log_rules_event(f"投票统计: {vote_counts_display}", "INFO", game_state_ref=game_state)
    if not vote_counts:
        _log_rules_event(colorize("计票后无有效得票者，无人出局。", Colors.YELLOW), "INFO", game_state_ref=game_state)
        return None, False

    max_votes = 0
    players_with_max_votes = []
    for player_config_name, count in vote_counts.items():
        if count > max_votes:
            max_votes = count
            players_with_max_votes = [player_config_name]
        elif count == max_votes:
            players_with_max_votes.append(player_config_name)

    if not players_with_max_votes:
        _log_rules_event(colorize("错误：无法确定最高票数玩家。", Colors.RED), "ERROR", game_state_ref=game_state)
        return None, False

    if len(players_with_max_votes) > 1:
        tied_players_display_colored = [_get_colored_player_display_name_from_rules(game_state, p) for p in players_with_max_votes]
        _log_rules_event(colorize(f"出现平票 ({bold(str(max_votes))}票): {', '.join(tied_players_display_colored)}。根据规则，本轮无人出局。", Colors.YELLOW), "INFO", game_state_ref=game_state)
        return None, False
    
    player_voted_out = players_with_max_votes[0]
    player_voted_out_display_colored = _get_colored_player_display_name_from_rules(game_state, player_voted_out)
    _log_rules_event(f"玩家 {player_voted_out_display_colored} 被投票出局 (获得 {bold(str(max_votes))} 票)。", "INFO", game_state_ref=game_state)
    return player_voted_out, False