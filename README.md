# LLM-Werewolf 🐺🤖

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个基于 Python 和大型语言模型（LLM）的文本狼人杀（又称“杀人游戏”、“Mafia”）模拟器框架。该项目允许你配置不同数量的AI玩家，赋予它们不同的角色（狼人、预言家、女巫、猎人、平民），并通过与LLM API交互来驱动它们的行为和决策，体验一场由AI主导的狼人杀游戏。

## ✨ 项目特点

*   **AI驱动的玩家**: 利用大型语言模型（如Qwen、GPT系列或其他兼容OpenAI API的模型）作为玩家进行游戏。
*   **灵活的角色配置**: 支持6-11名玩家，并根据不同人数自动分配经典角色。
*   **模块化设计**: 代码结构清晰，分为游戏状态管理、流程控制、AI接口、Prompt生成、规则引擎等模块，易于理解和扩展。
*   **GM（游戏主持人）中心化**:
    *   GM可以观察游戏全局信息。
    *   在AI决策不符合预期或API出错时，GM可以介入进行手动修正、重试或跳过。
    *   提供GM工具箱，方便查看玩家状态、历史记录、游戏日志等。
*   **详细的Prompt工程**: 为不同角色和行动精心设计了Prompt，引导AI做出符合角色的行为。
*   **Qwen模型优化**: 对Qwen模型的流式输出和思考过程有特别处理，可选择不打印思考过程。
*   **夜晚狼人讨论机制**: 实现了狼人内部提名袭击目标，再由决策狼人最终决定的流程。
*   **游戏报告生成**: 游戏结束后可选择导详细的游戏日志报告和关键事件摘要报告。
*   **彩色终端输出**: 优化了终端日志和信息的显示，使用不同颜色区分不同类型的消息，提升可读性。

## 目录结构

```
.
├── ai_interface.py             # AI模型API通信接口
├── game_config.py              # 游戏核心规则、角色分配、API默认配置等
├── game_flow_manager.py        # 游戏主要流程控制（夜晚、白天阶段）
├── game_report_generator.py    # 游戏报告生成模块
├── game_rules_engine.py        # 游戏胜负判断、发言顺序、计票等规则
├── game_setup.py               # 游戏初始化、角色分配
├── game_state.py               # 游戏状态类定义与管理
├── gm_tools.py                 # GM工具函数
├── player_interaction.py       # 玩家（AI）与游戏逻辑的交互，GM审批
├── response_parser.py          # AI响应解析
├── terminal_colors.py          # 终端彩色输出辅助模块
├── werewolf_game_main.py       # 游戏主入口
├── werewolf_prompts.py         # AI行动的Prompt生成逻辑
├── players_config.json         # AI玩家配置文件 (需用户自行创建或修改)
└── README.md                   # 本文档
```

## 🛠️ 安装与运行

### 依赖

*   Python 3.8+
*   `requests` (用于API调用)

你可以通过pip安装依赖：
```bash
pip install requests
```

### 配置

1.  **创建 `players_config.json` 文件**:
    在项目根目录下创建一个名为 `players_config.json` 的文件。这个文件用于配置每个AI玩家的API信息。文件内容应该是一个JSON数组，每个元素代表一个玩家的配置。

    **示例 `players_config.json` (至少6名玩家):**
    ```json
    [
      {
        "name": "PlayerAI1",
        "api_endpoint": "http://localhost:11434/v1/chat/completions",
        "api_key": "EMPTY",
        "model": "qwen:7b-chat",
        "response_handler_type": "standard"
      },
      {
        "name": "PlayerAI2",
        "api_endpoint": "YOUR_OPENAI_COMPATIBLE_ENDPOINT",
        "api_key": "YOUR_API_KEY_OR_EMPTY",
        "model": "your_model_name",
        "response_handler_type": "standard"
      },
      // ... 根据实际玩家数量添加更多配置 (至少6个，最多11个)
      {
        "name": "PlayerAI6",
        "api_endpoint": "...",
        "api_key": "...",
        "model": "...",
        "response_handler_type": "standard"
      }
    ]
    ```
    *   `name`: 玩家的唯一标识名。
    *   `api_endpoint`: AI模型的API端点。
    *   `api_key`: 对应的API密钥，如果不需要则设为 "EMPTY"。
    *   `model`: 使用的模型名称。
    *   `response_handler_type`: AI响应处理器类型，可选值：
        *   `"standard"`: 标准OpenAI格式，直接从`choices[0].message.content`获取回复。
        *   `"think_tags_in_content"`: 回复内容中可能包含`<think>...</think>`标签，解析时会移除。
        *   `"qwen_stream_with_thinking"`: 针对Qwen模型开启`enable_thinking`的流式输出，会自动分离思考与回答，不打印思考过程。
        *   `"content_with_separate_reasoning"`: 响应JSON中包含独立的`reasoning_content`字段和`message.content`字段（此模式在当前版本中主要依赖`message.content`）。

2.  **(可选) 修改 `game_config.py`**:
    *   你可以根据需要调整 `DEFAULT_API_ENDPOINT`, `DEFAULT_API_KEY`, `DEFAULT_MODEL_NAME` 等默认值。
    *   调整 `ROLE_DISTRIBUTIONS` 来改变不同人数下的角色配置。

### 运行游戏

在项目根目录下执行：
```bash
python werewolf_game_main.py
```
游戏将会开始，并根据 `players_config.json` 中的配置初始化AI玩家。GM（你）将通过终端与游戏交互。

## 🎮 游戏玩法

游戏将自动进行夜晚和白天阶段的循环。

*   **夜晚**: 狼人行动、女巫用药、预言家查验。
*   **白天**: 宣布死讯、猎人开枪（如果触发）、遗言、玩家发言、投票、宣布投票结果。
*   **GM介入**: 在每个AI行动决策点，GM都有机会审核AI的响应，并可以选择：
    *   **采纳**: 接受AI的决策。
    *   **让AI重试**: 如果对AI的决策不满意或认为其不合理。
    *   **手动输入/覆盖**: GM可以代替AI做出决策。
    *   **跳过**: 跳过当前AI的行动。
*   **GM工具**: 在夜晚和白天阶段之间，或通过特定指令（当前是输入 `gm`），可以进入GM工具箱进行更详细的查看和管理。

## 📄 游戏报告

游戏结束后，程序会询问是否导出游戏报告。如果选择是，将在项目根目录下创建一个 `game_reports` 文件夹（如果尚不存在），并生成两个报告文件：

*   `detailed_werewolf_report_[timestamp].txt`: 包含完整的游戏事件日志和每个玩家的详细消息历史。
*   `summary_werewolf_report_[timestamp].txt`: 包含游戏概览、最终玩家信息和按天组织的关键事件回顾。

## 🤝 贡献

欢迎各种形式的贡献！你可以：

*   报告Bug。
*   提出新功能建议。
*   改进Prompt设计。
*   优化代码或添加更多测试。
*   提交Pull Request。

在提交Pull Request之前，请确保你的代码风格与项目一致，并通过了基本的测试。

## 📜 开源许可

本项目采用 [MIT License](LICENSE) 开源。