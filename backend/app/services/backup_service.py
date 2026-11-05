"""数据备份服务：基于 SQLite 在线备份 API 生成一致性备份文件。"""

import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.schemas.backup_out import BackupOut


class BackupService:
    """数据备份服务：创建、列出与定位 SQLite 数据库备份。"""

    # 备份目录（backend/backups）
    BACKUP_DIR = Path(__file__).resolve().parents[2] / "backups"

    @staticmethod
    def _db_path() -> Path:
        """获取当前 SQLite 数据库文件路径。

        :return: 数据库文件绝对路径
        :raise ValueError: 非 SQLite 数据库
        """
        if not settings.database_url.startswith("sqlite:///"):
            raise ValueError("当前数据库不是 SQLite，暂不支持一键备份")
        return Path(settings.database_url.removeprefix("sqlite:///")).resolve()

    @staticmethod
    def list_backups() -> list[BackupOut]:
        """列出全部备份文件（按创建时间倒序）。

        :return: 备份文件列表
        """
        if not BackupService.BACKUP_DIR.exists():
            return []
        files = sorted(
            BackupService.BACKUP_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        return [
            BackupOut(
                name=f.name,
                size=f.stat().st_size,
                created_at=datetime.fromtimestamp(f.stat().st_mtime),
            )
            for f in files
        ]

    @staticmethod
    def create_backup() -> BackupOut:
        """创建一份数据库备份（使用 SQLite 在线备份，保证一致性）。

        :return: 新备份文件信息
        """
        BackupService.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        source = BackupService._db_path()
        if not source.exists():
            raise FileNotFoundError("数据库文件不存在，无法备份")
        name = f"pos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        target = BackupService.BACKUP_DIR / name
        # 使用 sqlite3 在线备份 API，避免直接复制正在写入的数据库
        with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
            src.backup(dst)
        stat = target.stat()
        return BackupOut(
            name=name, size=stat.st_size, created_at=datetime.fromtimestamp(stat.st_mtime)
        )

    @staticmethod
    def get_file(name: str) -> Path:
        """按文件名定位备份文件（仅允许备份目录内的 .db 文件）。

        :param name: 备份文件名
        :return: 备份文件路径
        :raise FileNotFoundError: 文件不存在或不合法
        """
        path = BackupService.BACKUP_DIR / Path(name).name
        if path.suffix != ".db" or not path.exists():
            raise FileNotFoundError("备份文件不存在")
        return path
