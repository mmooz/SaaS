/**
 * 雪花 ID 生成器（前端离线使用）
 *
 * 结构与后端一致：41 位毫秒时间戳 + 5 位数据中心 + 5 位机器 + 12 位序列。
 * JavaScript Number 无法安全表示 64 位整数，因此全程使用 BigInt 计算并以字符串返回。
 */
export class Snowflake {
  // 起始时间戳（2020-01-01 00:00:00 UTC，单位毫秒）
  static EPOCH = 1577836800000n
  // 机器位与序列位的位数
  static WORKER_BITS = 5n
  static DATACENTER_BITS = 5n
  static SEQUENCE_BITS = 12n
  // 各字段最大值
  static MAX_WORKER = (1n << Snowflake.WORKER_BITS) - 1n
  static MAX_DATACENTER = (1n << Snowflake.DATACENTER_BITS) - 1n
  static MAX_SEQUENCE = (1n << Snowflake.SEQUENCE_BITS) - 1n
  // 各字段左移位数
  static WORKER_SHIFT = Snowflake.SEQUENCE_BITS
  static DATACENTER_SHIFT = Snowflake.SEQUENCE_BITS + Snowflake.WORKER_BITS
  static TIMESTAMP_SHIFT =
    Snowflake.SEQUENCE_BITS + Snowflake.WORKER_BITS + Snowflake.DATACENTER_BITS

  /**
   * 初始化离线 ID 生成器
   * @param {number} workerId 机器 ID（0-31），桌面端固定使用 2 以区分后端
   * @param {number} datacenterId 数据中心 ID（0-31）
   */
  constructor(workerId = 2, datacenterId = 1) {
    // 机器与数据中心标识（BigInt）
    this.workerId = BigInt(workerId)
    this.datacenterId = BigInt(datacenterId)
    // 最近一次生成 ID 的毫秒时间戳
    this.lastTimestamp = -1n
    // 当前毫秒内的序列号
    this.sequence = 0n
  }

  /**
   * 获取当前毫秒时间戳
   * @returns {bigint} 毫秒时间戳
   */
  now() {
    return BigInt(Date.now())
  }

  /**
   * 生成下一个雪花 ID
   * @returns {string} 唯一 ID（字符串形式，避免精度丢失）
   */
  nextId() {
    let timestamp = this.now()
    // 时钟回拨时沿用最近时间戳，避免生成重复 ID
    if (timestamp < this.lastTimestamp) {
      timestamp = this.lastTimestamp
    }
    if (timestamp === this.lastTimestamp) {
      // 同一毫秒内序列号自增，用尽后等待下一毫秒
      this.sequence = (this.sequence + 1n) & Snowflake.MAX_SEQUENCE
      if (this.sequence === 0n) {
        while (timestamp <= this.lastTimestamp) {
          timestamp = this.now()
        }
      }
    } else {
      // 进入新的一毫秒，序列号归零
      this.sequence = 0n
    }
    this.lastTimestamp = timestamp
    const id =
      ((timestamp - Snowflake.EPOCH) << Snowflake.TIMESTAMP_SHIFT) |
      (this.datacenterId << Snowflake.DATACENTER_SHIFT) |
      (this.workerId << Snowflake.WORKER_SHIFT) |
      this.sequence
    return id.toString()
  }
}

// 桌面端共享的离线 ID 生成器实例
export const offlineSnowflake = new Snowflake()
