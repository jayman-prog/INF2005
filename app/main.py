# app/main.py
import sys
from PyQt6.QtWidgets import QApplication
from app.ui import MainWindow
from app.controllers import bind

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    bind(win)  # wire handlers
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
