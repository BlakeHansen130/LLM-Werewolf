# LLM-Werewolf 🐺🤖 - 全功能版
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个基于 Python 和大型语言模型（LLM）的文本狼人杀模拟器框架。该项目允许你配置不同数量的AI玩家，赋予它们不同的角色（狼人、预言家、女巫、猎人、平民），并通过与LLM API交互来驱动它们的行为和决策，体验一场由AI主导的狼人杀游戏。

<!-- 新增：项目现在支持两种模式 -->
本项目现在支持 **Web界面模式** 和经典的 **终端模式**，您可以根据喜好选择。

## ✨ 项目特点

*   **双模式运行**:
    *   **Web界面模式 (Gradio)**: 提供现代、直观的图形化界面，包括实时聊天、玩家状态面板、GM工具和动态审核面板。
    *   **终端模式**: 保留了经典的纯命令行交互方式，日志输出带有颜色，提升可读性。
*   **AI驱动的玩家**: 利用大型语言模型（如Qwen、GPT系列或其他兼容OpenAI API的模型）作为玩家进行游戏。
*   **灵活的角色配置**: 支持至少6名玩家，并根据不同人数自动分配经典角色。
*   **GM（游戏主持人）中心化**:
    *   GM可以观察游戏全局信息。
    *   在AI决策不符合预期或API出错时，GM可以介入进行手动修正、重试或跳过。
    *   **Web UI 优化**: 在Web界面上，审核变得更简单，可直接点击动态生成的选项按钮完成修正。
    *   提供GM工具箱，方便查看玩家状态、历史记录、游戏日志等。
*   **Qwen模型优化**: 对Qwen模型的流式输出和思考过程有特别处理，可选择不打印思考过程。
*   **游戏报告生成**: 游戏结束后可选择导详细的游戏日志报告和关键事件摘要报告。

## 目录结构

```
.
├── assets/ # 存放图片等静态资源
│ ├── roles/ # 角色头像文件夹
│ │ ├── small_hunter.png
│ │ ├── small_prophet.png
│ │ ├── small_unknown.png
│ │ ├── small_villager.png
│ │ ├── small_witch.png
│ │ └── small_wolf.png
│ └── small_logo.png
├── gradio_main.py # Web界面主入口
├── gradio_interface.py # Gradio界面定义
├── gradio_game_controller.py # Gradio的控制器和UI适配器
├── werewolf_game_main.py # 终端模式主入口
├── ui_adapter.py # UI抽象层 (连接终端和Web)
├── ai_interface.py # AI模型API通信接口
├── player_interaction.py # AI与游戏逻辑的交互，GM审批
├── game_flow_manager.py # 游戏主要流程控制
├── game_state.py # 游戏状态类定义
├── game_setup.py # 游戏初始化、角色分配
├── game_rules_engine.py # 游戏胜负判断、发言顺序等规则
├── werewolf_prompts.py # AI行动的Prompt生成逻辑
├── gm_tools.py # GM工具函数
├── game_report_generator.py # 游戏报告生成模块
├── response_parser.py # AI响应解析
├── game_config.py # 游戏核心规则、角色分配等
├── terminal_colors.py # 终端彩色输出辅助模块
├── assets_base64.py # 图片资源转Base64模块
├── players_config.json # AI玩家配置文件 (需用户自行创建)
└── requirements.txt # 项目依赖文件
```

<!-- 修改：更新了安装与运行部分 -->
## 🛠️ 安装与运行

### 1. 依赖环境

*   推荐使用Conda来管理Python环境。
*   Python 3.8 ~ 3.10

首先，创建一个新的Conda环境：
```bash
conda create --name werewolf_env python=3.10 -y
conda activate werewolf_env
```

### 2. 安装依赖

项目的所有依赖项都已在 `requirements.txt` 文件中列出。

```bash
pip install -r requirements.txt
```

### 3. 配置

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

### 4. 运行游戏

你有两种模式可以选择：

#### 🚀 Web界面模式 (推荐)

在项目根目录下执行：
```bash
python gradio_main.py
```
程序会自动在浏览器中打开一个网址 (通常是 `http://127.0.0.1:7860`)。

#### 💻 终端模式

如果你更喜欢经典的命令行体验，可以运行：
```bash
python werewolf_game_main.py
```

## 🎮 游戏玩法

游戏将自动进行夜晚和白天阶段的循环。

*   **夜晚**: 狼人行动、女巫用药、预言家查验。
*   **白天**: 宣布死讯、猎人开枪（如果触发）、遗言、玩家发言、投票、宣布投票结果。
*   **GM介入**: 在每个AI行动决策点，GM都有机会审核AI的响应。
    *   **在Web界面中**，会弹出专门的审核面板，GM可以轻松点击按钮完成操作，甚至可以直接点击动态生成的有效选项按钮来快速修正。
    *   **在终端模式中**，GM需要通过输入指令（如Y/M/R/S）来完成审核。
*   **GM工具**:
    *   **在Web界面中**，可以通过右下角可折叠的“GM工具”面板随时查看游戏信息。
    *   **在终端模式中**，可以在夜晚和白天阶段之间，通过提示进入GM工具箱。

## 📄 游戏报告

游戏正常结束后，**启动程序的终端**会询问是否导出游戏报告。如果选择是，将在项目根目录下创建一个 `game_reports` 文件夹，并生成两个报告文件：

*   `detailed_werewolf_report_[timestamp].txt`: 包含完整的游戏事件日志和每个玩家的详细消息历史。
*   `summary_werewolf_report_[timestamp].txt`: 包含游戏概览、最终玩家信息和按天组织的关键事件回顾。

## 🤝 贡献

欢迎各种形式的贡献！你可以：

*   报告Bug或提出界面改进建议。
*   改进Prompt设计。
*   优化代码或添加更多测试。
*   提交Pull Request。

在提交Pull Request之前，请确保你的代码风格与项目一致，并通过了基本的测试。

## 📜 开源许可

本项目采用 [MIT License](LICENSE) 开源。