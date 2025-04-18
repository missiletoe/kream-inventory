"""UI components for the KREAM Inventory Management Application.

This package contains all the user interface components for the KREAM inventory
management system.
"""

from .main_window import MainWindow
from .login_popup import LoginPopup
from .image_assets import (
    get_button_size,
    get_logo_pixmap,
    get_navigation_icons,
    get_window_icon
)

__all__ = [
    'MainWindow',
    'LoginPopup',
    'get_button_size',
    'get_logo_pixmap',
    'get_navigation_icons',
    'get_window_icon'
]
