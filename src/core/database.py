"""数据库操作模块"""

import sqlite3
import os
import logging
from datetime import date
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .models import VideoRecord, VideoMetadata, Actress, SourceType

logger = logging.getLogger(__name__)


class Database:
    """数据库操作封装"""

    def __init__(self, db_path: str):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_database_exists()

    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典形式的结果
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_database_exists(self):
        """确保数据库和表结构存在"""
        if not os.path.exists(self.db_path):
            # 创建数据库目录
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with self._get_connection() as conn:
            self._create_tables(conn)
            self._run_migrations(conn)

    def _create_tables(self, conn: sqlite3.Connection):
        """创建数据库表"""
        cursor = conn.cursor()

        # 视频表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                title TEXT,
                cover_path TEXT,
                cover_url TEXT,
                release_date DATE,
                studio TEXT,
                label TEXT,
                series TEXT,
                duration INTEGER,
                file_path TEXT UNIQUE,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT
            )
        """)

        # 演员表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS actresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                name_ja TEXT,
                avatar_path TEXT,
                UNIQUE(name)
            )
        """)

        # 视频-演员关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_actresses (
                video_id TEXT,
                actress_id INTEGER,
                PRIMARY KEY (video_id, actress_id),
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
                FOREIGN KEY (actress_id) REFERENCES actresses(id) ON DELETE CASCADE
            )
        """)

        # 标签表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                UNIQUE(name, category)
            )
        """)

        # 视频-标签关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_tags (
                video_id TEXT,
                tag_id INTEGER,
                PRIMARY KEY (video_id, tag_id),
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_title
            ON videos(title COLLATE NOCASE)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_studio
            ON videos(studio)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_videos_release_date
            ON videos(release_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_video_actresses_actress
            ON video_actresses(actress_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_video_tags_tag
            ON video_tags(tag_id)
        """)

    def _run_migrations(self, conn: sqlite3.Connection):
        """运行数据库迁移"""
        cursor = conn.cursor()

        # 检查并添加 cover_url 列（如果不存在）
        cursor.execute("PRAGMA table_info(videos)")
        video_columns = {row['name'] for row in cursor.fetchall()}

        if 'cover_url' not in video_columns:
            logger.info("执行迁移：添加 cover_url 列")
            cursor.execute("ALTER TABLE videos ADD COLUMN cover_url TEXT")
            conn.commit()

    def exists(self, code: str) -> bool:
        """检查番号是否已存在"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM videos WHERE id = ?", (code,))
            return cursor.fetchone() is not None

    def add_video(self, metadata: VideoMetadata, file_path: str, file_size: int) -> bool:
        """
        添加视频记录

        Args:
            metadata: 视频元数据
            file_path: 本地文件路径
            file_size: 文件大小

        Returns:
            是否成功添加
        """
        if self.exists(metadata.id):
            return self._update_video(metadata, file_path, file_size)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 插入视频记录
            release_date_str = metadata.release_date.isoformat() if metadata.release_date else None
            cursor.execute("""
                INSERT INTO videos (
                    id, title, cover_path, cover_url, release_date, studio, label,
                    series, duration, file_path, file_size, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.id,
                metadata.title,
                None,  # cover_path 将在下载封面后更新
                metadata.cover_url,  # 保存URL供下载使用
                release_date_str,
                metadata.studio,
                metadata.label,
                metadata.series,
                metadata.duration,
                file_path,
                file_size,
                metadata.source or SourceType.LOCAL
            ))

            # 添加演员（使用 INSERT OR IGNORE 避免重复）
            for actress_name in metadata.actresses:
                actress_id = self._get_or_create_actress(cursor, actress_name)
                cursor.execute(
                    "INSERT OR IGNORE INTO video_actresses (video_id, actress_id) VALUES (?, ?)",
                    (metadata.id, actress_id)
                )

            # 添加标签（使用 INSERT OR IGNORE 避免重复）
            for genre in metadata.genres:
                tag_id = self._get_or_create_tag(cursor, genre)
                cursor.execute(
                    "INSERT OR IGNORE INTO video_tags (video_id, tag_id) VALUES (?, ?)",
                    (metadata.id, tag_id)
                )

            return True

    def _update_video(self, metadata: VideoMetadata, file_path: str, file_size: int) -> bool:
        """更新已存在的视频记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            release_date_str = metadata.release_date.isoformat() if metadata.release_date else None
            cursor.execute("""
                UPDATE videos SET
                    title = ?, release_date = ?, studio = ?, label = ?,
                    series = ?, duration = ?, file_path = ?, file_size = ?,
                    cover_url = ?, source = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                metadata.title,
                release_date_str,
                metadata.studio,
                metadata.label,
                metadata.series,
                metadata.duration,
                file_path,
                file_size,
                metadata.cover_url,
                metadata.source or SourceType.LOCAL,
                metadata.id
            ))

            # 更新演员关联（简化处理：删除后重建）
            cursor.execute("DELETE FROM video_actresses WHERE video_id = ?", (metadata.id,))
            for actress_name in metadata.actresses:
                actress_id = self._get_or_create_actress(cursor, actress_name)
                cursor.execute(
                    "INSERT OR IGNORE INTO video_actresses (video_id, actress_id) VALUES (?, ?)",
                    (metadata.id, actress_id)
                )

            # 更新标签关联
            cursor.execute("DELETE FROM video_tags WHERE video_id = ?", (metadata.id,))
            for genre in metadata.genres:
                tag_id = self._get_or_create_tag(cursor, genre)
                cursor.execute(
                    "INSERT OR IGNORE INTO video_tags (video_id, tag_id) VALUES (?, ?)",
                    (metadata.id, tag_id)
                )

            return True

    def _get_or_create_actress(self, cursor: sqlite3.Cursor, name: str) -> int:
        """获取或创建演员记录，返回ID"""
        cursor.execute("SELECT id FROM actresses WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return row[0]

        cursor.execute("INSERT INTO actresses (name) VALUES (?)", (name,))
        return cursor.lastrowid

    def update_actress_avatar(self, name: str, avatar_path: str) -> bool:
        """更新演员头像路径"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE actresses SET avatar_path = ? WHERE name = ?",
                (avatar_path, name)
            )
            return cursor.rowcount > 0

    def get_actress_avatar(self, name: str) -> Optional[str]:
        """获取演员头像路径"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT avatar_path FROM actresses WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row['avatar_path'] if row else None

    def _get_or_create_tag(self, cursor: sqlite3.Cursor, name: str, category: str = None) -> int:
        """获取或创建标签记录，返回ID"""
        cursor.execute("SELECT id FROM tags WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return row[0]

        cursor.execute("INSERT INTO tags (name, category) VALUES (?, ?)", (name, category))
        return cursor.lastrowid

    def get_video(self, code: str) -> Optional[VideoRecord]:
        """根据番号获取视频记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM videos WHERE id = ?
            """, (code,))
            row = cursor.fetchone()
            if not row:
                return None

            return self._row_to_video_record(conn, row)

    def _row_to_video_record(self, conn: sqlite3.Connection, row: sqlite3.Row) -> VideoRecord:
        """将数据库行转换为VideoRecord对象"""
        video = VideoRecord(
            id=row['id'],
            title=row['title'],
            cover_path=row['cover_path'],
            cover_url=row['cover_url'] if 'cover_url' in row.keys() else None,
            release_date=date.fromisoformat(row['release_date']) if row['release_date'] else None,
            studio=row['studio'],
            label=row['label'],
            series=row['series'],
            duration=row['duration'],
            file_path=row['file_path'],
            file_size=row['file_size'],
            source=row['source']
        )

        # 获取演员
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.* FROM actresses a
            JOIN video_actresses va ON a.id = va.actress_id
            WHERE va.video_id = ?
        """, (row['id'],))
        for actress_row in cursor.fetchall():
            video.actresses.append(Actress(
                name=actress_row['name'],
                name_ja=actress_row['name_ja'] if 'name_ja' in actress_row.keys() else None,
                avatar_path=actress_row['avatar_path'] if 'avatar_path' in actress_row.keys() else None
            ))

        # 获取标签
        cursor.execute("""
            SELECT t.name FROM tags t
            JOIN video_tags vt ON t.id = vt.tag_id
            WHERE vt.video_id = ?
        """, (row['id'],))
        video.tags = [r[0] for r in cursor.fetchall()]

        return video

    def search(
        self,
        keyword: str = None,
        actress: str = None,
        tag: str = None,
        studio: str = None,
        series: str = None,
        sort_by: str = "release_date",
        sort_order: str = "DESC",
        limit: int = 100,
        offset: int = 0
    ) -> List[VideoRecord]:
        """
        搜索视频

        Args:
            keyword: 关键词（搜索番号和标题）
            actress: 演员名过滤
            tag: 标签过滤
            studio: 片商过滤
            series: 系列过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            视频记录列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 构建查询
            query = "SELECT DISTINCT v.* FROM videos v"
            params = []
            conditions = []

            # 需要JOIN的情况
            if actress:
                query += " JOIN video_actresses va ON v.id = va.video_id"
                query += " JOIN actresses a ON va.actress_id = a.id"
            if tag:
                query += " JOIN video_tags vt ON v.id = vt.video_id"
                query += " JOIN tags t ON vt.tag_id = t.id"

            # WHERE条件
            if keyword:
                conditions.append("(v.id LIKE ? OR v.title LIKE ?)")
                params.extend([f"%{keyword}%", f"%{keyword}%"])

            if actress:
                conditions.append("a.name LIKE ?")
                params.append(f"%{actress}%")

            if tag:
                conditions.append("t.name = ?")
                params.append(tag)

            if studio:
                conditions.append("v.studio = ?")
                params.append(studio)

            if series:
                conditions.append("v.series = ?")
                params.append(series)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            # 排序和分页 - 优先显示有封面的视频，然后按指定字段排序
            sort_column = {
                "release_date": "v.release_date",
                "created_at": "v.created_at",
                "id": "v.id",
            }.get(sort_by, "v.release_date")

            query += f" ORDER BY CASE WHEN v.cover_path IS NOT NULL THEN 0 ELSE 1 END, {sort_column} {sort_order} LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)

            results = []
            for row in cursor.fetchall():
                results.append(self._row_to_video_record(conn, row))

            return results

    def get_all_actresses(self) -> List[str]:
        """获取所有演员名"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT name FROM actresses ORDER BY name")
            return [row[0] for row in cursor.fetchall()]

    def get_all_tags(self) -> List[str]:
        """获取所有标签"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT name FROM tags ORDER BY name")
            return [row[0] for row in cursor.fetchall()]

    def get_all_studios(self) -> List[str]:
        """获取所有片商"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT studio FROM videos WHERE studio IS NOT NULL ORDER BY studio")
            return [row[0] for row in cursor.fetchall()]

    def get_all_series(self) -> List[str]:
        """获取所有系列"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT series FROM videos WHERE series IS NOT NULL ORDER BY series")
            return [row[0] for row in cursor.fetchall()]

    def get_videos_without_covers(self, limit: int = 100) -> List[VideoRecord]:
        """获取没有封面的视频（包括封面文件不存在的情况）

        Args:
            limit: 返回数量限制

        Returns:
            没有封面的视频列表
        """
        import os

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 首先查找 cover_path 为空的视频
            cursor.execute("""
                SELECT v.* FROM videos v
                WHERE v.cover_path IS NULL OR v.cover_path = ''
                ORDER BY v.created_at DESC
                LIMIT ?
            """, (limit,))

            results = []
            for row in cursor.fetchall():
                video = self._row_to_video_record(conn, row)
                results.append(video)

            # 如果还不够，查找 cover_path 有值但文件不存在的视频
            if len(results) < limit:
                remaining = limit - len(results)
                cursor.execute("""
                    SELECT v.* FROM videos v
                    WHERE v.cover_path IS NOT NULL AND v.cover_path != ''
                    ORDER BY v.created_at DESC
                    LIMIT ?
                """, (remaining * 10,))  # 获取更多，因为需要过滤

                for row in cursor.fetchall():
                    if len(results) >= limit:
                        break
                    video = self._row_to_video_record(conn, row)
                    # 检查文件是否存在
                    if video.cover_path and not os.path.exists(video.cover_path):
                        results.append(video)

            return results

    def get_videos_missing_release_date(self, limit: int = 1000, offset: int = 0) -> List[str]:
        """获取发行日期缺失的视频 ID 列表。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id FROM videos
                WHERE release_date IS NULL OR release_date = ''
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            return [row["id"] for row in cursor.fetchall()]

    def get_videos_needing_metadata_refresh(self, limit: int = 1000, offset: int = 0) -> List[str]:
        """获取疑似元数据不完整或假命中的视频 ID 列表。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT v.id
                FROM videos v
                LEFT JOIN video_actresses va ON v.id = va.video_id
                GROUP BY v.id
                HAVING
                    COALESCE(v.title, '') = v.id
                    OR (COALESCE(v.cover_url, '') = '' AND COALESCE(v.cover_path, '') = '')
                    OR COUNT(va.actress_id) = 0
                    OR COALESCE(v.studio, '') LIKE '%磁鏈搜索引擎%'
                    OR COALESCE(v.studio, '') LIKE '%關注演員%'
                    OR COALESCE(v.studio, '') LIKE '%功能增強%'
                    OR COALESCE(v.studio, '') LIKE '%Attention Required%'
                    OR COALESCE(v.studio, '') LIKE '%Cloudflare%'
                ORDER BY MAX(v.updated_at) DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            return [row["id"] for row in cursor.fetchall()]

    def update_release_date_if_missing(self, video_id: str, release_date: date) -> bool:
        """仅在当前发行日期为空时更新。"""
        if release_date is None:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE videos
                SET release_date = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND (release_date IS NULL OR release_date = '')
                """,
                (release_date.isoformat(), video_id)
            )
            return cursor.rowcount > 0

    def count_videos(self) -> int:
        """获取视频总数"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM videos")
            return cursor.fetchone()[0]

    def update_file_path(self, video_id: str, new_path: str) -> bool:
        """更新视频文件路径"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE videos SET file_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_path, video_id))
            return cursor.rowcount > 0

    def get_videos_with_missing_files(self) -> List['VideoRecord']:
        """获取文件路径不存在的视频"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos WHERE file_path IS NOT NULL")
            results = []
            for row in cursor.fetchall():
                if not os.path.exists(row['file_path']):
                    results.append(self._row_to_video_record(conn, row))
            return results

    def update_cover_path(self, code: str, cover_path: str) -> bool:
        """更新封面路径"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE videos SET cover_path = ? WHERE id = ?
            """, (cover_path, code))
            return cursor.rowcount > 0

    def delete_video(self, code: str) -> bool:
        """
        删除视频记录

        Args:
            code: 番号

        Returns:
            是否成功删除
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 先获取封面路径，用于删除封面文件
            cursor.execute("SELECT cover_path FROM videos WHERE id = ?", (code,))
            row = cursor.fetchone()
            cover_path = row['cover_path'] if row else None

            # 删除视频记录（由于有外键约束 ON DELETE CASCADE，关联的演员和标签会自动删除）
            cursor.execute("DELETE FROM videos WHERE id = ?", (code,))
            deleted = cursor.rowcount > 0

            if deleted and cover_path:
                # 尝试删除封面文件
                try:
                    if os.path.exists(cover_path):
                        os.remove(cover_path)
                        logger.info(f"已删除封面文件: {cover_path}")
                except Exception as e:
                    logger.warning(f"删除封面文件失败: {e}")

            return deleted

    def delete_videos(self, codes: list[str]) -> int:
        """
        批量删除视频记录

        Args:
            codes: 番号列表

        Returns:
            成功删除的数量
        """
        deleted_count = 0
        for code in codes:
            if self.delete_video(code):
                deleted_count += 1
        return deleted_count

    def update_video_metadata(self, video_id: str, metadata: VideoMetadata) -> bool:
        """更新视频元数据（仅更新非空字段）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 获取当前记录
            cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
            row = cursor.fetchone()
            if not row:
                return False

            # 更新封面URL和其他字段
            release_date_str = metadata.release_date.isoformat() if metadata.release_date else None
            cursor.execute("""
                UPDATE videos SET
                    title = COALESCE(?, title),
                    cover_url = COALESCE(?, cover_url),
                    release_date = COALESCE(?, release_date),
                    studio = COALESCE(?, studio),
                    label = COALESCE(?, label),
                    series = COALESCE(?, series),
                    duration = COALESCE(?, duration),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                metadata.title,
                metadata.cover_url,
                release_date_str,
                metadata.studio,
                metadata.label,
                metadata.series,
                metadata.duration,
                video_id
            ))

            # 更新演员关联（如果有的话）
            if metadata.actresses:
                cursor.execute("DELETE FROM video_actresses WHERE video_id = ?", (video_id,))
                for actress_name in metadata.actresses:
                    actress_id = self._get_or_create_actress(cursor, actress_name)
                    cursor.execute(
                        "INSERT INTO video_actresses (video_id, actress_id) VALUES (?, ?)",
                        (video_id, actress_id)
                    )

            # 更新标签关联（如果有的话）
            if metadata.genres:
                cursor.execute("DELETE FROM video_tags WHERE video_id = ?", (video_id,))
                for genre in metadata.genres:
                    tag_id = self._get_or_create_tag(cursor, genre)
                    cursor.execute(
                        "INSERT INTO video_tags (video_id, tag_id) VALUES (?, ?)",
                        (video_id, tag_id)
                    )

            return True

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {}

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 视频总数
            cursor.execute("SELECT COUNT(*) FROM videos")
            stats['total_videos'] = cursor.fetchone()[0]

            # 有封面的视频数
            cursor.execute("SELECT COUNT(*) FROM videos WHERE cover_path IS NOT NULL")
            stats['with_cover'] = cursor.fetchone()[0]

            # 演员总数
            cursor.execute("SELECT COUNT(*) FROM actresses")
            stats['total_actresses'] = cursor.fetchone()[0]

            # 标签总数
            cursor.execute("SELECT COUNT(*) FROM tags")
            stats['total_tags'] = cursor.fetchone()[0]

            # 片商总数
            cursor.execute("SELECT COUNT(DISTINCT studio) FROM videos WHERE studio IS NOT NULL")
            stats['total_studios'] = cursor.fetchone()[0]

            # 最近添加的视频
            cursor.execute("""
                SELECT id, title, created_at FROM videos
                ORDER BY created_at DESC LIMIT 5
            """)
            stats['recent_videos'] = cursor.fetchall()

        return stats

    def validate(self) -> List[str]:
        """验证数据库完整性，返回问题列表"""
        issues = []

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 检查孤立的视频-演员关联
            cursor.execute("""
                SELECT COUNT(*) FROM video_actresses va
                LEFT JOIN videos v ON va.video_id = v.id
                WHERE v.id IS NULL
            """)
            orphan_actresses = cursor.fetchone()[0]
            if orphan_actresses > 0:
                issues.append(f"发现 {orphan_actresses} 个孤立的视频-演员关联")

            # 检查孤立的视频-标签关联
            cursor.execute("""
                SELECT COUNT(*) FROM video_tags vt
                LEFT JOIN videos v ON vt.video_id = v.id
                WHERE v.id IS NULL
            """)
            orphan_tags = cursor.fetchone()[0]
            if orphan_tags > 0:
                issues.append(f"发现 {orphan_tags} 个孤立的视频-标签关联")

            # 检查缺失的文件
            cursor.execute("SELECT id, file_path FROM videos")
            missing_files = []
            for row in cursor.fetchall():
                if not os.path.exists(row[1]):
                    missing_files.append(row[0])

            if missing_files:
                issues.append(f"发现 {len(missing_files)} 个视频文件不存在: {', '.join(missing_files[:10])}")

        return issues

    def clear_all(self) -> bool:
        """清空所有数据"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 按依赖顺序删除
            cursor.execute("DELETE FROM video_tags")
            cursor.execute("DELETE FROM video_actresses")
            cursor.execute("DELETE FROM tags")
            cursor.execute("DELETE FROM actresses")
            cursor.execute("DELETE FROM videos")
            return True
