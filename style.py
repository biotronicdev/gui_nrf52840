# ==========================
# UI STYLE
# ==========================

STYLE = """
QWidget {
    background-color: #ffffff;
    font-family: Arial;
    color: #1f1f1f;
}

QMainWindow {
    background-color: #ffffff;
}

QTabWidget::pane {
    border: 0px;
    top: -1px;
}

QTabBar::tab {
    background: #e9edf5;
    color: #000000;
    padding: 10px 22px;
    border-radius: 14px;
    margin: 6px 6px 8px 0px;
    min-width: 110px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background: #72a2ff;
    color: #000000;
}

QTabBar::tab:hover {
    background: #dbe7ff;
    color: #000000;
}

QLineEdit, QTextEdit, QDateEdit, QComboBox, QDoubleSpinBox, QListWidget {
    border: 1px solid #d8dce3;
    border-radius: 8px;
    padding: 6px;
    background: #ffffff;
    color: #1f1f1f;
}

QPushButton {
    background-color: #4f8cff;
    color: white;
    border-radius: 10px;
    padding: 8px 12px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #3d7df2;
}

QPushButton:disabled {
    background-color: #b7cdfc;
    color: #ffffff;
}

QGroupBox {
    border: 1px solid #dddddd;
    border-radius: 10px;
    margin-top: 10px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px 0 6px;
    color: #333333;
}
"""