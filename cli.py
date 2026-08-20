import sys
import threading
from clicker_core import AutoClicker


def run_cli():
    print("=" * 50)
    print("       屏幕自动点击工具 (CLI 终端模式)")
    print("=" * 50)
    
    clicker = AutoClicker(log_callback=print)
    
    # 步骤 1: 取点
    print("\n[步骤 1: 屏幕取点]")
    input("👉 按 [Enter 回车键] 开始在屏幕上取点...")
    
    capture_event = threading.Event()
    def on_finish(pt_a, pt_b):
        capture_event.set()
        
    clicker.start_capture(on_finish=on_finish)
    capture_event.wait()
    
    print(f"\n📍 当前已设置坐标:")
    print(f"   A 点 (点击 1 次): {clicker.point_a}")
    print(f"   B 点 (点击 2 次): {clicker.point_b}")
    print(f"   随机半径: {clicker.radius} px")
    print(f"   间隔时间: {clicker.interval_ms} ms")
    
    # 步骤 2: 确认执行
    while True:
        choice = input("\n👉 请输入指令: [Enter]立即执行一次 | [数字]循环指定次数 | [q]退出: ").strip()
        if choice.lower() == 'q':
            print("👋 已退出。")
            break
            
        loop_count = 1
        if choice.isdigit() and int(choice) > 0:
            loop_count = int(choice)
            
        exec_event = threading.Event()
        clicker.start_execution(loop_count=loop_count, on_complete=lambda: exec_event.set())
        exec_event.wait()


if __name__ == "__main__":
    run_cli()
