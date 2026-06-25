"""
main.py
Interface PyQt6 do SIA — Sistema Identificador de Arquivos
Design moderno: navbar escura, cards brancos com sombra, accent azul.
"""

import sys
import os
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QListWidget, QListWidgetItem,
    QFrame, QSplitter, QScrollArea, QMessageBox, QProgressBar, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QPalette

sys.path.insert(0, str(Path(__file__).parent / "src"))

from extractor import processar_pdf, DocumentoFiscal
from matcher import executar_matching
from merger import processar_lote
try:
    from config_manager import chaves_configuradas
    CONFIG_OK = True
except ImportError:
    CONFIG_OK = False
try:
    from setup_dialog import DialogoConfiguracao
    SETUP_OK = True
except ImportError:
    SETUP_OK = False
try:
    from reporter import gerar_relatorio
    REPORTER_OK = True
except ImportError:
    REPORTER_OK = False
try:
    from dashboard import JanelaDashboard
    DASHBOARD_OK = True
except ImportError:
    DASHBOARD_OK = False


# ---------------------------------------------------------------------------
# Tokens de design
# ---------------------------------------------------------------------------

# Navbar
NAV_BG        = "#1E2433"
NAV_TEXT      = "#FFFFFF"
NAV_SUB       = "rgba(255,255,255,0.5)"

# Fundo e superfícies
BG_PAGE       = "#F0F2F5"
BG_CARD       = "#FFFFFF"
BG_INPUT      = "#F7F8FA"

# Accent azul
BLUE_500      = "#2563EB"
BLUE_600      = "#1D4ED8"
BLUE_50       = "#EFF6FF"
BLUE_100      = "#DBEAFE"

# Texto
TEXT_PRIMARY   = "#111827"
TEXT_SECONDARY = "#6B7280"
TEXT_HINT      = "#9CA3AF"

# Bordas
BORDER        = "#E5E7EB"
BORDER_FOCUS  = "#93C5FD"

# Semânticas
GREEN_500     = "#10B981"
GREEN_50      = "#ECFDF5"
AMBER_500     = "#F59E0B"
AMBER_50      = "#FFFBEB"
RED_500       = "#EF4444"
RED_50        = "#FEF2F2"

# Tipo de documento
COLOR_NF      = "#10B981"
COLOR_SAP     = "#2563EB"
COLOR_BOLETO  = "#F59E0B"
COLOR_DESC    = "#9CA3AF"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def abrir_pasta(caminho: str):
    if sys.platform == "win32":
        os.startfile(caminho)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", caminho])
    else:
        subprocess.Popen(["xdg-open", caminho])


def sombra(widget, raio=12, opacidade=18, dy=2):
    ef = QGraphicsDropShadowEffect()
    ef.setBlurRadius(raio)
    ef.setOffset(0, dy)
    ef.setColor(QColor(0, 0, 0, opacidade))
    widget.setGraphicsEffect(ef)
    return ef


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------

class WorkerCarregamento(QThread):
    arquivo_processado = pyqtSignal(object)
    concluido          = pyqtSignal()
    erro               = pyqtSignal(str)

    def __init__(self, caminhos):
        super().__init__()
        self.caminhos = caminhos

    def run(self):
        try:
            for c in self.caminhos:
                self.arquivo_processado.emit(processar_pdf(c))
            self.concluido.emit()
        except Exception as e:
            self.erro.emit(str(e))


class WorkerProcessamento(QThread):
    progresso = pyqtSignal(str)
    concluido = pyqtSignal(object, list)
    erro      = pyqtSignal(str)

    def __init__(self, documentos, pasta_saida):
        super().__init__()
        self.documentos  = documentos
        self.pasta_saida = pasta_saida

    def run(self):
        try:
            self.progresso.emit("Casando documentos...")
            resultado = executar_matching(self.documentos)
            self.progresso.emit("Gerando PDFs...")
            resultados = processar_lote(resultado, self.pasta_saida)
            self.concluido.emit(resultado, resultados)
        except Exception as e:
            self.erro.emit(str(e))


# ---------------------------------------------------------------------------
# Item da lista
# ---------------------------------------------------------------------------

class ItemArquivo(QListWidgetItem):
    CORES = {
        "NF":          ("#DCFCE7", "#166534", "NF"),
        "SAP":         ("#DBEAFE", "#1E40AF", "SAP"),
        "BOLETO":      ("#FEF9C3", "#854D0E", "Boleto"),
        "DESCONHECIDO":("#F3F4F6", "#374151", "?"),
    }

    def __init__(self, doc: DocumentoFiscal):
        super().__init__()
        self.doc = doc

        tipo = doc.tipo
        if tipo == "NF":
            detalhe = f"NF {doc.numero_nf or '?'}  ·  {doc.quantidade_ton or '?'} t  ·  R$ {doc.valor_nf or '?'}"
        elif tipo == "SAP":
            detalhe = f"Pedido {doc.numero_pedido or '?'}  ·  {doc.quantidade_sap_ton or '?'} t"
        elif tipo == "BOLETO":
            detalhe = f"R$ {doc.valor_boleto or '?'}  ·  venc. {doc.vencimento_boleto or '?'}"
        else:
            detalhe = doc.erros[0][:72] if doc.erros else "Não identificado"

        self.setText(f"{doc.nome_arquivo}\n{detalhe}")
        self.setSizeHint(QSize(0, 56))


# ---------------------------------------------------------------------------
# Janela principal
# ---------------------------------------------------------------------------

class JanelaOrganizador(QMainWindow):
    def __init__(self):
        super().__init__()
        self.documentos: list[DocumentoFiscal] = []
        self.pasta_saida = str(Path.cwd() / "output")
        self._construir_ui()
        self._aplicar_estilo()

    # -----------------------------------------------------------------------
    # UI
    # -----------------------------------------------------------------------

    def _construir_ui(self):
        self.setWindowTitle("SIA — Sistema Identificador de Arquivos")
        self.setMinimumSize(900, 660)
        self.resize(1080, 720)

        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        vbox.addWidget(self._navbar())

        # Corpo com padding
        body = QWidget()
        body.setObjectName("body")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 24, 24, 24)
        body_layout.setSpacing(16)

        # Linha de título + estatísticas
        body_layout.addWidget(self._titulo_row())

        # Dois cards lado a lado
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        splitter.addWidget(self._card_arquivos())
        splitter.addWidget(self._card_resultados())
        splitter.setSizes([480, 460])
        body_layout.addWidget(splitter, stretch=1)

        # Status bar
        body_layout.addWidget(self._status_bar())

        vbox.addWidget(body, stretch=1)

    def _navbar(self) -> QWidget:
        nav = QFrame()
        nav.setObjectName("navbar")
        nav.setFixedHeight(56)
        lay = QHBoxLayout(nav)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(0)

        logo = QLabel("📁  SIA")
        logo.setObjectName("nav_logo")

        sep = QLabel("·")
        sep.setObjectName("nav_sep")
        sep.setContentsMargins(12, 0, 12, 0)

        empresa = QLabel("Sistema Identificador de Arquivos")
        empresa.setObjectName("nav_empresa")

        lay.addWidget(logo)
        lay.addWidget(sep)
        lay.addWidget(empresa)
        lay.addStretch()
        btn_config = QPushButton('⚙️')
        btn_config.clicked.connect(self._abrir_configuracao)
        btn_config.setStyleSheet('background-color: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; padding: 5px 14px; font-size: 12px;')
        lay.addWidget(btn_config)

        return nav

    def _titulo_row(self) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)

        titulo = QLabel("Lote de Documentos")
        titulo.setObjectName("page_titulo")

        self.label_stats = QLabel("Nenhum arquivo carregado")
        self.label_stats.setObjectName("page_stats")

        lay.addWidget(titulo)
        lay.addStretch()
        lay.addWidget(self.label_stats)
        return row

    def _card_arquivos(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
#        sombra(card)  # removido
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        # Cabeçalho do card
        header = QHBoxLayout()
        lbl = QLabel("Arquivos no lote")
        lbl.setObjectName("card_titulo")
        self.label_contador = QLabel("")
        self.label_contador.setObjectName("label_contador_simples")
        header.addWidget(lbl)
        header.addStretch()
        header.addWidget(self.label_contador)
        lay.addLayout(header)

        # Lista
        self.lista_arquivos = QListWidget()
        self.lista_arquivos.setObjectName("file_list")
        self.lista_arquivos.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        lay.addWidget(self.lista_arquivos, stretch=1)
        self.lista_arquivos.setMinimumHeight(200)
        self.lista_arquivos.setMaximumHeight(99999)

        # Pasta de saída
        pasta_row = QHBoxLayout()
        pasta_row.setSpacing(8)
        self.label_pasta = QLabel(f"📂  {self.pasta_saida}")
        self.label_pasta.setObjectName("label_pasta")
        self.label_pasta.setWordWrap(True)
        btn_pasta = QPushButton("Alterar")
        btn_pasta.setObjectName("btn_link")
        btn_pasta.setFixedWidth(56)
        btn_pasta.clicked.connect(self._escolher_pasta)
        pasta_row.addWidget(self.label_pasta, stretch=1)
        pasta_row.addWidget(btn_pasta)
        lay.addLayout(pasta_row)

        # Botões
        btns = QHBoxLayout()
        btns.setSpacing(8)
        self.btn_adicionar = QPushButton("＋  Adicionar PDFs")
        self.btn_adicionar.setObjectName("btn_primary")
        self.btn_adicionar.clicked.connect(self._adicionar_arquivos)

        self.btn_remover = QPushButton("Remover")
        self.btn_remover.setObjectName("btn_ghost")
        self.btn_remover.clicked.connect(self._remover_selecionado)

        self.btn_limpar = QPushButton("Limpar")
        self.btn_limpar.setObjectName("btn_ghost")
        self.btn_limpar.clicked.connect(self._limpar_lote)

        btns.addWidget(self.btn_adicionar, stretch=2)
        btns.addWidget(self.btn_remover, stretch=1)
        btns.addWidget(self.btn_limpar, stretch=1)
        lay.addLayout(btns)

        # Botão processar
        self.btn_processar = QPushButton("▶   PROCESSAR LOTE")
        self.btn_processar.setObjectName("btn_processar")
        self.btn_processar.setFixedHeight(44)
        self.btn_processar.clicked.connect(self._processar_lote)
        self.btn_processar.setEnabled(False)
        lay.addWidget(self.btn_processar)

        return card

    def _card_resultados(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
#        sombra(card)  # removido
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        header = QHBoxLayout()
        lbl = QLabel("Resultado")
        lbl.setObjectName("card_titulo")
        self.btn_abrir_pasta = QPushButton("📂  Abrir pasta")
        self.btn_abrir_pasta.setObjectName("btn_ghost")
        self.btn_abrir_pasta.clicked.connect(self._abrir_pasta_saida)
        self.btn_abrir_pasta.setEnabled(False)
        self.btn_dashboard = QPushButton("Ver Dashboard")
        self.btn_dashboard.setObjectName("btn_ghost")
        self.btn_dashboard.clicked.connect(self._abrir_dashboard)
        self.btn_dashboard.setEnabled(False)
        self.btn_exportar = QPushButton("Exportar .xlsx")
        self.btn_exportar.setObjectName("btn_ghost")
        self.btn_exportar.clicked.connect(self._exportar_relatorio)
        self.btn_exportar.setEnabled(False)
        header.addWidget(lbl)
        header.addStretch()
        header.addWidget(self.btn_dashboard)
        header.addWidget(self.btn_exportar)
        header.addWidget(self.btn_abrir_pasta)
        lay.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("scroll_resultado")
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.widget_resultado = QWidget()
        self.layout_resultado = QVBoxLayout(self.widget_resultado)
        self.layout_resultado.setContentsMargins(0, 0, 4, 0)
        self.layout_resultado.setSpacing(8)
        self.layout_resultado.addStretch()

        scroll.setWidget(self.widget_resultado)
        scroll.viewport().setStyleSheet(f"background-color: {BG_CARD};")
        lay.addWidget(scroll, stretch=1)

        self._mostrar_placeholder()
        return card

    def _status_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("status_bar")
        bar.setFixedHeight(32)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(4, 0, 4, 0)

        self.label_status = QLabel("Pronto")
        credito = QLabel('<a href="https://www.linkedin.com/in/ramon-nunes2/" style="color:#9CA3AF;text-decoration:none;font-size:11px;">Desenvolvido por Ramon Nunes</a>')
        credito.setOpenExternalLinks(True)
        credito.setStyleSheet('background-color: transparent;')
        self.label_status.setObjectName("status_text")

        self.barra_progresso = QProgressBar()
        self.barra_progresso.setObjectName("progress")
        self.barra_progresso.setFixedWidth(160)
        self.barra_progresso.setFixedHeight(4)
        self.barra_progresso.setTextVisible(False)
        self.barra_progresso.hide()

        lay.addWidget(self.label_status, stretch=1)
        lay.addWidget(credito)
        lay.addWidget(self.barra_progresso)
        return bar

    # -----------------------------------------------------------------------
    # Estilo
    # -----------------------------------------------------------------------

    def _aplicar_estilo(self):
        self.setStyleSheet(f"""
            * {{ font-family: "Segoe UI", sans-serif; font-size: 13px; }}
            QMainWindow {{ background-color: {BG_PAGE}; }}
            QMainWindow > QWidget {{ background-color: {BG_PAGE}; }}
            #navbar {{ background-color: {NAV_BG}; border: none; }}
            #navbar * {{ background-color: {NAV_BG}; border: none; }}
            #nav_logo {{ color: white; font-size: 15px; font-weight: 700; }}
            #nav_sep {{ color: rgba(255,255,255,0.4); }}
            #nav_empresa {{ color: rgba(255,255,255,0.55); }}
            #body {{ background-color: {BG_PAGE}; }}
            #titulo_row {{ background-color: transparent; }}
            #page_titulo {{ font-size: 17px; font-weight: 700; color: {TEXT_PRIMARY}; background-color: transparent; }}
            #page_stats {{ font-size: 12px; color: {TEXT_SECONDARY}; background-color: transparent; }}
            #card {{ background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}
            #card > QWidget {{ background-color: {BG_CARD}; }}
            #card QLabel {{ background-color: transparent; }}
            #card QPushButton {{ background-color: transparent; }}
            #card_titulo {{ font-size: 13px; font-weight: 600; color: {TEXT_PRIMARY}; }}
            #label_contador {{ font-size: 12px; color: {TEXT_SECONDARY}; font-weight: 600; }}
            #file_list {{ background-color: {BG_INPUT}; border: 1px solid {BORDER}; border-radius: 8px; outline: none; font-size: 12px; }}
            #file_list::item {{ padding: 8px 12px; border-bottom: 1px solid {BORDER}; background-color: {BG_INPUT}; }}
            #file_list::item:selected {{ background-color: {BLUE_50}; color: {TEXT_PRIMARY}; }}
            #file_list::item:hover:!selected {{ background-color: #F3F4F6; }}
            #label_pasta {{ font-size: 11px; color: {TEXT_HINT}; }}
            #btn_primary {{ background-color: {BLUE_500}; color: white; border: none; border-radius: 8px; padding: 8px 16px; font-weight: 600; }}
            #btn_primary:hover {{ background-color: {BLUE_600}; }}
            #btn_primary:disabled {{ background-color: {TEXT_HINT}; color: white; }}
            #btn_ghost {{ background-color: {BG_CARD}; color: {TEXT_SECONDARY}; border: 1px solid {BORDER}; border-radius: 8px; padding: 7px 12px; font-size: 12px; }}
            #btn_ghost:hover {{ background-color: {BG_INPUT}; color: {TEXT_PRIMARY}; border-color: #D1D5DB; }}
            #btn_ghost:disabled {{ color: {TEXT_HINT}; border-color: {BORDER}; }}
            #btn_link {{ background-color: transparent; border: none; color: {BLUE_500}; font-size: 12px; font-weight: 600; padding: 0; }}
            #btn_link:hover {{ color: {BLUE_600}; text-decoration: underline; }}
            #btn_processar {{ background-color: {NAV_BG}; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 700; letter-spacing: 0.8px; }}
            #btn_processar:hover {{ background-color: #2D3748; }}
            #btn_processar:disabled {{ background-color: {TEXT_HINT}; color: white; }}
            #scroll_resultado {{ background-color: {BG_CARD}; border: none; }}
            #resultado_inner {{ background-color: {BG_CARD}; border: none; }}
            #resultado_inner QLabel {{ background-color: transparent; }}
            #status_bar {{ background-color: transparent; border: none; }}
            #status_text {{ font-size: 11px; color: {TEXT_HINT}; background-color: transparent; }}
            #progress {{ border: none; border-radius: 2px; background-color: {BORDER}; }}
            #progress::chunk {{ background-color: {BLUE_500}; border-radius: 2px; }}
            QSplitter {{ background-color: {BG_PAGE}; }}
            QSplitter::handle {{ background-color: {BG_PAGE}; width: 16px; }}
            QPushButton#btn_primary {{ background-color: {BLUE_500}; color: white; border: none; border-radius: 8px; padding: 8px 16px; font-weight: 600; font-size: 13px; }}
            QPushButton#btn_primary:hover {{ background-color: {BLUE_600}; }}
            QPushButton#btn_primary:disabled {{ background-color: {TEXT_HINT}; color: white; }}
            QPushButton#btn_ghost {{ background-color: {BG_CARD}; color: {TEXT_SECONDARY}; border: 1px solid {BORDER}; border-radius: 8px; padding: 7px 12px; font-size: 12px; }}
            QPushButton#btn_ghost:hover {{ background-color: {BG_INPUT}; color: {TEXT_PRIMARY}; }}
            QPushButton#btn_ghost:disabled {{ color: {TEXT_HINT}; }}
            QPushButton#btn_processar {{ background-color: {NAV_BG}; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 700; letter-spacing: 0.8px; }}
            QPushButton#btn_processar:hover {{ background-color: #2D3748; }}
            QPushButton#btn_processar:disabled {{ background-color: {TEXT_HINT}; color: white; }}
            QPushButton#btn_link {{ background-color: transparent; border: none; color: {BLUE_500}; font-size: 12px; font-weight: 600; padding: 0; }}
        """)

    # -----------------------------------------------------------------------
    # Ações
    # -----------------------------------------------------------------------

    def _adicionar_arquivos(self):
        caminhos, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar PDFs", "", "Arquivos PDF (*.pdf)"
        )
        if not caminhos:
            return

        novos = [c for c in caminhos if not any(d.caminho == c for d in self.documentos)]
        if not novos:
            self._set_status("Arquivos já estão no lote")
            return

        self.btn_adicionar.setEnabled(False)
        self.btn_processar.setEnabled(False)
        self.barra_progresso.setRange(0, len(novos))
        self.barra_progresso.setValue(0)
        self.barra_progresso.show()
        self._set_status(f"Identificando {len(novos)} arquivo(s)...")

        self.worker_carga = WorkerCarregamento(novos)
        self.worker_carga.arquivo_processado.connect(self._on_arquivo_carregado)
        self.worker_carga.concluido.connect(self._on_carregamento_concluido)
        self.worker_carga.erro.connect(self._on_carregamento_erro)
        self.worker_carga.start()

    def _on_arquivo_carregado(self, doc: DocumentoFiscal):
        self.documentos.append(doc)
        self.lista_arquivos.addItem(ItemArquivo(doc))
        self._atualizar_contador()
        self.barra_progresso.setValue(self.barra_progresso.value() + 1)
        self._set_status(f"Identificando... {doc.nome_arquivo}")

    def _on_carregamento_concluido(self):
        self.barra_progresso.hide()
        self.btn_adicionar.setEnabled(True)
        self.btn_processar.setEnabled(len(self.documentos) > 0)
        self._set_status(f"{len(self.documentos)} arquivo(s) no lote")

    def _on_carregamento_erro(self, msg):
        self.barra_progresso.hide()
        self.btn_adicionar.setEnabled(True)
        self.btn_processar.setEnabled(len(self.documentos) > 0)
        self._set_status(f"Erro: {msg}")
        QMessageBox.critical(self, "Erro ao carregar", msg)

    def _remover_selecionado(self):
        row = self.lista_arquivos.currentRow()
        if row < 0:
            return
        self.lista_arquivos.takeItem(row)
        self.documentos.pop(row)
        self._atualizar_contador()
        self.btn_processar.setEnabled(len(self.documentos) > 0)

    def _limpar_lote(self):
        if not self.documentos:
            return
        if QMessageBox.question(
            self, "Limpar lote", "Remover todos os arquivos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.lista_arquivos.clear()
            self.documentos.clear()
            self._atualizar_contador()
            self.btn_processar.setEnabled(False)
            self._mostrar_placeholder()
            self._set_status("Lote limpo")

    def _escolher_pasta(self):
        pasta = QFileDialog.getExistingDirectory(self, "Pasta de saída", self.pasta_saida)
        if pasta:
            self.pasta_saida = pasta
            self.label_pasta.setText(f"📂  {pasta}")

    def _processar_lote(self):
        if not self.documentos:
            return
        self.btn_processar.setEnabled(False)
        self.btn_adicionar.setEnabled(False)
        self.btn_abrir_pasta.setEnabled(False)
        self.barra_progresso.setRange(0, 0)
        self.barra_progresso.show()
        self._limpar_resultado()

        self.worker = WorkerProcessamento(self.documentos, self.pasta_saida)
        self.worker.progresso.connect(self._set_status)
        self.worker.concluido.connect(self._on_processamento_concluido)
        self.worker.erro.connect(self._on_processamento_erro)
        self.worker.start()

    def _abrir_pasta_saida(self):
        abrir_pasta(self.pasta_saida)

    def _abrir_configuracao(self, primeira_vez: bool = False):
        if not SETUP_OK:
            return
        dlg = DialogoConfiguracao(primeira_vez=primeira_vez, parent=self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            # Recarrega as chaves no extractor
            try:
                import importlib, extractor
                importlib.reload(extractor)
            except Exception:
                pass
            if primeira_vez:
                self._set_status('Configuracao salva. Pronto para usar!')

    def _abrir_dashboard(self):
        if not hasattr(self, "_ultimo_resultado") or not DASHBOARD_OK:
            return
        dlg = JanelaDashboard(self._ultimo_resultado, self._ultimos_merger, self)
        dlg.exec()

    def _exportar_relatorio(self):
        if not hasattr(self, "_ultimo_resultado") or not REPORTER_OK:
            return
        try:
            caminho = gerar_relatorio(self._ultimo_resultado, self._ultimos_merger, self.pasta_saida)
            if caminho:
                self._adicionar_info(f"Relatorio gerado: {Path(caminho).name}")
                self._set_status(f"Relatorio exportado: {Path(caminho).name}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Nao foi possivel exportar: {str(e)}")

    def _adicionar_info(self, msg: str):
        frame = QFrame()
        frame.setObjectName("info_card")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 8, 14, 8)
        frame.setStyleSheet(f"QFrame#info_card {{ background: {BLUE_50}; border: 1px solid #BFDBFE; border-left: 3px solid {BLUE_500}; border-radius: 8px; }}")
        lbl = QLabel(f"i  {msg}")
        lbl.setStyleSheet(f"font-size: 11px; color: #1E40AF; background: transparent;")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        self.layout_resultado.insertWidget(self.layout_resultado.count() - 1, frame)

    # -----------------------------------------------------------------------
    # Callbacks worker processamento
    # -----------------------------------------------------------------------

    def _on_processamento_concluido(self, resultado, resultados_merger):
        self._ultimo_resultado = resultado
        self._ultimos_merger = resultados_merger
        self.barra_progresso.hide()
        self.btn_processar.setEnabled(True)
        self.btn_adicionar.setEnabled(True)

        total_ok = sum(1 for r in resultados_merger if r["sucesso"])
        self._limpar_resultado()

        for res in resultados_merger:
            self._adicionar_card_resultado(res)

        for nf in resultado.nfs_sem_par:
            self._adicionar_alerta(f"NF {nf.numero_nf} sem par — não gerada")
        for b in resultado.boletos_sem_nf:
            self._adicionar_alerta(f"Boleto sem NF: {b.nome_arquivo}")
        for s in resultado.saps_sem_nf:
            self._adicionar_alerta(f"SAP {s.numero_pedido} sem NF correspondente")
        for d in resultado.desconhecidos:
            msg = f"Não identificado: {d.nome_arquivo}"
            if d.erros:
                msg += f"  —  {d.erros[-1]}"
            self._adicionar_alerta(msg)

        if total_ok > 0:
            self.btn_abrir_pasta.setEnabled(True)
            if DASHBOARD_OK:
                self.btn_dashboard.setEnabled(True)
            if REPORTER_OK:
                self.btn_exportar.setEnabled(True)
                # Exportacao automatica
                try:
                    caminho_xlsx = gerar_relatorio(resultado, resultados_merger, self.pasta_saida)
                    if caminho_xlsx:
                        self._adicionar_info(f"Relatorio exportado: {Path(caminho_xlsx).name}")
                except Exception as e:
                    self._adicionar_alerta(f"Erro ao exportar relatorio: {str(e)[:60]}")

        self._set_status(f"Concluído — {total_ok} arquivo(s) gerado(s)")

    def _on_processamento_erro(self, msg):
        self.barra_progresso.hide()
        self.btn_processar.setEnabled(True)
        self.btn_adicionar.setEnabled(True)
        self._set_status(f"Erro: {msg}")
        QMessageBox.critical(self, "Erro no processamento", msg)

    # -----------------------------------------------------------------------
    # Helpers UI
    # -----------------------------------------------------------------------

    def _atualizar_contador(self):
        n = len(self.documentos)
        if n == 0:
            self.label_contador.setText("")
            self.label_stats.setText("Nenhum arquivo carregado")
            return

        nfs     = sum(1 for d in self.documentos if d.tipo == "NF")
        saps    = sum(1 for d in self.documentos if d.tipo == "SAP")
        boletos = sum(1 for d in self.documentos if d.tipo == "BOLETO")
        outros  = sum(1 for d in self.documentos if d.tipo == "DESCONHECIDO")

        self.label_contador.setText(f"{n}")

        partes = []
        if nfs:     partes.append(f"{nfs} NF")
        if saps:    partes.append(f"{saps} SAP")
        if boletos: partes.append(f"{boletos} Boleto")
        if outros:  partes.append(f"{outros} não identificado")
        self.label_stats.setText("  ·  ".join(partes))

    def _set_status(self, msg: str):
        self.label_status.setText(msg)

    def _mostrar_placeholder(self):
        self._limpar_resultado()
        lbl = QLabel("Os arquivos combinados\naparecerão aqui após o processamento.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {TEXT_HINT}; font-size: 12px; line-height: 1.6;")
        self.layout_resultado.insertWidget(0, lbl)

    def _limpar_resultado(self):
        while self.layout_resultado.count() > 1:
            item = self.layout_resultado.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _adicionar_card_resultado(self, res: dict):
        par  = res["par"]
        ok   = res["sucesso"]

        card = QFrame()
        card.setObjectName("result_card")
        lay  = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(5)

        cor_left  = GREEN_500 if ok else RED_500
        cor_bg    = GREEN_50  if ok else RED_50
        icone     = "✓" if ok else "✕"

        card.setStyleSheet(f"""
            #result_card {{
                background: {cor_bg};
                border: 1px solid {"#D1FAE5" if ok else "#FEE2E2"};
                border-left: 3px solid {cor_left};
                border-radius: 8px;
            }}
        """)

        nome = res["nome_arquivo"] or res.get("erro", "Erro")
        cor_nome = GREEN_500 if ok else RED_500
        lbl_nome = QLabel(f"{icone}  {nome}")
        lbl_nome.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {cor_nome};")
        lbl_nome.setWordWrap(True)
        lay.addWidget(lbl_nome)

        partes = []
        if par.nf:     partes.append(f"NF {par.nf.numero_nf}")
        if par.sap:    partes.append(f"Pedido {par.sap.numero_pedido}")
        if par.boleto: partes.append(f"Boleto venc. {par.boleto.vencimento_boleto}")
        if partes:
            lbl_det = QLabel("  ·  ".join(partes))
            lbl_det.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
            lay.addWidget(lbl_det)

        if not ok and res.get("erro"):
            lbl_err = QLabel(res["erro"])
            lbl_err.setStyleSheet(f"font-size: 11px; color: {RED_500};")
            lbl_err.setWordWrap(True)
            lay.addWidget(lbl_err)

        for alerta in res.get("alertas", []):
            lbl_a = QLabel(f"⚠  {alerta}")
            lbl_a.setStyleSheet(f"font-size: 11px; color: {AMBER_500};")
            lbl_a.setWordWrap(True)
            lay.addWidget(lbl_a)

        self.layout_resultado.insertWidget(self.layout_resultado.count() - 1, card)

    def _adicionar_alerta(self, msg: str):
        frame = QFrame()
        frame.setObjectName("alerta_card")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10)
        frame.setStyleSheet(f"""
            #alerta_card {{
                background: {AMBER_50};
                border: 1px solid #FDE68A;
                border-left: 3px solid {AMBER_500};
                border-radius: 8px;
            }}
        """)
        lbl = QLabel(f"⚠  {msg}")
        lbl.setStyleSheet(f"font-size: 11px; color: #92400E;")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        self.layout_resultado.insertWidget(self.layout_resultado.count() - 1, frame)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    janela = JanelaOrganizador()
    janela.show()
    sys.exit(app.exec())