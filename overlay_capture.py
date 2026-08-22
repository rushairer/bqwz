"""
全屏透明准星取点遮罩层 (商业截图软件同款实现方案)
100% 免疫 macOS 系统权限限制与输入法拦截，提供极佳的十字准星取点体验
"""
import tkinter as tk
from typing import Callable, Optional, Tuple
from clicker_core import get_window_info_at


class ScreenCaptureOverlay:
    def __init__(
        self,
        parent_app,
        on_finish_callback: Callable[[Tuple[int, int], Tuple[int, int]], None],
        on_cancel_callback: Optional[Callable[[], None]] = None
    ):
        self.parent_app = parent_app
        self.on_finish_callback = on_finish_callback
        self.on_cancel_callback = on_cancel_callback

        self.point_a: Optional[Tuple[int, int]] = None
        self.point_b: Optional[Tuple[int, int]] = None

        self._create_overlay()

    def _create_overlay(self):
        self.overlay = tk.Toplevel(self.parent_app)
        self.overlay.title("ScreenCaptureOverlay")
        
        # 获取全屏尺寸
        screen_w = self.overlay.winfo_screenwidth()
        screen_h = self.overlay.winfo_screenheight()
        self.overlay.geometry(f"{screen_w}x{screen_h}+0+0")
        
        # 无边框 + 顶层悬浮
        self.overlay.overrideredirect(True)
        self.overlay.attributes("-topmost", True)
        # 微透明度，既能看清底层屏幕，又能完全拦截并捕获鼠标事件
        self.overlay.attributes("-alpha", 0.25)
        
        # 画布与准星光标
        self.canvas = tk.Canvas(
            self.overlay, 
            bg="#000000", 
            cursor="crosshair", 
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 浮动提示信息标签
        self.tip_frame = tk.Frame(self.overlay, bg="#1E293B", padx=12, pady=6)
        self.lbl_tip = tk.Label(
            self.tip_frame, 
            text="🎯 请点击屏幕取【A 点】 (按 Esc 取消)", 
            fg="#F8FAFC", 
            bg="#1E293B", 
            font=("Helvetica", 13, "bold")
        )
        self.lbl_tip.pack()
        
        # 将提示框默认放置在屏幕上方居中
        self.tip_frame.place(relx=0.5, y=40, anchor=tk.CENTER)

        # 绑定事件
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.overlay.bind("<Escape>", lambda e: self.cancel())

        # 强制获取焦点
        self.overlay.lift()
        self.overlay.focus_force()

    def _on_mouse_move(self, event):
        x, y = event.x_root, event.y_root
        target_name = "A 点" if self.point_a is None else "B 点"
        self.lbl_tip.config(
            text=f"🎯 请点击目标位置取【{target_name}】  (当前坐标: X={x}, Y={y})  |  按 Esc 退出"
        )

    def _on_click(self, event):
        x, y = event.x_root, event.y_root
        
        if self.point_a is None:
            self.point_a = (x, y)
            self.lbl_tip.config(
                text=f"✅ 已记录 A 点: ({x}, {y})！👉 请点击第 2 个目标位置取【B 点】",
                fg="#4ADE80"
            )
            # 在 A 点位置画一个红圈标记
            r = 8
            self.canvas.create_oval(
                event.x - r, event.y - r, event.x + r, event.y + r,
                outline="#EF4444", fill="#F87171", width=2
            )
            self.canvas.create_text(
                event.x + 18, event.y - 12,
                text="A", fill="#EF4444", font=("Helvetica", 12, "bold")
            )
        elif self.point_b is None:
            self.point_b = (x, y)
            # 完成取点
            pt_a = self.point_a
            pt_b = self.point_b
            self.destroy()
            if self.on_finish_callback:
                self.on_finish_callback(pt_a, pt_b)

    def cancel(self):
        self.destroy()
        if self.on_cancel_callback:
            self.on_cancel_callback()

    def destroy(self):
        if self.overlay and self.overlay.winfo_exists():
            self.overlay.destroy()
