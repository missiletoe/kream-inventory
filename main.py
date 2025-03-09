from PyQt6.QtWidgets import QApplication
import sys
from ui import UI

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ui = UI()
    ui.show()
    sys.exit(app.exec())