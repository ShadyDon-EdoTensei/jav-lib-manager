"""番号解析器 - 从文件名提取JAV番号"""

import re
from typing import Optional


class IDParser:
    """从文件名提取JAV番号"""

    # 常见番号格式:
    # ABC-123, ABC123, [ABC-123], ABC-123标题, [ABC-123]标题
    # 支持的厂商前缀: 通常是2-5个字母（大小写均可）
    # 数字部分: 通常是3-5位数字
    PATTERNS = [
        r'\[([A-Za-z]{2,5}-?\d{3,5})\]',           # [ABC-123] 或 [ABC123]
        r'([A-Za-z]{2,5}-\d{3,5})',                # ABC-123
        r'([A-Za-z]{2,5}\d{3,5})(?=[^0-9]|$)',     # ABC123 (后面不是数字或字符串结束)
    ]

    # 某些厂商的数字部分可能更长
    EXTENDED_PATTERNS = [
        r'([A-Za-z]{1,3}-?\d{5,6})',               # 1-3个字母 + 5-6位数字
        r'(\d{6}[A-Za-z]{1,2})',                   # 123456AB (某些反向格式)
    ]

    def __init__(self):
        """编译正则表达式"""
        self.compiled_patterns = [re.compile(p) for p in self.PATTERNS]
        self.extended_patterns = [re.compile(p) for p in self.EXTENDED_PATTERNS]

    def parse(self, filename: str) -> Optional[str]:
        """
        解析文件名，返回标准化的番号

        Args:
            filename: 文件名（不包含路径）

        Returns:
            标准化的番号 (如 "ABC-123") 或 None
        """
        if not filename:
            return None

        # 移除文件扩展名
        name = self._remove_extension(filename)

        # 检测 @ 符号格式：xxx@番号.mp4
        # 如果文件名包含 @，提取 @ 后面的部分
        if '@' in name:
            # 取 @ 后面的部分
            at_parts = name.split('@')
            if len(at_parts) >= 2:
                # 使用 @ 后面的部分进行解析
                name = at_parts[-1]

        # 先尝试标准模式
        for pattern in self.compiled_patterns:
            match = pattern.search(name)
            if match:
                code = match.group(1)
                return self.normalize(code)

        # 尝试扩展模式
        for pattern in self.extended_patterns:
            match = pattern.search(name)
            if match:
                code = match.group(1)
                return self.normalize(code)

        return None

    def normalize(self, code: str) -> str:
        """
        标准化番号格式

        将 "ABC123" 或 "abc-123" 转换为 "ABC-123"

        Args:
            code: 原始番号

        Returns:
            标准化后的番号
        """
        if not code:
            return code

        code = code.upper().strip()

        # 如果已有横杠，检查格式
        if '-' in code:
            parts = code.split('-')
            if len(parts) == 2:
                prefix, number = parts
                # 确保数字部分有前导零（至少3位）
                number = number.zfill(3)
                return f"{prefix}-{number}"
            return code

        # 没有横杠，需要插入
        # 找到字母和数字的分界点
        match = re.match(r'([A-Z]+)(\d+)', code)
        if match:
            prefix, number = match.groups()
            # 数字部分至少3位
            number = number.zfill(3)
            return f"{prefix}-{number}"

        return code

    def _remove_extension(self, filename: str) -> str:
        """移除文件扩展名和常见后缀"""
        # 处理常见的视频格式
        for ext in ['.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.m4v', '.ts', '.webm',
                    '.MP4', '.MKV', '.AVI', '.WMV', '.MOV', '.FLV', '.M4V', '.TS', '.WEBM']:
            if filename.endswith(ext):
                filename = filename[:-len(ext)]

        # 移除常见的编码和质量后缀（在扩展名之前）
        # 如 ipz-922.HD.mp4, PPPD-384.H265.mp4
        for suffix in ['.H265', '.h265', '.HEVC', '.hevc',
                       '.HD', '.FHD', '.4K', '.UHD', '.SD',
                       '.hd', '.fhd', '.4k', '.uhd', '.sd',
                       '.x264', '.X264', '.x265', '.X265']:
            if filename.endswith(suffix):
                filename = filename[:-len(suffix)]

        return filename

    def is_valid_code(self, code: str) -> bool:
        """
        检查是否是有效的番号格式

        Args:
            code: 番号

        Returns:
            是否有效
        """
        if not code:
            return False

        # 标准格式: 字母-数字
        pattern = re.compile(r'^[A-Z]{2,5}-\d{3,5}$')
        return bool(pattern.match(code))


# 单例实例
_parser_instance = None

def get_parser() -> IDParser:
    """获取解析器单例"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = IDParser()
    return _parser_instance
