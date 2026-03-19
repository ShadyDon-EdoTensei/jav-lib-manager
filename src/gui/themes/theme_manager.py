"""主题管理器 - 基于 Qt-Material"""

from qt_material import apply_stylesheet


class ThemeManager:
    """主题管理器"""

    THEMES = {
        'dark_amber': 'dark_amber.xml',
        'dark_blue': 'dark_blue.xml',
        'dark_cyan': 'dark_cyan.xml',
        'dark_lightgreen': 'dark_lightgreen.xml',
        'dark_pink': 'dark_pink.xml',
        'dark_purple': 'dark_purple.xml',
        'dark_red': 'dark_red.xml',
        'dark_teal': 'dark_teal.xml',
        'dark_yellow': 'dark_yellow.xml',
        'light_amber': 'light_amber.xml',
        'light_blue': 'light_blue.xml',
        'light_cyan': 'light_cyan.xml',
        'light_lightgreen': 'light_lightgreen.xml',
        'light_pink': 'light_pink.xml',
        'light_purple': 'light_purple.xml',
        'light_red': 'light_red.xml',
        'light_teal': 'light_teal.xml',
        'light_yellow': 'light_yellow.xml',
    }

    def apply_theme(self, app, theme_name: str = 'dark_amber'):
        """应用主题

        Args:
            app: QApplication 实例
            theme_name: 主题名称，默认 'dark_amber'
        """
        theme = self.THEMES.get(theme_name, 'dark_amber.xml')
        apply_stylesheet(app, theme=theme)

    def get_themes(self):
        """获取可用主题列表"""
        return list(self.THEMES.keys())

    def get_theme_info(self, theme_name: str) -> dict:
        """获取主题信息"""
        theme_file = self.THEMES.get(theme_name)
        if not theme_file:
            return None

        is_dark = theme_file.startswith('dark_')
        color = theme_file.replace('.xml', '').replace('dark_', '').replace('light_', '')

        color_names = {
            'amber': '琥珀色',
            'blue': '蓝色',
            'cyan': '青色',
            'lightgreen': '绿色',
            'pink': '粉色',
            'purple': '紫色',
            'red': '红色',
            'teal': '蓝绿色',
            'yellow': '黄色',
        }

        return {
            'name': theme_name,
            'file': theme_file,
            'type': '深色' if is_dark else '浅色',
            'color': color_names.get(color, color),
        }
