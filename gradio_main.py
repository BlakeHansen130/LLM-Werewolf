# gradio_main.py (Final, Simplified Version - Direct Launch)
import os
import sys
import argparse
import traceback

try:
    import gradio as gr
except ImportError:
    print("错误: 未安装gradio库。请在激活conda环境后运行: pip install -r requirements.txt")
    sys.exit(1)

try:
    from gradio_game_controller import create_gradio_controller, GradioGameController
    from assets_base64 import get_cache_info, preload_all_images
    from game_setup import CONFIG_FILENAME
except ImportError as e:
    print(f"错误: 无法导入必要模块: {e}")
    print("请确保所有依赖文件都在正确位置，且conda环境已激活。")
    sys.exit(1)

def check_dependencies():
    """检查依赖文件和配置"""
    print("=" * 40)
    print("🔍 检查系统依赖...")
    
    # 检查配置文件
    if not os.path.exists(CONFIG_FILENAME):
        print(f"❌ 错误: 配置文件 '{CONFIG_FILENAME}' 未找到")
        print("请确保玩家配置文件存在于当前目录")
        return False
    else:
        print(f"✅ 配置文件: {CONFIG_FILENAME}")
    
    # 检查图片资源
    print("🖼️ 检查图片资源...")
    try:
        preload_all_images()
        cache_info = get_cache_info()
        print(f"✅ 图片资源已加载/缓存 ({cache_info['cache_file_size_kb']}KB)")
    except Exception as e:
        print(f"⚠️ 加载图片资源时出现问题: {e}")

    # 检查Gradio版本
    try:
        print(f"✅ Gradio版本: {gr.__version__}")
    except Exception:
        print("⚠️ 无法获取Gradio版本信息")
    
    print("✅ 依赖检查完成")
    print("=" * 40 + "\n")
    return True

def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description="AI狼人杀游戏 - Web界面版")
    parser.add_argument("--port", type=int, default=7860, help="Web服务器端口 (默认: 7860)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Web服务器地址 (0.0.0.0表示可被局域网访问)")
    parser.add_argument("--share", action="store_true", help="创建Gradio的公开分享链接")
    parser.add_argument("--no-browser", action="store_true", help="不自动在浏览器中打开")
    parser.add_argument("--debug", action="store_true", help="启用Gradio的调试模式")
    
    args = parser.parse_args()
    
    print("🎮 AI狼人杀游戏 - Web界面版")
    
    # 1. 检查依赖
    if not check_dependencies():
        print("❌ 依赖检查失败，程序退出。")
        return
    
    try:
        # 2. 创建游戏控制器
        print("🚀 正在启动游戏控制器和界面...")
        controller = create_gradio_controller()
        
        # 3. 创建游戏界面
        app = controller.create_interface()
        print("✅ 游戏界面已准备就绪。")
        
        # 4. 启动Gradio服务器
        print(f"\n🌐 Web服务器配置:")
        print(f"   地址: http://{args.host}:{args.port} (如果host是0.0.0.0, 请用你的实际IP访问)")
        print(f"   分享链接: {'是' if args.share else '否'}")
        
        print("\n🎯 正在启动Web服务器... (按 CTRL+C 停止)")
        
        app.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            inbrowser=not args.no_browser,
            debug=args.debug
        )
        
    except KeyboardInterrupt:
        print("\n👋 用户中断，程序退出。")
    except Exception as e:
        print(f"\n💥 启动失败: {e}")
        print("请检查错误信息。如果问题与依赖库有关，请确保在一个干净的环境中通过 'pip install -r requirements.txt' 安装。")
        if args.debug:
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # 确保在正确的conda环境中
    if "CONDA_PREFIX" not in os.environ:
        print("\n⚠️ 警告: 似乎不在Conda环境中运行。")
        print("如果遇到库版本问题，请务必先激活正确的Conda环境。 (e.g., 'conda activate werewolf_env')\n")
        
    main()