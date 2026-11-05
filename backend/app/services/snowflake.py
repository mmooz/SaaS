"""雪花 ID 生成器：为所有业务表提供全局唯一、趋势递增的 64 位主键。

结构：1 位符号(0) + 41 位毫秒时间戳 + 5 位数据中心 + 5 位机器 + 12 位序列。
同一毫秒内最多生成 4096 个 ID，进程内线程安全。
"""

import threading
import time

from app.config import settings


class Snowflake:
    """雪花算法生成器：按配置的机器位生成唯一 ID。"""

    # 起始时间戳（2020-01-01 00:00:00 UTC，单位毫秒）
    EPOCH = 1577836800000
    # 机器位与序列位的位数
    WORKER_BITS = 5
    DATACENTER_BITS = 5
    SEQUENCE_BITS = 12
    # 各字段最大值
    MAX_WORKER = (1 << WORKER_BITS) - 1
    MAX_DATACENTER = (1 << DATACENTER_BITS) - 1
    MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1
    # 左移位数
    WORKER_SHIFT = SEQUENCE_BITS
    DATACENTER_SHIFT = SEQUENCE_BITS + WORKER_BITS
    TIMESTAMP_SHIFT = SEQUENCE_BITS + WORKER_BITS + DATACENTER_BITS

    def __init__(self, worker_id: int = 1, datacenter_id: int = 1):
        """初始化生成器。

        :param worker_id: 机器 ID（0-31）
        :param datacenter_id: 数据中心 ID（0-31）
        """
        if not 0 <= worker_id <= self.MAX_WORKER:
            raise ValueError("机器 ID 超出范围(0-31)")
        if not 0 <= datacenter_id <= self.MAX_DATACENTER:
            raise ValueError("数据中心 ID 超出范围(0-31)")
        # 机器与数据中心标识
        self.worker_id = worker_id
        self.datacenter_id = datacenter_id
        # 最近一次生成 ID 的毫秒时间戳
        self.last_timestamp = -1
        # 当前毫秒内的序列号
        self.sequence = 0
        # 线程锁：保证多线程生成不重复
        self._lock = threading.Lock()

    def _now(self) -> int:
        """获取当前毫秒时间戳。

        :return: 当前时间戳（毫秒）
        """
        return int(time.time() * 1000)

    def _wait_next_millis(self, last_timestamp: int) -> int:
        """等待进入下一毫秒（同一毫秒内序列号已用尽）。

        :param last_timestamp: 当前已使用的时间戳
        :return: 新的毫秒时间戳
        """
        timestamp = self._now()
        while timestamp <= last_timestamp:
            timestamp = self._now()
        return timestamp

    def next_id(self) -> int:
        """生成下一个雪花 ID。

        :return: 64 位唯一 ID
        :raises RuntimeError: 系统时钟回拨导致无法继续生成
        """
        with self._lock:
            timestamp = self._now()
            # 时钟回拨：拒绝生成，避免产生重复 ID
            if timestamp < self.last_timestamp:
                raise RuntimeError("系统时钟回拨，暂时无法生成雪花 ID")
            if timestamp == self.last_timestamp:
                # 同一毫秒内序列号自增
                self.sequence = (self.sequence + 1) & self.MAX_SEQUENCE
                if self.sequence == 0:
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                # 进入新的一毫秒，序列号归零
                self.sequence = 0
            self.last_timestamp = timestamp
            return (
                ((timestamp - self.EPOCH) << self.TIMESTAMP_SHIFT)
                | (self.datacenter_id << self.DATACENTER_SHIFT)
                | (self.worker_id << self.WORKER_SHIFT)
                | self.sequence
            )


# 进程内单例生成器：机器位来自配置，便于多实例部署时区分
_snowflake = Snowflake(settings.snowflake_worker_id, settings.snowflake_datacenter_id)


def next_id() -> int:
    """生成新的雪花 ID（供模型默认主键与业务代码调用）。

    :return: 64 位唯一 ID
    """
    return _snowflake.next_id()
