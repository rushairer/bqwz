import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="macOS 屏幕自动点击工具")
    parser.add_argument("--cli", action="store_true", help="使用命令行终端交互模式，不启动 GUI 窗口")
    args = parser.parse_args()

    if args.cli:
        from cli import run_cli
        run_cli()
    else:
        from gui import run_gui
        run_gui()


if __name__ == "__main__":
    main()
