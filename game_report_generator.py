# game_report_generator.py (更正和完善版)
import os
import time
from typing import List, Dict, Any, Optional
from collections import defaultdict
import re

# 假设 terminal_colors.py 在项目根目录或者Python可以找到的路径下
try:
    from terminal_colors import colorize, Colors, green, red, yellow, blue, bold, magenta, cyan
except ImportError:
    def colorize(text: str, _color_code: str) -> str: return text
    class Colors: RESET = ""; BOLD = ""; RED = ""; GREEN = ""; YELLOW = ""; BLUE = ""; MAGENTA = ""; CYAN = ""; BRIGHT_BLACK = ""
    def green(text: str) -> str: return text
    def red(text: str) -> str: return text
    def yellow(text: str) -> str: return text
    def blue(text: str) -> str: return text
    def bold(text: str) -> str: return text
    def magenta(text: str) -> str: return text # Add if used
    def cyan(text: str) -> str: return text    # Add if used

from game_state import GameState
import game_config

def _format_timestamp_str(ts_str: Optional[str] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    if ts_str: return ts_str
    return time.strftime(format_str, time.localtime())

def _get_player_line(p_data: Dict[str, Any], game_state: Optional[GameState] = None) -> str:
    parts = [
        f"玩家 {p_data.get('player_number', 'N/A')}",
        f"({p_data.get('config_name', '未知配置名')})",
        f"角色: {p_data.get('role', '未知角色')}",
        f"状态: {p_data.get('status', '未知状态')}"
    ]
    role = p_data.get('role')
    if role == "女巫":
        save = p_data.get(game_config.WITCH_HAS_SAVE_POTION_KEY, None)
        poison = p_data.get(game_config.WITCH_HAS_POISON_POTION_KEY, None)
        if save is not None: parts.append(f"解药:{'有' if save else '无'}")
        if poison is not None: parts.append(f"夜晚能力药剂:{'有' if poison else '无'}")
    elif role == "猎人":
        shoot = p_data.get(game_config.HUNTER_CAN_SHOOT_KEY, None)
        if shoot is not None: parts.append(f"开枪能力:{'可用' if shoot else '已用/不可用'}")
    elif role == "预言家" and game_state:
        history = p_data.get("prophet_check_history", [])
        if history:
            disp = [f"D{e.get('day','?')}:{game_state.get_player_display_name(e.get('target','?')) if e.get('target') != '?' else '?' }->{'狼' if e.get('is_wolf') else '好人'}" for e in history]
            if disp: parts.append(f"查验史:[{'; '.join(disp)}]")
    return " - ".join(parts)

def _extract_game_result(game_state: GameState) -> str:
    if hasattr(game_state, 'game_winner_message') and game_state.game_winner_message: # 假设有一个明确的胜利消息
        return str(game_state.game_winner_message)
    # 尝试从最后一个 PHASE_GAME_OVER 事件的 message 中提取
    for log_entry in reversed(game_state.game_log):
        if log_entry.get("event_type") == game_config.PHASE_GAME_OVER:
            return log_entry.get("message", "游戏结果未知 (需查阅日志)")
        # 更通用的检查
        msg_lower = log_entry.get("message", "").lower()
        if "游戏结束！结果:" in msg_lower:
            return log_entry.get("message").split("结果:", 1)[1].strip() if "结果:" in log_entry.get("message") else log_entry.get("message")
    return "游戏结果未知 (未在日志中明确记录)"

def generate_detailed_report(game_state: GameState, filename: str) -> bool:
    report_lines = []
    report_lines.append("=" * 50 + f"\n AI 狼人杀 - 详细游戏报告\n" + "=" * 50)
    report_lines.append(f"报告生成时间: {_format_timestamp_str()}")
    report_lines.append(f"游戏结束时天数: {game_state.game_day}")
    report_lines.append(f"游戏结束时阶段: {game_state.current_game_phase}")
    report_lines.append(f"游戏结果: {_extract_game_result(game_state)}")
    report_lines.append("\n--- 游戏配置与初始角色分配 (GM视角) ---")
    num_players = len(game_state.players_data)
    report_lines.append(f"玩家人数: {num_players}")
    dist_key = str(num_players) if isinstance(game_config.ROLE_DISTRIBUTIONS.get(num_players), list) else num_players # Handle if keys are strings
    if dist_key in game_config.ROLE_DISTRIBUTIONS:
        report_lines.append(f"角色板子 ({num_players}人): {', '.join(game_config.ROLE_DISTRIBUTIONS[dist_key])}")
    else: report_lines.append("未找到对应的角色板子配置。")
    report_lines.append("\n--- 最终玩家状态与信息 (GM视角) ---")
    sorted_players_data = sorted(game_state.players_data.values(), key=lambda p: p.get("player_number", 0))
    for p_data in sorted_players_data: report_lines.append(_get_player_line(p_data, game_state))
    report_lines.append("\n\n" + "=" * 20 + " 完整游戏事件日志 " + "=" * 20)
    if game_state.game_log:
        for log in game_state.game_log:
            details_str = f" | 详情: {log['details']}" if log.get("details") else ""
            report_lines.append(f"[{log.get('timestamp','?'):19s}] [{log.get('event_type','?'):25s}] {log.get('message','')}{details_str}")
    else: report_lines.append("游戏事件日志为空。")
    report_lines.append("\n\n" + "=" * 20 + " 玩家详细消息历史 " + "=" * 20)
    for p_data in sorted_players_data:
        hist_lines = [f"\n--- 玩家 {p_data.get('player_number','?')}({p_data.get('config_name','?')}) - 角色: {p_data.get('role','?')} 的历史 ---"]
        history = p_data.get("history", [])
        if history:
            for i, entry in enumerate(history):
                meta = f" (Meta: {entry['_meta']})" if "_meta" in entry else ""
                hist_lines.append(f"  [{i+1:02d}] {entry.get('role','?').upper():<9s}{meta}: {entry.get('content','')}")
        else: hist_lines.append("  (无消息历史)")
        report_lines.extend(hist_lines)
    try:
        with open(filename, 'w', encoding='utf-8') as f: f.write("\n".join(report_lines))
        print(green(f"详细报告已生成: {filename}"))
        return True
    except IOError as e:
        print(red(f"错误：无法写入详细报告文件 {filename}: {e}"))
        return False

def generate_summary_report(game_state: GameState, filename: str) -> bool:
    report_lines = []
    report_lines.append("=" * 50 + f"\n AI 狼人杀 - 游戏摘要报告\n" + "=" * 50)
    report_lines.append(f"报告生成时间: {_format_timestamp_str()}")
    report_lines.append("\n--- 游戏概览 ---")
    report_lines.append(f"游戏结果: {_extract_game_result(game_state)}")
    report_lines.append(f"游戏共进行: {game_state.game_day} 天")
    num_players = len(game_state.players_data)
    report_lines.append(f"参与玩家数: {num_players}")
    dist_key_sum = str(num_players) if isinstance(game_config.ROLE_DISTRIBUTIONS.get(num_players), list) else num_players
    if dist_key_sum in game_config.ROLE_DISTRIBUTIONS:
        report_lines.append(f"角色配置 ({num_players}人): {', '.join(game_config.ROLE_DISTRIBUTIONS[dist_key_sum])}")
    report_lines.append("\n--- 最终玩家信息 ---")
    sorted_players_data_sum = sorted(game_state.players_data.values(), key=lambda p: p.get("player_number", 0))
    for p_data in sorted_players_data_sum: report_lines.append(_get_player_line(p_data, game_state))
    report_lines.append("\n--- 关键事件回顾 ---")
    
    events_by_day = defaultdict(lambda: defaultdict(list))

    for log in game_state.game_log:
        details = log.get("details", {})
        day = details.get("day")
        phase = details.get("phase")
        event_type = log.get("event_type", "UnknownEvent")
        message = log.get("message", "")

        if day is None: # Attempt to infer day if not in details
            day_match = re.search(r"(?:第 |夜晚 |白天 )(\d+)", message)
            if day_match: day = int(day_match.group(1))
        
        day_key = f"Day {day}" if day is not None else "PreGame/PostGame"
        phase_key = phase if phase else "General"

        # Night Actions
        if event_type == "INFO" and "狼人团队最终选择袭击玩家" in message:
            match = re.search(r"狼人团队最终选择袭击玩家: (玩家\d+ \S+) \(由 (玩家\d+ \S+) 决定\)", message)
            if match: events_by_day[day_key][phase_key].append(f"  - 狼袭: {match.group(1)} (决策: {match.group(2)})")
        elif event_type == "INFO" and "狼人团队最终选择空刀" in message:
            events_by_day[day_key][phase_key].append("  - 狼袭: 空刀")
        elif event_type == "PotionUsed":
            p_name = game_state.get_player_display_name(details.get("player"))
            p_type = details.get("potion_type")
            target_name = details.get("target") # Witch save/poison might have target in details
            target_display = game_state.get_player_display_name(target_name) if target_name else ""
            events_by_day[day_key][phase_key].append(f"  - 女巫 ({p_name}) 使用 {p_type} {('于 '+target_display) if target_display else ''}")
        elif event_type == "INFO" and "预言家查验了" in message: # Public announcement of check
            match = re.search(r"预言家查验了 (玩家\d+ \S+)，其身份是 (.*?)。", message)
            if match: events_by_day[day_key][phase_key].append(f"  - 预言家查验: {match.group(1)} -> {match.group(2)}")
        
        # Deaths (from StatusUpdate or GM Broadcast)
        if event_type == "StatusUpdate" and details.get("new_status") == game_config.PLAYER_STATUS_DEAD:
            p_name = game_state.get_player_display_name(details.get("player"))
            reason = details.get("reason", "未知原因")
            events_by_day[day_key][phase_key].append(f"  - 死亡: {p_name} (原因: {reason})")
        elif event_type == "INFO" and "GM广播: 昨晚出局的玩家是:" in message:
             events_by_day[day_key][phase_key].append(f"  - 夜晚死亡宣告: {message.split('是:',1)[1].strip()}")
        elif event_type == "INFO" and "GM广播: 昨晚是平安夜" in message:
             events_by_day[day_key][phase_key].append(f"  - 夜晚: 平安夜")

        # Hunter
        if event_type == "INFO" and "猎人" in message and "使用能力选择" in message:
            events_by_day[day_key][phase_key].append(f"  - 猎人行动: {message.split('GM广播: ',1)[-1]}")
        elif event_type == "INFO" and "猎人" in message and "选择不使用能力" in message:
            events_by_day[day_key][phase_key].append(f"  - 猎人行动: {message.split('GM广播: ',1)[-1]}")

        # Last Words (from PlayerMessageLog with specific action_type or GM Broadcast)
        if event_type == "PlayerMessageLog" and details and "last_words_broadcast" in details.get("action_type",""):
            p_name = game_state.get_player_display_name(details.get("player"))
            events_by_day[day_key][phase_key].append(f"  - 遗言 ({p_name}): {message[:60]}{'...' if len(message)>60 else ''}")
        elif event_type == "INFO" and "的遗言:" in message: # From GM Broadcast
             events_by_day[day_key][phase_key].append(f"  - {message.split('GM广播: ',1)[-1][:80]}{'...' if len(message)>80 else ''}")


        # Votes
        if event_type == "INFO" and "投票结果:" in message:
            events_by_day[day_key][phase_key].append(f"  - {message.split('GM广播: ',1)[-1]}")
        elif event_type == "INFO" and "投票出现平票" in message:
            events_by_day[day_key][phase_key].append(f"  - 投票: 平票，无人出局")

    if events_by_day:
        sorted_day_keys = sorted(events_by_day.keys(), key=lambda x: (x.startswith("Day "), int(x.split(" ")[1]) if x.startswith("Day ") and x.split(" ")[1].isdigit() else float('-inf'), x))
        for day_k in sorted_day_keys:
            report_lines.append(f"\n--- {day_k} ---")
            if events_by_day[day_k]:
                # Define a preferred phase order for display
                phase_order = [game_config.PHASE_NIGHT_START, "NightActions", # Assuming you might use a generic NightActions phase
                               game_config.PHASE_DAY_START, game_config.PHASE_PROCESS_DEATH_EFFECTS, 
                               game_config.PHASE_LAST_WORDS_SPEECH, game_config.PHASE_SPEECH, 
                               game_config.PHASE_VOTE, "VoteResult", "General"]
                
                sorted_phase_keys = sorted(events_by_day[day_k].keys(), key=lambda p: phase_order.index(p) if p in phase_order else float('inf'))

                for phase_k in sorted_phase_keys:
                    if events_by_day[day_k][phase_k]:
                        report_lines.append(f"  [{phase_k}]")
                        for event_line in events_by_day[day_k][phase_k]:
                            report_lines.append(f"    {event_line.strip()}")
            else:
                report_lines.append("  (当天无符合筛选的关键事件记录)")
    else:
        report_lines.append("  (未能自动提取关键事件回顾，请参考详细报告中的游戏事件日志)")

    try:
        with open(filename, 'w', encoding='utf-8') as f: f.write("\n".join(report_lines))
        print(green(f"摘要报告已生成: {filename}"))
        return True
    except IOError as e:
        print(red(f"错误：无法写入摘要报告文件 {filename}: {e}"))
        return False

def export_game_reports(game_state: GameState, base_folder: str = "game_reports"):
    if not os.path.exists(base_folder):
        try:
            os.makedirs(base_folder)
            print(green(f"报告文件夹已创建: {base_folder}"))
        except OSError as e:
            print(red(f"错误: 无法创建报告文件夹 {base_folder}: {e}"))
            return
    timestamp_suffix = time.strftime("%Y%m%d_%H%M%S")
    detailed_filename = os.path.join(base_folder, f"detailed_werewolf_report_{timestamp_suffix}.txt")
    summary_filename = os.path.join(base_folder, f"summary_werewolf_report_{timestamp_suffix}.txt")
    print(blue("\n正在生成游戏报告..."))
    s_detailed = generate_detailed_report(game_state, detailed_filename)
    s_summary = generate_summary_report(game_state, summary_filename)
    if s_detailed or s_summary: print(green("报告生成完毕。"))
    else: print(yellow("部分或全部报告生成失败。"))