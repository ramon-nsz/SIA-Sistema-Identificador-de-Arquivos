"""
dashboard.py
Janela de dashboard exibida apos o processamento de um lote.
Mostra cards de resumo, tabela de pares e grafico de barras por NF.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QWidget, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPainter, QFont, QPen, QBrush

# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

NAV_BG        = "#1E2433"
BG_PAGE       = "#F0F2F5"
BG_CARD       = "#FFFFFF"
BLUE_500      = "#2563EB"
BLUE_50       = "#EFF6FF"
BLUE_100      = "#DBEAFE"
GREEN_500     = "#10B981"
GREEN_50      = "#ECFDF5"
AMBER_500     = "#F59E0B"
AMBER_50      = "#FFFBEB"
RED_500       = "#EF4444"
TEXT_PRIMARY  = "#111827"
TEXT_SECONDARY= "#6B7280"
TEXT_HINT     = "#9CA3AF"
BORDER        = "#E5E7EB"


# ---------------------------------------------------------------------------
# Widget de gráfico de barras simples (PyQt6 nativo)
# ---------------------------------------------------------------------------

class GraficoBarras(QWidget):
    def __init__(self, dados: list, parent=None):
        """
        dados: lista de (label, valor)
        """
        super().__init__(parent)
        self.dados = dados
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        if not self.dados:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad_left  = 80
        pad_right = 20
        pad_top   = 20
        pad_bottom= 40

        area_w = w - pad_left - pad_right
        area_h = h - pad_top - pad_bottom

        max_val = max(v for _, v in self.dados) if self.dados else 1
        n = len(self.dados)
        barra_w = max(8, (area_w // n) - 6)
        espaco  = (area_w - barra_w * n) // (n + 1)

        # Fundo
        painter.fillRect(0, 0, w, h, QColor(BG_CARD))

        # Linhas de grade horizontais
        painter.setPen(QPen(QColor(BORDER), 1, Qt.PenStyle.DashLine))
        for i in range(1, 5):
            y = pad_top + (area_h * i // 4)
            painter.drawLine(pad_left, y, w - pad_right, y)

        # Barras
        for i, (label, valor) in enumerate(self.dados):
            x = pad_left + espaco + i * (barra_w + espaco)
            barra_h = int(area_h * valor / max_val) if max_val > 0 else 0
            y = pad_top + area_h - barra_h

            # Cor alternada
            cor = QColor(BLUE_500) if i % 2 == 0 else QColor(GREEN_500)
            painter.fillRect(x, y, barra_w, barra_h, cor)

            # Label abaixo
            painter.setPen(QColor(TEXT_SECONDARY))
            painter.setFont(QFont("Segoe UI", 8))
            label_short = label[:6] if len(label) > 6 else label
            painter.drawText(x - 2, h - pad_bottom + 6, barra_w + 4, 30,
                           Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                           label_short)

            # Valor acima da barra
            painter.setPen(QColor(TEXT_PRIMARY))
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            val_str = f"R${valor/1000:.0f}k" if valor >= 1000 else f"R${valor:.0f}"
            painter.drawText(x - 4, y - 16, barra_w + 8, 14,
                           Qt.AlignmentFlag.AlignHCenter, val_str)

        # Eixo Y — valor máximo
        painter.setPen(QColor(TEXT_HINT))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(0, pad_top, pad_left - 4, 14,
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                        f"R${max_val/1000:.0f}k")

        painter.end()


# ---------------------------------------------------------------------------
# Card de métrica
# ---------------------------------------------------------------------------

def _card_metrica(titulo: str, valor: str, cor_accent: str, cor_bg: str) -> QFrame:
    card = QFrame()
    card.setStyleSheet(f"""
        QFrame {{
            background-color: {cor_bg};
            border: 1px solid {BORDER};
            border-left: 4px solid {cor_accent};
            border-radius: 10px;
            padding: 4px;
        }}
    """)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 12, 16, 12)
    lay.setSpacing(4)

    lbl_titulo = QLabel(titulo)
    lbl_titulo.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 600; background: transparent; border: none;")

    lbl_valor = QLabel(valor)
    lbl_valor.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 700; background: transparent; border: none;")

    lay.addWidget(lbl_titulo)
    lay.addWidget(lbl_valor)
    return card


# ---------------------------------------------------------------------------
# Janela principal do dashboard
# ---------------------------------------------------------------------------

class JanelaDashboard(QDialog):
    def __init__(self, resultado, resultados_merger: list, parent=None):
        super().__init__(parent)
        self.resultado = resultado
        self.resultados_merger = resultados_merger
        self.setWindowTitle("SIA — Dashboard do Lote")
        self.setMinimumSize(1200, 800)
        self.showMaximized()
        self._construir_ui()
        self._aplicar_estilo()

    def _construir_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("dash_header")
        header.setFixedHeight(52)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(24, 0, 24, 0)
        titulo = QLabel("Dashboard do Lote")
        titulo.setStyleSheet("color: white; font-size: 16px; font-weight: 700; background: transparent;")
        btn_fechar = QPushButton("Fechar")
        btn_fechar.setFixedWidth(80)
        btn_fechar.clicked.connect(self.close)
        btn_fechar.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.15);
                color: white;
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: rgba(255,255,255,0.25); }
        """)
        h_lay.addWidget(titulo)
        h_lay.addStretch()
        h_lay.addWidget(btn_fechar)
        root.addWidget(header)

        # Corpo com scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: #F0F2F5;")

        corpo = QWidget()
        corpo.setStyleSheet("background-color: #F0F2F5;")
        corpo_lay = QVBoxLayout(corpo)
        corpo_lay.setContentsMargins(24, 24, 24, 24)
        corpo_lay.setSpacing(20)

        # Cards de métricas
        corpo_lay.addWidget(self._secao_label("Resumo do Lote"))
        corpo_lay.addLayout(self._cards_metricas())

        # Gráfico
        corpo_lay.addWidget(self._secao_label("Valores por NF (R$)"))
        corpo_lay.addWidget(self._card_grafico())

        # Tabela
        corpo_lay.addWidget(self._secao_label("Pares Gerados"))
        corpo_lay.addWidget(self._tabela_pares())

        # Alertas e sobras
        alertas = self._card_alertas()
        if alertas:
            corpo_lay.addWidget(self._secao_label("Avisos"))
            corpo_lay.addWidget(alertas)

        corpo_lay.addStretch()
        scroll.setWidget(corpo)
        root.addWidget(scroll)

    def _secao_label(self, texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.8px;
            background: transparent;
        """)
        return lbl

    def _cards_metricas(self) -> QHBoxLayout:
        sucessos = [r for r in self.resultados_merger if r["sucesso"]]
        total_nfs    = len(sucessos)
        total_valor  = sum((r["par"].nf.valor_nf or 0) for r in sucessos)
        total_ton    = sum((r["par"].nf.quantidade_ton or 0) for r in sucessos)
        fornecedores = len(set(
            r["par"].nf.emitente or "?" for r in sucessos
        ))

        lay = QHBoxLayout()
        lay.setSpacing(12)
        lay.addWidget(_card_metrica("NFs Processadas", str(total_nfs), BLUE_500, BLUE_50))
        lay.addWidget(_card_metrica("Valor Total", f"R$ {total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), GREEN_500, GREEN_50))
        lay.addWidget(_card_metrica("Total Toneladas", f"{total_ton:,.3f} t".replace(",", "X").replace(".", ",").replace("X", "."), AMBER_500, AMBER_50))
        lay.addWidget(_card_metrica("Fornecedores", str(fornecedores), "#8B5CF6", "#F5F3FF"))
        return lay

    def _card_grafico(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)

        dados = []
        for r in self.resultados_merger:
            if not r["sucesso"]:
                continue
            nf = r["par"].nf
            num = nf.numero_nf or "?"
            label = num[-4:] if len(num) > 4 else num
            dados.append((label, nf.valor_nf or 0))

        # lbl_count removido
        

        if dados:
            grafico = GraficoBarras(dados)
            grafico.setFixedHeight(220)
            lay.addWidget(grafico)
        else:
            lbl = QLabel("Sem dados para exibir")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {TEXT_HINT}; font-size: 12px; background: transparent;")
            lay.addWidget(lbl)

        return card


    def _tabela_pares(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)

        cols = ["Arquivo", "NF Nº", "Emitente", "Produto", "Qtd (t)", "Valor NF", "Vencimento", "Pedido SAP", "Tipo"]
        tabela = QTableWidget()
        tabela.setColumnCount(len(cols))
        tabela.setHorizontalHeaderLabels(cols)
        tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tabela.setAlternatingRowColors(True)
        tabela.verticalHeader().setVisible(False)
        tabela.horizontalHeader().setStretchLastSection(True)
        tabela.setShowGrid(False)
        tabela.setStyleSheet(f"""
            QTableWidget {{
                background-color: {BG_CARD};
                border: none;
                border-radius: 12px;
                font-size: 12px;
                gridline-color: {BORDER};
            }}
            QTableWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid {BORDER};
                color: {TEXT_PRIMARY};
            }}
            QTableWidget::item:selected {{
                background-color: {BLUE_50};
                color: {TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {BG_PAGE};
                color: {TEXT_SECONDARY};
                font-weight: 600;
                font-size: 11px;
                padding: 8px 12px;
                border: none;
                border-bottom: 1px solid {BORDER};
            }}
            QTableWidget::item:alternate {{
                background-color: #FAFAFA;
            }}
        """)

        sucessos = [r for r in self.resultados_merger if r["sucesso"]]
        tabela.setRowCount(len(sucessos))

        for row, res in enumerate(sucessos):
            par = res["par"]
            nf  = par.nf
            sap = par.sap
            bol = par.boleto

            valor_fmt = f"R$ {nf.valor_nf:,.2f}".replace(",","X").replace(".",",").replace("X",".") if nf.valor_nf else "-"
            qtd_fmt   = f"{nf.quantidade_ton:,.3f}".replace(",","X").replace(".",",").replace("X",".") if nf.quantidade_ton else "-"

            vals = [
                res.get("nome_arquivo", "-"),
                nf.numero_nf or "-",
                (nf.emitente or "-")[:30],
                (nf.descricao_produto or "-")[:25],
                qtd_fmt,
                valor_fmt,
                nf.vencimento_nf or "-",
                sap.numero_pedido if sap else "-",
                par.tipo,
            ]

            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter |
                    (Qt.AlignmentFlag.AlignRight if col in (4, 5) else Qt.AlignmentFlag.AlignLeft))
                tabela.setItem(row, col, item)

        tabela.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in range(1, len(cols)):
            tabela.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)

        tabela.setMinimumHeight(min(400, 48 + len(sucessos) * 40))
        lay.addWidget(tabela)
        return card

    def _card_alertas(self):
        alertas = []
        for nf in self.resultado.nfs_sem_par:
            alertas.append(f"NF {nf.numero_nf} sem par — não gerada")
        for b in self.resultado.boletos_sem_nf:
            alertas.append(f"Boleto sem NF: {b.nome_arquivo}")
        for s in self.resultado.saps_sem_nf:
            alertas.append(f"SAP {s.numero_pedido} sem NF correspondente")
        for d in self.resultado.desconhecidos:
            alertas.append(f"Não identificado: {d.nome_arquivo}")

        if not alertas:
            return None

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {AMBER_50};
                border: 1px solid #FDE68A;
                border-left: 4px solid {AMBER_500};
                border-radius: 10px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)
        for msg in alertas:
            lbl = QLabel(f"⚠  {msg}")
            lbl.setStyleSheet(f"color: #92400E; font-size: 12px; background: transparent; border: none;")
            lay.addWidget(lbl)
        return card

    def _aplicar_estilo(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_PAGE};
                font-family: "Segoe UI", sans-serif;
            }}
            #dash_header {{
                background-color: {NAV_BG};
                border: none;
            }}
        """)