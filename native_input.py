"""
macOS 底层全局热键监听器 (基于 Quartz CGEventTap + 独立 CFRunLoop)
真正实现系统级全局热键：即使失去窗口焦点或在其他任意应用前台，Esc / F8 / F9 均能瞬间响应
"""
import threading
from typing import Callable, Optional
import Quartz

# macOS 物理虚拟键码
VK_F8 = 100
VK_F9 = 101
VK_ESC = 53


class GlobalHotkeyListener:
    def __init__(
        self,
        tk_app,
        on_f8: Optional[Callable[[], None]] = None,
        on_f9: Optional[Callable[[], None]] = None,
        on_esc: Optional[Callable[[], None]] = None
    ):
        self.tk_app = tk_app
        self.on_f8 = on_f8
        self.on_f9 = on_f9
        self.on_esc = on_esc
        
        self._run_loop = None
        self._thread = None
        self._is_running = False

    def _event_tap_callback(self, proxy, event_type, event, refcon):
        if event_type == Quartz.kCGEventKeyDown:
            try:
                keycode = Quartz.CGEventGetIntegerValueField(
                    event, Quartz.kCGKeyboardEventKeycode
                )
                if keycode == VK_ESC and self.on_esc:
                    # 线程安全派发到 Tkinter 主事件循环
                    self.tk_app.after(0, self.on_esc)
                elif keycode == VK_F8 and self.on_f8:
                    self.tk_app.after(0, self.on_f8)
                elif keycode == VK_F9 and self.on_f9:
                    self.tk_app.after(0, self.on_f9)
            except Exception:
                pass
        return event

    def start(self):
        if self._is_running:
            return
        self._is_running = True

        def loop_worker():
            try:
                # 监听底层键盘按下事件 (ListenOnly 模式，纯监听不拦截)
                tap = Quartz.CGEventTapCreate(
                    Quartz.kCGHIDEventTap,
                    Quartz.kCGHeadInsertEventTap,
                    Quartz.kCGEventTapOptionListenOnly,
                    Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown),
                    self._event_tap_callback,
                    None
                )
                if not tap:
                    return

                source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
                self._run_loop = Quartz.CFRunLoopGetCurrent()
                Quartz.CFRunLoopAddSource(self._run_loop, source, Quartz.kCFRunLoopCommonModes)
                Quartz.CGEventTapEnable(tap, True)
                Quartz.CFRunLoopRun()
            except Exception:
                pass

        self._thread = threading.Thread(target=loop_worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._is_running = False
        if self._run_loop:
            try:
                Quartz.CFRunLoopStop(self._run_loop)
            except Exception:
                pass
            self._run_loop = None
