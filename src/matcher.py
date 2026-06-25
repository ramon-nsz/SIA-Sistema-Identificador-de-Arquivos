"""
matcher.py
Recebe lista de DocumentoFiscal e aplica as regras de casamento:
  - NF <-> SAP  : por quantidade em toneladas (tolerância 0.002 t)
  - NF <-> Boleto: por valor total (tolerância R$ 1,00)
  - Tripla      : NF que casa com SAP e com Boleto ao mesmo tempo
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple
from extractor import DocumentoFiscal


# ---------------------------------------------------------------------------
# Estrutura de resultado
# ---------------------------------------------------------------------------

@dataclass
class Par:
    """Representa um par ou tripla de documentos casados."""
    nf: DocumentoFiscal
    sap: Optional[DocumentoFiscal] = None
    boleto: Optional[DocumentoFiscal] = None

    # Alertas sobre tolerâncias ou dados faltantes
    alertas: list = field(default_factory=list)

    @property
    def tipo(self) -> str:
        """Descreve a combinação encontrada."""
        if self.sap and self.boleto:
            return "TRIPLA"
        if self.sap:
            return "NF+SAP"
        if self.boleto:
            return "NF+BOLETO"
        return "NF_ISOLADA"


@dataclass
class ResultadoMatching:
    """Resultado completo do processo de matching de um lote."""
    pares: list = field(default_factory=list)           # lista de Par
    nfs_sem_par: list = field(default_factory=list)     # NFs que não casaram com nada
    boletos_sem_nf: list = field(default_factory=list)  # Boletos sem NF correspondente
    saps_sem_nf: list = field(default_factory=list)     # SAPs sem NF correspondente
    desconhecidos: list = field(default_factory=list)   # arquivos não identificados


# ---------------------------------------------------------------------------
# Tolerâncias
# ---------------------------------------------------------------------------

TOLERANCIA_QUANTIDADE_TON = 0.002   # toneladas
TOLERANCIA_VALOR_BRL = 1.00         # reais


# ---------------------------------------------------------------------------
# Funções de comparação
# ---------------------------------------------------------------------------

def _quantidades_casam(nf: DocumentoFiscal, sap: DocumentoFiscal) -> Tuple[bool, float]:
    """
    Verifica se as quantidades de NF e SAP casam dentro da tolerância.
    Retorna (casa, delta).
    """
    if nf.quantidade_ton is None or sap.quantidade_sap_ton is None:
        return False, 0.0
    delta = abs(nf.quantidade_ton - sap.quantidade_sap_ton)
    return delta <= TOLERANCIA_QUANTIDADE_TON, delta


def _valores_casam(nf: DocumentoFiscal, boleto: DocumentoFiscal) -> Tuple[bool, float]:
    """
    Verifica se os valores de NF e Boleto casam dentro da tolerância.
    Retorna (casa, delta).
    """
    if nf.valor_nf is None or boleto.valor_boleto is None:
        return False, 0.0
    delta = abs(nf.valor_nf - boleto.valor_boleto)
    return delta <= TOLERANCIA_VALOR_BRL, delta


# ---------------------------------------------------------------------------
# Matching principal
# ---------------------------------------------------------------------------

def executar_matching(documentos: list) -> ResultadoMatching:
    """
    Recebe lista de DocumentoFiscal e retorna ResultadoMatching com todos
    os pares, triplas e alertas gerados.
    """
    resultado = ResultadoMatching()

    # Separar por tipo
    nfs     = [d for d in documentos if d.tipo == "NF"]
    saps    = [d for d in documentos if d.tipo == "SAP"]
    boletos = [d for d in documentos if d.tipo == "BOLETO"]
    resultado.desconhecidos = [d for d in documentos if d.tipo == "DESCONHECIDO"]

    # Controle de uso (evita casar o mesmo documento duas vezes)
    saps_usados    = set()
    boletos_usados = set()

    # --- Passo 1: casar cada NF com SAP e/ou Boleto ---
    for nf in nfs:
        par = Par(nf=nf)

        # Alertas por campos faltando na NF
        if nf.quantidade_ton is None:
            par.alertas.append(f"NF {nf.numero_nf}: quantidade não extraída — matching com SAP impossível")
        if nf.valor_nf is None:
            par.alertas.append(f"NF {nf.numero_nf}: valor não extraído — matching com Boleto impossível")

        # Tentar casar com SAP (por quantidade)
        melhor_sap = None
        melhor_delta_sap = float("inf")

        for sap in saps:
            if id(sap) in saps_usados:
                continue
            casa, delta = _quantidades_casam(nf, sap)
            if casa and delta < melhor_delta_sap:
                melhor_sap = sap
                melhor_delta_sap = delta

        if melhor_sap:
            par.sap = melhor_sap
            saps_usados.add(id(melhor_sap))
            if melhor_delta_sap > 0:
                par.alertas.append(
                    f"Δ quantidade NF {nf.numero_nf} ↔ SAP {melhor_sap.numero_pedido}: "
                    f"{melhor_delta_sap:.3f} t"
                )

        # Tentar casar com Boleto (por valor)
        melhor_boleto = None
        melhor_delta_boleto = float("inf")

        for boleto in boletos:
            if id(boleto) in boletos_usados:
                continue
            casa, delta = _valores_casam(nf, boleto)
            if casa and delta < melhor_delta_boleto:
                melhor_boleto = boleto
                melhor_delta_boleto = delta

        if melhor_boleto:
            par.boleto = melhor_boleto
            boletos_usados.add(id(melhor_boleto))
            if melhor_delta_boleto > 0:
                par.alertas.append(
                    f"Δ valor NF {nf.numero_nf} ↔ Boleto: "
                    f"R$ {melhor_delta_boleto:.2f}"
                )

        # Registrar o par se tiver ao menos SAP ou Boleto
        if par.sap or par.boleto:
            resultado.pares.append(par)
        else:
            resultado.nfs_sem_par.append(nf)

    # --- Passo 2: registrar sobras ---
    for boleto in boletos:
        if id(boleto) not in boletos_usados:
            resultado.boletos_sem_nf.append(boleto)

    for sap in saps:
        if id(sap) not in saps_usados:
            resultado.saps_sem_nf.append(sap)

    return resultado


# ---------------------------------------------------------------------------
# Execução direta (teste via terminal)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from extractor import processar_pdf

    if len(sys.argv) < 2:
        print("Uso: py matcher.py <pdf1> <pdf2> <pdf3> ...")
        print("Exemplo: py matcher.py NF.pdf PEDIDO.pdf BOLETO.pdf")
        sys.exit(1)

    documentos = []
    print("\n📂 Processando arquivos...\n")
    for caminho in sys.argv[1:]:
        doc = processar_pdf(caminho)
        icone = {"NF": "🟢", "SAP": "🔵", "BOLETO": "🟡", "DESCONHECIDO": "⚠️ "}.get(doc.tipo, "❓")
        print(f"  {icone} {doc.nome_arquivo} → {doc.tipo}")
        if doc.erros:
            for e in doc.erros:
                print(f"       ⚠️  {e}")
        documentos.append(doc)

    resultado = executar_matching(documentos)

    print(f"\n{'='*55}")
    print(f"  RESULTADO DO MATCHING")
    print(f"{'='*55}")

    if resultado.pares:
        print(f"\n✅ Pares/triplas encontrados ({len(resultado.pares)}):\n")
        for par in resultado.pares:
            print(f"  [{par.tipo}]")
            print(f"    NF      : {par.nf.numero_nf} | {par.nf.quantidade_ton} t | R$ {par.nf.valor_nf}")
            if par.sap:
                print(f"    SAP     : {par.sap.numero_pedido} | {par.sap.quantidade_sap_ton} t")
            if par.boleto:
                print(f"    Boleto  : venc. {par.boleto.vencimento_boleto} | R$ {par.boleto.valor_boleto}")
            if par.alertas:
                for a in par.alertas:
                    print(f"    ⚠️  {a}")
            print()

    if resultado.nfs_sem_par:
        print(f"⚠️  NFs sem par ({len(resultado.nfs_sem_par)}):")
        for nf in resultado.nfs_sem_par:
            print(f"    - NF {nf.numero_nf} | {nf.quantidade_ton} t | R$ {nf.valor_nf}")

    if resultado.boletos_sem_nf:
        print(f"\n⚠️  Boletos sem NF correspondente ({len(resultado.boletos_sem_nf)}):")
        for b in resultado.boletos_sem_nf:
            print(f"    - venc. {b.vencimento_boleto} | R$ {b.valor_boleto} | {b.nome_arquivo}")

    if resultado.saps_sem_nf:
        print(f"\n⚠️  SAPs sem NF correspondente ({len(resultado.saps_sem_nf)}):")
        for s in resultado.saps_sem_nf:
            print(f"    - {s.numero_pedido} | {s.nome_arquivo}")

    if resultado.desconhecidos:
        print(f"\n❓ Arquivos não identificados ({len(resultado.desconhecidos)}):")
        for d in resultado.desconhecidos:
            print(f"    - {d.nome_arquivo}")