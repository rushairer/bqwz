"""
macOS 原生零崩溃热键与鼠标捕获模块 (基于 CoreGraphics 状态轮询)
彻底避免跨线程 C-Block 导致的 Python 3.13 GIL 锁崩溃 (PyEval_RestoreThread)
"""
import Quartz
from typing import Callable, Optional

# macOS 虚拟键码
VK_F8 = 100
VK_F9 = 101
VK_ESC = 53


class NativeHotkeyPoller:
    """在 Tkinter 主事件循环中通过定时器安全检测按键（无多线程 GIL 冲突）"""
    def __init__(self, tk_root, on_f8: Callable[[], None], on_f9: Callable[[], None], on_esc: Callable[[], None]):
        self.tk_root = tk_root
        self.on_f8 = on_f8
        self.on_f9 = on_f9
        self.on_esc = on_esc
        
        self._prev_f8 = False
        self._prev_f9 = False
        self._prev_esc = False
        self._running = True
        
        self._schedule_poll()

    def _schedule_poll(self):
        if not self._running:
            return
        try:
            self._check_keys()
        except Exception:
            pass
        # 每 40ms 检测一次按键状态 (25Hz，足够敏锐且 CPU 占用为 0%)
        self.tk_root.after(40, self._schedule_poll)

    def _check_keys(self):
        # 1. 检查 F8
        is_f8 = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, VK_F8)
        if is_f8 and not self._prev_f8:
            self.on_f8()
        self._prev_f8 = is_f8

        # 2. 检查 F9
        is_f9 = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, VK_F9)
        if is_f9 and not self._prev_f9:
            self.on_f9()
        self._prev_f9 = is_f9

        # 3. 检查 Esc
        is_esc = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, VK_ESC)
        if is_esc and not self._prev_esc:
            self.on_esc()
        self._prev_esc = is_esc

    def stop(self):
        self._running = False


class NativeMouseCapturePoller:
    """在 Tkinter 主事件循环中通过定时器安全捕获屏幕鼠标点击"""
    def __init__(self, tk_root, on_click_callback: Callable[[int, int], bool]):
        self.tk_root = tk_root
        self.on_click_callback = on_click_callback
        self._prev_mouse_down = False
        self.is_active = False

    def start(self):
        self.is_active = True
        # 初始化当前鼠标状态，防止启动瞬间已有按下
        self._prev_mouse_down = Quartz.CGEventSourceButtonState(
            Quartz.kCGEventSourceStateHIDSystemState, Quartz.kCGMouseButtonLeft
        )
        self._schedule_poll()

    def _schedule_poll(self):
        if not self.is_active:
            return
        try:
            is_down = Quartz.CGEventSourceButtonState(
                Quartz.kCGEventSourceStateHIDSystemState, Quartz.kCGMouseButtonLeft
            )
            # 检测鼠标左键按下瞬间 (Rising Edge)
            if is_down and not self._prev_mouse_down:
                pos = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
                x, y = round(pos.x), round(pos.y)
                should_continue = self.on_click_callback(x, y)
                if not should_continue:
                    self.stop()
                    return
            self._prev_mouse_down = is_down
        except Exception:
            pass

        # 取点时每 20ms 检测一次，确保点按捕获不漏
        if self.is_active:
            self.tk_root.after(20, self._schedule_poll)

    def stop(self):
        self.is_active = False
