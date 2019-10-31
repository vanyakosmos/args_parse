import sys
from pathlib import Path

import argser

root = Path(__file__).parents[2]
package_dir = root / 'argser'
sys.path.insert(0, str(package_dir))

# -- Project information -----------------------------------------------------

project = 'argser'
copyright = '2019, Bachynin Ivan'
author = 'Bachynin Ivan'

# The full version, including alpha/beta/rc tags.
release = argser.__version__

# -- General configuration ---------------------------------------------------

master_doc = 'index'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinxcontrib.apidoc',
    'm2r',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'
pygments_style = 'friendly'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_context = {
    "display_github": True,
    "github_user": "vanyakosmos",
    "github_repo": "argser",
    "github_version": "master",
}

# -- Extensions --------------------------------------------------------------

apidoc_module_dir = str(package_dir)
apidoc_output_dir = 'modules'
apidoc_excluded_paths = [
    'consts.py',
    'logging.py',
]
apidoc_separate_modules = True
apidoc_toc_file = False
