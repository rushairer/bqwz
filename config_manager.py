import json
import os
import sys
from typing import Dict, Any

def get_config_path() -> str:
    """
    获取配置文件的存放路径。
    如果是打包后的 macOS .app (frozen)，优先存放在 ~/Library/Application Support/AutoClicker/config.json
    如果是脚本运行，优先存放在本地工作目录，如不可写则存放在 Application Support。
    """
    if getattr(sys, 'frozen', False):
        app_support = os.path.expanduser("~/Library/Application Support/AutoClicker")
        os.makedirs(app_support, exist_ok=True)
        return os.path.join(app_support, "config.json")
    else:
        local_path = os.path.join(os.path.dirname(__file__), "config.json")
        return local_path

CONFIG_FILE = get_config_path()

DEFAULT_CONFIG = {
    "point_a": None,            # [x, y]
    "point_b": None,            # [x, y]
    "radius": 10.0,
    "interval_ms": 300,         # A-B 基础间隔 (ms)
    "interval_jitter_ms": 50,   # A-B ± 漂移值 (ms)
    "bb_interval_ms": 100,      # B-B 基础间隔 (ms)
    "bb_interval_jitter_ms": 20,# B-B ± 漂移值 (ms)
    "loops": 1,
    "infinite_loop": False,     # 无限循环开关
    "target_app_name": None,    # 锁定的目标应用名称
    "target_pid": None,         # 锁定的目标进程 PID
    "lock_to_target_app": True, # 是否锁定并自动激活目标应用
    "prevent_sleep": True       # 运行期间防止系统休眠/锁屏
}


def load_config() -> Dict[str, Any]:
    """从本地读取配置，如不存在则返回默认配置"""
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]):
    """保存配置到 config.json"""
    try:
        config_path = get_config_path()
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存配置文件失败: {e}")
