# player_interaction.py (最终版，基于26K原始文件修改，保证终端功能完整)
import time
from typing import List, Dict, Any, Optional, Callable, Tuple
from ui_adapter import get_current_ui_adapter, is_gradio_mode, GMApprovalResult

# 假设 terminal_colors.py 在项目根目录或者Python可以找到的路径下
try:
    from terminal_colors import (
        colorize, log_level_color, Colors, player_name_color,
        red, green, yellow, blue, magenta, cyan, grey, bold,
        ai_response_color, underline
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
import game_config

MODULE_COLOR = Colors.CYAN

def _get_colored_player_display_name_from_interaction(game_state: GameState, player_config_name: Optional[str], show_role_to_gm: bool = False) -> str:
    if not player_config_name:
        return colorize("未知玩家", Colors.BRIGHT_BLACK)
    player_data = game_state.get_player_info(player_config_name)
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
        prefix += f" ({colorize(player_config_name, Colors.BRIGHT_YELLOW)})"
    print(f"{prefix} {message}")


def _validate_ai_response(
    response_text: Optional[str],
    action_type: str,
    game_state: GameState,
    player_config_name: str,
    action_specific_info: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str], Optional[Any], Optional[List[str]]]:
    if response_text is None or not response_text.strip():
        return False, colorize("AI响应为空或仅包含空白。", Colors.RED), None, None

    response = response_text.strip()
    cleaned_response_for_keyword_match = response.lower().strip(".。！!?？【】")
    use_colors = not is_gradio_mode()

    def create_error_and_choices(target_type: str, valid_targets: List[str], no_action_option: str) -> Tuple[str, List[str]]:
        if use_colors:
            valid_targets_display = [_get_colored_player_display_name_from_interaction(game_state, p, True) for p in valid_targets]
            response_display = colorize(response, Colors.YELLOW)
            no_action_display = colorize(no_action_option, Colors.GREEN)
        else:
            valid_targets_display = [game_state.get_player_display_name(p, show_number=True) for p in valid_targets]
            response_display = f"'{response}'"
            no_action_display = f"'{no_action_option}'"
            
        error_msg = f"{target_type} {response_display} 无效。可选: {', '.join(valid_targets_display)} 或 {no_action_display}"
        choices = valid_targets + [no_action_option]
        return error_msg, choices

    if action_type in ["speech", "last_words"]:
        if len(response) < 1:
            return False, "发言/遗言内容过短。", None, None
        return True, None, response, None

    if action_type == "vote":
        alive_players = game_state.get_alive_players(exclude_self_config_name=player_config_name)
        if cleaned_response_for_keyword_match in ["弃票", "skip", "pass"]:
            return True, None, game_config.VOTE_SKIP, None
        for p_name in alive_players:
            p_info = game_state.get_player_info(p_name)
            if response == p_name or response == game_state.get_player_display_name(p_name, show_number=True) or (p_info and response == str(p_info.get("player_number"))):
                return True, None, p_name, None
        err_msg, choices = create_error_and_choices("投票目标", alive_players, game_config.VOTE_SKIP)
        return False, err_msg, None, choices
        
    if action_type == "witch_save":
        if "是" in response or "yes" in response.lower() or "救" in response:
            return True, None, True, None
        if "否" in response or "no" in response.lower() or "不救" in response:
            return True, None, False, None
        
        killed_player_name = action_specific_info.get("killed_player_name", "未知玩家") if action_specific_info else "未知玩家"
        display_name = game_state.get_player_display_name(killed_player_name, show_number=True) if not use_colors else _get_colored_player_display_name_from_interaction(game_state, killed_player_name)
        option_yes = '是' if not use_colors else colorize('是', Colors.GREEN + Colors.BOLD)
        option_no = '否' if not use_colors else colorize('否', Colors.RED + Colors.BOLD)
            
        err_msg = f"对于是否拯救【{display_name}】，请明确回复【{option_yes}】或【{option_no}】。"
        return False, err_msg, None, ["是", "否"]

    target_list: Optional[List[str]] = None
    no_action_word: Optional[str] = None
    target_type_str: Optional[str] = None
    if action_type == "prophet_check":
        prophet_info = game_state.get_player_info(player_config_name)
        checked_targets = {entry["target"] for entry in prophet_info.get("prophet_check_history", [])} if prophet_info else set()
        target_list = [p for p in game_state.get_alive_players(exclude_self_config_name=player_config_name) if p not in checked_targets]
        no_action_word, target_type_str = "不查验", "查验目标"
    elif action_type in ["wolf_nominate", "wolf_kill"]:
        wolf_team = {p for p, d in game_state.players_data.items() if d["role"] == "狼人"}
        target_list = [p for p in game_state.get_alive_players() if p not in wolf_team]
        no_action_word, target_type_str = ("空刀" if action_type == "wolf_kill" else "不提名"), "袭击目标"
    elif action_type == "witch_poison":
        target_list = game_state.get_alive_players(exclude_self_config_name=player_config_name)
        no_action_word, target_type_str = "不使用", "用药目标"
    elif action_type == "hunter_shoot":
        target_list = game_state.get_alive_players(exclude_self_config_name=player_config_name)
        no_action_word, target_type_str = "不开枪", "开枪目标"

    if target_list is not None:
        no_action_keywords = [no_action_word.lower(), "skip", "pass", "不用", "不使用", "不验", "弃票", "不提名", "空过", "本回合不行动", "不开枪", "不射击", "不使用此能力"]
        if cleaned_response_for_keyword_match in no_action_keywords:
            return True, None, no_action_word, None
        for p_name in target_list:
            p_info = game_state.get_player_info(p_name)
            if response == p_name or response == game_state.get_player_display_name(p_name, show_number=True) or (p_info and response == str(p_info.get("player_number"))):
                return True, None, p_name, None
        err_msg, choices = create_error_and_choices(target_type_str, target_list, no_action_word)
        return False, err_msg, None, choices

    return True, None, response, None

def get_ai_decision_with_gm_approval(
    game_state: GameState,
    player_config_name: str,
    action_type: str,
    action_specific_info: Optional[Dict[str, Any]] = None,
    max_api_error_auto_retries: int = 1,
    ui_adapter=None
) -> Optional[Any]:
    player_info = game_state.get_player_info(player_config_name)
    p_display_name_colored = _get_colored_player_display_name_from_interaction(game_state, player_config_name, True)
    action_type_colored = colorize(action_type, Colors.YELLOW)

    if not player_info:
        _log_player_interact(f"错误: 无法为不存在的玩家 {p_display_name_colored} 获取决策。", "ERROR", player_config_name, game_state_ref=game_state)
        return None

    if "history" not in player_info or not isinstance(player_info["history"], list):
        player_info["history"] = []

    while True:
        current_history_for_prompt = game_state.get_player_history(player_config_name)
        messages_for_ai = generate_prompt_for_action(game_state, player_config_name, action_type, current_history_for_prompt, action_specific_info)

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
                    _, _, parsed_value, _ = _validate_ai_response(manual_input, action_type, game_state, player_config_name, action_specific_info)
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
                    _, _, parsed_value, _ = _validate_ai_response(manual_input, action_type, game_state, player_config_name, action_specific_info)
                    return parsed_value if parsed_value is not None else manual_input
                else:
                    _log_player_interact(f"GM选择跳过 {p_display_name_colored} 的行动 {action_type_colored} (因API持续错误)。", "WARN", player_config_name, game_state_ref=game_state)
                    game_state.add_player_message_to_history(player_config_name, f"GM跳过了此行动({action_type}) due to persistent API error", role="system", action_type=f"gm_skip_{action_type}", is_gm_override=True)
                    return None
        
        is_valid, validation_error_msg, parsed_action_value, valid_choices = _validate_ai_response(
            ai_response_text, action_type, game_state, player_config_name, action_specific_info
        )

        active_ui_adapter = get_current_ui_adapter()
        
        if active_ui_adapter and is_gradio_mode():
            result = active_ui_adapter.get_gm_approval(player_config_name, ai_response_text, action_type, validation_error_msg, parsed_action_value, valid_choices)
        else:
            # 终端模式逻辑（保持完整）
            print(colorize(f"\n--- GM审核点: {p_display_name_colored} (行动: {action_type_colored}) ---", Colors.BOLD + Colors.MAGENTA))
            print(f"AI ({_get_colored_player_display_name_from_interaction(game_state, player_config_name)}) 响应原文:\n```\n{ai_response_color(ai_response_text)}\n```")
            
            if not is_valid:
                print(colorize(f"AI响应内容校验失败: {validation_error_msg}", Colors.RED))
                gm_content_choice = input(
                    f"请选择操作: [{bold('R')}]让AI重试(提供修正), [{bold('M')}]手动输入, [{bold('A')}]接受此原始响应(风险自负), [{bold('S')}]跳过: "
                ).strip().upper()
                result = GMApprovalResult({"R": "retry", "M": "manual", "A": "accept_invalid"}.get(gm_content_choice, "skip"))
                if result.action == "manual":
                    result.content = input(f"请输入 {p_display_name_colored} 的 {action_type_colored} 内容: ").strip()
            else:
                parsed_value_display = colorize(str(parsed_action_value)[:100], Colors.BRIGHT_WHITE) + (grey('...') if len(str(parsed_action_value)) > 100 else '')
                print(f"{green('AI响应有效')}。解析后的行动值: '{parsed_value_display}'")
                gm_final_choice = input(
                    f"请选择操作: [{bold('Y')}]确认采纳, [{bold('R')}]让AI重试(不满意), [{bold('M')}]手动修改/覆盖: "
                ).strip().upper()
                if gm_final_choice == 'Y':
                    result = GMApprovalResult("accept")
                elif gm_final_choice == 'R':
                    result = GMApprovalResult("retry")
                elif gm_final_choice == 'M':
                    manual_input = input(f"当前AI建议为: '{parsed_value_display}'\n请输入你修改后的 {p_display_name_colored} 的 {action_type_colored} 内容: ").strip()
                    result = GMApprovalResult("manual", manual_input)
                else:
                    _log_player_interact(colorize(f"GM输入无效 ({gm_final_choice})，默认采纳AI的有效响应。", Colors.YELLOW), "WARN", player_config_name, game_state_ref=game_state)
                    result = GMApprovalResult("accept")
        
        # --- 处理GM决定的通用逻辑 ---
        if result.action == "accept":
            game_state.add_player_message_to_history(player_config_name, ai_response_text, role="assistant", action_type=action_type)
            return parsed_action_value
        elif result.action == "retry":
            game_state.add_player_message_to_history(player_config_name, ai_response_text, role="assistant", action_type=action_type, is_error=True)
            correction_prompt = f"GM指示：你之前的回答 '{str(ai_response_text)[:70].replace(chr(10), ' ')}...' 是无效的或不被接受。请修正并重新回答。"
            game_state.add_player_message_to_history(player_config_name, correction_prompt, role="user", action_type="gm_correction_for_ai")
            continue
        elif result.action == "manual":
            manual_input = result.content
            game_state.add_player_message_to_history(player_config_name, manual_input, role="assistant", action_type=f"gm_override_{action_type}", is_gm_override=True)
            _, _, final_parsed_value, _ = _validate_ai_response(manual_input, action_type, game_state, player_config_name, action_specific_info)
            return final_parsed_value if final_parsed_value is not None else manual_input
        elif result.action == "accept_invalid":
            _log_player_interact(f"GM接受了来自 {p_display_name_colored} 的原始无效响应。", "WARN", player_config_name, game_state_ref=game_state)
            game_state.add_player_message_to_history(player_config_name, ai_response_text, role="assistant", action_type=action_type, is_accepted_invalid=True)
            return ai_response_text
        else: # skip
            _log_player_interact(f"GM选择跳过 {p_display_name_colored} 的行动。", "WARN", player_config_name, game_state_ref=game_state)
            game_state.add_player_message_to_history(player_config_name, f"GM跳过了此行动({action_type})", role="system", action_type=f"gm_skip_{action_type}", is_gm_override=True)
            return None