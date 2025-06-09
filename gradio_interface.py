# gradio_interface.py (最终修复版 - 解决Lambda闭包问题)
import gradio as gr
import time
import os
from typing import List, Dict, Any, Optional
from queue import Queue, Empty
import threading

from assets_base64 import get_logo, get_role_icon, get_status_emoji
from ui_adapter import GradioUIAdapter, GMApprovalResult
from game_state import GameState
import game_config

class GradioGameInterface:
    def __init__(self):
        self.game_state: Optional[GameState] = None
        self.ui_adapter: Optional[GradioUIAdapter] = None
        self.approval_lock = threading.Lock()
        self.approval_waiting = False
        self.approval_result_queue = Queue()
        self.current_approval_data = {}
        self.continue_lock = threading.Lock()
        self.continue_event = threading.Event()
        self.is_waiting_for_continue = False

    def set_game_state(self, game_state: GameState):
        self.game_state = game_state

    def set_ui_adapter(self, ui_adapter: GradioUIAdapter):
        self.ui_adapter = ui_adapter
        if self.ui_adapter:
            ui_adapter.interface = self

    def _get_custom_css(self) -> str:
        return """
        #game-info { background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; text-align: center; font-weight: bold; }
        #player-status { background: #f8f9fa; border: 2px solid #e9ecef; border-radius: 8px; padding: 10px; }
        #chat-interface { border: 2px solid #dee2e6; border-radius: 8px; }
        #gm-ai-response { background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 10px; margin-bottom: 10px; }
        #gm-result { background: #d1ecf1; border: 1px solid #bee5eb; border-radius: 6px; padding: 15px; margin-top: 15px; }
        .player-alive { color: #28a745; font-weight: bold; }
        .player-dead { color: #dc3545; text-decoration: line-through; }
        .player-item:hover { background-color: #e9ecef; transition: background-color 0.2s; }
        """

    def _format_game_info(self, phase: str, stage: str, day: int, alive_count: int) -> str:
        return f"""<div><span style="font-size: 18px;">第 {day} 天</span> | <span style="font-size: 16px;">{phase}</span> | <span style="font-size: 16px;">存活：{alive_count} 人</span> | <span style="font-size: 14px;">状态：{stage}</span></div>"""

    def _format_player_status(self, players_data: Dict[str, Dict[str, Any]], show_gm_view: bool = True) -> str:
        if not players_data: return "<p>暂无玩家数据</p>"
        sorted_players = sorted(players_data.values(), key=lambda p: p.get("player_number", 0))
        html_parts = []
        for player_data in sorted_players:
            is_alive = player_data.get("status") == game_config.PLAYER_STATUS_ALIVE
            role = player_data.get("role", "未知")
            role_icon_html = f'<img src="{get_role_icon(role, is_alive, show_gm_view)}" width="24" height="24" style="vertical-align: middle; margin-right: 5px;">'
            role_text = f"[{role}]" if show_gm_view else ""
            extra_info_text = ""
            if role == "女巫": extra_info_text = f" (解:{'有' if player_data.get(game_config.WITCH_HAS_SAVE_POTION_KEY) else '无'},毒:{'有' if player_data.get(game_config.WITCH_HAS_POISON_POTION_KEY) else '无'})"
            elif role == "猎人": extra_info_text = f" (枪:{'可' if player_data.get(game_config.HUNTER_CAN_SHOOT_KEY) else '否'})"
            html_parts.append(f"""
            <div class="player-item" style="margin: 2px 0; padding: 8px; border-radius: 5px;">
                {role_icon_html}
                <span class="{'player-alive' if is_alive else 'player-dead'}">
                    {get_status_emoji(is_alive)} 玩家{player_data.get("player_number", "?")} ({player_data.get("config_name", "Unknown")}) {role_text}{extra_info_text}
                </span>
            </div>""")
        return "".join(html_parts)
    
    def wait_for_ui_continue(self, prompt: str):
        with self.continue_lock:
            self.is_waiting_for_continue = True
        self.continue_event.wait()
        self.continue_event.clear()
        
    def show_gm_approval(self, player_config_name: str, ai_response: str, 
                        action_type: str, validation_error: Optional[str] = None,
                        parsed_value: Any = None, valid_choices: Optional[List[str]] = None):
        with self.approval_lock:
            self.approval_waiting = True
            self.current_approval_data = {
                "player_config_name": player_config_name, "ai_response": ai_response, 
                "action_type": action_type, "validation_error": validation_error, 
                "parsed_value": parsed_value, "valid_choices": valid_choices
            }
            while not self.approval_result_queue.empty(): self.approval_result_queue.get()
        result = self.approval_result_queue.get()
        with self.approval_lock:
            self.approval_waiting = False
        return result

    def create_interface(self) -> gr.Blocks:
        with gr.Blocks(title="AI狼人杀 - Web版", theme=gr.themes.Soft(), css=self._get_custom_css()) as interface:
            
            dummy_state = gr.State(0) 
            
            gr.HTML(f"""<div style="text-align: center; padding: 20px;"><img src="{get_logo()}" width="60" height="60" style="vertical-align: middle;"><h1 style="display: inline; margin-left: 15px; color: #2E86AB;">🎮 AI狼人杀 - Web版</h1></div>""")
            with gr.Row():
                start_game_btn = gr.Button("🚀 开始游戏", variant="primary", size="lg")
                end_game_btn = gr.Button("⏹️ 强制结束", variant="stop", size="lg", visible=False)
                continue_btn = gr.Button("▶️ 进入下一夜", variant="secondary", size="lg", visible=False)

            game_info_html = gr.HTML(self._format_game_info("游戏准备中", "等待开始", 0, 0))
            
            with gr.Row():
                with gr.Column(scale=1, min_width=300):
                    player_status_html = gr.HTML("<p>等待游戏开始...</p>", elem_id="player-status")
                with gr.Column(scale=2, min_width=600):
                    chat_interface = gr.Chatbot([], label="游戏进程", height=500, elem_id="chat-interface")
                    with gr.Accordion("GM工具", open=False):
                        with gr.Row():
                            gm_status_btn = gr.Button("👥 详细状态")
                            gm_log_btn = gr.Button("📜 游戏日志") 
                        gm_player_input = gr.Textbox(placeholder="输入玩家名查看历史，然后按回车")
                        gm_result_area = gr.HTML("", elem_id="gm-result", visible=False)

                    with gr.Group(visible=False) as gm_approval_area:
                        gm_ai_response_html = gr.HTML()
                        MAX_CHOICE_BUTTONS = 12
                        choice_buttons = []
                        with gr.Row(visible=False) as gm_choice_buttons_row:
                            for i in range(MAX_CHOICE_BUTTONS):
                                choice_buttons.append(gr.Button(visible=False, variant="secondary", size="sm"))
                        with gr.Row():
                            gm_accept_btn = gr.Button("✅ 确认", variant="primary")
                            gm_retry_btn = gr.Button("🔄 重试")
                            gm_skip_btn = gr.Button("⏭️ 跳过")
                            gm_accept_invalid_btn = gr.Button("⚠️ 接受无效响应")
                        with gr.Accordion("手动覆盖", open=False):
                            gm_manual_input = gr.Textbox(lines=2)
                            gm_manual_submit_btn = gr.Button("✏️ 提交手动输入")

            # --- Event Handlers ---
            def start_game_thread():
                threading.Thread(target=self.ui_adapter.start_game_callback, daemon=True).start()
                return gr.update(visible=False), gr.update(visible=True), 0

            def end_game_thread():
                os._exit(0)

            def on_continue_click():
                with self.continue_lock:
                    self.is_waiting_for_continue = False
                self.continue_event.set()
                return gr.update(visible=False)

            def ui_update_loop(dummy_val):
                while True:
                    time.sleep(0.5)
                    chat_history_list = self.ui_adapter.message_history if self.ui_adapter else []
                    status_html_val, info_html_val = "<p>...", self._format_game_info("...", "...", 0, 0)
                    if self.game_state:
                        status_html_val = self._format_player_status(self.game_state.players_data, True)
                        info_html_val = self._format_game_info(self.game_state.current_game_phase, "进行中", self.game_state.game_day, len(self.game_state.get_alive_players()))
                    
                    show_approval, approval_html, show_choice_row = False, "", False
                    button_updates = [gr.update(visible=False) for _ in range(MAX_CHOICE_BUTTONS)]
                    show_continue_button = False
                    with self.continue_lock:
                        if self.is_waiting_for_continue:
                            show_continue_button = True
                    
                    with self.approval_lock:
                        if self.approval_waiting:
                            show_approval = True
                            data = self.current_approval_data
                            player_display = self.game_state.get_player_display_name(data['player_config_name']) if self.game_state else data['player_config_name']
                            title_color = "#721c24" if data['validation_error'] else "#155724"
                            title_icon = "❌" if data['validation_error'] else "✅"
                            error_info_msg = ('验证失败: ' + str(data.get('validation_error',''))) if data['validation_error'] else ('验证通过: ' + str(data.get('parsed_value','')))
                            error_info = f"<p style='color:{title_color};'><b>{title_icon} {error_info_msg}</b></p>"
                            approval_html = f"<div style='border: 2px solid {title_color}; padding: 10px; border-radius: 8px; background: {'#f8d7da' if data['validation_error'] else '#d4edda'};'><h4 style='color: {title_color}; margin-top:0;'>审核 {player_display} 的 {data['action_type']}</h4><p><b>AI响应:</b> <code>{data['ai_response']}</code></p>{error_info}</div>"
                            
                            if data.get("valid_choices"):
                                show_choice_row = True
                                choices = data["valid_choices"]
                                for i in range(len(choices)):
                                    if i < MAX_CHOICE_BUTTONS:
                                        button_updates[i] = gr.update(value=choices[i], visible=True)
                    
                    yield_tuple = (
                        chat_history_list, status_html_val, info_html_val, 
                        gr.update(visible=show_approval), approval_html, 
                        gr.update(visible=show_choice_row),
                        gr.update(visible=show_continue_button)
                    ) + tuple(button_updates)
                    yield yield_tuple
            
            all_outputs = [
                chat_interface, player_status_html, game_info_html, 
                gm_approval_area, gm_ai_response_html, gm_choice_buttons_row,
                continue_btn
            ] + choice_buttons

            start_game_btn.click(start_game_thread, outputs=[start_game_btn, end_game_btn, dummy_state]).then(
                ui_update_loop, inputs=[dummy_state], outputs=all_outputs
            )

            end_game_btn.click(end_game_thread)
            continue_btn.click(on_continue_click, outputs=[continue_btn])

            def log_and_queue(action: str, content: Optional[str] = None):
                print("\n" + "="*20 + " UI Event Log " + "="*20)
                print(f"Time: {time.strftime('%H:%M:%S')}")
                print(f"GM Action Triggered: '{action}'")
                if content is not None:
                    print(f"Associated Content: '{content}' (Type: {type(content)})")
                else:
                    print("Associated Content: None")
                if self.approval_waiting:
                    self.approval_result_queue.put(GMApprovalResult(action, content))
                    print("Result placed in queue for a waiting game thread.")
                else:
                    print("Warning: Action triggered but no game thread is waiting for approval.")
                print("="*56 + "\n")
            
            # --- 最终修复：为动态按钮绑定事件的正确方式 ---
            def create_click_handler(choice_value):
                # 这个内部函数捕获了正确的 choice_value
                def handler():
                    log_and_queue("manual", choice_value)
                return handler

            for i, btn in enumerate(choice_buttons):
                # 每次循环都创建一个新的 handler 函数，它知道自己的值
                # 我们不能在这里直接绑定，因为我们不知道按钮的值是什么。
                # 绑定必须在知道值之后进行。
                # 最好的方法是，当ui_update_loop更新按钮时，我们不光更新值，也更新它的交互性
                # 但这在gradio 4.x中很困难。
                # 所以我们采用一种技巧：按钮的值就是它自己，我们通过inputs获取
                btn.click(
                    lambda value: log_and_queue("manual", value), # lambda接收按钮的值
                    inputs=[btn], # 将按钮本身作为输入
                    outputs=None
                )
            
            gm_accept_btn.click(lambda: log_and_queue("accept"))
            gm_retry_btn.click(lambda: log_and_queue("retry"))
            gm_skip_btn.click(lambda: log_and_queue("skip"))
            gm_accept_invalid_btn.click(lambda: log_and_queue("accept_invalid"))
            gm_manual_submit_btn.click(lambda content: log_and_queue("manual", content), inputs=[gm_manual_input], outputs=[gm_manual_input])
            
            def handle_gm_tool(tool_name, player_name=None):
                if not self.game_state: return gr.update(value="游戏未开始", visible=True)
                if tool_name == "status": return gr.update(value=self._format_player_status(self.game_state.players_data, True), visible=True)
                if tool_name == "log":
                    logs = self.game_state.game_log[-20:]
                    return gr.update(value="<br>".join([f"<small>{l['timestamp']}</small> <strong>[{l['event_type']}]</strong> {l['message']}" for l in logs]), visible=True)
                if tool_name == "history":
                    if not player_name: return gr.update(value="请输入玩家名", visible=True)
                    info = self.game_state.get_player_info(player_name)
                    if info and 'history' in info:
                        return gr.update(value="<br>".join([f"<strong>{h['role']}:</strong> {h['content'][:100]}..." for h in info['history']]), visible=True)
                    return gr.update(value=f"找不到玩家 {player_name}", visible=True)
                return gr.update(visible=False)
                
            gm_status_btn.click(lambda: handle_gm_tool("status"), outputs=[gm_result_area]).then(lambda: gr.update(visible=True), outputs=[gm_result_area])
            gm_log_btn.click(lambda: handle_gm_tool("log"), outputs=[gm_result_area]).then(lambda: gr.update(visible=True), outputs=[gm_result_area])
            gm_player_input.submit(lambda p: handle_gm_tool("history", p), inputs=[gm_player_input], outputs=[gm_result_area]).then(lambda: gr.update(visible=True), outputs=[gm_result_area])
            
        return interface