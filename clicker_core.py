import math
import random
import time
import threading
import subprocess
import os
from typing import Optional, Tuple, Callable, Dict, Any

from config_manager import load_config, save_config

try:
    import Quartz
    import ApplicationServices
    import AppKit
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False


def check_accessibility_permission(prompt: bool = False) -> bool:
    """检查当前进程是否有 macOS 辅助功能 (Accessibility) 权限"""
    if not HAS_QUARTZ:
        return True
    try:
        if prompt:
            options = {ApplicationServices.kAXTrustedCheckOptionPrompt: True}
            return ApplicationServices.AXIsProcessTrustedWithOptions(options)
        return ApplicationServices.AXIsProcessTrusted()
    except Exception:
        return False


def is_screen_locked() -> bool:
    """检测当前 macOS 系统是否处于锁屏或屏保状态"""
    if not HAS_QUARTZ:
        return False
    try:
        session_dict = Quartz.CGSessionCopyCurrentDictionary()
        if session_dict:
            return bool(session_dict.get('CGSSessionScreenIsLocked', 0))
    except Exception:
        pass
    return False


def get_window_info_at(x: int, y: int, ignore_self_pid: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """获取指定屏幕坐标下的最顶层窗口及其所属 App 和 PID"""
    if not HAS_QUARTZ:
        return None
    try:
        options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
        window_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
        my_pid = os.getpid()
        
        for win in window_list:
            layer = win.get(Quartz.kCGWindowLayer, 0)
            if layer != 0:
                continue
                
            pid = win.get(Quartz.kCGWindowOwnerPID, 0)
            if pid == my_pid or (ignore_self_pid and pid == ignore_self_pid):
                continue
                
            bounds = win.get(Quartz.kCGWindowBounds, {})
            wx, wy, ww, wh = bounds.get('X', 0), bounds.get('Y', 0), bounds.get('Width', 0), bounds.get('Height', 0)
            
            if wx <= x <= wx + ww and wy <= y <= wy + wh:
                owner_name = win.get(Quartz.kCGWindowOwnerName, 'Unknown')
                return {
                    'app_name': owner_name,
                    'pid': pid,
                    'bounds': (wx, wy, ww, wh)
                }
    except Exception:
        pass
    return None


def activate_app(app_name: Optional[str], pid: Optional[int]) -> bool:
    """根据 App 名字或 PID 激活目标应用至前台"""
    if not HAS_QUARTZ:
        return False
    try:
        ws = AppKit.NSWorkspace.sharedWorkspace()
        for app in ws.runningApplications():
            if (pid and app.processIdentifier() == pid) or (app_name and app.localizedName() == app_name):
                app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
                time.sleep(0.04)
                return True
    except Exception:
        pass
    return False


def get_random_offset(x: int, y: int, radius: float = 10.0) -> Tuple[int, int]:
    """在以 (x, y) 为圆心，半径为 radius 的圆内均匀生成一个随机坐标点"""
    if radius <= 0:
        return x, y
    r = radius * math.sqrt(random.random())
    theta = random.random() * 2 * math.pi
    offset_x = x + r * math.cos(theta)
    offset_y = y + r * math.sin(theta)
    return round(offset_x), round(offset_y)


def get_jittered_delay(base_ms: float, jitter_ms: float) -> Tuple[float, int]:
    """计算带有 ± 随机漂移的延时时间"""
    if jitter_ms <= 0:
        actual_ms = max(1.0, float(base_ms))
    else:
        actual_ms = base_ms + random.uniform(-jitter_ms, jitter_ms)
        actual_ms = max(1.0, actual_ms)
    return actual_ms / 1000.0, round(actual_ms)


def native_macos_click(x: int, y: int, count: int = 1):
    """使用 macOS Quartz 底层 CGEvent 发送硬件级鼠标点击"""
    if HAS_QUARTZ:
        pos = Quartz.CGPoint(x, y)
        move_event = Quartz.CGEventCreateMouseEvent(
            None, Quartz.kCGEventMouseMoved, pos, Quartz.kCGMouseButtonLeft
        )
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, move_event)
        time.sleep(0.01)

        for i in range(count):
            down_event = Quartz.CGEventCreateMouseEvent(
                None, Quartz.kCGEventLeftMouseDown, pos, Quartz.kCGMouseButtonLeft
            )
            Quartz.CGEventSetIntegerValueField(down_event, Quartz.kCGMouseEventClickState, i + 1)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, down_event)
            
            time.sleep(0.02)
            
            up_event = Quartz.CGEventCreateMouseEvent(
                None, Quartz.kCGEventLeftMouseUp, pos, Quartz.kCGMouseButtonLeft
            )
            Quartz.CGEventSetIntegerValueField(up_event, Quartz.kCGMouseEventClickState, i + 1)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, up_event)
            
            if i < count - 1:
                time.sleep(0.04)


class AutoClicker:
    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        config = load_config()
        self.point_a: Optional[Tuple[int, int]] = tuple(config["point_a"]) if config.get("point_a") else None
        self.point_b: Optional[Tuple[int, int]] = tuple(config["point_b"]) if config.get("point_b") else None
        self.radius: float = float(config.get("radius", 10.0))
        
        # A-B 间隔
        self.interval_ms: int = int(config.get("interval_ms", 300))
        self.interval_jitter_ms: int = int(config.get("interval_jitter_ms", 50))
        
        # B-B 间隔
        self.bb_interval_ms: int = int(config.get("bb_interval_ms", 100))
        self.bb_interval_jitter_ms: int = int(config.get("bb_interval_jitter_ms", 20))
        
        self.loops: int = int(config.get("loops", 1))
        self.infinite_loop: bool = bool(config.get("infinite_loop", False))
        
        self.target_app_name: Optional[str] = config.get("target_app_name")
        self.target_pid: Optional[int] = config.get("target_pid")
        self.lock_to_target_app: bool = bool(config.get("lock_to_target_app", True))
        self.prevent_sleep: bool = bool(config.get("prevent_sleep", True))
        
        self.log_callback = log_callback or (lambda msg: print(msg))
        
        self._is_running = False
        self._stop_requested = False
        self._exec_thread: Optional[threading.Thread] = None
        self._caffeinate_process: Optional[subprocess.Popen] = None

    def log(self, message: str):
        if self.log_callback:
            self.log_callback(message)

    def persist_current_config(self):
        """持久化保存当前设置"""
        cfg = {
            "point_a": list(self.point_a) if self.point_a else None,
            "point_b": list(self.point_b) if self.point_b else None,
            "radius": self.radius,
            "interval_ms": self.interval_ms,
            "interval_jitter_ms": self.interval_jitter_ms,
            "bb_interval_ms": self.bb_interval_ms,
            "bb_interval_jitter_ms": self.bb_interval_jitter_ms,
            "loops": self.loops,
            "infinite_loop": self.infinite_loop,
            "target_app_name": self.target_app_name,
            "target_pid": self.target_pid,
            "lock_to_target_app": self.lock_to_target_app,
            "prevent_sleep": self.prevent_sleep
        }
        save_config(cfg)

    def _start_caffeinate(self):
        """启动 caffeinate 进程防止系统休眠/锁屏"""
        if self.prevent_sleep and self._caffeinate_process is None:
            try:
                self._caffeinate_process = subprocess.Popen(
                    ["caffeinate", "-d", "-i", "-u"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.log("☕ 已激活系统防休眠/防锁屏保持 (Caffeinate)")
            except Exception:
                pass

    def _stop_caffeinate(self):
        """停止 caffeinate 进程"""
        if self._caffeinate_process:
            try:
                self._caffeinate_process.terminate()
                self._caffeinate_process.wait(timeout=1.0)
            except Exception:
                pass
            self._caffeinate_process = None

    def execute_one_abb_cycle(self) -> bool:
        """执行一次完整的【原子性 ABB 点击流程】"""
        if not self.point_a or not self.point_b:
            self.log("❌ 尚未完成取点，请先设置 A 点和 B 点！")
            return False

        if is_screen_locked():
            return False

        if self.lock_to_target_app and self.target_app_name:
            activate_app(self.target_app_name, self.target_pid)

        # 1. 点击 A 点
        ax, ay = get_random_offset(self.point_a[0], self.point_a[1], self.radius)
        native_macos_click(ax, ay, count=1)
        self.log(f"👉 [A点] 点击 1 次: 基准 {self.point_a} ➜ 实际落点 ({ax}, {ay})")

        # 2. 等待 A-B 间隔
        ab_sec, actual_ab_ms = get_jittered_delay(self.interval_ms, self.interval_jitter_ms)
        self.log(f"⏳ A-B 间隔等待: {actual_ab_ms}ms (基准 {self.interval_ms}ms ± {self.interval_jitter_ms}ms)")
        time.sleep(ab_sec)

        # 3. 点击 B 点第 1 次
        bx1, by1 = get_random_offset(self.point_b[0], self.point_b[1], self.radius)
        native_macos_click(bx1, by1, count=1)
        self.log(f"👉 [B点-1] 点击第 1 次: 基准 {self.point_b} ➜ 独立落点 ({bx1}, {by1})")

        # 4. 等待 B-B 间隔
        bb_sec, actual_bb_ms = get_jittered_delay(self.bb_interval_ms, self.bb_interval_jitter_ms)
        self.log(f"⏳ B-B 间隔等待: {actual_bb_ms}ms (基准 {self.bb_interval_ms}ms ± {self.bb_interval_jitter_ms}ms)")
        time.sleep(bb_sec)

        # 5. 点击 B 点第 2 次
        bx2, by2 = get_random_offset(self.point_b[0], self.point_b[1], self.radius)
        retry = 0
        while (bx2, by2) == (bx1, by1) and retry < 5 and self.radius > 0:
            bx2, by2 = get_random_offset(self.point_b[0], self.point_b[1], self.radius)
            retry += 1

        native_macos_click(bx2, by2, count=1)
        self.log(f"👉 [B点-2] 点击第 2 次: 基准 {self.point_b} ➜ 独立落点 ({bx2}, {by2})")

        return True

    def start_execution(self, on_complete: Optional[Callable[[], None]] = None):
        """在新线程中执行点击任务"""
        if self._is_running:
            self.log("⚠️ 任务已在运行中...")
            return

        if not self.point_a or not self.point_b:
            self.log("❌ 请先完成 A/B 点的屏幕取点！")
            return

        self.persist_current_config()
        self._is_running = True
        self._stop_requested = False
        self._start_caffeinate()

        def run_task():
            mode_desc = "♾️ 无限循环模式" if self.infinite_loop else f"共 {self.loops} 轮"
            target_desc = f"[锁定: {self.target_app_name}]" if (self.lock_to_target_app and self.target_app_name) else "[全局屏幕]"
            self.log(f"\n🚀 开始执行任务 ({mode_desc} | {target_desc} | 半径={self.radius}px | AB间隔={self.interval_ms}ms±{self.interval_jitter_ms}ms | BB间隔={self.bb_interval_ms}ms±{self.bb_interval_jitter_ms}ms)...")
            
            round_idx = 0
            while self._is_running:
                if is_screen_locked():
                    self.log("🛡️ 检测到系统处于锁屏/屏保状态！已自动暂停点击（保护安全）...")
                    while is_screen_locked() and self._is_running:
                        time.sleep(1.0)
                    if not self._is_running:
                        break
                    self.log("🔓 屏幕已解锁，恢复自动化点击！")
                    time.sleep(0.5)

                round_idx += 1
                if not self.infinite_loop and round_idx > self.loops:
                    break

                if self.infinite_loop or self.loops > 1:
                    self.log(f"--- 第 {round_idx} 轮 (ABB 周期) ---")

                success = self.execute_one_abb_cycle()
                if not success and not is_screen_locked():
                    break

                if self._stop_requested:
                    self.log("🛑 已完成当前轮次完整的 ABB 点击，安全退出！")
                    break

                if self._is_running:
                    if self.infinite_loop or round_idx < self.loops:
                        time.sleep(0.3)

            self._stop_caffeinate()
            self._is_running = False
            self._stop_requested = False
            self.log("🏁 任务已安全结束！\n")
            if on_complete:
                on_complete()

        self._exec_thread = threading.Thread(target=run_task, daemon=True)
        self._exec_thread.start()

    def stop_execution(self):
        """优雅停止"""
        if self._is_running and not self._stop_requested:
            self._stop_requested = True
            self.log("⏳ 收到停止指令：将在完成当前完整的一轮 ABB 点击后安全停止...")
