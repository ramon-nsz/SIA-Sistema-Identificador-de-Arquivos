from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QTextEdit, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from config_manager import carregar_config, salvar_config, config_path_str

NAV_BG="#1E2433"; BG_PAGE="#F0F2F5"; BG_CARD="#FFFFFF"
BLUE_500="#2563EB"; BLUE_600="#1D4ED8"; BLUE_50="#EFF6FF"
GREEN_500="#10B981"; RED_500="#EF4444"; AMBER_500="#F59E0B"
TEXT_PRIMARY="#111827"; TEXT_SECONDARY="#6B7280"; TEXT_HINT="#9CA3AF"; BORDER="#E5E7EB"

class WorkerTesteChave(QThread):
    resultado = pyqtSignal(bool, str)
    def __init__(self, chave):
        super().__init__()
        self.chave = chave
    def run(self):
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=self.chave)
            client.models.generate_content(
                model="gemini-2.0-flash",
                contents=["Responda apenas: OK"],
                config=types.GenerateContentConfig(temperature=0, max_output_tokens=5)
            )
            self.resultado.emit(True, "Chave valida e funcionando!")
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                self.resultado.emit(False, "Chave valida mas quota esgotada. Aguarde o reset diario (21h de Brasilia).")
            elif "401" in msg or "API_KEY_INVALID" in msg:
                self.resultado.emit(False, "Chave invalida. Verifique e tente novamente.")
            else:
                self.resultado.emit(False, f"Erro: {msg[:100]}")

class DialogoConfiguracao(QDialog):
    def __init__(self, primeira_vez=False, parent=None):
        super().__init__(parent)
        self.primeira_vez = primeira_vez
        self.setWindowTitle("SIA - Configuracao")
        self.setMinimumWidth(580)
        self.setMaximumWidth(680)
        self._construir_ui()
        self._carregar_config()
        self._aplicar_estilo()

    def _construir_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("cfg_header")
        header.setFixedHeight(56)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(24,0,24,0)
        titulo = QLabel("Configuracao do SIA")
        titulo.setStyleSheet("color:white;font-size:15px;font-weight:700;background:transparent;")
        h_lay.addWidget(titulo)
        root.addWidget(header)

        corpo = QFrame()
        corpo.setObjectName("cfg_corpo")
        lay = QVBoxLayout(corpo)
        lay.setContentsMargins(28,24,28,24)
        lay.setSpacing(16)

        if self.primeira_vez:
            aviso = QFrame()
            aviso.setStyleSheet(f"QFrame{{background:{BLUE_50};border:1px solid #BFDBFE;border-left:4px solid {BLUE_500};border-radius:8px;}}")
            av = QVBoxLayout(aviso)
            av.setContentsMargins(16,12,16,12)
            l1 = QLabel("Bem-vindo ao SIA!")
            l1.setStyleSheet(f"font-weight:700;font-size:14px;color:{TEXT_PRIMARY};background:transparent;border:none;")
            l2 = QLabel("Para identificar documentos escaneados, o SIA usa a API Gemini do Google - gratuita para uso pessoal. Configure sua chave abaixo para comecar.")
            l2.setWordWrap(True)
            l2.setStyleSheet(f"color:{TEXT_SECONDARY};font-size:12px;background:transparent;border:none;")
            av.addWidget(l1); av.addWidget(l2)
            lay.addWidget(aviso)

        passos = QFrame()
        passos.setStyleSheet(f"QFrame{{background:{BG_PAGE};border-radius:8px;border:1px solid {BORDER};}}")
        pl = QVBoxLayout(passos)
        pl.setContentsMargins(16,14,16,14)
        pl.setSpacing(8)
        for num, txt in [("1","Acesse o Google AI Studio e faca login com sua conta Google"),("2",'Clique em "Get API key" e depois "Create API key"'),("3","Cole a chave no campo abaixo e clique em Salvar")]:
            row = QHBoxLayout()
            badge = QLabel(num)
            badge.setFixedSize(22,22)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(f"background-color:{BLUE_500};color:white;border-radius:11px;font-size:11px;font-weight:700;")
            lbl = QLabel(txt)
            lbl.setStyleSheet(f"color:{TEXT_PRIMARY};font-size:12px;background:transparent;")
            lbl.setWordWrap(True)
            row.addWidget(badge); row.addWidget(lbl,stretch=1)
            pl.addLayout(row)
        btn_ai = QPushButton("Abrir Google AI Studio")
        btn_ai.setStyleSheet(f"background:transparent;border:none;color:{BLUE_500};font-size:12px;font-weight:600;text-align:left;padding:4px 0;")
        btn_ai.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://aistudio.google.com/apikey")))
        pl.addWidget(btn_ai)
        lay.addWidget(passos)

        lbl_hint = QLabel("Cole uma ou mais chaves separadas por virgula. O SIA alternara automaticamente entre elas.")
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet(f"color:{TEXT_SECONDARY};font-size:11px;")
        lay.addWidget(lbl_hint)

        self.campo_chaves = QTextEdit()
        self.campo_chaves.setObjectName("campo_chaves")
        self.campo_chaves.setPlaceholderText("Cole sua chave Gemini aqui...\n\nPara multiplas chaves, separe por virgula.")
        self.campo_chaves.setFixedHeight(90)
        lay.addWidget(self.campo_chaves)

        self.btn_testar = QPushButton("Testar chave")
        self.btn_testar.setObjectName("btn_ghost_cfg")
        self.btn_testar.clicked.connect(self._testar_chave)
        self.label_teste = QLabel("")
        self.label_teste.setStyleSheet(f"font-size:11px;color:{TEXT_HINT};")
        self.label_teste.setWordWrap(True)
        teste_row = QHBoxLayout()
        teste_row.addWidget(self.btn_testar)
        teste_row.addWidget(self.label_teste,stretch=1)
        lay.addLayout(teste_row)

        lbl_path = QLabel(f"Configuracao salva em: {config_path_str()}")
        lbl_path.setStyleSheet(f"font-size:10px;color:{TEXT_HINT};")
        lbl_path.setWordWrap(True)
        lay.addWidget(lbl_path)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        if not self.primeira_vez:
            btn_cancelar = QPushButton("Cancelar")
            btn_cancelar.setObjectName("btn_ghost_cfg")
            btn_cancelar.clicked.connect(self.reject)
            btns.addWidget(btn_cancelar)
        btns.addStretch()
        self.btn_salvar = QPushButton("Salvar e continuar" if self.primeira_vez else "Salvar")
        self.btn_salvar.setObjectName("btn_salvar")
        self.btn_salvar.setFixedHeight(40)
        self.btn_salvar.clicked.connect(self._salvar)
        btns.addWidget(self.btn_salvar)
        lay.addLayout(btns)
        root.addWidget(corpo)

    def _carregar_config(self):
        config = carregar_config()
        chaves = config.get("gemini_keys","")
        if chaves:
            self.campo_chaves.setPlainText(chaves)

    def _testar_chave(self):
        texto = self.campo_chaves.toPlainText().strip()
        chaves = [k.strip() for k in texto.replace("\n",",").split(",") if k.strip()]
        if not chaves:
            self.label_teste.setText("Cole pelo menos uma chave antes de testar.")
            self.label_teste.setStyleSheet(f"font-size:11px;color:{AMBER_500};")
            return
        self.btn_testar.setEnabled(False)
        self.btn_testar.setText("Testando...")
        self.label_teste.setText("Aguarde...")
        self.label_teste.setStyleSheet(f"font-size:11px;color:{TEXT_HINT};")
        self.worker_teste = WorkerTesteChave(chaves[0])
        self.worker_teste.resultado.connect(self._on_teste)
        self.worker_teste.start()

    def _on_teste(self, sucesso, msg):
        self.btn_testar.setEnabled(True)
        self.btn_testar.setText("Testar chave")
        cor = GREEN_500 if sucesso else RED_500
        self.label_teste.setText(msg)
        self.label_teste.setStyleSheet(f"font-size:11px;color:{cor};")

    def _salvar(self):
        texto = self.campo_chaves.toPlainText().strip()
        chaves = [k.strip() for k in texto.replace("\n",",").split(",") if k.strip()]
        if not chaves:
            QMessageBox.warning(self,"Chave obrigatoria","Configure pelo menos uma chave Gemini.\n\nAcesse aistudio.google.com para obter uma chave gratuita.")
            return
        try:
            salvar_config({"gemini_keys": ", ".join(chaves)})
        except Exception as e:
            QMessageBox.critical(self,"Erro ao salvar",str(e))
            return
        self.accept()

    def _aplicar_estilo(self):
        self.setStyleSheet(f"""
            QDialog{{background-color:{BG_PAGE};font-family:"Segoe UI",sans-serif;}}
            #cfg_header{{background-color:{NAV_BG};border:none;}}
            #cfg_corpo{{background-color:{BG_PAGE};}}
            #campo_chaves{{background-color:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:8px;font-size:12px;font-family:"Consolas",monospace;color:{TEXT_PRIMARY};}}
            QPushButton#btn_ghost_cfg{{background-color:{BG_CARD};color:{TEXT_SECONDARY};border:1px solid {BORDER};border-radius:8px;padding:7px 14px;font-size:12px;}}
            QPushButton#btn_ghost_cfg:hover{{background-color:{BG_PAGE};color:{TEXT_PRIMARY};}}
            QPushButton#btn_salvar{{background-color:{BLUE_500};color:white;border:none;border-radius:8px;padding:8px 24px;font-size:13px;font-weight:600;min-width:140px;}}
            QPushButton#btn_salvar:hover{{background-color:{BLUE_600};}}
        """)
