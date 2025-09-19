import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = 'AT-CAD'
author = 'Alexander Tutubalin'
release = '0.1'

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
]

templates_path = ['_templates']
exclude_patterns = []

language = 'en'

# --- HTML Options ---
html_theme = 'sphinx_rtd_theme'  # современный стиль
html_static_path = ['_static']
html_css_files = ['custom.css']  # для своего стиля
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'titles_only': False
}
