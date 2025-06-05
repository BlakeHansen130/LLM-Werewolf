# response_parser.py (优化版 - 根据明确的规则调整 + 颜色日志)
import re
import json # 主要用于调试时打印复杂的JSON对象

# 假设 terminal_colors.py 在项目根目录或者Python可以找到的路径下
try:
    from terminal_colors import colorize, log_level_color, Colors, red, yellow, blue, magenta, cyan, grey, bold
except ImportError:
    # Fallback if terminal_colors is not found
    def colorize(text: str, _color_code: str) -> str: return text
    def log_level_color(_level: str) -> str: return ""
    class Colors: RESET = ""; BOLD = ""; RED = ""; GREEN = ""; YELLOW = ""; BLUE = ""; MAGENTA = ""; CYAN = ""; BRIGHT_BLACK = ""; BRIGHT_MAGENTA = ""
    def red(text: str) -> str: return text
    def yellow(text: str) -> str: return text
    def blue(text: str) -> str: return text
    # (add other colors if needed by this file)

MODULE_COLOR = Colors.MAGENTA # ResponseParser 用品红色

def _remove_think_tags(text_content):
    """辅助函数：移除文本中的 <think>...</think> 标签块。"""
    if isinstance(text_content, str):
        return re.sub(r"<think.*?>.*?</think>\s*", "", text_content, flags=re.DOTALL | re.IGNORECASE).strip()
    return text_content

# 将 _log_parser_event 移到 parse_ai_response 前面，因为它被后者调用
def _log_parser_event(message: str, level: str = "INFO", model_name_for_logging="未知模型", player_display_name_for_log="AI玩家"):
    """解析器模块的日志记录器。"""
    level_colored = colorize(level, log_level_color(level))
    prefix_module = colorize("[ResponseParser:", MODULE_COLOR)
    model_colored = colorize(model_name_for_logging, Colors.CYAN)
    player_colored = colorize(player_display_name_for_log, Colors.BRIGHT_MAGENTA)

    # 将 player_display_name 和 model_name_for_logging 从 message 中移除，因为它们现在是日志前缀的一部分
    # 这是一个简化的替换，假设它们总是在消息的特定位置
    # 更稳健的做法是修改调用 _log_parser_event 的地方，不传入这些信息到 message 字符串中
    message_cleaned = message.replace(f"[{player_display_name_for_log}]", "").replace(f"使用 {model_name_for_logging}", "").strip()
    
    print(f"{prefix_module}{level_colored}:{model_colored}] ({player_colored}) {message_cleaned}")


def parse_ai_response(response_data, handler_type, model_name_for_logging="未知模型", player_display_name="AI玩家"):
    """
    根据处理器类型解析来自AI模型的原始JSON响应。
    """
    content_raw = None
    final_content = colorize("（AI未能按预期格式回应）", Colors.RED) # 默认错误消息上色

    player_name_colored = colorize(player_display_name, Colors.BRIGHT_MAGENTA)
    model_name_colored = colorize(model_name_for_logging, Colors.CYAN)
    handler_type_colored = colorize(handler_type, Colors.YELLOW)

    try:
        if handler_type == "qwen_stream_with_thinking":
            content_raw = response_data
            if not isinstance(content_raw, str):
                # 直接使用 print 而不是 _log_parser_event，因为这个日志格式更特定
                print(colorize(f"!! [{player_name_colored} 使用 {model_name_colored}] {handler_type_colored} 类型期望得到字符串，实际为 {colorize(str(type(content_raw)), Colors.RED)}", Colors.RED))
                return final_content
        elif isinstance(response_data, dict):
            if "choices" in response_data and response_data["choices"]:
                choice = response_data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content_raw = choice["message"]["content"]
                else:
                    print(colorize(f"!! [{player_name_colored} 使用 {model_name_colored}] 在 'choices[0]' 中未找到 'message.content'。响应: {grey(str(choice)[:200])}", Colors.RED))
            else:
                print(colorize(f"!! [{player_name_colored} 使用 {model_name_colored}] 响应数据 'choices' 缺失/为空。响应: {grey(str(response_data)[:200])}", Colors.RED))
        else:
            print(colorize(f"!! [{player_name_colored} 使用 {model_name_colored}] 未知响应数据格式。类型: {colorize(str(type(response_data)), Colors.RED)}, 数据(部分): {grey(str(response_data)[:200])}", Colors.RED))
            return final_content
        
        if content_raw is None and handler_type != "qwen_stream_with_thinking":
             print(colorize(f"!! [{player_name_colored} 使用 {model_name_colored}] 未能从响应中提取到核心内容字符串。", Colors.RED))
             return final_content

    except Exception as e:
        print(colorize(f"!! [{player_name_colored} 使用 {model_name_colored}] 初始内容提取阶段出错: {red(str(e))}", Colors.RED))
        return final_content

    if handler_type == "think_tags_in_content":
        cleaned_content = _remove_think_tags(content_raw)
    else:
        if isinstance(content_raw, str):
            cleaned_content = content_raw.strip()
        else:
            cleaned_content = content_raw

    if isinstance(cleaned_content, str):
        final_content = cleaned_content.strip()
        if not final_content and isinstance(content_raw, str) and content_raw.strip():
            if handler_type == "think_tags_in_content":
                 _log_parser_event(f"{handler_type_colored} 类型在移除<think>标签后内容为空，原始提取内容非空。", "DEBUG", model_name_for_logging, player_display_name_for_log=player_display_name)
    elif cleaned_content is None:
        _log_parser_event("清理后的内容为None (可能提取失败)。", "WARN", model_name_for_logging, player_display_name_for_log=player_display_name)
        # final_content 保持为默认的错误消息 "（AI未能按预期格式回应）"
    else:
        _log_parser_event(f"清理后的内容不是字符串: {colorize(str(type(cleaned_content)), Colors.RED)}。原始提取: {grey(str(content_raw)[:100])}", "ERROR", model_name_for_logging, player_display_name_for_log=player_display_name)
        final_content = colorize("（AI内容解析后非文本或意外类型）", Colors.RED)

    return final_content