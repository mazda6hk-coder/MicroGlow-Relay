"""Release metadata for this source candidate; not a claim of public release."""
# app/__init__.py 已把 src 放进 sys.path（frozen 时 PyInstaller 已收集）。
from storage import VERSION  # noqa: E402  (single source of truth)

# 构建标识从唯一版本源 storage.VERSION 派生，避免手写串与程序版本漂移。
BUILD_ID = f"{VERSION}-source"
RELEASE_DATE = ""
