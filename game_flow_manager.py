# game_flow_manager.py (最终完整版)
import time
from typing import List, Dict, Any, Optional
from ui_adapter import get_current_ui_adapter, is_gradio_mode

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
    def role_color(name: str) -> str: return text
    def red(text: str) -> str: return text
    def green(text: str) -> str: return text
    def yellow(text: str) -> str: return text
    def blue(text: str) -> str: return text
    def magenta(text: str) -> str: return text
    def cyan(text: str) -> str: return text
    def grey(text: str) -> str: return text
    def bold(text: str) -> str: return text


import game_config

from game_state import GameState, PLAYER_STATUS_DEAD, PLAYER_STATUS_ALIVE
from game_config import (
    PHASE_NIGHT_START, PHASE_DAY_START, PHASE_SPEECH, PHASE_VOTE, PHASE_GAME_OVER,
    PHASE_LAST_WORDS_SPEECH, PHASE_PROCESS_DEATH_EFFECTS,
    ALL_POSSIBLE_ROLES,
    WITCH_HAS_SAVE_POTION_KEY, WITCH_HAS_POISON_POTION_KEY, HUNTER_CAN_SHOOT_KEY,
    PLAYER_IS_POISONED_KEY, VOTE_SKIP,
    ACTION_WOLF_KILL, ACTION_WOLF_NOMINATE
)
from player_interaction import get_ai_decision_with_gm_approval
from game_rules_engine import check_for_win_conditions, determine_speech_order, tally_votes_and_handle_ties

MODULE_COLOR = Colors.GREEN

def _log_flow_event(message: str, level: str = "INFO", day: Optional[int]=None, phase: Optional[str]=None, game_state_ref: Optional[GameState]=None):
    ui_adapter = get_current_ui_adapter()
    
    if ui_adapter and is_gradio_mode():
        ui_adapter.log_flow_event(message, level, day, phase)
    else:
        level_colored = colorize(level, log_level_color(level))
        prefix_module = colorize("[FlowManager:", MODULE_COLOR)
        prefix = f"\n{prefix_module}{level_colored}]"
        if day is not None:
            prefix += f" [{colorize('Day ' + str(day), Colors.BOLD)}]"
        if phase:
            prefix += f" [{game_phase_color(phase)}]"
        print(f"{prefix} {message}")


def _announce_to_all_alive(game_state: GameState, message: str, is_gm_broadcast: bool = True):
    ui_adapter = get_current_ui_adapter()
    
    if ui_adapter and is_gradio_mode():
        # 在Gradio模式下，让UI适配器处理消息格式
        # message_type='gm_broadcast' 将帮助UI适配器决定如何显示它
        ui_adapter.broadcast_message(message, message_type='gm_broadcast' if is_gm_broadcast else 'info')
    else:
        # 终端模式下，我们自己添加 "GM广播" 前缀和颜色
        if is_gm_broadcast:
            colored_message = gm_broadcast_color(f"GM广播: {message}")
            _log_flow_event(colored_message, "INFO", game_state.game_day, game_state.current_game_phase, game_state_ref=game_state)
        else:
            _log_flow_event(message, "INFO", game_state.game_day, game_state.current_game_phase, game_state_ref=game_state)

def _get_colored_player_display_name(game_state: GameState, player_config_name: Optional[str], show_role_to_gm: bool = False) -> str:
    if not player_config_name:
        return colorize("未知玩家", Colors.BRIGHT_BLACK)
    player_data = game_state.get_player_info(player_config_name)
    display_name = game_state.get_player_display_name(player_config_name, show_role_to_gm=show_role_to_gm, show_number=True)
    return player_name_color(display_name, player_data, game_state)


def run_night_phase(game_state: GameState) -> Optional[str]:
    game_state.game_day += 1
    game_state.current_game_phase = PHASE_NIGHT_START
    _log_flow_event(f"夜晚 {bold(str(game_state.game_day))} 开始。", "INFO", game_state.game_day, game_state.current_game_phase, game_state_ref=game_state)

    game_state.reset_nightly_events()
    game_state.current_round_deaths = []
    game_state.set_player_poisoned_status(None, False)

    _log_flow_event(f"{role_color('狼人')}请睁眼，请依次表达袭击意向，并由决策狼人最终决定。", "INFO", game_state.game_day, game_state_ref=game_state)
    alive_wolves_config_names = [name for name, data in game_state.players_data.items() if data["role"] == "狼人" and data["status"] == PLAYER_STATUS_ALIVE]
    wolf_final_target = None
    if not alive_wolves_config_names:
        _log_flow_event(colorize("所有狼人已出局，夜晚跳过狼人行动。", Colors.YELLOW), "INFO", game_state.game_day, game_state_ref=game_state)
    else:
        sorted_alive_wolves = sorted(alive_wolves_config_names, key=lambda wolf_name: game_state.players_data[wolf_name]["player_number"])
        decision_maker_wolf = sorted_alive_wolves[-1] if sorted_alive_wolves else None
        nominating_wolves = sorted_alive_wolves[:-1] if len(sorted_alive_wolves) > 1 else []
        if decision_maker_wolf:
            dm_display = _get_colored_player_display_name(game_state, decision_maker_wolf, True)
            _log_flow_event(f"{role_color('狼人')}内部讨论开始。决策者: {dm_display}。", "DEBUG", game_state.game_day, game_state_ref=game_state)
        for wolf_name_to_nominate in nominating_wolves:
            nom_wolf_display = _get_colored_player_display_name(game_state, wolf_name_to_nominate, True)
            _log_flow_event(f"请狼人 {nom_wolf_display} 表达袭击意向。", "INFO", game_state.game_day, game_state_ref=game_state)
            action_specific_info_for_nomination = {"decision_maker_name": decision_maker_wolf}
            nominated_target = get_ai_decision_with_gm_approval(game_state, wolf_name_to_nominate, ACTION_WOLF_NOMINATE, action_specific_info=action_specific_info_for_nomination)
            game_state.wolf_nominations_this_night[wolf_name_to_nominate] = nominated_target
            if nominated_target and game_state.get_player_info(nominated_target):
                target_display_nom = _get_colored_player_display_name(game_state, nominated_target)
            else:
                target_display_nom = colorize("空过/不提名", Colors.GREEN)
            _log_flow_event(f"狼人 {nom_wolf_display} 的意向是: {target_display_nom} (已记录)。", "DEBUG", game_state.game_day, game_state_ref=game_state)
        if decision_maker_wolf:
            dm_display_decision = _get_colored_player_display_name(game_state, decision_maker_wolf, True)
            if nominating_wolves:
                _log_flow_event(f"请决策狼人 {dm_display_decision} 根据队友意向和自己判断，做出最终袭击决定。", "INFO", game_state.game_day, game_state_ref=game_state)
            else:
                _log_flow_event(f"请狼人 {dm_display_decision} (单独行动) 做出袭击决定。", "INFO", game_state.game_day, game_state_ref=game_state)
            wolf_final_target = get_ai_decision_with_gm_approval(game_state, decision_maker_wolf, ACTION_WOLF_KILL)
        
        if wolf_final_target and game_state.get_player_info(wolf_final_target):
            final_decider_display = _get_colored_player_display_name(game_state, decision_maker_wolf, True)
            target_display_final = _get_colored_player_display_name(game_state, wolf_final_target)
            _log_flow_event(f"{role_color('狼人')}团队最终选择袭击玩家: {target_display_final} (由 {final_decider_display} 决定)。", "INFO", game_state.game_day, game_state_ref=game_state)
            game_state.last_night_events["wolf_intended_kill_target"] = wolf_final_target
        else:
            final_decider_display = _get_colored_player_display_name(game_state, decision_maker_wolf, True)
            if wolf_final_target: # This means it was an invalid target, like "Run"
                 _log_flow_event(f"{role_color('狼人')}团队最终选择{colorize('空刀', Colors.GREEN)} (决策者 {final_decider_display} 的选择 '{wolf_final_target}' 无效)。", "WARN", game_state.game_day, game_state_ref=game_state)
            else:
                 _log_flow_event(f"{role_color('狼人')}团队最终选择{colorize('空刀', Colors.GREEN)} (由 {final_decider_display} 决定)。", "INFO", game_state.game_day, game_state_ref=game_state)
            wolf_final_target = None
            game_state.last_night_events["wolf_intended_kill_target"] = None
            
        if game_state.wolf_nominations_this_night:
            nominations_summary_parts = []
            for nom_wolf, nom_target_name in game_state.wolf_nominations_this_night.items():
                nom_wolf_disp = _get_colored_player_display_name(game_state, nom_wolf, True)
                if nom_target_name and game_state.get_player_info(nom_target_name):
                    nom_target_disp = _get_colored_player_display_name(game_state, nom_target_name)
                else:
                    nom_target_disp = colorize("空过/不提名", Colors.GREEN)
                nominations_summary_parts.append(f"{nom_wolf_disp}意向:{nom_target_disp}")
            if nominations_summary_parts:
                 _log_flow_event(f"{colorize('GM参考', Colors.BRIGHT_BLACK)}：本轮狼人提名意向 - {'; '.join(nominations_summary_parts)}", "DEBUG", game_state.game_day, game_state_ref=game_state)

    _log_flow_event(f"{role_color('女巫')}请睁眼。", "INFO", game_state.game_day, game_state_ref=game_state)
    alive_witches = [name for name, data in game_state.players_data.items() if data["role"] == "女巫" and data["status"] == PLAYER_STATUS_ALIVE]
    if alive_witches:
        witch_player_name = alive_witches[0]
        witch_display = _get_colored_player_display_name(game_state, witch_player_name, True)
        target_of_wolf_attack = game_state.last_night_events["wolf_intended_kill_target"]
        potion_used_this_night_by_witch = False
        if target_of_wolf_attack:
            target_attack_display = _get_colored_player_display_name(game_state, target_of_wolf_attack)
            _log_flow_event(f"{role_color('女巫')}，今晚 {target_attack_display} 被袭击了。", "INFO", game_state.game_day, game_state_ref=game_state)
            game_state.last_night_events["witch_informed_of_kill_target"] = target_of_wolf_attack
            if game_state.can_witch_use_potion(witch_player_name, "save"):
                use_save = get_ai_decision_with_gm_approval(game_state, witch_player_name, game_config.ACTION_WITCH_SAVE, action_specific_info={"killed_player_name": target_of_wolf_attack})
                if use_save is True:
                    game_state.use_witch_potion(witch_player_name, "save")
                    game_state.last_night_events["witch_used_save_on"] = target_of_wolf_attack
                    _log_flow_event(f"{witch_display}使用了【{colorize('解药', Colors.GREEN)}】拯救了 {target_attack_display}。", "INFO", game_state.game_day, game_state_ref=game_state)
                    potion_used_this_night_by_witch = True
                else:
                    _log_flow_event(f"{witch_display}没有使用解药。", "INFO", game_state.game_day, game_state_ref=game_state)
            else:
                _log_flow_event(f"{witch_display}已经没有解药了。", "INFO", game_state.game_day, game_state_ref=game_state)
        else:
            _log_flow_event(f"{role_color('女巫')}，今晚是{colorize('平安夜', Colors.GREEN)} (狼人空刀)。", "INFO", game_state.game_day, game_state_ref=game_state)
            game_state.last_night_events["witch_informed_of_kill_target"] = None
        if not potion_used_this_night_by_witch:
            if game_state.can_witch_use_potion(witch_player_name, "poison"):
                _log_flow_event(f"{witch_display}，你要使用【{colorize('夜晚能力药剂', Colors.MAGENTA)}】吗？（你本晚尚未使用过其他药剂）", "INFO", game_state.game_day, game_state_ref=game_state)
                poison_target = get_ai_decision_with_gm_approval(game_state, witch_player_name, game_config.ACTION_WITCH_POISON)
                if poison_target:
                    poison_target_display = _get_colored_player_display_name(game_state, poison_target)
                    game_state.use_witch_potion(witch_player_name, "poison", poison_target)
                    game_state.last_night_events["witch_used_poison_on"] = poison_target
                    game_state.set_player_poisoned_status(poison_target, True)
                    _log_flow_event(f"{witch_display}使用了【{colorize('夜晚能力药剂', Colors.MAGENTA)}】指向了 {poison_target_display}。", "INFO", game_state.game_day, game_state_ref=game_state)
                else:
                    _log_flow_event(f"{witch_display}没有使用夜晚能力药剂。", "INFO", game_state.game_day, game_state_ref=game_state)
            else:
                _log_flow_event(f"{witch_display}已经没有夜晚能力药剂了。", "INFO", game_state.game_day, game_state_ref=game_state)
        elif game_state.can_witch_use_potion(witch_player_name, "poison"):
             _log_flow_event(f"{witch_display}本晚已使用过解药，按规则不能再使用夜晚能力药剂。", "INFO", game_state.game_day, game_state_ref=game_state)
    else:
        _log_flow_event(colorize("女巫已出局或不存在。", Colors.YELLOW), "INFO", game_state.game_day, game_state_ref=game_state)

    _log_flow_event(f"{role_color('预言家')}请睁眼，请选择一名玩家查验身份。", "INFO", game_state.game_day, game_state_ref=game_state)
    alive_prophets = [name for name, data in game_state.players_data.items() if data["role"] == "预言家" and data["status"] == PLAYER_STATUS_ALIVE]
    if alive_prophets:
        prophet_player_name = alive_prophets[0]
        prophet_display = _get_colored_player_display_name(game_state, prophet_player_name, True)
        prophet_target = get_ai_decision_with_gm_approval(game_state, prophet_player_name, game_config.ACTION_PROPHET_CHECK)
        if prophet_target:
            target_info = game_state.get_player_info(prophet_target)
            is_wolf = target_info["role"] == "狼人" if target_info else False
            game_state.last_night_events["prophet_selected_target"] = prophet_target
            game_state.last_night_events["prophet_check_result_is_wolf"] = is_wolf
            prophet_player_data = game_state.get_player_info(prophet_player_name)
            if prophet_player_data:
                if "prophet_check_history" not in prophet_player_data: prophet_player_data["prophet_check_history"] = []
                prophet_player_data["prophet_check_history"].append({"day": game_state.game_day, "target": prophet_target, "is_wolf": is_wolf})
            target_display_prophet = _get_colored_player_display_name(game_state, prophet_target)
            result_colored = colorize("狼人阵营成员", Colors.RED) if is_wolf else colorize("好人阵营成员", Colors.GREEN)
            prophet_personal_history_msg = f"夜晚{game_state.game_day}你查验了 {target_display_prophet}，他是 {result_colored}。"
            game_state.add_player_message_to_history(prophet_player_name, prophet_personal_history_msg, role="system", action_type="prophet_result_private")
            _log_flow_event(f"{prophet_display}查验了 {target_display_prophet}，其身份是 {result_colored}。", "INFO", game_state.game_day, game_state_ref=game_state)
        else:
            _log_flow_event(f"{prophet_display}选择不查验或无法查验。", "INFO", game_state.game_day, game_state_ref=game_state)
    else:
        _log_flow_event(colorize("预言家已出局或不存在。", Colors.YELLOW), "INFO", game_state.game_day, game_state_ref=game_state)

    _log_flow_event(bold("天亮了，夜晚结束，结算死亡情况。"), "INFO", game_state.game_day, game_state_ref=game_state)
    wolf_actual_kill_target = game_state.last_night_events["wolf_intended_kill_target"]
    if wolf_actual_kill_target and wolf_actual_kill_target != game_state.last_night_events.get("witch_used_save_on"):
        game_state.update_player_status(wolf_actual_kill_target, PLAYER_STATUS_DEAD, reason=f"夜晚{game_state.game_day}被狼人袭击")
    poison_kill_target = game_state.last_night_events.get("witch_used_poison_on")
    if poison_kill_target and game_state.get_player_status(poison_kill_target) == PLAYER_STATUS_ALIVE:
        game_state.update_player_status(poison_kill_target, PLAYER_STATUS_DEAD, reason=f"夜晚{game_state.game_day}被女巫能力作用")
    game_state.last_night_events["final_deaths_this_night"] = list(game_state.current_round_deaths)
    
    ui_adapter = get_current_ui_adapter()
    if ui_adapter and is_gradio_mode():
        ui_adapter.show_player_status(game_state.players_data, True)
    
    return check_for_win_conditions(game_state)


def run_day_phase(game_state: GameState) -> Optional[str]:
    game_state.current_game_phase = PHASE_DAY_START
    _log_flow_event(f"白天 {bold(str(game_state.game_day))} 开始。", "INFO", game_state.game_day, game_state.current_game_phase, game_state_ref=game_state)
    game_state.reset_daily_round_data()

    night_deaths_from_event = game_state.last_night_events.get("final_deaths_this_night", [])
    if not night_deaths_from_event:
        _announce_to_all_alive(game_state, "昨晚是平安夜。")
        last_night_dead_player_for_speech_order = None
    else:
        death_announcements = []
        for dead_player_name in night_deaths_from_event:
            dead_player_display = _get_colored_player_display_name(game_state, dead_player_name, True)
            death_announcements.append(dead_player_display)
        _announce_to_all_alive(game_state, f"昨晚出局的玩家是: {', '.join(death_announcements)}。")
        last_night_dead_player_for_speech_order = night_deaths_from_event[0] if night_deaths_from_event else None

    game_state.current_game_phase = PHASE_PROCESS_DEATH_EFFECTS
    deaths_to_process_for_effects = list(game_state.current_round_deaths)
    for dead_player_name in deaths_to_process_for_effects:
        player_info = game_state.get_player_info(dead_player_name)
        dead_player_display_hunter = _get_colored_player_display_name(game_state, dead_player_name, True)
        if player_info and player_info["role"] == "猎人" and player_info["status"] == PLAYER_STATUS_DEAD and game_state.can_hunter_shoot(dead_player_name):
            _announce_to_all_alive(game_state, f"出局的玩家 {dead_player_display_hunter} 是{role_color('猎人')}，他可以选择是否使用能力！")
            shot_target = get_ai_decision_with_gm_approval(game_state, dead_player_name, game_config.ACTION_HUNTER_SHOOT)
            if shot_target:
                shot_target_display = _get_colored_player_display_name(game_state, shot_target)
                _announce_to_all_alive(game_state, f"{role_color('猎人')} {dead_player_display_hunter} 使用能力选择了 {shot_target_display}！")
                game_state.update_player_status(shot_target, PLAYER_STATUS_DEAD, reason=f"被猎人{dead_player_name}能力作用")
                game_state.hunter_uses_shot(dead_player_name)
                winner = check_for_win_conditions(game_state);
                if winner: return winner
            else:
                _announce_to_all_alive(game_state, f"{role_color('猎人')} {dead_player_display_hunter} 选择不使用能力。")
                game_state.hunter_uses_shot(dead_player_name)

    game_state.current_game_phase = PHASE_LAST_WORDS_SPEECH
    unique_dead_for_last_words = list(dict.fromkeys(game_state.current_round_deaths))
    if unique_dead_for_last_words:
        _log_flow_event(bold("进入遗言阶段") + " (针对夜晚死亡及猎人效果)。", "INFO", game_state.game_day, game_state.current_game_phase, game_state_ref=game_state)
        for dead_player_config_name in unique_dead_for_last_words:
            if game_state.get_player_status(dead_player_config_name) == PLAYER_STATUS_DEAD:
                dead_player_lw_display = _get_colored_player_display_name(game_state, dead_player_config_name, True)
                _announce_to_all_alive(game_state, f"请玩家 {dead_player_lw_display} 发表遗言。")
                last_words = get_ai_decision_with_gm_approval(game_state, dead_player_config_name, game_config.ACTION_LAST_WORDS)
                if last_words:
                    _announce_to_all_alive(game_state, f"{_get_colored_player_display_name(game_state, dead_player_config_name)} 的遗言: {last_words}")
                    game_state.add_player_message_to_history(dead_player_config_name, last_words, role="assistant", action_type="last_words_broadcast_night")
                else:
                    _announce_to_all_alive(game_state, f"玩家 {dead_player_lw_display} 没有发表遗言。")
    else:
        _log_flow_event("本轮没有玩家需要发表遗言（针对夜晚死亡及猎人效果）。", "INFO", game_state.game_day, game_state_ref=game_state)

    game_state.current_round_deaths = []
    game_state.current_game_phase = PHASE_SPEECH
    speech_order = determine_speech_order(game_state, last_night_dead_player_for_speech_order)
    if not speech_order:
        _log_flow_event(colorize("没有存活的玩家可以发言了。", Colors.YELLOW), "WARN", game_state.game_day, game_state_ref=game_state)
    else:
        speech_order_display = [_get_colored_player_display_name(game_state, p) for p in speech_order]
        _announce_to_all_alive(game_state, f"请按以下顺序发言: {', '.join(speech_order_display)}")
        for i, speaker_name in enumerate(speech_order):
            speaker_display_speech = _get_colored_player_display_name(game_state, speaker_name)
            if game_state.get_player_status(speaker_name) != PLAYER_STATUS_ALIVE:
                _log_flow_event(f"玩家 {speaker_display_speech} 在轮到其发言前已出局，跳过。", "WARN", game_state.game_day, game_state_ref=game_state)
                continue
            _announce_to_all_alive(game_state, f"轮到玩家 {speaker_display_speech} 发言。({i+1}/{len(speech_order)})")
            speech = get_ai_decision_with_gm_approval(game_state, speaker_name, game_config.ACTION_SPEECH)
            if speech:
                _announce_to_all_alive(game_state, f"{speaker_display_speech} 发言: {speech}", is_gm_broadcast=False)
                game_state.add_player_message_to_history(speaker_name, speech, role="assistant", action_type="speech_taken")
                game_state.round_speeches_log.append({"player": speaker_name, "speech": speech})
            else:
                 _announce_to_all_alive(game_state, f"玩家 {speaker_display_speech} 选择不发言或被跳过。")
                 game_state.round_speeches_log.append({"player": speaker_name, "speech": "(选择不发言)"})
            game_state.last_round_final_speaker = speaker_name

    game_state.current_game_phase = PHASE_VOTE
    _announce_to_all_alive(game_state, bold("发言结束，现在开始投票。") + "请投票选出你认为是“狼人伙伴”的玩家。")
    votes_this_round: Dict[str, str] = {}
    alive_voters = game_state.get_alive_players()
    for voter_name in sorted(alive_voters, key=lambda name: game_state.players_data[name]["player_number"]):
        if game_state.get_player_status(voter_name) != PLAYER_STATUS_ALIVE: continue
        voter_display = _get_colored_player_display_name(game_state, voter_name)
        vote_target = get_ai_decision_with_gm_approval(game_state, voter_name, game_config.ACTION_VOTE)
        if vote_target:
            votes_this_round[voter_name] = vote_target
            target_display_vote = colorize("弃票", Colors.GREEN) if vote_target == VOTE_SKIP else _get_colored_player_display_name(game_state, vote_target)
            _log_flow_event(f"{voter_display} 投票给 --> {target_display_vote} (记录完毕)。", "DEBUG", game_state.game_day, game_state_ref=game_state)
        else:
            _log_flow_event(f"玩家 {voter_display} 未能完成投票，默认记为弃票。", "WARN", game_state.game_day, game_state_ref=game_state)
            votes_this_round[voter_name] = VOTE_SKIP
    game_state.votes_current_round = votes_this_round

    player_voted_out, was_tie_and_no_one_out = tally_votes_and_handle_ties(game_state, votes_this_round)
    if was_tie_and_no_one_out:
        _announce_to_all_alive(game_state, "投票出现平票，本轮无人出局。")
    elif player_voted_out:
        voted_out_display = _get_colored_player_display_name(game_state, player_voted_out, True)
        _announce_to_all_alive(game_state, f"投票结果: 玩家 {voted_out_display} 被公投出局！")
        game_state.update_player_status(player_voted_out, PLAYER_STATUS_DEAD, reason=f"白天{game_state.game_day}被投票出局")
        winner = check_for_win_conditions(game_state);
        if winner: return winner
        game_state.current_game_phase = PHASE_PROCESS_DEATH_EFFECTS
        voted_out_info = game_state.get_player_info(player_voted_out)
        if voted_out_info and voted_out_info["role"] == "猎人" and game_state.can_hunter_shoot(player_voted_out):
            _announce_to_all_alive(game_state, f"被票出局的玩家 {voted_out_display} 是{role_color('猎人')}，他可以选择是否使用能力！")
            shot_target_after_vote = get_ai_decision_with_gm_approval(game_state, player_voted_out, game_config.ACTION_HUNTER_SHOOT)
            if shot_target_after_vote:
                shot_target_display_vote = _get_colored_player_display_name(game_state, shot_target_after_vote)
                _announce_to_all_alive(game_state, f"{role_color('猎人')} {voted_out_display} 使用能力选择了 {shot_target_display_vote}！")
                game_state.update_player_status(shot_target_after_vote, PLAYER_STATUS_DEAD, reason=f"被猎人{player_voted_out}能力作用(票出后)")
                game_state.hunter_uses_shot(player_voted_out)
                winner = check_for_win_conditions(game_state);
                if winner: return winner
            else:
                _announce_to_all_alive(game_state, f"{role_color('猎人')} {voted_out_display} 选择不使用能力。")
                game_state.hunter_uses_shot(player_voted_out)

        game_state.current_game_phase = PHASE_LAST_WORDS_SPEECH
        unique_dead_after_vote = list(dict.fromkeys(game_state.current_round_deaths))
        if unique_dead_after_vote:
            _log_flow_event(bold("进入（投票后）遗言阶段。"), "INFO", game_state.game_day, game_state.current_game_phase, game_state_ref=game_state)
            for dead_player_config_name_vote in unique_dead_after_vote:
                 if game_state.get_player_status(dead_player_config_name_vote) == PLAYER_STATUS_DEAD:
                    dead_vote_lw_display = _get_colored_player_display_name(game_state, dead_player_config_name_vote, True)
                    _announce_to_all_alive(game_state, f"请被票出或因此出局的玩家 {dead_vote_lw_display} 发表遗言。")
                    last_words_vote = get_ai_decision_with_gm_approval(game_state, dead_player_config_name_vote, game_config.ACTION_LAST_WORDS)
                    if last_words_vote:
                        _announce_to_all_alive(game_state, f"{_get_colored_player_display_name(game_state, dead_player_config_name_vote)} 的遗言: {last_words_vote}")
                        game_state.add_player_message_to_history(dead_player_config_name_vote, last_words_vote, role="assistant", action_type="last_words_broadcast_vote")
                    else:
                         _announce_to_all_alive(game_state, f"玩家 {dead_vote_lw_display} 没有发表遗言。")
    else:
        _announce_to_all_alive(game_state, "本轮投票无人出局。")

    ui_adapter = get_current_ui_adapter()
    if ui_adapter and is_gradio_mode():
        ui_adapter.show_player_status(game_state.players_data, True)

    return check_for_win_conditions(game_state)


def run_game_loop(game_state: GameState, ui_adapter):
    if ui_adapter:
        from ui_adapter import set_current_ui_adapter
        set_current_ui_adapter(ui_adapter)
        
    _log_flow_event(bold(green("游戏开始！")), "INFO", game_state_ref=game_state)
    winner = None
    max_days = 20
    while not winner:
        winner = run_night_phase(game_state)
        if winner: break
        winner = run_day_phase(game_state)
        if winner: break
        if game_state.game_day >= max_days:
            _log_flow_event(colorize(f"游戏达到最大天数 ({max_days})，强制结束。", Colors.BOLD + Colors.YELLOW), "WARN", game_state_ref=game_state)
            winner = check_for_win_conditions(game_state)
            if not winner: winner = f"达到最大天数({max_days})仍未分胜负"
            break
        
        _log_flow_event(f"第 {bold(str(game_state.game_day))} 天结束，准备进入夜晚。", "INFO", game_state_ref=game_state)
        
        # 调用UI适配器来处理暂停
        ui_adapter.wait_for_continue("请按回车或在UI上点击“继续”进入下一夜...")
    
    game_state.current_game_phase = PHASE_GAME_OVER
    winner_colored = colorize(str(winner), Colors.BOLD + (Colors.GREEN if "好人" in str(winner) else Colors.RED if "狼人" in str(winner) else Colors.YELLOW))
    _log_flow_event(f"{bold(magenta('游戏结束！'))}结果: {winner_colored}", "INFO", game_state_ref=game_state)
    _announce_to_all_alive(game_state, f"游戏结束！结果: {winner}")

    _log_flow_event(f"--- {bold(blue('游戏最终状态回顾'))} ---", "INFO", game_state_ref=game_state)
    sorted_players_final = sorted(game_state.players_data.values(), key=lambda p: p.get("player_number", 0))
    for p_data in sorted_players_final:
        p_name_display_final = _get_colored_player_display_name(game_state, p_data["config_name"], True)
        p_role_final = role_color(p_data['role'])
        p_status_final = colorize(p_data['status'], Colors.GREEN if p_data['status'] == PLAYER_STATUS_ALIVE else Colors.RED)
        _log_flow_event(f"{p_name_display_final} - 身份: {p_role_final}, 状态: {p_status_final}", "INFO", game_state_ref=game_state)