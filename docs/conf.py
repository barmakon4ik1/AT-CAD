import os
import sys
import sphinx_rtd_theme
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


# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

html_static_path = ['_static']
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'titles_only': False
}
