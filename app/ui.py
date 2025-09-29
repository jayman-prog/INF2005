from PyQt6 import QtWidgets, QtGui, QtCore

class DropArea(QtWidgets.QFrame):
    fileDropped = QtCore.pyqtSignal(str)
    def __init__(self, text):
        super().__init__()
        self.setAcceptDrops(True)
        self.setStyleSheet("QFrame{border:2px dashed #888; border-radius:8px;}")
        self.label = QtWidgets.QLabel(text)
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lay = QtWidgets.QVBoxLayout(self); lay.addWidget(self.label)
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path: self.fileDropped.emit(path)
        e.acceptProposedAction()

class PixmapBox(QtWidgets.QGroupBox):
    """Preview box that also supports a small footer toolbar (buttons)."""
    def __init__(self, title):
        super().__init__(title)
        self._v = QtWidgets.QVBoxLayout(self)
        self._v.setContentsMargins(8, 12, 8, 8)

        self.label = QtWidgets.QLabel()
        self.label.setMinimumSize(420, 260)
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                 QtWidgets.QSizePolicy.Policy.Expanding)
        self.label.setScaledContents(True)

        self._footer = QtWidgets.QWidget()
        self._footer_layout = QtWidgets.QHBoxLayout(self._footer)
        self._footer_layout.setContentsMargins(0, 6, 0, 0)
        self._footer_layout.addStretch(1)
        self._footer.hide()

        self._v.addWidget(self.label, 1)
        self._v.addWidget(self._footer, 0)

    def setPixmap(self, pm: QtGui.QPixmap):
        self.label.setPixmap(pm)

    def add_footer_widget(self, w: QtWidgets.QWidget):
        self._footer.show()
        self._footer_layout.insertWidget(0, w)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INF2005 Stego LSB")
        self.resize(1280, 760)

        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        # ===================== ENCODE TAB =====================
        enc = QtWidgets.QWidget()
        enc_root = QtWidgets.QHBoxLayout(enc)

        # Cover selection
        self.encodeCoverDrop = DropArea("Drop COVER (BMP/PNG/WAV)")
        self.browseCoverBtn = QtWidgets.QPushButton("Browse Cover...")

        self.lsbSpinEnc = QtWidgets.QSpinBox(); self.lsbSpinEnc.setRange(1, 8); self.lsbSpinEnc.setValue(2)
        self.keySpinEnc = QtWidgets.QSpinBox(); self.keySpinEnc.setRange(0, 2_000_000_000); self.keySpinEnc.setValue(1234)
        self.capacityLblEnc = QtWidgets.QLabel("Capacity: -")

        encCtrls = QtWidgets.QFormLayout()
        encCtrls.addRow("LSBs:", self.lsbSpinEnc)
        encCtrls.addRow("Key:", self.keySpinEnc)
        encCtrls.addRow(self.capacityLblEnc)

        # Region (Image only)
        self.regionXSpin = QtWidgets.QSpinBox(); self.regionXSpin.setRange(0, 10000); self.regionXSpin.setValue(0)
        self.regionYSpin = QtWidgets.QSpinBox(); self.regionYSpin.setRange(0, 10000); self.regionYSpin.setValue(0)
        self.regionWSpin = QtWidgets.QSpinBox(); self.regionWSpin.setRange(0, 10000); self.regionWSpin.setValue(0)
        self.regionHSpin = QtWidgets.QSpinBox(); self.regionHSpin.setRange(0, 10000); self.regionHSpin.setValue(0)

        self.regionGroup = QtWidgets.QGroupBox("Region (Image only)")
        rg = QtWidgets.QFormLayout(self.regionGroup)
        rg.addRow("Region X:", self.regionXSpin)
        rg.addRow("Region Y:", self.regionYSpin)
        rg.addRow("Region W:", self.regionWSpin)
        rg.addRow("Region H:", self.regionHSpin)
        self.regionGroup.setVisible(False)

        # Payload Tabs (File / Text)
        self.payloadTabs = QtWidgets.QTabWidget()
        fileTab = QtWidgets.QWidget(); fileLay = QtWidgets.QVBoxLayout(fileTab)
        self.encodePayloadDrop = DropArea("Drop PAYLOAD (any file)")
        self.browsePayloadBtn = QtWidgets.QPushButton("Browse Payload...")
        fileLay.addWidget(self.encodePayloadDrop); fileLay.addWidget(self.browsePayloadBtn)
        self.payloadTabs.addTab(fileTab, "File")
        textTab = QtWidgets.QWidget(); textLay = QtWidgets.QVBoxLayout(textTab)
        self.payloadTextEdit = QtWidgets.QTextEdit()
        self.payloadTextEdit.setPlaceholderText("Type payload text here…")
        textLay.addWidget(self.payloadTextEdit)
        self.payloadLenLbl = QtWidgets.QLabel("0 bytes")
        textLay.addWidget(self.payloadLenLbl, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.payloadTextEdit.textChanged.connect(self._update_text_len)
        self.payloadTabs.addTab(textTab, "Text")

        self.encodeBtn = QtWidgets.QPushButton("Encode → Save Stego")
        self.statusLblEnc = QtWidgets.QLabel("Ready."); self.statusLblEnc.setWordWrap(True)

        leftEnc = QtWidgets.QVBoxLayout()
        leftEnc.addWidget(self.encodeCoverDrop, 3)
        leftEnc.addWidget(self.browseCoverBtn)
        leftEnc.addLayout(encCtrls)
        leftEnc.addWidget(self.regionGroup)
        leftEnc.addWidget(self.payloadTabs, 3)
        leftEnc.addWidget(self.encodeBtn)
        leftEnc.addWidget(self.statusLblEnc)
        leftEncW = QtWidgets.QWidget(); leftEncW.setLayout(leftEnc)
        leftEncW.setMinimumWidth(480)

        self.imagePreviewEnc = PixmapBox("Preview (Cover/Stego)")
        self.diffPreviewEnc = PixmapBox("Difference Map")

        rightEnc = QtWidgets.QVBoxLayout()
        rightEnc.addWidget(self.imagePreviewEnc, 1)
        rightEnc.addWidget(self.diffPreviewEnc, 1)
        rightEncW = QtWidgets.QWidget(); rightEncW.setLayout(rightEnc)
        rightEncW.setMaximumWidth(900)

        enc_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        enc_splitter.addWidget(leftEncW); enc_splitter.addWidget(rightEncW)
        enc_splitter.setChildrenCollapsible(False)
        enc_splitter.setHandleWidth(8)
        enc_splitter.setStretchFactor(0, 3)
        enc_splitter.setStretchFactor(1, 2)
        enc_splitter.setSizes([620, 560])
        enc_root.addWidget(enc_splitter)

        # ===================== DECODE TAB =====================
        dec = QtWidgets.QWidget()
        dec_root = QtWidgets.QHBoxLayout(dec)

        self.decodeStegoDrop = DropArea("Drop STEGO (PNG/BMP/WAV)")
        self.browseStegoBtn = QtWidgets.QPushButton("Browse Stego...")
        self.lsbSpinDec = QtWidgets.QSpinBox(); self.lsbSpinDec.setRange(1, 8); self.lsbSpinDec.setValue(2)
        self.keySpinDec = QtWidgets.QSpinBox(); self.keySpinDec.setRange(0, 2_000_000_000); self.keySpinDec.setValue(1234)
        self.decodeBtn = QtWidgets.QPushButton("Decode from Stego")

        decCtrls = QtWidgets.QFormLayout()
        decCtrls.addRow("LSBs:", self.lsbSpinDec)
        decCtrls.addRow("Key:", self.keySpinDec)
        
        # Region (Image only)
        self.regionXSpinDec = QtWidgets.QSpinBox(); self.regionXSpinDec.setRange(0, 10000); self.regionXSpinDec.setValue(0)
        self.regionYSpinDec = QtWidgets.QSpinBox(); self.regionYSpinDec.setRange(0, 10000); self.regionYSpinDec.setValue(0)
        self.regionWSpinDec = QtWidgets.QSpinBox(); self.regionWSpinDec.setRange(0, 10000); self.regionWSpinDec.setValue(0)
        self.regionHSpinDec = QtWidgets.QSpinBox(); self.regionHSpinDec.setRange(0, 10000); self.regionHSpinDec.setValue(0)

        self.regionGroupDec = QtWidgets.QGroupBox("Region (Image only)")
        rgd = QtWidgets.QFormLayout(self.regionGroupDec)
        rgd.addRow("Region X:", self.regionXSpinDec)
        rgd.addRow("Region Y:", self.regionYSpinDec)
        rgd.addRow("Region W:", self.regionWSpinDec)
        rgd.addRow("Region H:", self.regionHSpinDec)
        self.regionGroupDec.setVisible(False)

        leftDec = QtWidgets.QVBoxLayout()
        leftDec.addWidget(self.decodeStegoDrop, 3)
        leftDec.addWidget(self.browseStegoBtn)
        leftDec.addLayout(decCtrls)
        leftDec.addWidget(self.regionGroupDec)
        leftDec.addWidget(self.decodeBtn)
        self.statusLbl = QtWidgets.QLabel("Ready."); self.statusLbl.setWordWrap(True)
        leftDec.addWidget(self.statusLbl)
        leftDecW = QtWidgets.QWidget(); leftDecW.setLayout(leftDec)
        leftDecW.setMinimumWidth(480)

        self.imagePreviewDec = PixmapBox("Preview (Stego)")
        rightDec = QtWidgets.QVBoxLayout(); rightDec.addWidget(self.imagePreviewDec, 1)
        rightDecW = QtWidgets.QWidget(); rightDecW.setLayout(rightDec); rightDecW.setMaximumWidth(900)

        dec_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        dec_splitter.addWidget(leftDecW); dec_splitter.addWidget(rightDecW)
        dec_splitter.setChildrenCollapsible(False); dec_splitter.setHandleWidth(8)
        dec_splitter.setStretchFactor(0, 3); dec_splitter.setStretchFactor(1, 2)
        dec_splitter.setSizes([620, 560]); dec_root.addWidget(dec_splitter)

        # Assemble
        self.tabs.addTab(enc, "Encode")
        self.tabs.addTab(dec, "Decode")

        # Global statusbar
        self.appStatus = QtWidgets.QStatusBar(); self.setStatusBar(self.appStatus)
        self.appStatus.showMessage("Ready.")

    def _update_text_len(self):
        b = len(self.payloadTextEdit.toPlainText().encode("utf-8"))
        self.payloadLenLbl.setText(f"{b} bytes")