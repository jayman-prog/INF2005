# app/ui.py
from PyQt6 import QtWidgets, QtCore, QtGui

class DropArea(QtWidgets.QFrame):
    fileDropped = QtCore.pyqtSignal(str)
    def __init__(self, text):
        super().__init__()
        self.setAcceptDrops(True)
        self.setStyleSheet("QFrame{border:2px dashed #888; border-radius:8px;}")
        self.label = QtWidgets.QLabel(text)
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.label)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.fileDropped.emit(path)
        e.acceptProposedAction()

class PixmapBox(QtWidgets.QGroupBox):
    def __init__(self, title):
        super().__init__(title)
        self.label = QtWidgets.QLabel()
        self.label.setMinimumSize(420, 260)
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.label)
    def setPixmap(self, pm: QtGui.QPixmap):
        self.label.setPixmap(pm)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INF2005 Stego LSB")
        self.resize(1100, 700)

        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        # ===================== ENCODE TAB =====================
        enc = QtWidgets.QWidget()
        enc_layout = QtWidgets.QGridLayout(enc)

        self.encodeCoverDrop = DropArea("Drop COVER (BMP/PNG/JPG or WAV)")
        self.encodePayloadDrop = DropArea("Drop PAYLOAD (any file)")

        self.lsbSpinEnc = QtWidgets.QSpinBox(); self.lsbSpinEnc.setRange(1,8); self.lsbSpinEnc.setValue(2)
        self.keySpinEnc = QtWidgets.QSpinBox(); self.keySpinEnc.setRange(0, 2_000_000_000); self.keySpinEnc.setValue(1234)
        self.capacityLblEnc = QtWidgets.QLabel("Capacity: -")
        self.encodeBtn = QtWidgets.QPushButton("Encode → Save Stego")

        encCtrls = QtWidgets.QFormLayout()
        encCtrls.addRow("LSBs:", self.lsbSpinEnc)
        encCtrls.addRow("Key:", self.keySpinEnc)
        encCtrls.addRow(self.capacityLblEnc)

        leftEnc = QtWidgets.QVBoxLayout()
        leftEnc.addWidget(self.encodeCoverDrop, 3)
        leftEnc.addLayout(encCtrls)
        leftEnc.addWidget(self.encodePayloadDrop, 3)
        leftEnc.addWidget(self.encodeBtn)
        leftEncW = QtWidgets.QWidget(); leftEncW.setLayout(leftEnc)

        self.imagePreviewEnc = PixmapBox("Preview (Cover/Stego)")
        self.diffPreviewEnc = PixmapBox("Difference Map")
        rightEnc = QtWidgets.QVBoxLayout()
        rightEnc.addWidget(self.imagePreviewEnc, 1)
        rightEnc.addWidget(self.diffPreviewEnc, 1)
        rightEncW = QtWidgets.QWidget(); rightEncW.setLayout(rightEnc)

        enc_layout.addWidget(leftEncW, 0, 0)
        enc_layout.addWidget(rightEncW, 0, 1)

        # ===================== DECODE TAB =====================
        dec = QtWidgets.QWidget()
        dec_layout = QtWidgets.QGridLayout(dec)

        self.decodeStegoDrop = DropArea("Drop STEGO (PNG/BMP or WAV)")
        self.lsbSpinDec = QtWidgets.QSpinBox(); self.lsbSpinDec.setRange(1,8); self.lsbSpinDec.setValue(2)
        self.keySpinDec = QtWidgets.QSpinBox(); self.keySpinDec.setRange(0, 2_000_000_000); self.keySpinDec.setValue(1234)
        self.decodeBtn = QtWidgets.QPushButton("Decode from Stego")

        decCtrls = QtWidgets.QFormLayout()
        decCtrls.addRow("LSBs:", self.lsbSpinDec)
        decCtrls.addRow("Key:", self.keySpinDec)

        leftDec = QtWidgets.QVBoxLayout()
        leftDec.addWidget(self.decodeStegoDrop, 3)
        leftDec.addLayout(decCtrls)
        leftDec.addWidget(self.decodeBtn)
        leftDecW = QtWidgets.QWidget(); leftDecW.setLayout(leftDec)

        self.imagePreviewDec = PixmapBox("Preview (Stego)")
        self.statusLbl = QtWidgets.QLabel("Ready.")
        self.statusLbl.setWordWrap(True)
        rightDec = QtWidgets.QVBoxLayout()
        rightDec.addWidget(self.imagePreviewDec, 1)
        rightDec.addWidget(self.statusLbl)
        rightDecW = QtWidgets.QWidget(); rightDecW.setLayout(rightDec)

        dec_layout.addWidget(leftDecW, 0, 0)
        dec_layout.addWidget(rightDecW, 0, 1)

        self.tabs.addTab(enc, "Encode")
        self.tabs.addTab(dec, "Decode")
