"""Multi-channel routing with weighted selection and cooldowns.

一个逻辑模型配置（profile）可以挂多个上游渠道（base_url + key 组合）。
网关按权重在健康渠道间做加权随机选择；某渠道失败时进入冷却，冷却期内
不参与选择，到期自动恢复。全部渠道都在冷却时，选冷却最早结束的那家——
总得有人接电话。

无 channels 字段的旧 profile 视为单渠道：行为与历史版本逐字节一致，
所以这个模块对旧配置是零侵入的。
"""
from __future__ import annotations

import random
import threading
import time


# 渠道失败后的冷却秒数。60 秒是同类实现的常见量级：足够跨过一次上游抖动，
# 又不至于让一次 429 把渠道雪藏太久。
COOLDOWN_SECONDS = 60.0
# 渠道权重上限：防手滑写 99999 让加权随机退化成「永远第一家」。
MAX_WEIGHT = 100


class ChannelRouter:
    """一个 profile 的渠道选择器；实例挂在 Gateway 上，随网关同生命周期。

    冷却状态只活在内存里：重启即视为全部健康。跨进程持久化冷却没有意义
    ——渠道的好坏的半衰期远短于一次重启间隔。
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._cooldown_until: dict[int, float] = {}  # channel index -> monotonic deadline

    # ------------------------------------------------------------- selection
    @staticmethod
    def channels_of(profile: dict) -> list[dict]:
        """profile 的渠道列表；无 channels 的旧 profile 折算成单渠道。"""
        members = profile.get("_group_members")
        if members:
            return [dict(channel, _owner=member, _owner_index=index)
                    for member in members
                    for index, channel in enumerate(ChannelRouter.channels_of(member))]
        channels = profile.get("channels")
        if not isinstance(channels, list) or not channels:
            return [{
                "base_url": profile.get("base_url", ""),
                "api_key": profile.get("api_key", ""),
                "weight": 1,
                "enabled": True,
                "label": "",
            }]
        return channels

    def select(self, profile: dict, *, exclude: set[tuple[str, int]] | None = None) -> tuple[dict, int]:
        """按权重挑一个健康渠道，返回（注入了该渠道连接信息的 profile 副本, 渠道序号）。

        全部健康渠道都在冷却时，选冷却最早结束的——宁可等，也不能没有上游。
        exclude 仅限当前请求；即使所有渠道都在冷却，也不回选本轮已失败的渠道。
        调用方拿到的是副本，改 base_url/api_key 不会污染配置存储。
        """
        channels = self.channels_of(profile)
        eligible: list[tuple[int, dict, int]] = []
        cooling: list[tuple[float, int, dict]] = []
        now = time.monotonic()
        with self._lock:
            for index, channel in enumerate(channels):
                if not channel.get("enabled", True):
                    continue
                owner = channel.get("_owner", profile)
                owner_index = channel.get("_owner_index", index)
                if exclude and (owner.get("id", ""), owner_index) in exclude:
                    continue
                deadline = self._cooldown_until.get((owner["id"], owner_index), self._cooldown_until.get(index, 0.0)) if owner.get("id") else self._cooldown_until.get(index, 0.0)
                if deadline <= now:
                    eligible.append((index, channel, max(1, min(MAX_WEIGHT, int(channel.get("weight") or 1)))))
                else:
                    cooling.append((deadline, index, channel))
        if eligible:
            index, channel, weight = random.choices(
                [(i, c, w) for i, c, w in eligible], weights=[w for _i, _c, w in eligible])[0]
        elif cooling:
            cooling.sort()
            _deadline, index, channel = cooling[0]
        else:
            raise ValueError("没有启用的渠道。")
        owner = channel.get("_owner", profile)
        return dict(owner, base_url=channel.get("base_url") or owner.get("base_url", ""),
                    api_key=channel.get("api_key", "")), channel.get("_owner_index", index)

    # -------------------------------------------------------------- feedback
    def mark_failure(self, index: int, profile_id: str = "") -> float:
        """渠道失败：进入冷却。返回冷却剩余秒数（用于日志）。"""
        with self._lock:
            self._cooldown_until[(profile_id, index) if profile_id else index] = time.monotonic() + COOLDOWN_SECONDS
        return COOLDOWN_SECONDS

    def mark_success(self, index: int, profile_id: str = "") -> None:
        """渠道成功：清除冷却（若在）。"""
        with self._lock:
            self._cooldown_until.pop((profile_id, index) if profile_id else index, None)

    def cooling(self) -> dict[int, float]:
        """只读快照：仍在冷却中的渠道（UI/测试用）。"""
        now = time.monotonic()
        with self._lock:
            return {index: deadline for index, deadline in self._cooldown_until.items()
                    if deadline > now}
