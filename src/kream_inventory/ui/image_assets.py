import os
import sys

import requests
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap


def get_window_icon():
    """Get the application window icon"""
    icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.icns")
    if sys.platform == "darwin":
        from PyQt6.QtGui import QGuiApplication
        return QIcon(icon_path)
    else:
        from PyQt6.QtWidgets import QApplication
        return QIcon(icon_path)

def get_logo_pixmap():
    """Get the application logo pixmap"""
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")
    return QPixmap(logo_path)

def get_navigation_icons():
    """Get left and right navigation icons"""
    left_icon_url = 'https://cdn-icons-png.flaticon.com/512/271/271220.png'
    right_icon_url = 'https://cdn-icons-png.flaticon.com/512/271/271228.png'
    
    # Left icon
    left_icon = QIcon()
    left_icon_data = requests.get(left_icon_url).content
    left_icon_pixmap = QPixmap()
    left_icon_pixmap.loadFromData(left_icon_data)
    left_icon.addPixmap(left_icon_pixmap)
    
    # Right icon
    right_icon = QIcon()
    right_icon_data = requests.get(right_icon_url).content
    right_icon_pixmap = QPixmap()
    right_icon_pixmap.loadFromData(right_icon_data)
    right_icon.addPixmap(right_icon_pixmap)
    
    return left_icon, right_icon

def get_button_size(screen):
    """Get the appropriate button size based on platform and screen DPI"""
    if sys.platform == 'win32' and screen.logicalDotsPerInch() > 96:
        return 100
    return 50 