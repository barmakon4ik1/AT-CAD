import os
import sys
from unittest.mock import MagicMock

# Добавляем путь к проекту (чтобы видеть E:\AT-CAD)
sys.path.insert(0, os.path.abspath('..'))

# Подмена (mock) модулей, которых нет в окружении
class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()

MOCK_MODULES = ["matplotlib", "at_construction", "config.at_config"]
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

# -- Project information -----------------------------------------------------
project = 'AT-CAD'
author = 'Alexander Tutubalin'
release = '0.1'

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",   # поддержка TODO
]

# включаем показ TODO в финальной документации
todo_include_todos = True

templates_path = ['_templates']
exclude_patterns = []

language = 'en'

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'

html_static_path = ['_static']  # если папки нет — лучше убрать

html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'titles_only': False,
}
