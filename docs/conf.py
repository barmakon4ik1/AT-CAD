# ============================================================
# Sphinx configuration for AT-CAD
# ============================================================

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

# ------------------------------------------------------------
# Пути проекта
# ------------------------------------------------------------

# docs/
#   conf.py
# project_root/
PROJECT_ROOT = os.path.abspath("..")
sys.path.insert(0, PROJECT_ROOT)

# ------------------------------------------------------------
# Mock внешних / недоступных модулей
# ------------------------------------------------------------

class _Mock(MagicMock):
    """Безопасный mock для отсутствующих библиотек."""
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()

# Модули, которые невозможно импортировать вне AutoCAD / runtime
MOCK_MODULES = [
    "matplotlib",
    "pythoncom",
    "win32com",
    "win32com.client",
]

for module_name in MOCK_MODULES:
    sys.modules[module_name] = _Mock()

# ------------------------------------------------------------
# Project information
# ------------------------------------------------------------

project = "AT-CAD"
author = "Alexander Tutubalin"
release = "0.1"
version = release

# ------------------------------------------------------------
# General configuration
# ------------------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
]

autosummary_generate = True

napoleon_google_docstring = True
napoleon_numpy_docstring = False

todo_include_todos = True

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "engineering_handbook/**",
]


# ------------------------------------------------------------
# Autodoc behaviour
# ------------------------------------------------------------

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "member-order": "bysource",
}

autodoc_typehints = "description"
autodoc_mock_imports = MOCK_MODULES

# ------------------------------------------------------------
# HTML output
# ------------------------------------------------------------

html_theme = "sphinx_rtd_theme"

html_static_path = ["_static"]

html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "titles_only": False,
}

# ------------------------------------------------------------
# Misc
# ------------------------------------------------------------

# Убирает предупреждение, если файл не импортируется
suppress_warnings = [
    "autodoc.import_object",
]

# Делает вывод ошибок autodoc менее шумным
nitpicky = False

# ------------------------------------------------------------
# Internationalization
# ------------------------------------------------------------

language = "en"

locale_dirs = ["locales"]
gettext_compact = False
