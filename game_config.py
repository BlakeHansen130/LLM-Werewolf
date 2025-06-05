# game_config.py

# --- Game Rules & Setup ---
MIN_PLAYERS = 6 # 游戏支持的最小玩家数
MAX_PLAYERS = 11 # 游戏支持的最大玩家数 (根据你的要求到11人)

# 角色分配: 只包含 预言家(P), 女巫(W), 猎人(H), 狼人(Wolf), 平民(Villager)
# P: 预言家, W: 女巫, H: 猎人
# 配置思路：
# - 神民固定为 预言家、女巫、猎人 (共3神)
# - 狼人数量随总人数增加而适当增加
# - 其余为平民
ROLE_DISTRIBUTIONS = {
    6: ["预言家", "女巫", "猎人", "狼人", "平民", "平民"],
    # 3神, 1狼, 2民 (好人阵营: 4, 狼人阵营: 1)

    7: ["预言家", "女巫", "猎人", "狼人", "狼人", "平民", "平民"],
    # 3神, 2狼, 2民 (好人阵营: 5, 狼人阵营: 2)

    8: ["预言家", "女巫", "猎人", "狼人", "狼人", "平民", "平民", "平民"],
    # 3神, 2狼, 3民 (好人阵营: 6, 狼人阵营: 2) - 这是你之前提到的常见8人配置

    9: ["预言家", "女巫", "猎人", "狼人", "狼人", "狼人", "平民", "平民", "平民"],
    # 3神, 3狼, 3民 (好人阵营: 6, 狼人阵营: 3)

    10: ["预言家", "女巫", "猎人", "狼人", "狼人", "狼人", "平民", "平民", "平民", "平民"],
    # 3神, 3狼, 4民 (好人阵营: 7, 狼人阵营: 3)
    # 或者对于10人也可以考虑4狼：["预言家", "女巫", "猎人", "狼人", "狼人", "狼人", "狼人", "平民", "平民", "平民"] (3神, 4狼, 3民. 好人:6, 狼人:4)
    # 我们先用3狼配置，如果觉得狼弱可以调整为4狼。

    11: ["预言家", "女巫", "猎人", "狼人", "狼人", "狼人", "狼人", "平民", "平民", "平民", "平民"]
    # 3神, 4狼, 4民 (好人阵营: 7, 狼人阵营: 4)
}

# 定义所有游戏内实际使用的角色名 (必须与 ROLE_DISTRIBUTIONS 中的名称一致)
ALL_POSSIBLE_ROLES = ["平民", "狼人", "预言家", "女巫", "猎人"]

# --- AI & API Configuration ---
DEFAULT_API_ENDPOINT = "http://localhost:1234/v1/chat/completions" # 示例 OpenAI 兼容的 API 端点
DEFAULT_API_KEY = "EMPTY" # 如果 API 不需要 key，或 key 在其他地方（如环境变量）处理
DEFAULT_MODEL_NAME = "gpt-3.5-turbo" # 默认使用的模型名称
CONFIG_FILENAME = "players_config.json" # AI 玩家配置文件的名称

# --- Game Phase Constants ---
PHASE_GAME_SETUP = "GAME_SETUP"
PHASE_START_GAME = "START_GAME" # 游戏正式开始的标志，在setup之后
PHASE_NIGHT_START = "NIGHT_START"
PHASE_DAY_START = "DAY_START"
PHASE_PROCESS_DEATH_EFFECTS = "PROCESS_DEATH_EFFECTS" # 例如猎人开枪
PHASE_LAST_WORDS_SPEECH = "LAST_WORDS_SPEECH" # 遗言阶段
PHASE_SPEECH = "SPEECH" # 白天发言阶段
PHASE_VOTE = "VOTE" # 白天投票阶段
PHASE_GAME_OVER = "GAME_OVER"
# 可以根据需要添加更多细分的阶段，例如 PHASE_WOLF_ACTION, PHASE_PROPHET_ACTION 等，
# 但 current_game_phase 通常用于表示大的游戏环节。

# --- Logging & Display ---
# (如果需要全局的日志格式或级别可以在这里定义，但通常由日志库或主程序控制)

# --- Role-specific constants (用作 player_data 字典中的键名) ---
WITCH_HAS_SAVE_POTION_KEY = "witch_can_use_save_potion" # 女巫是否有解药
WITCH_HAS_POISON_POTION_KEY = "witch_can_use_poison_potion" # 女巫是否有特殊药剂（毒药）
HUNTER_CAN_SHOOT_KEY = "hunter_can_shoot_on_death" # 猎人死亡时是否能开枪
PLAYER_STATUS_ALIVE = "alive" # 玩家存活状态
PLAYER_STATUS_DEAD = "dead"   # 玩家死亡状态
PLAYER_IS_POISONED_KEY = "is_poisoned_this_round" # 标记玩家是否在本轮被女巫的特殊药剂作用

# --- Special Vote Strings ---
VOTE_SKIP = "弃票" # 用于投票时的弃票行为，确保与 werewolf_prompts.py 和 game_rules_engine.py 中的处理一致

# --- Action Types (主要用于 player_interaction.py 和 werewolf_prompts.py 的逻辑分支) ---
# 这些是 player_interaction.py 中 _validate_ai_response 和 werewolf_prompts.py 中
# generate_prompt_for_action 函数会用到的行动类型标识符。
ACTION_SPEECH = "speech"
ACTION_VOTE = "vote"
ACTION_LAST_WORDS = "last_words"
ACTION_WOLF_KILL = "wolf_kill" # 狼人夜晚选择目标使其出局 (最终决策)
ACTION_WOLF_NOMINATE = "wolf_nominate" # 狼人内部提名袭击目标 (新增)
ACTION_PROPHET_CHECK = "prophet_check" # 预言家查验
ACTION_WITCH_SAVE = "witch_save" # 女巫使用解药
ACTION_WITCH_POISON = "witch_poison" # 女巫使用特殊药剂
ACTION_HUNTER_SHOOT = "hunter_shoot" # 猎人开枪
# 如果有其他需要AI决策的行动，例如狼人内部讨论提名，也可以在这里定义常量。
# ACTION_WOLF_NOMINATE = "wolf_nominate" (示例)