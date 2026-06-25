"""
merger.py
Recebe um Par (NF + SAP + Boleto) e gera o PDF combinado
na ordem: Pedido SAP → NF-e (todas as páginas) → Boleto

Regras de nomenclatura:
  - Padrão  : DDMMAAAA_PEDIDO_4500XXXXXX.pdf
  - Data    : SEMPRE o vencimento da NF (nunca do boleto)
  - Especial: se o arquivo SAP já tiver nome customizado, preservar exatamente
"""

import re
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from matcher import Par


# ---------------------------------------------------------------------------
# Geração do nome do arquivo de saída
# ---------------------------------------------------------------------------

def _data_para_nome(data_str: str) -> str:
    """
    Converte data DD/MM/AAAA para DDMMAAAA (formato do nome do arquivo).
    Retorna string vazia se a data for inválida.
    """
    if not data_str:
        return ""
    match = re.match(r"(\d{2})/(\d{2})/(\d{4})", data_str)
    if match:
        return f"{match.group(1)}{match.group(2)}{match.group(3)}"
    return ""


def _nome_sap_e_customizado(nome_original: str) -> bool:
    """
    Verifica se o nome original do SAP já é um nome customizado
    (ex: '25062026_PEDIDO_4500034717_NF_414445_LANÇAR_URGENTE').
    Critério: começa com 8 dígitos (data DDMMAAAA) seguido de _PEDIDO_.
    """
    return bool(re.match(r"^\d{8}_PEDIDO_", nome_original or ""))


def gerar_nome_saida(par: Par) -> str:
    """
    Gera o nome do arquivo PDF de saída conforme as regras do projeto.
    Formato: DDMMAAAA_PEDIDO_{numero_pedido}.pdf

    Regras (em ordem de prioridade):
    1. SAP com nome customizado → preservar exatamente o nome original
    2. Data = SEMPRE vencimento da NF (nunca do boleto)
    3. Sem vencimento na NF → prefixo "SEMDATA"
    4. Sem SAP no par → número do pedido = "SEMPEDIDO"
    """
    nf = par.nf
    sap = par.sap

    # Regra especial: SAP com nome customizado → preservar exatamente
    if sap and _nome_sap_e_customizado(sap.nome_original):
        return f"{sap.nome_original}.pdf"

    # Data: SEMPRE vencimento da NF
    data_str = _data_para_nome(nf.vencimento_nf) if nf.vencimento_nf else ""
    if not data_str:
        data_str = "SEMDATA"

    # Número do pedido SAP
    numero_pedido = sap.numero_pedido if sap else "SEMPEDIDO"

    return f"{data_str}_PEDIDO_{numero_pedido}.pdf"


# ---------------------------------------------------------------------------
# Combinação dos PDFs
# ---------------------------------------------------------------------------

def combinar_pdfs(par: Par, pasta_saida: str) -> dict:
    """
    Combina os PDFs do par na ordem: SAP → NF → Boleto.
    Grava o resultado em pasta_saida.

    Retorna dict com:
      - sucesso (bool)
      - caminho_saida (str)
      - nome_arquivo (str)
      - erro (str) — preenchido se sucesso=False
    """
    writer = PdfWriter()
    ordem = []

    # Montar ordem de inclusão
    if par.sap:
        ordem.append(("SAP", par.sap.caminho))
    ordem.append(("NF", par.nf.caminho))
    if par.boleto:
        ordem.append(("Boleto", par.boleto.caminho))

    # Adicionar páginas de cada documento
    for tipo_doc, caminho in ordem:
        try:
            reader = PdfReader(caminho)
            if reader.is_encrypted:
                # Tenta descriptografar com senha vazia (proteção de impressão/edição)
                resultado = reader.decrypt("")
                if resultado == 0:
                    return {
                        "sucesso": False,
                        "caminho_saida": "",
                        "nome_arquivo": "",
                        "erro": (
                            f"PDF protegido por senha (não foi possível abrir): "
                            f"{Path(caminho).name}. Abra o arquivo manualmente, "
                            f'salve sem senha e tente novamente.'
                        ),
                    }
            for pagina in reader.pages:
                writer.add_page(pagina)
        except Exception as e:
            return {
                "sucesso": False,
                "caminho_saida": "",
                "nome_arquivo": "",
                "erro": f"Erro ao ler {Path(caminho).name}: {str(e)}",
            }

    # Gerar nome e caminho de saída
    nome_arquivo = gerar_nome_saida(par)
    Path(pasta_saida).mkdir(parents=True, exist_ok=True)
    caminho_saida = str(Path(pasta_saida) / nome_arquivo)

    # Gravar PDF combinado
    try:
        with open(caminho_saida, "wb") as f:
            writer.write(f)
    except Exception as e:
        return {
            "sucesso": False,
            "caminho_saida": "",
            "nome_arquivo": nome_arquivo,
            "erro": f"Erro ao gravar arquivo de saída: {str(e)}",
        }

    return {
        "sucesso": True,
        "caminho_saida": caminho_saida,
        "nome_arquivo": nome_arquivo,
        "erro": "",
    }


def processar_lote(resultado_matching, pasta_saida: str) -> list:
    """
    Processa todos os pares de um ResultadoMatching e retorna
    lista de resultados de cada combinação.
    """
    resultados = []

    for par in resultado_matching.pares:
        res = combinar_pdfs(par, pasta_saida)
        res["par"] = par
        res["alertas"] = par.alertas
        resultados.append(res)

    return resultados


# ---------------------------------------------------------------------------
# Execução direta (teste via terminal)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from extractor import processar_pdf
    from matcher import executar_matching

    if len(sys.argv) < 3:
        print("Uso: py merger.py <pasta_saida> <pdf1> <pdf2> ...")
        print("Exemplo: py merger.py output\\ NF.pdf PEDIDO.pdf")
        sys.exit(1)

    pasta_saida = sys.argv[1]
    caminhos = sys.argv[2:]

    print("\n📂 Processando arquivos...\n")
    documentos = []
    for caminho in caminhos:
        doc = processar_pdf(caminho)
        icone = {"NF": "🟢", "SAP": "🔵", "BOLETO": "🟡", "DESCONHECIDO": "⚠️ "}.get(doc.tipo, "❓")
        print(f"  {icone} {doc.nome_arquivo} → {doc.tipo}")
        documentos.append(doc)

    resultado = executar_matching(documentos)

    print(f"\n📄 Gerando PDFs em: {pasta_saida}\n")
    resultados = processar_lote(resultado, pasta_saida)

    for res in resultados:
        if res["sucesso"]:
            print(f"  ✅ {res['nome_arquivo']}")
            for a in res.get("alertas", []):
                print(f"     ⚠️  {a}")
        else:
            print(f"  ❌ Erro: {res['erro']}")

    if resultado.nfs_sem_par:
        print(f"\n⚠️  NFs sem par (não geradas):")
        for nf in resultado.nfs_sem_par:
            print(f"    - NF {nf.numero_nf}")

    if resultado.boletos_sem_nf:
        print(f"\n⚠️  Boletos sem NF correspondente:")
        for b in resultado.boletos_sem_nf:
            print(f"    - {b.nome_arquivo} | R$ {b.valor_boleto}")

    if resultado.saps_sem_nf:
        print(f"\n⚠️  SAPs sem NF correspondente:")
        for s in resultado.saps_sem_nf:
            print(f"    - {s.numero_pedido} | {s.nome_arquivo}")

    if resultado.desconhecidos:
        print(f"\n❓ Arquivos não identificados:")
        for d in resultado.desconhecidos:
            print(f"    - {d.nome_arquivo}")

    ok = len([r for r in resultados if r["sucesso"]])
    print(f"\n✅ Concluído. {ok} arquivo(s) gerado(s) em '{pasta_saida}'")