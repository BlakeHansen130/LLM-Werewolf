# player_interaction.py (修改版 - 支持狼人提名验证 + 颜色日志)
import time
from typing import List, Dict, Any, Optional, Callable, Tuple

# 假设 terminal_colors.py 在项目根目录或者Python可以找到的路径下
try:
    from terminal_colors import (
        colorize, log_level_color, Colors, player_name_color,
        red, green, yellow, blue, magenta, cyan, grey, bold,
        ai_response_color, underline # 确保导入所有需要的
    )
except ImportError:
    # Fallback if terminal_colors is not found
    def colorize(text: str, _color_code: str) -> str: return text
    def log_level_color(_level: str) -> str: return ""
    class Colors: RESET = ""; BOLD = ""; RED = ""; GREEN = ""; YELLOW = ""; BLUE = ""; MAGENTA = ""; CYAN = ""; BRIGHT_BLACK = ""; BRIGHT_YELLOW = ""; BRIGHT_MAGENTA = ""; BRIGHT_WHITE = ""; UNDERLINE = ""
    def player_name_color(name: str, _player_data=None, _game_state=None) -> str: return name
    def red(text: str) -> str: return text
    def green(text: str) -> str: return text
    def yellow(text: str) -> str: return text
    def blue(text: str) -> str: return text
    def magenta(text: str) -> str: return text
    def cyan(text: str) -> str: return text
    def grey(text: str) -> str: return text
    def bold(text: str) -> str: return text
    def ai_response_color(text: str) -> str: return text
    def underline(text: str) -> str: return text


from game_state import GameState
from ai_interface import make_api_call_to_ai
from werewolf_prompts import generate_prompt_for_action
import game_config # For VOTE_SKIP etc.

MODULE_COLOR = Colors.CYAN # PlayerInteract 用青色

def _get_colored_player_display_name_from_interaction(game_state: GameState, player_config_name: Optional[str], show_role_to_gm: bool = False) -> str:
    """专门为本模块使用的玩家名上色函数，避免与 game_flow_manager 中的重名"""
    if not player_config_name:
        return colorize("未知玩家", Colors.BRIGHT_BLACK)
    player_data = game_state.get_player_info(player_config_name)
    # 使用 game_state 的方法获取基础显示名，然后上色
    base_display_name = game_state.get_player_display_name(player_config_name, show_role_to_gm=show_role_to_gm, show_number=True)
    return player_name_color(base_display_name, player_data, game_state)


def _log_player_interact(message: str, level: str = "INFO", player_config_name: Optional[str] = None, game_state_ref: Optional[GameState] = None):
    level_colored = colorize(level, log_level_color(level))
    prefix_module = colorize("[PlayerInteract:", MODULE_COLOR)

    prefix = f"{prefix_module}{level_colored}]"
    if player_config_name and game_state_ref:
        p_name_colored = _get_colored_player_display_name_from_interaction(game_state_ref, player_config_name, True)
        prefix += f" ({p_name_colored})"
    elif player_config_name:
        prefix += f" ({colorize(player_config_name, Colors.BRIGHT_YELLOW)})" # Fallback color
    print(f"{prefix} {message}")


def _validate_ai_response(
    response_text: Optional[str],
    action_type: str,
    game_state: GameState,
    player_config_name: str,
    action_specific_info: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str], Optional[Any]]:
    """
    验证AI的响应是否符合当前行动类型的格式和基本规则。
    返回 (is_valid, error_message_for_gm, parsed_action_value)
    """
    if response_text is None or not response_text.strip():
        return False, colorize("AI响应为空或仅包含空白。", Colors.RED), None

    response = response_text.strip()
    cleaned_response_for_keyword_match = response.lower().strip(".。！!?？【】")

    # (内部验证逻辑不变，但错误消息可以上色)
    # ... (所有 action_type 的 if/elif 分支)

    if action_type in ["speech", "last_words"]:
        if len(response) < 1:
            return False, colorize("发言/遗言内容过短 (少于1字符)。", Colors.RED), None
        return True, None, response

    elif action_type == "vote":
        alive_players_config_names = game_state.get_alive_players(exclude_self_config_name=player_config_name)
        valid_targets_display_colored = [
            _get_colored_player_display_name_from_interaction(game_state, p_name) for p_name in alive_players_config_names
        ]

        if cleaned_response_for_keyword_match in ["弃票", "skip", "pass"]:
            return True, None, game_config.VOTE_SKIP

        if response in alive_players_config_names:
            return True, None, response
        for p_conf_name in alive_players_config_names:
            if game_state.get_player_display_name(p_conf_name, show_number=True) == response:
                return True, None, p_conf_name
            if response == str(game_state.players_data[p_conf_name]["player_number"]):
                return True, None, p_conf_name
        err_msg = f"投票目标 '{colorize(response, Colors.YELLOW)}' 无效。可选: {', '.join(valid_targets_display_colored)} 或 '{colorize(game_config.VOTE_SKIP, Colors.GREEN)}'."
        return False, colorize(err_msg, Colors.RED), None

    elif action_type == "prophet_check":
        prophet_info = game_state.get_player_info(player_config_name)
        checked_targets_by_this_prophet = prophet_info.get("prophet_check_history", [])
        potential_targets = [p_name for p_name in game_state.get_alive_players(exclude_self_config_name=player_config_name) if p_name not in [entry["target"] for entry in checked_targets_by_this_prophet]]
        valid_targets_display_colored = [_get_colored_player_display_name_from_interaction(game_state, p_name) for p_name in potential_targets]
        if not potential_targets:
             if cleaned_response_for_keyword_match in ["不验", "跳过", "无法查验", "不查验"]: return True, None, None
             return False, colorize("没有可供查验的目标了，但AI未表示不查验。", Colors.RED), None
        if cleaned_response_for_keyword_match in ["不验", "跳过", "无法查验", "不查验"]: return True, None, None
        if response in potential_targets: return True, None, response
        for p_conf_name in potential_targets:
            if game_state.get_player_display_name(p_conf_name, show_number=True) == response: return True, None, p_conf_name
            if response == str(game_state.players_data[p_conf_name]["player_number"]): return True, None, p_conf_name
        err_msg = f"查验目标 '{colorize(response, Colors.YELLOW)}' 无效。可选: {', '.join(valid_targets_display_colored)} 或 '{colorize('不查验', Colors.GREEN)}'."
        return False, colorize(err_msg, Colors.RED), None

    elif action_type == game_config.ACTION_WOLF_NOMINATE:
        wolf_team_alive = [p_name for p_name, p_data in game_state.players_data.items() if p_data["role"] == "狼人" and p_data["status"] == game_config.PLAYER_STATUS_ALIVE]
        killable_targets = [p_name for p_name in game_state.get_alive_players() if p_name not in wolf_team_alive]
        valid_targets_display_colored = [_get_colored_player_display_name_from_interaction(game_state, p_name) for p_name in killable_targets]
        if not killable_targets:
             if cleaned_response_for_keyword_match in ["不刀", "无法袭击", "空刀", "空过", "本回合不行动", "不提名", "跳过"]: return True, None, None
             return False, colorize("没有可供提名的非狼人目标了，但AI未表示不提名。", Colors.RED), None
        if cleaned_response_for_keyword_match in ["不刀", "无法袭击", "空刀", "空过", "本回合不行动", "不提名", "跳过"]: return True, None, None
        if response in killable_targets: return True, None, response
        for p_conf_name in killable_targets:
            if game_state.get_player_display_name(p_conf_name, show_number=True) == response: return True, None, p_conf_name
            if response == str(game_state.players_data[p_conf_name]["player_number"]): return True, None, p_conf_name
        err_msg = f"提名目标 '{colorize(response, Colors.YELLOW)}' 无效。可选: {', '.join(valid_targets_display_colored)} 或 '{colorize('不提名', Colors.GREEN)}'."
        return False, colorize(err_msg, Colors.RED), None

    elif action_type == "wolf_kill":
        wolf_team_alive = [p_name for p_name, p_data in game_state.players_data.items() if p_data["role"] == "狼人" and p_data["status"] == game_config.PLAYER_STATUS_ALIVE]
        killable_targets = [p_name for p_name in game_state.get_alive_players() if p_name not in wolf_team_alive]
        valid_targets_display_colored = [_get_colored_player_display_name_from_interaction(game_state, p_name) for p_name in killable_targets]
        if not killable_targets:
             if cleaned_response_for_keyword_match in ["不刀", "无法袭击", "空刀", "空过", "本回合不行动"]: return True, None, None
             return False, colorize("没有可供袭击的目标了，但AI未表示空刀。", Colors.RED), None
        if cleaned_response_for_keyword_match in ["不刀", "无法袭击", "空刀", "空过", "本回合不行动"]: return True, None, None
        if response in killable_targets: return True, None, response
        for p_conf_name in killable_targets:
            if game_state.get_player_display_name(p_conf_name, show_number=True) == response: return True, None, p_conf_name
            if response == str(game_state.players_data[p_conf_name]["player_number"]): return True, None, p_conf_name
        err_msg = f"袭击目标 '{colorize(response, Colors.YELLOW)}' 无效。可选: {', '.join(valid_targets_display_colored)} 或 '{colorize('空刀', Colors.GREEN)}'."
        return False, colorize(err_msg, Colors.RED), None

    elif action_type == "witch_save":
        if not game_state.can_witch_use_potion(player_config_name, "save"):
            if cleaned_response_for_keyword_match in ["否", "no", "不救", "没有解药", "不使用解药"]: return True, None, False
            return False, colorize("女巫没有解药，但AI未明确表示不使用。", Colors.RED), False
        if cleaned_response_for_keyword_match in ["是", "yes", "救", "使用解药"]: return True, None, True
        elif cleaned_response_for_keyword_match in ["否", "no", "不救", "不使用解药"]: return True, None, False
        else:
            killed_player_name = action_specific_info.get("killed_player_name", "未知玩家") if action_specific_info else "未知玩家"
            killed_display_colored = _get_colored_player_display_name_from_interaction(game_state, killed_player_name)
            err_msg = f"对于是否拯救【{killed_display_colored}】，请明确回复【{colorize('是', Colors.GREEN + Colors.BOLD)}】或【{colorize('否', Colors.RED + Colors.BOLD)}】。"
            return False, colorize(err_msg, Colors.RED), None

    elif action_type == "witch_poison":
        if not game_state.can_witch_use_potion(player_config_name, "poison"):
            if cleaned_response_for_keyword_match in ["不使用", "不用", "不使用毒药", "没有毒药"]: return True, None, None
            return False, colorize("女巫没有夜晚能力药剂，但AI未明确表示不使用。", Colors.RED), None
        if cleaned_response_for_keyword_match in ["不使用", "不用", "不使用毒药"]: return True, None, None
        poisonable_targets = game_state.get_alive_players(exclude_self_config_name=player_config_name)
        valid_targets_display_colored = [_get_colored_player_display_name_from_interaction(game_state, p_name) for p_name in poisonable_targets]
        if not poisonable_targets and cleaned_response_for_keyword_match in ["不使用", "不用", "不使用毒药"]: return True, None, None
        elif not poisonable_targets: return False, colorize(f"下毒目标 '{colorize(response, Colors.YELLOW)}' 无效 (无可选目标)。请回复【{colorize('不使用', Colors.GREEN)}】。", Colors.RED), None
        if response in poisonable_targets: return True, None, response
        for p_conf_name in poisonable_targets:
            if game_state.get_player_display_name(p_conf_name, show_number=True) == response: return True, None, p_conf_name
            if response == str(game_state.players_data[p_conf_name]["player_number"]): return True, None, p_conf_name
        err_msg = f"下毒目标 '{colorize(response, Colors.YELLOW)}' 无效。可选: {', '.join(valid_targets_display_colored)} 或 '{colorize('不使用', Colors.GREEN)}'."
        return False, colorize(err_msg, Colors.RED), None

    elif action_type == "hunter_shoot":
        shootable_targets = [p_name for p_name in game_state.get_alive_players() if p_name != player_config_name]
        valid_targets_display_colored = [_get_colored_player_display_name_from_interaction(game_state, p_name) for p_name in shootable_targets]
        if not shootable_targets:
            if cleaned_response_for_keyword_match in ["不开枪", "无法开枪", "不射击", "不使用此能力"]: return True, None, None
            return False, colorize("没有可供开枪的目标了，但AI未表示不开枪。", Colors.RED), None
        if cleaned_response_for_keyword_match in ["不开枪", "无法开枪", "不射击", "不使用此能力"]: return True, None, None
        if response in shootable_targets: return True, None, response
        for p_conf_name in shootable_targets:
            if game_state.get_player_display_name(p_conf_name, show_number=True) == response: return True, None, p_conf_name
            if response == str(game_state.players_data[p_conf_name]["player_number"]): return True, None, p_conf_name
        err_msg = f"开枪目标 '{colorize(response, Colors.YELLOW)}' 无效。可选: {', '.join(valid_targets_display_colored)} 或 '{colorize('不开枪', Colors.GREEN)}'."
        return False, colorize(err_msg, Colors.RED), None

    _log_player_interact(colorize(f"警告: Action type '{action_type}' 没有特定的响应验证逻辑，默认有效。", Colors.YELLOW), "WARN", player_config_name, game_state_ref=game_state)
    return True, None, response


def get_ai_decision_with_gm_approval(
    game_state: GameState,
    player_config_name: str,
    action_type: str,
    action_specific_info: Optional[Dict[str, Any]] = None,
    max_api_error_auto_retries: int = 1
) -> Optional[Any]:
    player_info = game_state.get_player_info(player_config_name)
    p_display_name_colored = _get_colored_player_display_name_from_interaction(game_state, player_config_name, True)

    if not player_info:
        _log_player_interact(colorize(f"错误: 无法为不存在的玩家 {p_display_name_colored} 获取决策。", Colors.RED), "ERROR", player_config_name, game_state_ref=game_state)
        return None

    if "history" not in player_info or not isinstance(player_info["history"], list):
        player_info["history"] = []

    while True:
        current_history_for_prompt = game_state.get_player_history(player_config_name)
        messages_for_ai = generate_prompt_for_action(game_state, player_config_name, action_type, current_history_for_prompt, action_specific_info)

        action_type_colored = colorize(action_type, Colors.YELLOW)
        if not messages_for_ai or len(messages_for_ai) < 1:
            _log_player_interact(f"为 {p_display_name_colored} 生成的prompt为空或不完整，GM需要介入。", "ERROR", player_config_name, game_state_ref=game_state)
            user_choice = input(
                colorize(f"GM Alert: 无法为 {p_display_name_colored} 生成行动 '{action_type_colored}' 的有效Prompt。\n", Colors.RED) +
                f"[{bold('M')}]手动输入行动, [{bold('S')}]跳过此行动: "
            ).strip().upper()
            if user_choice == 'M':
                manual_input = input(f"请输入 {p_display_name_colored} 的 {action_type_colored} 内容: ").strip()
                if manual_input:
                    game_state.add_player_message_to_history(player_config_name, manual_input, role="assistant", action_type=f"gm_override_{action_type}", is_gm_override=True)
                    _, _, parsed_value = _validate_ai_response(manual_input, action_type, game_state, player_config_name, action_specific_info)
                    return parsed_value if parsed_value is not None else manual_input
                else:
                    _log_player_interact(colorize("GM手动输入为空，视为跳过。", Colors.YELLOW), "WARN", player_config_name, game_state_ref=game_state)
                    game_state.add_player_message_to_history(player_config_name, f"GM跳过了此行动({action_type}) due to prompt error and empty manual input", role="system", action_type=f"gm_skip_{action_type}", is_gm_override=True)
                    return None
            else:
                _log_player_interact(f"GM选择跳过 {p_display_name_colored} 的行动 {action_type_colored} (因prompt生成错误)。", "WARN", player_config_name, game_state_ref=game_state)
                game_state.add_player_message_to_history(player_config_name, f"GM跳过了此行动({action_type}) due to prompt error", role="system", action_type=f"gm_skip_{action_type}", is_gm_override=True)
                return None

        _log_player_interact(f"准备为 {p_display_name_colored} (行动: {action_type_colored}) 调用API。将发送的消息:", "DEBUG", player_config_name, game_state_ref=game_state)
        for i, msg in enumerate(messages_for_ai):
            role_colored = colorize(msg['role'].upper(), Colors.BOLD + (Colors.GREEN if msg['role'] == 'user' else Colors.CYAN if msg['role'] == 'assistant' else Colors.BLUE))
            _log_player_interact(f"  MSG[{i+1}/{len(messages_for_ai)}] Role: {role_colored}, Content(部分): {grey(str(msg['content'])[:250])}{grey('...') if len(str(msg['content'])) > 250 else ''}", "DEBUG", player_config_name, game_state_ref=game_state)

        ai_response_text = None
        api_error_message = None
        api_call_attempts_current_round = 0

        while True:
            api_call_attempts_current_round += 1
            _log_player_interact(f"请求AI ({p_display_name_colored}) 执行 '{action_type_colored}' (API尝试 {colorize(str(api_call_attempts_current_round), Colors.BOLD)})", "INFO", player_config_name, game_state_ref=game_state)
            ai_response_text, api_error_message = make_api_call_to_ai(
                player_config_name=player_config_name, messages=messages_for_ai,
                api_endpoint=player_info.get("api_endpoint"), api_key=player_info.get("api_key"),
                model_name=player_info.get("model"), response_handler_type=player_info.get("response_handler_type", "standard"),
                player_display_name_for_parser=game_state.get_player_display_name(player_config_name)
            )
            if not api_error_message: break
            _log_player_interact(colorize(f"API调用失败: {api_error_message}", Colors.RED), "ERROR", player_config_name, game_state_ref=game_state)
            if api_call_attempts_current_round <= max_api_error_auto_retries:
                _log_player_interact(colorize(f"将在3秒后自动重试API调用 ({api_call_attempts_current_round}/{max_api_error_auto_retries})...", Colors.YELLOW), "WARN", player_config_name, game_state_ref=game_state)
                time.sleep(3)
                continue
            else:
                print(colorize(f"\n--- GM干预: API调用持续失败 ({p_display_name_colored}, 行动: {action_type_colored}) ---", Colors.BOLD + Colors.RED))
                print(colorize(f"已尝试 {api_call_attempts_current_round} 次。最后错误: {api_error_message}", Colors.RED))
                gm_api_choice = input(
                    f"请选择操作: [{bold('R')}]再次尝试API调用, [{bold('M')}]手动输入此AI行动, [{bold('S')}]跳过此AI行动: "
                ).strip().upper()
                if gm_api_choice == 'R': continue
                elif gm_api_choice == 'M':
                    manual_input = input(f"请输入 {p_display_name_colored} 的 {action_type_colored} 内容: ").strip()
                    game_state.add_player_message_to_history(player_config_name, manual_input, role="assistant", action_type=f"gm_override_{action_type}", is_gm_override=True)
                    _, _, parsed_value = _validate_ai_response(manual_input, action_type, game_state, player_config_name, action_specific_info)
                    return parsed_value if parsed_value is not None else manual_input
                else:
                    _log_player_interact(f"GM选择跳过 {p_display_name_colored} 的行动 {action_type_colored} (因API持续错误)。", "WARN", player_config_name, game_state_ref=game_state)
                    game_state.add_player_message_to_history(player_config_name, f"GM跳过了此行动({action_type}) due to persistent API error", role="system", action_type=f"gm_skip_{action_type}", is_gm_override=True)
                    return None
        
        print(colorize(f"\n--- GM审核点: {p_display_name_colored} (行动: {action_type_colored}) ---", Colors.BOLD + Colors.MAGENTA))
        print(f"AI ({_get_colored_player_display_name_from_interaction(game_state, player_config_name)}) 响应原文:\n```\n{ai_response_color(ai_response_text)}\n```")
        is_valid, validation_error_msg, parsed_action_value = _validate_ai_response(ai_response_text, action_type, game_state, player_config_name, action_specific_info)

        if not is_valid:
            print(colorize(f"AI响应内容校验失败: {validation_error_msg}", Colors.RED)) # validation_error_msg is already colored
            gm_content_choice = input(
                f"请选择操作: [{bold('R')}]让AI重试(提供修正), [{bold('M')}]手动输入, [{bold('A')}]接受此原始响应(风险自负), [{bold('S')}]跳过: "
            ).strip().upper()
            if gm_content_choice == 'R':
                game_state.add_player_message_to_history(player_config_name, ai_response_text, role="assistant", action_type=action_type, is_error=True)
                correction_prompt = f"GM指示：你之前的回答 '{str(ai_response_text)[:70].replace(chr(10), ' ')}...' 因为 “{validation_error_msg}” 是无效的。请修正并重新回答。"
                game_state.add_player_message_to_history(player_config_name, correction_prompt, role="user", action_type="gm_correction_for_ai")
                continue
            elif gm_content_choice == 'M':
                manual_input = input(f"请输入 {p_display_name_colored} 的 {action_type_colored} 内容: ").strip()
                game_state.add_player_message_to_history(player_config_name, manual_input, role="assistant", action_type=f"gm_override_{action_type}", is_gm_override=True)
                _, _, parsed_value = _validate_ai_response(manual_input, action_type, game_state, player_config_name, action_specific_info)
                return parsed_value if parsed_value is not None else manual_input
            elif gm_content_choice == 'A':
                _log_player_interact(colorize(f"GM接受了来自 {p_display_name_colored} 的原始无效响应: '{str(ai_response_text)[:70]}...'", Colors.YELLOW), "WARN", player_config_name, game_state_ref=game_state)
                game_state.add_player_message_to_history(player_config_name, ai_response_text, role="assistant", action_type=action_type, is_accepted_invalid=True)
                return ai_response_text
            else:
                _log_player_interact(f"GM选择跳过 {p_display_name_colored} 的行动 {action_type_colored} (因内容无效)。", "WARN", player_config_name, game_state_ref=game_state)
                game_state.add_player_message_to_history(player_config_name, f"GM跳过了此行动({action_type}) due to invalid AI response", role="system", action_type=f"gm_skip_{action_type}", is_gm_override=True)
                return None
        else:
            parsed_value_display = colorize(str(parsed_action_value)[:100], Colors.BRIGHT_WHITE) + (grey('...') if len(str(parsed_action_value)) > 100 else '')
            print(f"{green('AI响应有效')}。解析后的行动值: '{parsed_value_display}'")
            gm_final_choice = input(
                f"请选择操作: [{bold('Y')}]确认采纳, [{bold('R')}]让AI重试(不满意), [{bold('M')}]手动修改/覆盖: "
            ).strip().upper()
            if gm_final_choice == 'Y':
                game_state.add_player_message_to_history(player_config_name, ai_response_text, role="assistant", action_type=action_type)
                return parsed_action_value
            elif gm_final_choice == 'R':
                game_state.add_player_message_to_history(player_config_name, ai_response_text, role="assistant", action_type=action_type, is_error=True)
                dissatisfaction_prompt = f"GM指示：你之前的回答 '{str(ai_response_text)[:70].replace(chr(10), ' ')}...' 虽然有效，但GM希望你重新考虑并给出不同的回答。"
                game_state.add_player_message_to_history(player_config_name, dissatisfaction_prompt, role="user", action_type="gm_request_ai_retry")
                continue
            elif gm_final_choice == 'M':
                manual_input = input(f"当前AI建议为: '{parsed_value_display}'\n请输入你修改后的 {p_display_name_colored} 的 {action_type_colored} 内容: ").strip()
                game_state.add_player_message_to_history(player_config_name, manual_input, role="assistant", action_type=f"gm_override_{action_type}", is_gm_override=True)
                _, _, parsed_value_manual = _validate_ai_response(manual_input, action_type, game_state, player_config_name, action_specific_info)
                return parsed_value_manual if parsed_value_manual is not None else manual_input
            else:
                _log_player_interact(colorize(f"GM输入无效 ({gm_final_choice})，默认采纳AI的有效响应。", Colors.YELLOW), "WARN", player_config_name, game_state_ref=game_state)
                game_state.add_player_message_to_history(player_config_name, ai_response_text, role="assistant", action_type=action_type)
                return parsed_action_value