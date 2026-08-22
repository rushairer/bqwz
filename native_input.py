"""
macOS 原生全局热键与鼠标捕获模块
采用 CombinedSessionState + HIDSystemState 双状态轮询
100% 避免跨线程 C 回调与 Python 3.13 GIL 锁争用冲突，彻底杜绝 PyEval_RestoreThread 崩溃
"""
import Quartz
from typing import Callable, Optional

# macOS 虚拟键码
VK_F8 = 100
VK_F9 = 101
VK_F10 = 109
VK_ESC = 53


def is_mac_key_down(key_code: int) -> bool:
    """同时检查全局组合会话状态与底层硬件状态，确保无论焦点在任何应用均能捕获"""
    try:
        return (
            Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateCombinedSessionState, key_code) or
            Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, key_code)
        )
    except Exception:
        return False


class NativeHotkeyPoller:
    """在 Tkinter 主事件循环中以 25ms 间隔高频轮询全局按键，无 GIL 冲突，0 崩溃"""
    def __init__(
        self,
        tk_root,
        on_f8: Optional[Callable[[], None]] = None,
        on_f9: Optional[Callable[[], None]] = None,
        on_esc: Optional[Callable[[], None]] = None
    ):
        self.tk_root = tk_root
        self.on_f8 = on_f8
        self.on_f9 = on_f9
        self.on_esc = on_esc
        
        self._prev_f8 = False
        self._prev_f9 = False
        self._prev_esc = False
        self._prev_f10 = False
        self._running = True
        
        self._schedule_poll()

    def _schedule_poll(self):
        if not self._running:
            return
        try:
            self._check_keys()
        except Exception:
            pass
        # 25ms 高频采样 (40Hz)，保证按键瞬间被捕获，CPU 占用微乎其微
        self.tk_root.after(25, self._schedule_poll)

    def _check_keys(self):
        # 1. 检查 F8 (屏幕取点)
        is_f8 = is_mac_key_down(VK_F8)
        if is_f8 and not self._prev_f8:
            if self.on_f8:
                self.on_f8()
        self._prev_f8 = is_f8

        # 2. 检查 F9 (开始执行)
        is_f9 = is_mac_key_down(VK_F9)
        if is_f9 and not self._prev_f9:
            if self.on_f9:
                self.on_f9()
        self._prev_f9 = is_f9

        # 3. 检查 Esc 与 F10 (停止执行，双保险)
        is_esc = is_mac_key_down(VK_ESC)
        is_f10 = is_mac_key_down(VK_F10)
        
        if (is_esc and not self._prev_esc) or (is_f10 and not self._prev_f10):
            if self.on_esc:
                self.on_esc()
                
        self._prev_esc = is_esc
        self._prev_f10 = is_f10

    def stop(self):
        self._running = False
