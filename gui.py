import os
import subprocess
import threading
import time
from typing import Optional

import customtkinter as ctk
from pynput import keyboard

from clicker_core import AutoClicker, check_accessibility_permission, is_screen_locked, get_window_info_at
from overlay_capture import ScreenCaptureOverlay

# 设置 CustomTkinter 外观
ctk.set_appearance_mode("System")  # 跟随系统深色/浅色模式
ctk.set_default_color_theme("blue")


class ModernClickerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("屏幕自动点击助手 (macOS)")
        self.geometry("540x820")
        self.minsize(510, 750)

        # 窗口置顶，方便悬浮
        self.attributes("-topmost", True)

        self.clicker = AutoClicker(log_callback=self._append_log)
        self.overlay_capture = None

        self._create_widgets()
        self._setup_hotkeys()
        self._check_permission_status()
        self._load_initial_values()

    def _create_widgets(self):
        # 1. 顶部权限与状态指示栏
        self.perm_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#E8F5E9")
        self.perm_frame.pack(fill="x", padx=16, pady=(10, 4))

        self.lbl_perm = ctk.CTkLabel(
            self.perm_frame,
            text="正在检测权限...",
            font=ctk.CTkFont(family="SF Pro Text", size=12, weight="bold"),
            text_color="#2E7D32"
        )
        self.lbl_perm.pack(side="left", padx=14, pady=8)

        self.btn_fix_perm = ctk.CTkButton(
            self.perm_frame,
            text="授权/检查",
            width=80,
            height=28,
            font=ctk.CTkFont(size=11),
            command=self.on_btn_fix_perm
        )
        self.btn_fix_perm.pack(side="right", padx=10, pady=6)

        # 2. 标题区
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(2, 4))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="⚡ 屏幕自动连点器 (ABB 周期模式)",
            font=ctk.CTkFont(family="SF Pro Display", size=18, weight="bold")
        )
        title_lbl.pack(anchor="w")

        hint_lbl = ctk.CTkLabel(
            header_frame,
            text="全局快捷键：[F8] 屏幕取点  |  [F9] 开始执行  |  [Esc] 停止/退出",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        hint_lbl.pack(anchor="w", pady=(1, 0))

        # 3. 目标坐标与绑定应用卡片
        coords_frame = ctk.CTkFrame(self, corner_radius=12)
        coords_frame.pack(fill="x", padx=16, pady=4)

        coords_title_box = ctk.CTkFrame(coords_frame, fg_color="transparent")
        coords_title_box.pack(fill="x", padx=12, pady=(8, 2))
        
        ctk.CTkLabel(
            coords_title_box,
            text="📍 目标点坐标 & 目标应用绑定",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left")

        # 目标应用信息条
        app_bar = ctk.CTkFrame(coords_frame, fg_color=("gray90", "gray20"), corner_radius=6)
        app_bar.pack(fill="x", padx=12, pady=(2, 6))

        self.lbl_target_app = ctk.CTkLabel(
            app_bar,
            text="🏷️ 目标应用: 未绑定 (取点时自动识别)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#1976D2", "#64B5F6")
        )
        self.lbl_target_app.pack(side="left", padx=8, pady=4)

        # A 点行
        row_a = ctk.CTkFrame(coords_frame, fg_color="transparent")
        row_a.pack(fill="x", padx=12, pady=3)

        self.badge_a = ctk.CTkLabel(
            row_a,
            text=" A 点 (点击 1 次) ",
            fg_color=("#3B8ED0", "#1F6AA5"),
            text_color="white",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=110
        )
        self.badge_a.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row_a, text="X:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 2))
        self.entry_ax = ctk.CTkEntry(row_a, width=65, height=28)
        self.entry_ax.pack(side="left", padx=(0, 10))
        self.entry_ax.bind("<FocusOut>", lambda e: self._on_coords_manual_change())

        ctk.CTkLabel(row_a, text="Y:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 2))
        self.entry_ay = ctk.CTkEntry(row_a, width=65, height=28)
        self.entry_ay.pack(side="left", padx=(0, 10))
        self.entry_ay.bind("<FocusOut>", lambda e: self._on_coords_manual_change())

        self.lbl_status_a = ctk.CTkLabel(row_a, text="未设置", font=ctk.CTkFont(size=11), text_color="gray")
        self.lbl_status_a.pack(side="left")

        # B 点行
        row_b = ctk.CTkFrame(coords_frame, fg_color="transparent")
        row_b.pack(fill="x", padx=12, pady=(3, 8))

        self.badge_b = ctk.CTkLabel(
            row_b,
            text=" B 点 (点击 2 次) ",
            fg_color=("#8A2BE2", "#6A1B9A"),
            text_color="white",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            width=110
        )
        self.badge_b.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row_b, text="X:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 2))
        self.entry_bx = ctk.CTkEntry(row_b, width=65, height=28)
        self.entry_bx.pack(side="left", padx=(0, 10))
        self.entry_bx.bind("<FocusOut>", lambda e: self._on_coords_manual_change())

        ctk.CTkLabel(row_b, text="Y:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 2))
        self.entry_by = ctk.CTkEntry(row_b, width=65, height=28)
        self.entry_by.pack(side="left", padx=(0, 10))
        self.entry_by.bind("<FocusOut>", lambda e: self._on_coords_manual_change())

        self.lbl_status_b = ctk.CTkLabel(row_b, text="未设置", font=ctk.CTkFont(size=11), text_color="gray")
        self.lbl_status_b.pack(side="left")

        # 4. 运行参数与防锁屏/防误触卡片
        params_frame = ctk.CTkFrame(self, corner_radius=12)
        params_frame.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            params_frame,
            text="⚙️ 点击规则与安全防护设置",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=12, pady=(8, 4))

        param_grid = ctk.CTkFrame(params_frame, fg_color="transparent")
        param_grid.pack(fill="x", padx=12, pady=(0, 8))

        # 随机半径
        p_row1 = ctk.CTkFrame(param_grid, fg_color="transparent")
        p_row1.pack(fill="x", pady=2)
        ctk.CTkLabel(p_row1, text="随机偏移半径:", width=105, anchor="w", font=ctk.CTkFont(size=12)).pack(side="left")
        self.entry_radius = ctk.CTkEntry(p_row1, width=60, height=28)
        self.entry_radius.pack(side="left", padx=(0, 6))
        self.entry_radius.bind("<FocusOut>", lambda e: self._save_ui_params())
        ctk.CTkLabel(p_row1, text="px (两次B落点均独立重新随机采样)", font=ctk.CTkFont(size=11), text_color="gray").pack(side="left")

        # A-B 间隔时间 + 漂移值
        p_row2 = ctk.CTkFrame(param_grid, fg_color="transparent")
        p_row2.pack(fill="x", pady=2)
        ctk.CTkLabel(p_row2, text="A-B 间隔时间:", width=105, anchor="w", font=ctk.CTkFont(size=12)).pack(side="left")
        self.entry_interval = ctk.CTkEntry(p_row2, width=60, height=28)
        self.entry_interval.pack(side="left", padx=(0, 4))
        self.entry_interval.bind("<FocusOut>", lambda e: self._save_ui_params())
        ctk.CTkLabel(p_row2, text="ms  ± 漂移:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 4))
        self.entry_jitter = ctk.CTkEntry(p_row2, width=50, height=28)
        self.entry_jitter.pack(side="left", padx=(0, 4))
        self.entry_jitter.bind("<FocusOut>", lambda e: self._save_ui_params())
        ctk.CTkLabel(p_row2, text="ms", font=ctk.CTkFont(size=11), text_color="gray").pack(side="left")

        # B-B 间隔时间 + 漂移值
        p_row_bb = ctk.CTkFrame(param_grid, fg_color="transparent")
        p_row_bb.pack(fill="x", pady=2)
        ctk.CTkLabel(p_row_bb, text="B-B 间隔时间:", width=105, anchor="w", font=ctk.CTkFont(size=12)).pack(side="left")
        self.entry_bb_interval = ctk.CTkEntry(p_row_bb, width=60, height=28)
        self.entry_bb_interval.pack(side="left", padx=(0, 4))
        self.entry_bb_interval.bind("<FocusOut>", lambda e: self._save_ui_params())
        ctk.CTkLabel(p_row_bb, text="ms  ± 漂移:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 4))
        self.entry_bb_jitter = ctk.CTkEntry(p_row_bb, width=50, height=28)
        self.entry_bb_jitter.pack(side="left", padx=(0, 4))
        self.entry_bb_jitter.bind("<FocusOut>", lambda e: self._save_ui_params())
        ctk.CTkLabel(p_row_bb, text="ms (两击B之间的等待)", font=ctk.CTkFont(size=11), text_color="gray").pack(side="left")

        # 循环轮数 + 无限循环开关
        p_row3 = ctk.CTkFrame(param_grid, fg_color="transparent")
        p_row3.pack(fill="x", pady=2)
        ctk.CTkLabel(p_row3, text="执行轮数:", width=105, anchor="w", font=ctk.CTkFont(size=12)).pack(side="left")
        self.entry_loops = ctk.CTkEntry(p_row3, width=60, height=28)
        self.entry_loops.pack(side="left", padx=(0, 10))
        self.entry_loops.bind("<FocusOut>", lambda e: self._save_ui_params())

        self.switch_infinite = ctk.CTkCheckBox(
            p_row3,
            text="♾️ 无限循环 (按 Esc 完成本轮后停止)",
            font=ctk.CTkFont(size=12),
            command=self._on_toggle_infinite
        )
        self.switch_infinite.pack(side="left")

        # 高级防护开关
        p_row4 = ctk.CTkFrame(param_grid, fg_color="transparent")
        p_row4.pack(fill="x", pady=(6, 2))

        self.chk_lock_app = ctk.CTkCheckBox(
            p_row4,
            text="🎯 点击前自动唤醒/置顶目标应用 (防误触其他窗口)",
            font=ctk.CTkFont(size=11),
            command=self._save_ui_params
        )
        self.chk_lock_app.pack(anchor="w", pady=1)

        self.chk_prevent_sleep = ctk.CTkCheckBox(
            p_row4,
            text="☕ 运行期间防止系统休眠/锁屏 (Caffeinate 保持屏幕常亮)",
            font=ctk.CTkFont(size=11),
            command=self._save_ui_params
        )
        self.chk_prevent_sleep.pack(anchor="w", pady=1)

        # 5. 操作按钮区
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=6)

        self.btn_capture = ctk.CTkButton(
            btn_frame,
            text="① 屏幕取点 (F8)",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            fg_color=("#1976D2", "#1565C0"),
            hover_color=("#1565C0", "#0D47A1"),
            command=self.on_btn_capture
        )
        self.btn_capture.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_run = ctk.CTkButton(
            btn_frame,
            text="② 开始执行 (F9)",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            fg_color=("#2E7D32", "#1B5E20"),
            hover_color=("#1B5E20", "#0E3913"),
            command=self.on_btn_run
        )
        self.btn_run.pack(side="left", fill="x", expand=True, padx=4)

        self.btn_stop = ctk.CTkButton(
            btn_frame,
            text="⏹ 停止 (Esc)",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            fg_color=("#D32F2F", "#C62828"),
            hover_color=("#B71C1C", "#8E0000"),
            command=self.on_btn_stop
        )
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # 6. 运行日志区
        log_frame = ctk.CTkFrame(self, corner_radius=12)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(2, 12))

        log_top = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_top.pack(fill="x", padx=12, pady=(6, 2))

        ctk.CTkLabel(
            log_top,
            text="📜 运行日志",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left")

        btn_clear = ctk.CTkButton(
            log_top,
            text="清空",
            width=48,
            height=20,
            font=ctk.CTkFont(size=10),
            fg_color=("gray75", "gray30"),
            command=self._clear_log
        )
        btn_clear.pack(side="right")

        self.log_textbox = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Menlo", size=11),
            corner_radius=8,
            activate_scrollbars=True
        )
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=(2, 8))

    def _load_initial_values(self):
        """恢复上次保存的参数与坐标"""
        if self.clicker.point_a:
            self.entry_ax.delete(0, "end")
            self.entry_ax.insert(0, str(self.clicker.point_a[0]))
            self.entry_ay.delete(0, "end")
            self.entry_ay.insert(0, str(self.clicker.point_a[1]))
            self.lbl_status_a.configure(text="✅ 已就绪", text_color="#2E7D32")

        if self.clicker.point_b:
            self.entry_bx.delete(0, "end")
            self.entry_bx.insert(0, str(self.clicker.point_b[0]))
            self.entry_by.delete(0, "end")
            self.entry_by.insert(0, str(self.clicker.point_b[1]))
            self.lbl_status_b.configure(text="✅ 已就绪", text_color="#2E7D32")

        if self.clicker.target_app_name:
            self.lbl_target_app.configure(
                text=f"🏷️ 目标应用: {self.clicker.target_app_name} (PID: {self.clicker.target_pid or 'N/A'})"
            )

        self.entry_radius.delete(0, "end")
        self.entry_radius.insert(0, str(self.clicker.radius))

        self.entry_interval.delete(0, "end")
        self.entry_interval.insert(0, str(self.clicker.interval_ms))

        self.entry_jitter.delete(0, "end")
        self.entry_jitter.insert(0, str(self.clicker.interval_jitter_ms))

        self.entry_bb_interval.delete(0, "end")
        self.entry_bb_interval.insert(0, str(self.clicker.bb_interval_ms))

        self.entry_bb_jitter.delete(0, "end")
        self.entry_bb_jitter.insert(0, str(self.clicker.bb_interval_jitter_ms))

        self.entry_loops.delete(0, "end")
        self.entry_loops.insert(0, str(self.clicker.loops))

        if self.clicker.infinite_loop:
            self.switch_infinite.select()
            self.entry_loops.configure(state="disabled")
        else:
            self.switch_infinite.deselect()
            self.entry_loops.configure(state="normal")

        if self.clicker.lock_to_target_app:
            self.chk_lock_app.select()
        else:
            self.chk_lock_app.deselect()

        if self.clicker.prevent_sleep:
            self.chk_prevent_sleep.select()
        else:
            self.chk_prevent_sleep.deselect()

        if self.clicker.point_a and self.clicker.point_b:
            self._append_log("💾 已恢复上次保存的配置：")
            self._append_log(f"   A: {self.clicker.point_a} | B: {self.clicker.point_b}")
            self._append_log(f"   AB间隔: {self.clicker.interval_ms}ms±{self.clicker.interval_jitter_ms}ms | BB间隔: {self.clicker.bb_interval_ms}ms±{self.clicker.bb_interval_jitter_ms}ms")

    def _on_toggle_infinite(self):
        is_inf = bool(self.switch_infinite.get())
        self.clicker.infinite_loop = is_inf
        if is_inf:
            self.entry_loops.configure(state="disabled")
        else:
            self.entry_loops.configure(state="normal")
        self._save_ui_params()

    def _check_permission_status(self):
        trusted = check_accessibility_permission(prompt=False)
        if trusted:
            self.perm_frame.configure(fg_color=("#E8F5E9", "#1B3B22"))
            self.lbl_perm.configure(
                text="✅ 辅助功能权限已获得（点击功能正常）",
                text_color=("#2E7D32", "#81C784")
            )
            self.btn_fix_perm.configure(text="刷新检查")
        else:
            self.perm_frame.configure(fg_color=("#FFEBEE", "#3E1F21"))
            self.lbl_perm.configure(
                text="❌ 未获辅助功能权限（点击将无效）",
                text_color=("#C62828", "#E57373")
            )
            self.btn_fix_perm.configure(text="去授权")

    def on_btn_fix_perm(self):
        check_accessibility_permission(prompt=True)
        subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])
        self._check_permission_status()

    def _append_log(self, msg: str):
        def _update():
            self.log_textbox.insert("end", f"{msg}\n")
            self.log_textbox.see("end")
        self.after(0, _update)

    def _clear_log(self):
        self.log_textbox.delete("1.0", "end")

    def _on_coords_manual_change(self):
        """当用户在输入框手动微调坐标时，同步并保存"""
        try:
            ax_str = self.entry_ax.get().strip()
            ay_str = self.entry_ay.get().strip()
            if ax_str and ay_str:
                self.clicker.point_a = (int(ax_str), int(ay_str))
                self.lbl_status_a.configure(text="✅ 已就绪", text_color="#2E7D32")

            bx_str = self.entry_bx.get().strip()
            by_str = self.entry_by.get().strip()
            if bx_str and by_str:
                self.clicker.point_b = (int(bx_str), int(by_str))
                self.lbl_status_b.configure(text="✅ 已就绪", text_color="#2E7D32")

            self._save_ui_params()
        except ValueError:
            pass

    def _save_ui_params(self):
        try:
            self.clicker.radius = float(self.entry_radius.get().strip())
            self.clicker.interval_ms = int(self.entry_interval.get().strip())
            self.clicker.interval_jitter_ms = int(self.entry_jitter.get().strip())
            self.clicker.bb_interval_ms = int(self.entry_bb_interval.get().strip())
            self.clicker.bb_interval_jitter_ms = int(self.entry_bb_jitter.get().strip())
            if self.entry_loops.cget("state") == "normal":
                self.clicker.loops = int(self.entry_loops.get().strip())
            self.clicker.infinite_loop = bool(self.switch_infinite.get())
            self.clicker.lock_to_target_app = bool(self.chk_lock_app.get())
            self.clicker.prevent_sleep = bool(self.chk_prevent_sleep.get())
            self.clicker.persist_current_config()
        except ValueError:
            pass

    def _setup_hotkeys(self):
        # 恢复 run.sh 同款 pynput 全局热键监听（由于已预先初始化 NSApplication，完全不崩溃）
        def on_press(key):
            try:
                if key == keyboard.Key.esc:
                    self.after(0, self.on_btn_stop)
                elif key == keyboard.Key.f8:
                    self.after(0, self.on_btn_capture)
                elif key == keyboard.Key.f9:
                    self.after(0, self.on_btn_run)
            except Exception:
                pass

        self.kb_listener = keyboard.Listener(on_press=on_press)
        self.kb_listener.daemon = True
        self.kb_listener.start()

        # 本地快捷键双保险
        self.bind_all("<F8>", lambda e: self.on_btn_capture())
        self.bind_all("<F9>", lambda e: self.on_btn_run())
        self.bind_all("<Escape>", lambda e: self.on_btn_stop())

    def on_btn_capture(self):
        """开启全屏准星取点模式"""
        if self.overlay_capture is not None:
            return

        self.btn_capture.configure(text="🎯 正在全屏取点中...", state="disabled")
        self._append_log("🎯 [取点模式开启] 请在全屏十字准星遮罩上依次点击【A 点】与【B 点】 (按 Esc 取消)...")

        def on_finish(pt_a, pt_b):
            self.overlay_capture = None
            self.clicker.point_a = pt_a
            self.clicker.point_b = pt_b

            self.entry_ax.delete(0, "end")
            self.entry_ax.insert(0, str(pt_a[0]))
            self.entry_ay.delete(0, "end")
            self.entry_ay.insert(0, str(pt_a[1]))
            self.lbl_status_a.configure(text="✅ 已就绪", text_color="#2E7D32")

            self.entry_bx.delete(0, "end")
            self.entry_bx.insert(0, str(pt_b[0]))
            self.entry_by.delete(0, "end")
            self.entry_by.insert(0, str(pt_b[1]))
            self.lbl_status_b.configure(text="✅ 已就绪", text_color="#2E7D32")

            win_info = get_window_info_at(pt_a[0], pt_a[1])
            if win_info:
                self.clicker.target_app_name = win_info['app_name']
                self.clicker.target_pid = win_info['pid']
                self.lbl_target_app.configure(
                    text=f"🏷️ 目标应用: {self.clicker.target_app_name} (PID: {self.clicker.target_pid or 'N/A'})"
                )
                self._append_log(f"✅ 已记录 A 点: {pt_a} (所属应用: 🏷️ {self.clicker.target_app_name})")
            else:
                self._append_log(f"✅ 已记录 A 点: {pt_a}")

            self._append_log(f"✅ 已记录 B 点: {pt_b}")
            self._append_log("🎉 A/B 两点取点完成并自动保存！")
            self.clicker.persist_current_config()
            self.btn_capture.configure(text="① 重新取点 (F8)", state="normal")

        def on_cancel():
            self.overlay_capture = None
            self.btn_capture.configure(text="① 屏幕取点 (F8)", state="normal")
            self._append_log("🛑 已取消屏幕取点。")

        self.overlay_capture = ScreenCaptureOverlay(
            parent_app=self,
            on_finish_callback=on_finish,
            on_cancel_callback=on_cancel
        )

    def on_btn_run(self):
        self._on_coords_manual_change()
        self._save_ui_params()

        if not self.clicker.point_a or not self.clicker.point_b:
            self._append_log("❌ 错误：请先设置 A 点和 B 点坐标！")
            return

        self.btn_run.configure(state="disabled")
        self.btn_capture.configure(state="disabled")
        self.btn_stop.configure(text="⏹ 停止 (Esc)", state="normal")

        def on_complete():
            def _restore_btn():
                self.btn_run.configure(state="normal")
                self.btn_capture.configure(state="normal")
                self.btn_stop.configure(text="⏹ 停止 (Esc)", state="normal")
            self.after(0, _restore_btn)

        self.clicker.start_execution(on_complete=on_complete)

    def on_btn_stop(self):
        if self.overlay_capture is not None:
            self.overlay_capture.cancel()
            return

        if self.clicker._is_running:
            self.btn_stop.configure(text="⏳ 等待本轮ABB完成...", state="disabled")
            self.clicker.stop_execution()
        else:
            self.btn_capture.configure(text="① 屏幕取点 (F8)", state="normal")
            self.btn_run.configure(state="normal")


def run_gui():
    app = ModernClickerApp()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
