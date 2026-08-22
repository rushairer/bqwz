"""
macOS 原生全局热键与鼠标监听模块 (基于 AppKit & CoreGraphics)
彻底解决 pynput 在 macOS 14+ / macOS 15+ 子线程中调用 HIToolbox 导致的 crash
"""
import AppKit
import Quartz
from typing import Callable, Optional

# macOS 常用虚拟键码 (Virtual Key Codes)
VK_F8 = 100
VK_F9 = 101
VK_ESC = 53


class NativeHotkeyManager:
    def __init__(self, on_f8: Callable[[], None], on_f9: Callable[[], None], on_esc: Callable[[], None]):
        self.on_f8 = on_f8
        self.on_f9 = on_f9
        self.on_esc = on_esc
        
        self._global_monitor = None
        self._local_monitor = None
        self._setup_monitors()

    def _setup_monitors(self):
        try:
            mask = AppKit.NSEventMaskKeyDown
            
            def handle_event(event):
                try:
                    keycode = event.keyCode()
                    if keycode == VK_F8:
                        self.on_f8()
                    elif keycode == VK_F9:
                        self.on_f9()
                    elif keycode == VK_ESC:
                        self.on_esc()
                except Exception:
                    pass
                return event

            # 1. 全局监听（当焦点在其他应用时）
            self._global_monitor = AppKit.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                mask, handle_event
            )
            # 2. 本地监听（当焦点在本应用窗口内时）
            self._local_monitor = AppKit.NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
                mask, handle_event
            )
        except Exception as e:
            print(f"初始化原生热键监听失败: {e}")

    def stop(self):
        if self._global_monitor:
            AppKit.NSEvent.removeMonitor_(self._global_monitor)
            self._global_monitor = None
        if self._local_monitor:
            AppKit.NSEvent.removeMonitor_(self._local_monitor)
            self._local_monitor = None


class NativeMouseCapture:
    """macOS 原生屏幕取点监听器"""
    def __init__(self, on_click_callback: Callable[[int, int], bool]):
        self.on_click_callback = on_click_callback
        self._global_monitor = None
        self._local_monitor = None
        self.is_active = False

    def start(self):
        if self.is_active:
            return
        self.is_active = True
        
        mask = AppKit.NSEventMaskLeftMouseDown

        def handle_mouse(event):
            if not self.is_active:
                return event
            try:
                # 获取当前全局鼠标物理坐标
                pos = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
                x, y = round(pos.x), round(pos.y)
                # 回调返回 False 表示停止取点
                should_continue = self.on_click_callback(x, y)
                if not should_continue:
                    self.stop()
            except Exception:
                pass
            return event

        self._global_monitor = AppKit.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            mask, handle_mouse
        )
        self._local_monitor = AppKit.NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            mask, handle_mouse
        )

    def stop(self):
        self.is_active = False
        if self._global_monitor:
            AppKit.NSEvent.removeMonitor_(self._global_monitor)
            self._global_monitor = None
        if self._local_monitor:
            AppKit.NSEvent.removeMonitor_(self._local_monitor)
            self._local_monitor = None
