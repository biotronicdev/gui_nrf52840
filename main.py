import sys
from PyQt6.QtWidgets import QApplication

from style import STYLE
from interf_emg import VentanaPrincipal

if __name__ == "__main__":
    app = QApplication(sys.argv)

    ventana = VentanaPrincipal()
    ventana.setStyleSheet(STYLE)

    ventana.show()

    sys.exit(app.exec())