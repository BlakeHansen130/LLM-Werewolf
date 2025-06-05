# werewolf_game_main.py (修改版 - 颜色输出)
import os
import sys
import traceback

# 假设 terminal_colors.py 在项目根目录或者Python可以找到的路径下
try:
    from terminal_colors import (
        colorize, Colors, red, green, yellow, blue, magenta, cyan, grey, bold, underline
    )
except ImportError:
    # Fallback if terminal_colors is not found
    def colorize(text: str, _color_code: str) -> str: return text
    class Colors: RESET = ""; BOLD = ""; RED = ""; GREEN = ""; YELLOW = ""; BLUE = ""; MAGENTA = ""; CYAN = ""; BRIGHT_BLACK = ""; BRIGHT_YELLOW = ""; UNDERLINE = ""
    def red(text: str) -> str: return text
    def green(text: str) -> str: return text
    def yellow(text: str) -> str: return text
    def blue(text: str) -> str: return text
    def magenta(text: str) -> str: return text
    def cyan(text: str) -> str: return text
    def grey(text: str) -> str: return text
    def bold(text: str) -> str: return text
    def underline(text: str) -> str: return text


from game_state import GameState
from game_setup import initialize_game, CONFIG_FILENAME
from game_flow_manager import run_game_loop
from gm_tools import (
    display_all_player_statuses,
    view_player_game_history,
    display_game_log,
    gm_manual_set_player_status,
    display_current_votes
)
import game_config # 确保 game_config 被导入
from game_config import PLAYER_STATUS_ALIVE, PLAYER_STATUS_DEAD, PHASE_GAME_SETUP, PHASE_START_GAME # 显式导入用到的常量
from game_report_generator import export_game_reports


def run_gm_command_interface(game_state: GameState, during_game: bool = False):
    """一个简单的GM命令行界面。"""
    while True:
        print(bold(blue("\n--- GM 工具箱 ---")))
        print(f"1. 查看所有玩家状态")
        print(f"2. 查看特定玩家消息历史")
        print(f"3. 查看游戏事件日志 (最新)")
        if during_game or game_state.current_game_phase not in [PHASE_GAME_SETUP, PHASE_START_GAME]:
            print(f"4. 查看当前轮次投票 (如果适用)")
        print(colorize("5. 手动设置玩家状态 (极度慎用!)", Colors.BOLD + Colors.YELLOW))
        print("0. 返回游戏 / 结束GM会话")

        choice = input(cyan("请输入GM操作编号: ")).strip()

        if choice == '1':
            display_all_player_statuses(game_state) # gm_tools 内部会处理自己的颜色
        elif choice == '2':
            p_name_input = input(cyan("请输入要查看历史的玩家配置名 (例如 PlayerAI1): ")).strip()
            if p_name_input in game_state.ai_player_config_names:
                view_player_game_history(game_state, p_name_input)
            else:
                print(red(f"错误: 玩家配置名 '{colorize(p_name_input, Colors.YELLOW)}' 不存在。可用: {colorize(str(game_state.ai_player_config_names), Colors.CYAN)}"))
        elif choice == '3':
            count_str = input(cyan("要显示多少条日志 (默认20)? ")).strip()
            count = int(count_str) if count_str.isdigit() and int(count_str) > 0 else 20
            display_game_log(game_state, count)
        elif choice == '4' and (during_game or game_state.current_game_phase not in [PHASE_GAME_SETUP, PHASE_START_GAME]):
            display_current_votes(game_state)
        elif choice == '5':
            print(colorize("警告：手动修改玩家状态可能导致游戏逻辑混乱，请仅在特殊调试情况下使用。", Colors.BOLD + Colors.RED))
            p_name_manual = input(cyan("请输入要修改状态的玩家配置名: ")).strip()
            if p_name_manual not in game_state.ai_player_config_names:
                print(red(f"错误: 玩家配置名 '{colorize(p_name_manual, Colors.YELLOW)}' 不存在。"))
                continue
            status_input = input(cyan(f"请输入新状态 ('{green(PLAYER_STATUS_ALIVE)}' 或 '{red(PLAYER_STATUS_DEAD)}'): ")).strip().lower()
            if status_input not in [PLAYER_STATUS_ALIVE, PLAYER_STATUS_DEAD]:
                print(red(f"错误: 无效的状态 '{colorize(status_input, Colors.YELLOW)}'。"))
                continue
            reason_input = input(cyan("请输入修改原因 (例如 'GM调试修正'): ")).strip()
            if not reason_input: reason_input = "GM手动操作"
            confirm_input = input(
                yellow(f"确认将玩家 {colorize(p_name_manual, Colors.BRIGHT_YELLOW)} 状态设为 {colorize(status_input, Colors.GREEN if status_input == PLAYER_STATUS_ALIVE else Colors.RED)} ") +
                yellow(f"(原因: {reason_input})? (y/n): ")
            ).strip().lower()
            if confirm_input == 'y':
                gm_manual_set_player_status(game_state, p_name_manual, status_input, reason_input)
            else:
                print(yellow("操作已取消。"))
        elif choice == '0':
            print(green("结束GM工具会话。"))
            break
        else:
            print(red("无效的GM命令编号。"))
        input(grey("按回车键继续GM操作或返回..."))


def main():
    print(bold(magenta("欢迎来到AI狼人杀游戏！")))
    print(magenta("=" * 30))

    config_file_colored = colorize(CONFIG_FILENAME, Colors.BLUE)
    if not os.path.exists(CONFIG_FILENAME):
        print(red(f"错误: 核心玩家配置文件 '{config_file_colored}' 未找到！"))
        print(yellow("请确保该文件存在于程序运行目录下，并包含玩家AI的配置。"))
        print(grey("示例内容 (一个玩家):"))
        print(grey("""
[
  {
    "name": "PlayerAI1",
    "api_endpoint": "YOUR_API_ENDPOINT_HERE (e.g., http://localhost:11434/v1/chat/completions)",
    "api_key": "YOUR_API_KEY_HERE (or 'EMPTY')",
    "model": "YOUR_MODEL_NAME_HERE (e.g., llama3)",
    "response_handler_type": "standard"
  }
]
        """))
        print(cyan(f"支持的 response_handler_type 包括: 'standard', 'think_tags_in_content', 'qwen_stream_with_thinking', 'content_with_separate_reasoning'."))
        return

    game_state = GameState()

    print(bold(blue("\n--- 游戏设置阶段 ---")))
    if not initialize_game(game_state):
        print(red("游戏初始化失败，无法开始。请检查日志输出。"))
        return

    num_players_colored = bold(str(len(game_state.ai_player_config_names)))
    print(green(f"\n游戏设置完毕！共有 {num_players_colored} 名玩家参与。"))
    print(cyan("GM可以随时通过特定指令（如果实现）或在阶段间隙介入。"))
    display_all_player_statuses(game_state)
    input(bold(cyan("\n按回车键开始第一夜...")))

    try:
        run_game_loop(game_state)
    except KeyboardInterrupt:
        print(yellow("\nGM通过Ctrl+C中断了游戏。"))
        game_state.add_game_event_log("GameInterrupt", "游戏被GM通过键盘中断。", {"day": game_state.game_day, "phase": game_state.current_game_phase})
    except Exception as e:
        print(red(f"\n游戏循环中发生严重错误: {e}"))
        tb_str = traceback.format_exc()
        print(grey(tb_str)) # Traceback用灰色
        game_state.add_game_event_log("GameError", f"游戏主循环严重错误: {e}", {"traceback": tb_str, "day": game_state.game_day, "phase": game_state.current_game_phase})
    finally:
        print(magenta("\n" + "=" * 30))
        print(bold(magenta("--- 游戏会话结束 ---")))
        
        final_phase_colored = colorize(game_state.current_game_phase, Colors.MAGENTA)
        print(f"最终游戏状态: {final_phase_colored}")
        
        # 使用 game_state 中存储的获胜消息 (如果存在)
        final_result_msg = game_state.game_winner_message if game_state.game_winner_message else "请查看报告或日志确定最终结果"
        final_result_colored = final_result_msg # 假设 game_winner_message 本身可能已带颜色
        if "好人胜利" in final_result_msg: final_result_colored = green(final_result_msg)
        elif "狼人胜利" in final_result_msg: final_result_colored = red(final_result_msg)
        elif "平局" in final_result_msg: final_result_colored = yellow(final_result_msg)
        print(f"游戏结果: {final_result_colored}")

        if game_state.game_day > 0 or game_state.game_log:
            export_choice = input(cyan("是否要导出本局游戏报告? (y/n): ")).strip().lower()
            if export_choice == 'y':
                export_game_reports(game_state)
        else:
            print(yellow("游戏未实际开始或无日志记录，跳过报告导出。"))

        print(cyan("\n你可以使用GM工具查看更多信息。"))
        run_gm_command_interface(game_state, during_game=False)
        print(bold(green("\n感谢游玩！")))


if __name__ == "__main__":
    main()