# app/ui.py
from PyQt6 import QtWidgets, QtGui, QtCore


class DropArea(QtWidgets.QLabel):
    fileDropped = QtCore.pyqtSignal(str)

    def __init__(self, text="Drop file here"):
        super().__init__(text)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setStyleSheet("border: 2px dashed #888; color: #aaa;")
        self.setMinimumHeight(150)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            path = e.mimeData().urls()[0].toLocalFile()
            self.fileDropped.emit(path)


class PixmapBox(QtWidgets.QGroupBox):
    def __init__(self, title="Preview"):
        super().__init__(title)
        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label.setScaledContents(True)
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                 QtWidgets.QSizePolicy.Policy.Expanding)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.label)

        # Footer row for buttons
        self.footer = QtWidgets.QHBoxLayout()
        lay.addLayout(self.footer)

    def setPixmap(self, pm: QtGui.QPixmap):
        self.label.setPixmap(pm)

    def add_footer_widget(self, w):
        self.footer.addWidget(w)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INF2005 Stego LSB")
        self.resize(1200, 720)

        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        # ===================== ENCODE TAB =====================
        enc = QtWidgets.QWidget()
        enc_layout = QtWidgets.QHBoxLayout(enc)

        self.encodeCoverDrop = DropArea("Drop COVER (BMP/PNG/JPG or WAV)")
        self.encodePayloadDrop = DropArea("Drop PAYLOAD (any file)")

        self.lsbSpinEnc = QtWidgets.QSpinBox()
        self.lsbSpinEnc.setRange(1, 8)
        self.lsbSpinEnc.setValue(2)

        self.keySpinEnc = QtWidgets.QSpinBox()
        self.keySpinEnc.setRange(0, 2_000_000_000)
        self.keySpinEnc.setValue(1234)

        self.capacityLblEnc = QtWidgets.QLabel("Capacity: -")
        self.encodeBtn = QtWidgets.QPushButton("Encode → Save Stego")
        self.statusLblEnc = QtWidgets.QLabel("Ready.")
        self.statusLblEnc.setWordWrap(True)

        encCtrls = QtWidgets.QFormLayout()
        encCtrls.addRow("LSBs:", self.lsbSpinEnc)
        encCtrls.addRow("Key:", self.keySpinEnc)
        encCtrls.addRow(self.capacityLblEnc)

        leftEnc = QtWidgets.QVBoxLayout()
        leftEnc.addWidget(self.encodeCoverDrop, 3)
        leftEnc.addLayout(encCtrls)
        leftEnc.addWidget(self.encodePayloadDrop, 3)
        leftEnc.addWidget(self.encodeBtn)
        leftEnc.addWidget(self.statusLblEnc)

        leftEncW = QtWidgets.QWidget()
        leftEncW.setLayout(leftEnc)
        leftEncW.setMinimumWidth(480)

        self.imagePreviewEnc = PixmapBox("Preview (Cover/Stego)")
        self.diffPreviewEnc = PixmapBox("Difference Map")

        rightEnc = QtWidgets.QVBoxLayout()
        rightEnc.addWidget(self.imagePreviewEnc, 1)
        rightEnc.addWidget(self.diffPreviewEnc, 1)

        rightEncW = QtWidgets.QWidget()
        rightEncW.setLayout(rightEnc)
        rightEncW.setMaximumWidth(900)  # optional cap

        enc_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        enc_splitter.addWidget(leftEncW)
        enc_splitter.addWidget(rightEncW)
        enc_splitter.setStretchFactor(0, 3)
        enc_splitter.setStretchFactor(1, 2)
        enc_splitter.setSizes([620, 560])

        enc_layout.addWidget(enc_splitter)

        # ===================== DECODE TAB =====================
        dec = QtWidgets.QWidget()
        dec_layout = QtWidgets.QHBoxLayout(dec)

        self.decodeStegoDrop = DropArea("Drop STEGO (PNG/BMP or WAV)")

        self.lsbSpinDec = QtWidgets.QSpinBox()
        self.lsbSpinDec.setRange(1, 8)
        self.lsbSpinDec.setValue(2)

        self.keySpinDec = QtWidgets.QSpinBox()
        self.keySpinDec.setRange(0, 2_000_000_000)
        self.keySpinDec.setValue(1234)

        self.decodeBtn = QtWidgets.QPushButton("Decode from Stego")
        self.statusLbl = QtWidgets.QLabel("Ready.")
        self.statusLbl.setWordWrap(True)

        decCtrls = QtWidgets.QFormLayout()
        decCtrls.addRow("LSBs:", self.lsbSpinDec)
        decCtrls.addRow("Key:", self.keySpinDec)

        leftDec = QtWidgets.QVBoxLayout()
        leftDec.addWidget(self.decodeStegoDrop, 3)
        leftDec.addLayout(decCtrls)
        leftDec.addWidget(self.decodeBtn)
        leftDec.addWidget(self.statusLbl)

        leftDecW = QtWidgets.QWidget()
        leftDecW.setLayout(leftDec)
        leftDecW.setMinimumWidth(480)

        self.imagePreviewDec = PixmapBox("Preview (Stego)")

        rightDec = QtWidgets.QVBoxLayout()
        rightDec.addWidget(self.imagePreviewDec, 1)

        rightDecW = QtWidgets.QWidget()
        rightDecW.setLayout(rightDec)
        rightDecW.setMaximumWidth(900)

        dec_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        dec_splitter.addWidget(leftDecW)
        dec_splitter.addWidget(rightDecW)
        dec_splitter.setStretchFactor(0, 3)
        dec_splitter.setStretchFactor(1, 2)
        dec_splitter.setSizes([620, 560])

        dec_layout.addWidget(dec_splitter)

        # ===================== Assemble Tabs =====================
        self.tabs.addTab(enc, "Encode")
        self.tabs.addTab(dec, "Decode")

        # ===================== Global Status Bar =====================
        self.appStatus = QtWidgets.QStatusBar()
        self.setStatusBar(self.appStatus)
        self.appStatus.showMessage("Ready.")
