# assets_base64.py - 图片资源管理（动态加载避免代码文件过大）
import base64
import os
import json
from typing import Optional, Dict

# 图片文件路径映射
IMAGE_PATHS = {
    "logo": "assets/small_logo.png",
    "预言家": "assets/roles/small_prophet.png",
    "女巫": "assets/roles/small_witch.png", 
    "猎人": "assets/roles/small_hunter.png",
    "狼人": "assets/roles/small_wolf.png",
    "平民": "assets/roles/small_villager.png",
    "unknown": "assets/roles/small_unknown.png"
}

# 缓存的base64数据
_cached_base64: Dict[str, str] = {}
_cache_file = "assets_cache.json"

def _load_image_as_base64(image_path: str) -> Optional[str]:
    """将图片文件转换为base64数据URL"""
    try:
        if os.path.exists(image_path):
            with open(image_path, 'rb') as img_file:
                img_data = base64.b64encode(img_file.read()).decode()
                return f"data:image/png;base64,{img_data}"
        else:
            print(f"警告: 图片文件不存在: {image_path}")
            return None
    except Exception as e:
        print(f"错误: 加载图片失败 {image_path}: {e}")
        return None

def _load_cache() -> Dict[str, str]:
    """从缓存文件加载base64数据"""
    if os.path.exists(_cache_file):
        try:
            with open(_cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告: 加载缓存文件失败: {e}")
    return {}

def _save_cache(cache_data: Dict[str, str]) -> None:
    """保存base64数据到缓存文件"""
    try:
        with open(_cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        print(f"警告: 保存缓存文件失败: {e}")

def _get_image_base64(key: str) -> str:
    """获取图片的base64编码，使用缓存机制"""
    # 先检查内存缓存
    if key in _cached_base64:
        return _cached_base64[key]
    
    # 检查文件缓存
    if not _cached_base64:  # 第一次加载
        _cached_base64.update(_load_cache())
        if key in _cached_base64:
            return _cached_base64[key]
    
    # 如果缓存中没有，则从文件加载
    if key in IMAGE_PATHS:
        base64_data = _load_image_as_base64(IMAGE_PATHS[key])
        if base64_data:
            _cached_base64[key] = base64_data
            # 更新文件缓存
            _save_cache(_cached_base64)
            return base64_data
    
    # 如果都失败了，返回默认图标（emoji）
    return _get_fallback_icon(key)

def _get_fallback_icon(key: str) -> str:
    """当图片加载失败时的fallback图标"""
    fallback_icons = {
        "logo": "🎮",
        "预言家": "🔮",
        "女巫": "🧙‍♀️",
        "猎人": "🏹", 
        "狼人": "🐺",
        "平民": "👤",
        "unknown": "❓"
    }
    return fallback_icons.get(key, "❓")

# 动态生成的ROLE_ICONS字典
class _RoleIcons:
    """延迟加载的角色图标字典"""
    def __getitem__(self, key: str) -> str:
        return _get_image_base64(key)
    
    def get(self, key: str, default: str = None) -> str:
        try:
            return self[key]
        except:
            return default or _get_fallback_icon(key)

ROLE_ICONS = _RoleIcons()

# 状态图标（可选，如果需要更多视觉元素）
STATUS_ICONS = {
    "alive": "🟢",
    "dead": "🔴", 
    "unknown": "⚪"
}

# GM操作简化消息图标
GM_ACTION_ICONS = {
    "accept": "✅",
    "retry": "🔄", 
    "manual": "✏️",
    "skip": "⏭️",
    "tool": "🛠️",
    "warning": "⚠️"
}

def get_role_icon(role_name: str, is_alive: bool = True, show_gm_view: bool = False) -> str:
    """
    获取角色图标
    
    Args:
        role_name: 角色名称
        is_alive: 是否存活
        show_gm_view: 是否GM视角（GM视角显示真实角色，玩家视角可能显示unknown）
    
    Returns:
        Base64编码的图片数据URL或emoji fallback
    """
    if not is_alive and not show_gm_view:
        # 非GM视角下，死亡玩家显示unknown图标
        return ROLE_ICONS["unknown"]
    
    return ROLE_ICONS.get(role_name, ROLE_ICONS["unknown"])

def get_status_emoji(is_alive: bool) -> str:
    """获取状态emoji"""
    return STATUS_ICONS["alive"] if is_alive else STATUS_ICONS["dead"]

def get_gm_action_icon(action_type: str) -> str:
    """获取GM操作图标"""
    return GM_ACTION_ICONS.get(action_type, "🎮")

def get_logo() -> str:
    """获取游戏Logo"""
    return _get_image_base64("logo")

# 用于生成简化聊天消息的函数
def format_gm_action_message(action_type: str, player_name: Optional[str] = None) -> str:
    """
    格式化GM操作的简化消息
    
    Args:
        action_type: 操作类型 (accept, retry, manual, skip, tool)
        player_name: 玩家名称（可选）
    
    Returns:
        格式化后的简化消息
    """
    icon = get_gm_action_icon(action_type)
    
    message_templates = {
        "accept": f"{icon} GM确认了AI决策",
        "retry": f"{icon} GM要求AI重试",
        "manual": f"{icon} GM手动输入了决策", 
        "skip": f"{icon} GM跳过了此行动",
        "tool": f"{icon} GM查看了游戏信息",
        "warning": f"{icon} 系统提醒"
    }
    
    base_message = message_templates.get(action_type, f"{icon} GM操作")
    
    if player_name:
        base_message += f" ({player_name})"
    
    return base_message

# 用于在gradio中显示带图标的玩家信息
def format_player_display(player_number: int, player_name: str, role: str, 
                         is_alive: bool, show_role: bool = False) -> str:
    """
    格式化玩家显示信息
    
    Args:
        player_number: 玩家编号
        player_name: 玩家配置名
        role: 角色名称
        is_alive: 是否存活
        show_role: 是否显示角色（GM视角）
    
    Returns:
        格式化后的显示文本
    """
    status_emoji = get_status_emoji(is_alive)
    
    if show_role:
        return f"{status_emoji} 玩家{player_number} ({player_name}) [{role}]"
    else:
        return f"{status_emoji} 玩家{player_number} ({player_name})"

# 用于在聊天区域显示消息
def format_chat_message(sender_type: str, sender_name: str, message: str, 
                       role: Optional[str] = None, is_alive: bool = True) -> tuple:
    """
    格式化聊天消息
    
    Args:
        sender_type: 发送者类型 ('ai', 'gm', 'system')
        sender_name: 发送者名称
        message: 消息内容
        role: 角色名称（如果是AI玩家）
        is_alive: 是否存活
    
    Returns:
        (头像/图标, 格式化的消息文本)
    """
    if sender_type == "ai" and role:
        icon = get_role_icon(role, is_alive, show_gm_view=False)
        formatted_message = f"**{sender_name}**: {message}"
        return icon, formatted_message
    elif sender_type == "gm":
        # GM消息使用特殊标识
        return "👑", f"**GM**: {message}"
    elif sender_type == "system":
        # 系统消息
        return "🎮", f"*{message}*"
    else:
        # 默认情况
        return "❓", f"**{sender_name}**: {message}"

# 开发辅助函数
def preload_all_images() -> bool:
    """
    预加载所有图片到缓存
    
    Returns:
        是否成功加载所有图片
    """
    success = True
    print("=== 预加载所有游戏图片 ===")
    
    for key, path in IMAGE_PATHS.items():
        print(f"加载 {key}: {path}")
        result = _get_image_base64(key)
        if result.startswith("data:image"):
            print(f"  ✅ 成功")
        else:
            print(f"  ❌ 失败，使用fallback: {result}")
            success = False
    
    print(f"\n预加载完成，缓存已保存到 {_cache_file}")
    return success

def clear_cache() -> None:
    """清除图片缓存"""
    global _cached_base64
    _cached_base64.clear()
    if os.path.exists(_cache_file):
        os.remove(_cache_file)
        print("图片缓存已清除")

def get_cache_info() -> Dict[str, any]:
    """获取缓存信息"""
    cache_size = len(_cached_base64)
    file_exists = os.path.exists(_cache_file)
    file_size = os.path.getsize(_cache_file) if file_exists else 0
    
    return {
        "memory_cache_count": cache_size,
        "cache_file_exists": file_exists,
        "cache_file_size_kb": round(file_size / 1024, 2) if file_exists else 0,
        "available_images": list(IMAGE_PATHS.keys())
    }

if __name__ == "__main__":
    print("=== 图片资源管理工具 ===")
    print("1. 预加载所有图片")
    print("2. 清除缓存") 
    print("3. 查看缓存信息")
    print("4. 测试单个图片")
    
    choice = input("请选择操作 (1-4): ").strip()
    
    if choice == "1":
        preload_all_images()
    elif choice == "2":
        clear_cache()
    elif choice == "3":
        info = get_cache_info()
        print("\n=== 缓存信息 ===")
        for key, value in info.items():
            print(f"{key}: {value}")
    elif choice == "4":
        print("可用图片:", list(IMAGE_PATHS.keys()))
        img_key = input("请输入图片key: ").strip()
        result = _get_image_base64(img_key)
        if result.startswith("data:image"):
            print(f"✅ 成功加载，数据长度: {len(result)} 字符")
        else:
            print(f"❌ 加载失败，使用fallback: {result}")
    else:
        print("无效选择")
