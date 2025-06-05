# ai_interface.py (最终版 - 完全不打印Qwen思考过程 + 颜色日志)
import requests
import json
import time
from typing import List, Dict, Any, Optional, Tuple
import traceback # 移到顶部

# 假设 terminal_colors.py 在项目根目录或者Python可以找到的路径下
try:
    from terminal_colors import (
        colorize, log_level_color, Colors,
        red, green, yellow, blue, magenta, cyan, grey, bold
    )
except ImportError:
    # Fallback if terminal_colors is not found
    def colorize(text: str, _color_code: str) -> str: return text
    def log_level_color(_level: str) -> str: return ""
    class Colors: RESET = ""; BOLD = ""; RED = ""; GREEN = ""; YELLOW = ""; BLUE = ""; MAGENTA = ""; CYAN = ""; BRIGHT_BLACK = ""; BRIGHT_MAGENTA = ""; BRIGHT_YELLOW = ""; BRIGHT_RED = ""
    def red(text: str) -> str: return text
    def green(text: str) -> str: return text
    def yellow(text: str) -> str: return text
    def blue(text: str) -> str: return text
    def magenta(text: str) -> str: return text
    def cyan(text: str) -> str: return text
    def grey(text: str) -> str: return text
    def bold(text: str) -> str: return text

from game_config import DEFAULT_API_ENDPOINT, DEFAULT_API_KEY, DEFAULT_MODEL_NAME
from response_parser import parse_ai_response # 仍然需要它来处理其他模型的<think>标签或做通用清理

MODULE_COLOR = Colors.BLUE # AIComms 用蓝色

def _log_ai_comms(message: str, level: str = "INFO", player_config_name: Optional[str] = None):
    """AI通信模块的日志记录器。"""
    level_colored = colorize(level, log_level_color(level))
    prefix_module = colorize("[AIComms:", MODULE_COLOR)

    prefix = f"{prefix_module}{level_colored}]"
    if player_config_name:
        p_name_colored = colorize(player_config_name, Colors.BRIGHT_MAGENTA) # AI玩家名用亮品红
        prefix += f" ({p_name_colored})"
    
    print(f"{prefix} {message}")

def make_api_call_to_ai(
    player_config_name: str,
    messages: List[Dict[str, str]],
    api_endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    response_handler_type: str = "standard",
    player_display_name_for_parser: str = "AI玩家",
    timeout_seconds: int = 180
) -> Tuple[Optional[str], Optional[str]]:
    """
    向指定的AI API发送请求，并根据handler_type处理响应。
    对于 "qwen_stream_with_thinking"，会直接解析SSE并分离思考与回答，不打印思考过程。
    对于其他类型，会依赖 parse_ai_response进行处理。
    """
    endpoint_to_use = api_endpoint or DEFAULT_API_ENDPOINT
    key_to_use = api_key if api_key is not None else DEFAULT_API_KEY
    model_to_use = model_name or DEFAULT_MODEL_NAME

    headers = {
        "Content-Type": "application/json",
    }
    if key_to_use and key_to_use.strip().upper() != "EMPTY":
        headers["Authorization"] = f"Bearer {key_to_use}"

    payload: Dict[str, Any] = {
        "model": model_to_use,
        "messages": messages,
    }

    is_qwen_deep_think_stream = response_handler_type == "qwen_stream_with_thinking"
    
    if is_qwen_deep_think_stream:
        payload["stream"] = True
        payload["enable_thinking"] = True
        _log_ai_comms(f"为Qwen深度思考流启用了 '{green('enable_thinking: True')}' (顶层参数)。", "DEBUG", player_config_name)
    
    _log_ai_comms(
        f"向模型 '{colorize(model_to_use, Colors.CYAN)}' @ '{colorize(endpoint_to_use, Colors.BLUE)}' 发送请求. "
        f"Handler: '{colorize(response_handler_type, Colors.YELLOW)}'. Streaming: {colorize(str(payload.get('stream', False)), Colors.BOLD)}",
        "DEBUG", player_config_name
    )
    if messages:
        _log_ai_comms(f"最后消息预览 (user prompt): {grey(messages[-1]['content'][:150])}{grey('...') if len(messages[-1]['content']) > 150 else ''}", "TRACE", player_config_name)

    try:
        response_obj = requests.post( # Renamed to response_obj to avoid conflict with 'response' in except block
            endpoint_to_use,
            headers=headers,
            json=payload,
            timeout=timeout_seconds,
            stream=payload.get('stream', False)
        )
        response_obj.raise_for_status()

        final_ai_output_text: Optional[str] = None
        api_call_error_message: Optional[str] = None

        if is_qwen_deep_think_stream:
            qwen_reasoning_content_parts = []
            qwen_answer_content_parts = []
            is_qwen_answering_started = False

            _log_ai_comms(colorize("开始接收Qwen SSE深度思考流...", Colors.GREEN), "DEBUG", player_config_name)
            
            for line_bytes in response_obj.iter_lines():
                if line_bytes:
                    decoded_line = line_bytes.decode('utf-8', errors='replace').strip()
                    if decoded_line.startswith("data:"):
                        json_data_string = decoded_line[len("data:"):].strip()
                        if json_data_string == "[DONE]":
                            _log_ai_comms(colorize("Qwen SSE流结束标记 [DONE] 收到。", Colors.GREEN), "DEBUG", player_config_name)
                            break
                        if not json_data_string: continue
                        try:
                            chunk = json.loads(json_data_string)
                            if not chunk.get("choices"):
                                if chunk.get("usage"):
                                    _log_ai_comms(f"Qwen Usage data received: {colorize(str(chunk['usage']), Colors.BRIGHT_BLACK)}", "DEBUG", player_config_name)
                                continue
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            current_reasoning_chunk = delta.get("reasoning_content")
                            if current_reasoning_chunk is not None:
                                qwen_reasoning_content_parts.append(str(current_reasoning_chunk))
                            current_answer_chunk = delta.get("content")
                            if current_answer_chunk is not None:
                                if not is_qwen_answering_started and str(current_answer_chunk).strip():
                                    _log_ai_comms(colorize("Qwen开始正式回复...", Colors.CYAN), "DEBUG", player_config_name)
                                    is_qwen_answering_started = True
                                qwen_answer_content_parts.append(str(current_answer_chunk))
                        except json.JSONDecodeError:
                            _log_ai_comms(colorize(f"无法解析Qwen SSE流中的JSON块: {json_data_string}", Colors.YELLOW), "WARN", player_config_name)
                            continue
            
            final_reasoning_text = "".join(qwen_reasoning_content_parts)
            final_answer_text = "".join(qwen_answer_content_parts)
            _log_ai_comms(
                f"Qwen SSE流解析完毕. 思考内容长度: {bold(str(len(final_reasoning_text)))}. 回复内容长度: {bold(str(len(final_answer_text)))}",
                "DEBUG", player_config_name
            )

            if not final_answer_text.strip():
                api_call_error_message = "Qwen AI流式回复内容为空"
                if final_reasoning_text.strip():
                     api_call_error_message += colorize(" (但记录到有思考过程)", Colors.BRIGHT_BLACK)
            else:
                final_ai_output_text = final_answer_text.strip()
        
        else: # Not Qwen Deep Think Stream
            try:
                if payload.get('stream', False):
                     raw_response_data_for_parser = response_obj.text # For general streaming (non-Qwen specific)
                else:
                    raw_response_data_for_parser = response_obj.json()

                final_ai_output_text = parse_ai_response(
                    response_data=raw_response_data_for_parser,
                    handler_type=response_handler_type,
                    model_name_for_logging=model_to_use,
                    player_display_name=player_display_name_for_parser
                )
            except json.JSONDecodeError as e_json_dec:
                _log_ai_comms(colorize(f"API响应非JSON (用于非Qwen深度流场景): {response_obj.text[:250]}... Error: {e_json_dec}", Colors.RED), "ERROR", player_config_name)
                api_call_error_message = "API响应JSON解析错误（非Qwen深度流）"
            except Exception as e_parse:
                _log_ai_comms(colorize(f"调用 parse_ai_response 时出错: {e_parse}", Colors.RED), "ERROR", player_config_name)
                api_call_error_message = f"响应解析器错误: {e_parse}"

        if api_call_error_message:
            return None, api_call_error_message
        
        if not final_ai_output_text or \
           (isinstance(final_ai_output_text, str) and (
               final_ai_output_text.strip().startswith("（AI未能按预期格式回应）") or
               final_ai_output_text.strip().startswith("（AI内容解析后非文本）")
           )):
            error_detail = f"最终AI输出内容为空或为解析器错误提示: '{colorize(final_ai_output_text if final_ai_output_text else '空响应', Colors.YELLOW)}'"
            _log_ai_comms(error_detail, "WARN", player_config_name)
            return None, f"AI响应处理失败: {final_ai_output_text if final_ai_output_text else '空响应'}"
        
        return str(final_ai_output_text).strip(), None

    except requests.exceptions.Timeout:
        _log_ai_comms(colorize(f"API调用超时 ({timeout_seconds}s)。", Colors.RED), "ERROR", player_config_name)
        return None, f"API调用超时({timeout_seconds}s)"
    except requests.exceptions.RequestException as e_req:
        error_msg = colorize(f"API调用时发生网络或请求错误: {e_req}", Colors.RED)
        _log_ai_comms(error_msg, "ERROR", player_config_name)
        error_response_text = ""
        # Check if e_req.response exists (it's an optional attribute)
        if hasattr(e_req, 'response') and e_req.response is not None:
            try:
                server_error_detail = e_req.response.json() if e_req.response.headers.get('Content-Type') == 'application/json' else e_req.response.text
                error_response_text = colorize(f" (服务器响应: {e_req.response.status_code} {str(server_error_detail)[:150]}...)", Colors.BRIGHT_RED)
            except json.JSONDecodeError:
                 error_response_text = colorize(f" (服务器响应: {e_req.response.status_code} {e_req.response.text[:150]}...)", Colors.BRIGHT_RED)
        return None, f"API网络/请求错误: {str(e_req)}{error_response_text}"
    except Exception as e_unknown:
        _log_ai_comms(colorize(f"API调用或响应处理时发生未知严重错误: {e_unknown}", Colors.BOLD + Colors.RED), "CRITICAL", player_config_name)
        tb_str = traceback.format_exc()
        _log_ai_comms(colorize(tb_str, Colors.BRIGHT_RED), "CRITICAL", player_config_name) # Colorize traceback too
        return None, f"API未知严重错误: {str(e_unknown)}"