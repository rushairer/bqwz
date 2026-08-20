import json
import os
from typing import Dict, Any

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

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
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]):
    """保存配置到本地 config.json"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存配置文件失败: {e}")
