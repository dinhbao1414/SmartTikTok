import sys

from PyQt6 import QtWidgets

from gui import Ui_MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = Ui_MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
