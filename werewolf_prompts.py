# werewolf_prompts.py (修改版 - 支持狼人提名和最终决策 + 颜色日志)
from typing import List, Dict, Any, Optional

# 假设 terminal_colors.py 在项目根目录或者Python可以找到的路径下
try:
    from terminal_colors import colorize, log_level_color, Colors, player_name_color, role_color, magenta
except ImportError:
    # Fallback if terminal_colors is not found, to prevent crashing
    def colorize(text: str, _color_code: str) -> str: return text
    def log_level_color(_level: str) -> str: return ""
    class Colors: RESET = ""; MAGENTA = ""; BRIGHT_MAGENTA = ""; BLUE = ""; YELLOW = "" # Add more if needed
    def player_name_color(name: str, _player_data=None, _game_state=None) -> str: return name
    def role_color(name: str) -> str: return name
    def magenta(text: str) -> str: return text


from game_state import GameState
import game_config # For role names, VOTE_SKIP etc.

MODULE_COLOR = Colors.MAGENTA # PromptGen 用洋红色

def _log_prompt_event(message: str, level: str = "INFO", player_config_name: Optional[str]=None):
    level_colored = colorize(level, log_level_color(level))
    prefix_module = colorize("[PromptGen:", MODULE_COLOR)

    prefix = f"{prefix_module}{level_colored}]"
    if player_config_name:
        # 尝试获取玩家数据以根据角色上色，如果失败则用通用颜色
        player_data = None
        if 'game_state' in globals() and isinstance(game_state, GameState): # 检查 game_state 是否已定义
            player_data_temp = game_state.get_player_info(player_config_name)
            if player_data_temp:
                player_data = player_data_temp
        
        if player_data:
            p_name_colored = player_name_color(player_config_name, player_data)
        else:
            p_name_colored = colorize(player_config_name, Colors.BRIGHT_MAGENTA) # 通用玩家名颜色
        prefix += f" ({p_name_colored})"
    
    print(f"{prefix} {message}")

def _is_api_strict_alternating(player_info: Dict[str, Any]) -> bool:
    """
    判断当前AI的API是否要求严格的user/assistant交替格式。
    当前默认所有API都需要严格模式以保证最大兼容性。
    未来可以从 player_info.get("api_format_rules") 获取具体规则。
    """
    return True # 默认所有API都采用最严格的user/assistant交替模式

def _validate_and_normalize_history(
    history: List[Dict[str, str]],
    player_config_name: Optional[str] = None # 保持 player_config_name 以便日志能识别来源
) -> List[Dict[str, str]]:
    """
    验证历史记录并尝试规范化为 user/assistant 交替。
    - 移除开头的 assistant 消息。
    - 合并连续的同角色消息。
    """
    if not history:
        return []

    normalized_history = []

    # 移除所有非 user/assistant 的消息，并确保不以 assistant 开头
    temp_history = []
    started_with_user = False
    for msg in history:
        if msg["role"] == "user":
            started_with_user = True
            temp_history.append(msg)
        elif msg["role"] == "assistant":
            if started_with_user: # 只有在 user 消息之后才接受 assistant
                temp_history.append(msg)
            else:
                _log_prompt_event(f"历史记录中，在第一个user消息前出现assistant，已忽略: {colorize(str(msg['content'])[:50], Colors.YELLOW)}", "DEBUG", player_config_name)
        # 其他 role (如 system) 在此阶段被忽略，因为 system prompt 会被合并

    if not temp_history:
        return []

    # 合并连续的同角色消息
    normalized_history.append(temp_history[0])
    for i in range(1, len(temp_history)):
        current_msg = temp_history[i]
        last_added_msg = normalized_history[-1]
        if current_msg["role"] == last_added_msg["role"]:
            _log_prompt_event(f"历史记录中连续出现'{colorize(current_msg['role'], Colors.YELLOW)}'，将合并内容。", "DEBUG", player_config_name)
            last_added_msg["content"] += "\n" + current_msg["content"]
        else:
            normalized_history.append(current_msg)

    return normalized_history


def generate_prompt_for_action(
    game_state: GameState, # game_state 实例在这里传递，所以 _log_prompt_event 可以尝试使用它
    player_config_name: str,
    action_type: str,
    current_player_history: List[Dict[str, str]],
    action_specific_info: Optional[Dict[str, Any]] = None
) -> List[Dict[str, str]]:
    """
    为AI生成包含完整上下文的提示信息。
    通用策略：
    1. System Prompt 内容预置到第一个 User 消息的开头。
    2. Messages 列表严格为 User/Assistant 交替，以 User 开始，以 User 结束。
    """
    player_info = game_state.get_player_info(player_config_name)
    if not player_info:
        _log_prompt_event(f"错误: 无法为不存在的玩家 {colorize(player_config_name, Colors.YELLOW)} 生成prompt。", "ERROR", player_config_name)
        return [{"role": "user", "content": "关键内部错误：玩家数据丢失。请告知游戏主持人此问题。"}]

    role = player_info["role"]
    colored_role = role_color(role)


    # --- 1. 构建 System Prompt 的内容字符串 ---
    system_prompt_content_parts = []
    system_prompt_content_parts.append(f"你正在参与一场狼人杀推理游戏。你的身份是【{colored_role}】。") # 给角色上色
    system_prompt_content_parts.append("你的目标是与你的阵营一起获得胜利。")
    system_prompt_content_parts.append("请始终以你的角色身份进行思考和回应。")
    system_prompt_content_parts.append(
        "当你需要公开发言或发表遗言时，请务必使用【第一人称】（例如“我认为...”、“我怀疑...”）。"
        "你最终输出的公开发言或行动决策，应该是简洁明了的、符合你角色的直接表达，不应包含你的内心分析过程。"
    )
    system_prompt_content_parts.append("在描述较为激烈的行动时，请使用委婉的说法，例如用“出局”、“淘汰”、“使其离开游戏”、“引导信息”等词语代替直接的负面词汇。")

    if role == "平民":
        system_prompt_content_parts.append("你的目标是找出所有“狼人伙伴”并将他们票选出局。你没有任何特殊能力，需要通过逻辑分析和听取他人发言来判断。")
    elif role == "狼人":
        system_prompt_content_parts.append("你的目标是逐步淘汰好人阵营的玩家（包括神职和平民），直到狼人数量达到或超过好人数量，或者所有神职或所有平民均已出局。")
        system_prompt_content_parts.append("夜晚，你需要和你的狼队友一起商议，选择一位玩家使其在本回合结束时“出局”。白天你需要隐藏身份，混淆视听，争取不被票选出局。")
    elif role == "预言家":
        system_prompt_content_parts.append("你的目标是找出狼人并带领好人获胜。每晚你可以查验一名玩家的阵营（好人阵营或狼人阵营的成员）。白天你需要用你的信息引导好人。")
    elif role == "女巫":
        system_prompt_content_parts.append("你的目标是帮助好人获胜。你拥有一瓶【解药】，可以使一名当晚被狼人团队选择使其出局的玩家免于出局（只可使用一次）。")
        system_prompt_content_parts.append("你也拥有一种特殊的【夜晚能力药剂】，可以选择一名玩家使其在当晚结束时出局（只可使用一次）。")
        system_prompt_content_parts.append("【夜晚能力药剂】是你强大的武器，应该优先用于你高度怀疑是“狼人伙伴”的玩家，或者在关键时刻用于打破场上僵局以帮助好人阵营。请谨慎使用，避免误伤好人阵营的同伴。")
        system_prompt_content_parts.append("【重要规则】：你【不能】在同一个夜晚同时使用解药和夜晚能力药剂。一旦使用其中一种，当晚便不能再使用另一种。")
        has_save = player_info.get(game_config.WITCH_HAS_SAVE_POTION_KEY, False)
        has_poison = player_info.get(game_config.WITCH_HAS_POISON_POTION_KEY, False)
        system_prompt_content_parts.append(f"当前解药状态: {colorize('可用', Colors.GREEN) if has_save else colorize('已使用', Colors.RED)}。")
        system_prompt_content_parts.append(f"当前夜晚能力药剂状态: {colorize('可用', Colors.GREEN) if has_poison else colorize('已使用', Colors.RED)}。")
    elif role == "猎人":
        system_prompt_content_parts.append("你的目标是帮助好人获胜。当你因为任何原因（被票选、被狼人团队选择、被女巫的特殊药剂选择）出局时，你可以选择场上任意一名其他存活玩家与你一同出局，除非你被女巫的特殊药剂明确阻止了此能力。此能力只能使用一次。")
        can_shoot = player_info.get(game_config.HUNTER_CAN_SHOOT_KEY, True)
        system_prompt_content_parts.append(f"当前特殊能力状态: {colorize('可用', Colors.GREEN) if can_shoot else colorize('已使用或被阻止', Colors.RED)}。")

    full_system_content = "\n".join(system_prompt_content_parts)
    system_wrapper_start = f"--- {colorize('系统指令与角色设定', Colors.BLUE + Colors.BOLD)} ---\n"
    system_wrapper_end = f"\n--- {colorize('系统指令结束', Colors.BLUE + Colors.BOLD)} ---\n"


    # --- 2. 构建当前的 User Prompt 内容 ---
    current_action_user_prompt_parts = []
    current_action_user_prompt_parts.append(
        f"--- {colorize('当前游戏情境', Colors.YELLOW)}：第 {colorize(str(game_state.game_day), Colors.BOLD)} 天，阶段：{colorize(game_state.current_game_phase, Colors.BOLD)} ---"
    )

    alive_players_display_colored = []
    sorted_alive_players = sorted(
        game_state.get_alive_players(),
        key=lambda name: game_state.players_data[name]["player_number"]
    )
    for p_name in sorted_alive_players:
        p_data_temp = game_state.get_player_info(p_name)
        p_num = p_data_temp["player_number"]
        
        display_entry_base = f"玩家{p_num} ({p_name})"
        display_entry_colored = player_name_color(display_entry_base, p_data_temp)

        if p_name == player_config_name:
            display_entry_colored += colorize(" [你]", Colors.GREEN + Colors.BOLD)
        elif role == "狼人" and p_data_temp["role"] == "狼人":
            display_entry_colored += colorize(" [狼队友]", Colors.RED + Colors.BOLD)
        alive_players_display_colored.append(display_entry_colored)
    current_action_user_prompt_parts.append(f"目前场上存活的玩家: {', '.join(alive_players_display_colored)}。")

    if game_state.current_game_phase not in [game_config.PHASE_NIGHT_START, game_config.PHASE_GAME_SETUP, game_config.PHASE_START_GAME]:
        night_deaths_display_colored = []
        if game_state.last_night_events.get("final_deaths_this_night"):
            for dead_p_name in game_state.last_night_events["final_deaths_this_night"]:
                dead_p_data = game_state.get_player_info(dead_p_name)
                night_deaths_display_colored.append(player_name_color(game_state.get_player_display_name(dead_p_name), dead_p_data))
            current_action_user_prompt_parts.append(f"昨晚出局的玩家是: {colorize(', '.join(night_deaths_display_colored), Colors.RED)}。")
        elif game_state.game_day > 0:
             current_action_user_prompt_parts.append(colorize("昨晚平安无事，没有人出局。", Colors.GREEN))

    if action_type == game_config.ACTION_SPEECH or action_type == game_config.ACTION_VOTE:
        if game_state.round_speeches_log:
            current_action_user_prompt_parts.append(f"\n--- {colorize('本轮已进行的公开发言', Colors.YELLOW)} ---")
            for speech_entry in game_state.round_speeches_log:
                speaker_p_data = game_state.get_player_info(speech_entry["player"])
                speaker_name_display_colored = player_name_color(game_state.get_player_display_name(speech_entry["player"]), speaker_p_data)
                current_action_user_prompt_parts.append(f"  {speaker_name_display_colored}: \"{speech_entry['speech']}\"") # Speech content not colored here
        else:
            if action_type == game_config.ACTION_SPEECH:
                current_action_user_prompt_parts.append(colorize("你是本轮第一个发言。", Colors.CYAN))

    current_action_user_prompt_parts.append(f"\n--- {colorize('你的行动指示', Colors.YELLOW + Colors.BOLD)} ---")

    # --- 特定行动的指令 (内容保持不变，只对包裹的标题上色) ---
    # (Omitted for brevity, the content of these specific prompts remains the same as your previous version)
    # ... (所有 if/elif action_type == ... 的分支，里面的文本内容不变) ...
    # ... (只是确保外部的标题或关键词，如果适合，可以被 colorize 包裹)
    # 例子：
    if action_type == game_config.ACTION_SPEECH:
        current_action_user_prompt_parts.append("轮到你发言了。请仔细分析当前局势、其他人的发言（如果有）、以及你的身份和目标。")
        current_action_user_prompt_parts.append(f"重要：你的公开发言必须使用【{colorize('第一人称', Colors.BOLD)}】（例如“我认为...”，“我的看法是...”）。")
        current_action_user_prompt_parts.append("最终，请直接输出你要公开发表的【第一人称发言内容】。")
        current_action_user_prompt_parts.append("你的发言应该有助于你的阵营获胜。")

    elif action_type == game_config.ACTION_LAST_WORDS:
        current_action_user_prompt_parts.append("你已经出局了。请发表你的遗言。")
        current_action_user_prompt_parts.append(f"重要：你的遗言必须使用【{colorize('第一人称', Colors.BOLD)}】。")
        current_action_user_prompt_parts.append("最终，请直接输出你要公开发表的【第一人称遗言内容】。")

    elif action_type == game_config.ACTION_VOTE:
        current_action_user_prompt_parts.append("轮到你投票了。请从以下存活的玩家中，选择一位你认为最应该是“狼人伙伴”的玩家进行投票。")
        votable_players = [p_name for p_name in sorted_alive_players if p_name != player_config_name]
        votable_display_colored = [player_name_color(f"玩家{game_state.players_data[p]['player_number']} ({p})", game_state.get_player_info(p)) for p in votable_players]
        current_action_user_prompt_parts.append(f"可选的投票目标: {', '.join(votable_display_colored) if votable_display_colored else colorize('无其他可选目标', Colors.YELLOW)}。")
        current_action_user_prompt_parts.append(f"请回复你选择的玩家的配置名 (例如 '{votable_players[0] if votable_players else 'PlayerAI_X'}')、或他们的编号 (例如 '1')、或他们的编号+配置名，或者回复 '{colorize(game_config.VOTE_SKIP, Colors.GREEN)}' 表示弃票。")
        current_action_user_prompt_parts.append("你的选择应基于你的判断，不需要解释理由，直接给出目标或弃票。")

    elif action_type == game_config.ACTION_WOLF_NOMINATE:
        current_action_user_prompt_parts.append("你是狼人团队的一员。现在是狼人内部提名袭击目标的时间。")
        alive_wolves_config_names = [name for name, data in game_state.players_data.items() if data["role"] == "狼人" and data["status"] == game_config.PLAYER_STATUS_ALIVE]
        decision_maker_wolf_name = action_specific_info.get("decision_maker_name") if action_specific_info else None
        if not decision_maker_wolf_name and alive_wolves_config_names: # Fallback
            sorted_wolves = sorted(alive_wolves_config_names, key=lambda n: game_state.players_data[n]["player_number"])
            if sorted_wolves: decision_maker_wolf_name = sorted_wolves[-1]

        wolf_team_display_colored = []
        for wolf_name in alive_wolves_config_names:
            wolf_p_data = game_state.get_player_info(wolf_name)
            entry_base = f"玩家{wolf_p_data['player_number']} ({wolf_name})"
            entry_colored = player_name_color(entry_base, wolf_p_data)
            if wolf_name == player_config_name: entry_colored += colorize(" [你]", Colors.GREEN + Colors.BOLD)
            elif wolf_name == decision_maker_wolf_name: entry_colored += colorize(" [决策者]", Colors.YELLOW + Colors.BOLD)
            else: entry_colored += colorize(" [狼队友]", Colors.RED + Colors.BOLD)
            wolf_team_display_colored.append(entry_colored)
        current_action_user_prompt_parts.append(f"你的狼人团队成员: {', '.join(wolf_team_display_colored) if wolf_team_display_colored else colorize('错误：未找到狼队信息', Colors.RED)}")
        killable_targets = [p_name for p_name in sorted_alive_players if game_state.players_data[p_name]["role"] != "狼人"]
        killable_display_colored = [player_name_color(f"玩家{game_state.players_data[p]['player_number']} ({p})", game_state.get_player_info(p)) for p in killable_targets]
        if not killable_targets: current_action_user_prompt_parts.append(colorize("场上似乎没有其他阵营的玩家可供提名。", Colors.YELLOW))
        else: current_action_user_prompt_parts.append(f"可供你提名的非狼人阵营玩家有: {', '.join(killable_display_colored)}。")
        if decision_maker_wolf_name:
             dm_display = player_name_color(game_state.get_player_display_name(decision_maker_wolf_name), game_state.get_player_info(decision_maker_wolf_name))
             current_action_user_prompt_parts.append(f"请你提出一个你希望本回合袭击的目标（即你的“提名”）。最终的决定将由【{dm_display}】做出。")
        else: current_action_user_prompt_parts.append(f"请你提出一个你希望本回合袭击的目标（即你的“提名”）。最终的决定将由团队决策者做出。")
        current_action_user_prompt_parts.append(f"请直接回复你提名的玩家的配置名、或编号、或编号+配置名，或者回复 '{colorize('空过', Colors.GREEN)}' / '{colorize('不提名', Colors.GREEN)}' / '{colorize('本回合不行动', Colors.GREEN)}' 表示你没有特别想袭击的目标。")

    elif action_type == game_config.ACTION_WOLF_KILL:
        current_action_user_prompt_parts.append(f"你是狼人团队的【{colorize('决策者', Colors.BOLD + Colors.YELLOW)}】。现在你需要做出本回合最终的袭击决定。")
        alive_wolves_config_names = [name for name, data in game_state.players_data.items() if data["role"] == "狼人" and data["status"] == game_config.PLAYER_STATUS_ALIVE]
        wolf_team_display_colored = [] # (Similar logic as ACTION_WOLF_NOMINATE for displaying team)
        for wolf_name in alive_wolves_config_names:
            wolf_p_data = game_state.get_player_info(wolf_name)
            entry_base = f"玩家{wolf_p_data['player_number']} ({wolf_name})"
            entry_colored = player_name_color(entry_base, wolf_p_data)
            if wolf_name == player_config_name: entry_colored += colorize(" [你, 决策者]", Colors.GREEN + Colors.BOLD)
            else: entry_colored += colorize(" [狼队友]", Colors.RED + Colors.BOLD)
            wolf_team_display_colored.append(entry_colored)
        current_action_user_prompt_parts.append(f"你的狼人团队成员: {', '.join(wolf_team_display_colored) if wolf_team_display_colored else colorize('错误：未找到狼队信息', Colors.RED)}")

        if game_state.wolf_nominations_this_night:
            current_action_user_prompt_parts.append(f"\n--- {colorize('你的狼队友的袭击意向 (提名) 如下', Colors.YELLOW)} ---")
            nominations_found = False
            for nom_wolf, nom_target_name in game_state.wolf_nominations_this_night.items():
                if nom_wolf == player_config_name: continue
                nom_wolf_data = game_state.get_player_info(nom_wolf)
                nom_wolf_display = player_name_color(game_state.get_player_display_name(nom_wolf), nom_wolf_data)
                nom_target_display = colorize("空过/无明确提名", Colors.GREEN)
                if nom_target_name:
                    nom_target_data = game_state.get_player_info(nom_target_name)
                    nom_target_display = player_name_color(game_state.get_player_display_name(nom_target_name), nom_target_data)
                current_action_user_prompt_parts.append(f"  狼队友 {nom_wolf_display} 的意向是: {nom_target_display}")
                nominations_found = True
            if not nominations_found: current_action_user_prompt_parts.append(colorize("  (尚未收到其他狼队友的明确提名或他们都选择了空过。)", Colors.CYAN))
        else: current_action_user_prompt_parts.append(colorize("\n目前还没有收到其他狼队友的袭击意向记录。", Colors.CYAN))
        killable_targets = [p_name for p_name in sorted_alive_players if game_state.players_data[p_name]["role"] != "狼人"]
        killable_display_colored = [player_name_color(f"玩家{game_state.players_data[p]['player_number']} ({p})", game_state.get_player_info(p)) for p in killable_targets]
        if not killable_targets: current_action_user_prompt_parts.append(colorize("\n场上似乎没有其他阵营的玩家可供袭击了。", Colors.YELLOW))
        else: current_action_user_prompt_parts.append(f"\n请综合以上狼队友的意向（如果有）和你自己的判断，从以下非狼人阵营的玩家中选择一位，作为本回合【{colorize('最终', Colors.BOLD)}】的袭击目标: {', '.join(killable_display_colored)}。")
        current_action_user_prompt_parts.append(f"请直接回复你最终选择的玩家的配置名、或编号、或编号+配置名，或者回复 '{colorize('空过', Colors.GREEN)}' / '{colorize('本回合不行动', Colors.GREEN)}' 表示最终决定不袭击任何人。")

    elif action_type == game_config.ACTION_PROPHET_CHECK:
        current_action_user_prompt_parts.append("你是预言家。现在是夜晚行动时间，你可以选择一名玩家查验其阵营。")
        prophet_check_history = player_info.get("prophet_check_history", [])
        if prophet_check_history:
            history_display_parts_colored = []
            for entry in prophet_check_history:
                target_p_data = game_state.get_player_info(entry.get('target','未知目标'))
                target_display_name_colored = player_name_color(game_state.get_player_display_name(entry.get('target','未知目标')), target_p_data)
                result_text_colored = colorize('狼人阵营', Colors.RED) if entry.get('is_wolf', False) else colorize('好人阵营', Colors.GREEN)
                day_checked = entry.get('day', game_state.game_day)
                history_display_parts_colored.append(f"第{colorize(str(day_checked), Colors.BOLD)}晚查验 {target_display_name_colored} -> {result_text_colored}")
            current_action_user_prompt_parts.append(f"你过往的查验记录: {'; '.join(history_display_parts_colored)}。")
        checkable_targets = [p_name for p_name in sorted_alive_players if p_name != player_config_name and p_name not in [entry.get("target") for entry in prophet_check_history]]
        checkable_display_colored = [player_name_color(f"玩家{game_state.players_data[p]['player_number']} ({p})", game_state.get_player_info(p)) for p in checkable_targets]
        if not checkable_targets: current_action_user_prompt_parts.append(colorize("目前没有可供你查验的新目标了。", Colors.YELLOW))
        else: current_action_user_prompt_parts.append(f"请从以下你尚未查验过的存活玩家中选择一位进行查验: {', '.join(checkable_display_colored)}。")
        current_action_user_prompt_parts.append(f"请直接回复你选择的玩家的配置名、或编号、或编号+配置名，或者回复 '{colorize('不查验', Colors.GREEN)}'。")

    elif action_type == game_config.ACTION_WITCH_SAVE:
        current_action_user_prompt_parts.append("你是女巫。现在是夜晚行动时间。")
        killed_player_name = action_specific_info.get("killed_player_name") if action_specific_info else None
        if killed_player_name:
            killed_player_data = game_state.get_player_info(killed_player_name)
            killed_player_display_colored = player_name_color(game_state.get_player_display_name(killed_player_name), killed_player_data)
            current_action_user_prompt_parts.append(f"今晚玩家 {killed_player_display_colored} 被狼人团队选择使其出局。")
            if player_info.get(game_config.WITCH_HAS_SAVE_POTION_KEY, False):
                current_action_user_prompt_parts.append(f"你拥有一瓶解药。你是否要使用解药使 Ta 免于出局？请直接回复【{colorize('是', Colors.GREEN + Colors.BOLD)}】或【{colorize('否', Colors.RED + Colors.BOLD)}】。")
            else:
                current_action_user_prompt_parts.append(f"你已经没有解药了。请回复【{colorize('否', Colors.RED + Colors.BOLD)}】或类似词语确认。")
        else:
            current_action_user_prompt_parts.append(colorize("今晚狼人团队没有选择任何人使其出局 (平安夜)。", Colors.GREEN))
            current_action_user_prompt_parts.append(f"你不需要使用解药。请回复【{colorize('否', Colors.RED + Colors.BOLD)}】或类似词语确认。")

    elif action_type == game_config.ACTION_WITCH_POISON:
        current_action_user_prompt_parts.append(f"现在，关于你的【{colorize('夜晚能力药剂', Colors.MAGENTA + Colors.BOLD)}】：")
        if player_info.get(game_config.WITCH_HAS_POISON_POTION_KEY, False):
            current_action_user_prompt_parts.append("你是否要使用它选择一位存活玩家，使其在本回合结束时出局？")
            poisonable_targets = [p_name for p_name in sorted_alive_players if p_name != player_config_name]
            poisonable_display_colored = [player_name_color(f"玩家{game_state.players_data[p]['player_number']} ({p})", game_state.get_player_info(p)) for p in poisonable_targets]
            if not poisonable_targets: current_action_user_prompt_parts.append(colorize("场上已无其他存活玩家可供你选择。", Colors.YELLOW))
            else: current_action_user_prompt_parts.append(f"可选的目标: {', '.join(poisonable_display_colored)}。")
            current_action_user_prompt_parts.append(f"请直接回复你选择的玩家的配置名、或编号、或编号+配置名，或者回复 '{colorize('不使用', Colors.GREEN)}' (不带任何标点或括号)。")
        else:
            current_action_user_prompt_parts.append(f"你已经没有夜晚能力药剂了。请回复 '{colorize('不使用', Colors.GREEN)}' 或类似词语确认。")

    elif action_type == game_config.ACTION_HUNTER_SHOOT:
        current_action_user_prompt_parts.append("你是猎人，你已经出局了。")
        if player_info.get(game_config.PLAYER_IS_POISONED_KEY, False):
            current_action_user_prompt_parts.append(colorize("由于你是被女巫的特殊药剂选定出局的，你本次无法使用能力。", Colors.RED) + f"请回复 '{colorize('无法行动', Colors.YELLOW)}' 或 '{colorize('不开枪', Colors.YELLOW)}'。")
        elif not player_info.get(game_config.HUNTER_CAN_SHOOT_KEY, True):
             current_action_user_prompt_parts.append(colorize("你的能力已经使用过或因其他原因无法使用了。", Colors.RED) + f"请回复 '{colorize('无法行动', Colors.YELLOW)}' 或 '{colorize('不开枪', Colors.YELLOW)}'。")
        else:
            current_action_user_prompt_parts.append("你现在可以使用你的能力，选择场上任意一名其他存活玩家与你一同出局。")
            shootable_targets = [p_name for p_name in sorted_alive_players if p_name != player_config_name]
            shootable_display_colored = [player_name_color(f"玩家{game_state.players_data[p]['player_number']} ({p})", game_state.get_player_info(p)) for p in shootable_targets]
            if not shootable_targets: current_action_user_prompt_parts.append(colorize("场上已无其他存活玩家可供你选择。", Colors.YELLOW))
            else: current_action_user_prompt_parts.append(f"可选的目标: {', '.join(shootable_display_colored)}。")
            current_action_user_prompt_parts.append(f"请直接回复你选择的玩家的配置名、或编号、或编号+配置名，或者回复 '{colorize('不开枪', Colors.GREEN)}' / '{colorize('不使用此能力', Colors.GREEN)}'。")
    
    else:
        current_action_user_prompt_parts.append(f"当前需要你执行一个未知类型的行动: '{colorize(action_type, Colors.RED)}'。请根据你的角色、当前情境和通用游戏规则进行回应。")
        current_action_user_prompt_parts.append("如果需要发言，请使用第一人称。如果需要做决策，请给出明确的决策结果。")


    final_current_action_user_content = "\n".join(current_action_user_prompt_parts)

    # --- 3. 组合消息列表 ---
    messages: List[Dict[str, str]] = []
    normalized_history = _validate_and_normalize_history(current_player_history, player_config_name)

    if not normalized_history:
        user_content_with_system = system_wrapper_start + full_system_content + system_wrapper_end + final_current_action_user_content
        messages.append({"role": "user", "content": user_content_with_system})
    else:
        temp_messages = []
        system_prompt_prepended_to_history = False
        for hist_msg in normalized_history:
            if hist_msg["role"] == "user" and not system_prompt_prepended_to_history:
                merged_content = system_wrapper_start + full_system_content + system_wrapper_end + \
                                 f"--- {colorize('历史对话回顾', Colors.BLUE)} ---\n" + hist_msg["content"]
                temp_messages.append({"role": "user", "content": merged_content})
                system_prompt_prepended_to_history = True
            elif hist_msg["role"] == "assistant":
                if not temp_messages or temp_messages[-1]["role"] != "user":
                    _log_prompt_event(f"修正历史：在assistant消息前补充占位user消息。", "DEBUG", player_config_name)
                    temp_messages.append({"role": "user", "content": colorize("(之前的对话继续...)", Colors.BRIGHT_BLACK)})
                temp_messages.append(hist_msg)
            elif hist_msg["role"] == "user":
                 temp_messages.append(hist_msg)
        if not system_prompt_prepended_to_history and temp_messages:
             _log_prompt_event(f"警告：历史记录在规范化后仍不以user开头，这不应发生。", "WARN", player_config_name)
        messages.extend(temp_messages)
        if not messages:
            user_content_with_system = system_wrapper_start + full_system_content + system_wrapper_end + final_current_action_user_content
            messages.append({"role": "user", "content": user_content_with_system})
        elif messages[-1]["role"] == "assistant":
            messages.append({"role": "user", "content": final_current_action_user_content})
        elif messages[-1]["role"] == "user":
             _log_prompt_event(f"历史最后是user，将当前新指令合并到最后一个user消息。", "DEBUG", player_config_name)
             messages[-1]["content"] += f"\n\n--- {colorize('当前新指令', Colors.YELLOW + Colors.BOLD)} ---\n" + final_current_action_user_content
        else:
             _log_prompt_event(f"组合消息时出现意外的最后角色: {colorize(messages[-1]['role'], Colors.RED)}", "ERROR", player_config_name)
             messages.append({"role": "user", "content": final_current_action_user_content})

    # --- 最后一步校验和日志 ---
    if not messages or messages[0]["role"] != "user":
        _log_prompt_event(f"严重错误: 生成的messages列表为空或不以user开始! Player: {colorize(player_config_name, Colors.YELLOW)}, Action: {colorize(action_type, Colors.RED)}", "CRITICAL")
        return [{"role": "user", "content": system_wrapper_start + full_system_content + system_wrapper_end + \
                                            "发生内部提示生成错误。请根据你的角色和当前已知情境行动。"}]
    if messages[-1]["role"] != "user":
        _log_prompt_event(f"严重错误: 生成的messages列表不以user结束! Player: {colorize(player_config_name, Colors.YELLOW)}, Action: {colorize(action_type, Colors.RED)}", "CRITICAL")
        messages.append({"role": "user", "content": "（请根据以上信息行动，确保你的回复是针对此用户消息的。）"})

    p_role_colored = role_color(role)
    _log_prompt_event(f"为 {player_name_color(player_config_name, player_info)} ({p_role_colored}) 生成 {colorize(action_type, Colors.YELLOW)} 的Prompt。最终消息数: {len(messages)}", "DEBUG")

    if True: # 调试时可以始终打印 (或者你可以添加一个全局开关)
        _log_prompt_event(f"--- 为 {player_name_color(player_config_name, player_info)} 生成的最终消息列表 (Action: {colorize(action_type, Colors.YELLOW)}) ---", "TRACE")
        for i, msg in enumerate(messages):
            content_preview = str(msg.get('content',''))[:300] + ('...' if len(str(msg.get('content',''))) > 300 else '')
            msg_role_colored = colorize(msg.get('role','unknown').upper(), Colors.BOLD + (Colors.GREEN if msg.get('role') == 'user' else Colors.CYAN if msg.get('role') == 'assistant' else Colors.BLUE))
            _log_prompt_event(f"  MSG[{i+1}/{len(messages)}] Role: {msg_role_colored}\n      Content: {content_preview.replace(chr(10), chr(10)+'      ')}", "TRACE")
            
    return messages