"""
extractor.py
Identifica o tipo de cada PDF (NF-e, Boleto, Pedido SAP) e extrai
os campos necessários via Gemini AI. Regex como fallback offline.
"""

import re
import os
import json
import base64
import pdfplumber
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Rodízio de chaves Gemini
# ---------------------------------------------------------------------------

_GEMINI_KEYS_ENV = os.environ.get("GEMINI_API_KEYS", "")
_GEMINI_KEY_SINGLE = os.environ.get("GEMINI_API_KEY", "")

if _GEMINI_KEYS_ENV:
    _GEMINI_KEY_LIST = [k.strip() for k in _GEMINI_KEYS_ENV.split(",") if k.strip()]
elif _GEMINI_KEY_SINGLE:
    _GEMINI_KEY_LIST = [_GEMINI_KEY_SINGLE]
else:
    _GEMINI_KEY_LIST = []

# FIX Bug 3: índice de rodízio começa sempre do zero; cada ciclo de chamadas
# reseta para a primeira chave disponível, evitando acumulação entre sessões.
_GEMINI_KEY_INDEX = 0

GEMINI_API_KEY = _GEMINI_KEY_LIST[0] if _GEMINI_KEY_LIST else ""


def _gemini_generate(contents, max_tokens=512) -> Optional[str]:
    """Chama Gemini com rodízio automático de chaves em caso de quota 429."""
    global _GEMINI_KEY_INDEX
    if not _GEMINI_KEY_LIST:
        return None

    from google import genai
    from google.genai import types
    from google.genai.errors import ClientError

    for tentativa in range(len(_GEMINI_KEY_LIST)):
        key = _GEMINI_KEY_LIST[_GEMINI_KEY_INDEX % len(_GEMINI_KEY_LIST)]
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=contents,
                config=types.GenerateContentConfig(temperature=0, max_output_tokens=max_tokens)
            )
            # FIX Bug 3: reset do índice ao ter sucesso garante que a próxima
            # chamada começa pela mesma chave que funcionou (menor latência).
            return response.text
        except ClientError as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                _GEMINI_KEY_INDEX += 1
                continue
            raise
        except Exception:
            raise

    return None


# ---------------------------------------------------------------------------
# Dataclass principal
# ---------------------------------------------------------------------------

@dataclass
class DocumentoFiscal:
    caminho: str
    nome_arquivo: str
    tipo: str
    texto_completo: str = ""

    numero_nf: Optional[str] = None
    valor_nf: Optional[float] = None
    quantidade_ton: Optional[float] = None
    vencimento_nf: Optional[str] = None
    descricao_produto: Optional[str] = None
    ncm_produto: Optional[str] = None
    valor_unitario: Optional[float] = None
    emitente: Optional[str] = None

    valor_boleto: Optional[float] = None
    vencimento_boleto: Optional[str] = None
    beneficiario: Optional[str] = None
    pagador: Optional[str] = None

    numero_pedido: Optional[str] = None
    quantidade_sap_ton: Optional[float] = None
    valor_liquido_sap: Optional[float] = None
    nome_original: Optional[str] = None

    erros: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Extração de texto via pdfplumber
# ---------------------------------------------------------------------------

def extrair_texto(caminho: str) -> str:
    texto = []
    try:
        with pdfplumber.open(caminho) as pdf:
            # Tenta descriptografar silenciosamente se necessário
            for pagina in pdf.pages:
                t = pagina.extract_text()
                if t:
                    texto.append(t)
    except Exception:
        return ""
    return "\n".join(texto)


# ---------------------------------------------------------------------------
# OCR via Gemini Vision (PDFs escaneados)
# ---------------------------------------------------------------------------

def _pdf_para_imagem_base64(caminho: str, pagina: int = 0) -> Optional[str]:
    try:
        import fitz
        doc = fitz.open(caminho)
        page = doc[pagina]
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        return base64.b64encode(img_bytes).decode("utf-8")
    except Exception as e:
        return None



# ---------------------------------------------------------------------------
# OCR via Tesseract (fallback offline quando Gemini Vision falha)
# ---------------------------------------------------------------------------

import sys as _sys, os as _os
def _get_tesseract_cmd():
    # PyInstaller: usa tesseract bundlado na pasta do executavel
    if getattr(_sys, "frozen", False):
        base = _os.path.dirname(_sys.executable)
        bundled = _os.path.join(base, "tesseract", "tesseract.exe")
        if _os.path.exists(bundled):
            return bundled
    # Desenvolvimento: usa PATH do sistema
    return r"C:\Program Files\Tesseract-OCR\tesseract.exe"

TESSERACT_CMD = _get_tesseract_cmd()


def _extrair_texto_tesseract(caminho: str) -> str:
    """
    Extrai texto de PDF escaneado via Tesseract OCR.
    Retorna string vazia se Tesseract não estiver disponível.
    """
    try:
        import pytesseract
        from PIL import Image
        import io

        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

        import fitz
        doc = fitz.open(caminho)
        textos = []
        for page in doc:
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            texto = pytesseract.image_to_string(img, lang="por+eng")
            if texto.strip():
                textos.append(texto)
        return "\n".join(textos)
    except Exception:
        return ""

_PROMPT_VISION = """Analise este documento fiscal brasileiro e extraia os dados.
Identifique o tipo do documento e retorne APENAS um JSON válido.

Se for DANFE/NF-e:
{"tipo": "NF", "numero_nf": "...", "valor_total": ..., "quantidade_ton": ..., "vencimento": "DD/MM/AAAA"}

Se for Boleto bancário:
{"tipo": "BOLETO", "valor": ..., "vencimento": "DD/MM/AAAA", "beneficiario": "...", "pagador": "..."}

Se for Pedido SAP:
{"tipo": "SAP", "numero_pedido": "...", "quantidade_ton": ..., "valor_liquido": ...}

Se nao conseguir identificar:
{"tipo": "DESCONHECIDO"}

Regras:
- numero_nf: apenas digitos, sem zeros a esquerda
- quantidade_ton: sempre em toneladas. Se unidade for KG, divida por 1000. Formatos possiveis: "25.080,000 t" (BR) ou "25,080.0000 KG" (americano). Exemplo KG americano: 25080 KG = 25.080 t
- valores: float com ponto decimal (ex: 510455.53)
- vencimento: formato DD/MM/AAAA
- Use null para campos nao encontrados

Responda APENAS com o JSON, sem markdown."""


def _extrair_via_gemini_vision(caminho: str) -> Optional[dict]:
    """
    Tenta extrair dados de um PDF escaneado via Gemini Vision.
    Estratégia 1: envia o PDF diretamente (melhor qualidade).
    Estratégia 2 (fallback): converte a 1ª página para PNG via PyMuPDF.
    Retorna dict com os dados ou None se ambas as estratégias falharem.
    """
    if not _GEMINI_KEY_LIST:
        return None

    from google import genai
    from google.genai import types
    from google.genai.errors import ClientError

    def _tentar_com_conteudo(conteudo_parts: list) -> Optional[dict]:
        """Tenta todas as chaves disponíveis para um dado conteúdo."""
        global _GEMINI_KEY_INDEX
        for _ in range(len(_GEMINI_KEY_LIST)):
            key = _GEMINI_KEY_LIST[_GEMINI_KEY_INDEX % len(_GEMINI_KEY_LIST)]
            try:
                client = genai.Client(api_key=key)
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=conteudo_parts,
                    config=types.GenerateContentConfig(temperature=0, max_output_tokens=512)
                )
                raw = re.sub(r"```json|```", "", response.text.strip()).strip()
                return json.loads(raw)
            except ClientError as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    _GEMINI_KEY_INDEX += 1
                    continue
                # FIX Bug 1: propaga erros de autenticação/permissão
                raise
            except json.JSONDecodeError:
                # Resposta não era JSON válido — não tenta mais com essa chave
                return None
        return None

    # --- Estratégia 1: PDF completo ---
    try:
        with open(caminho, "rb") as f:
            pdf_bytes = f.read()
        partes = [
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            _PROMPT_VISION,
        ]
        resultado = _tentar_com_conteudo(partes)
        if resultado is not None:
            return resultado
    except Exception as e:
        # Falha ao abrir/enviar PDF — tenta estratégia de imagem
        pass

    # --- Estratégia 2: PNG da primeira página (fallback para PDFs problemáticos) ---
    try:
        img_b64 = _pdf_para_imagem_base64(caminho)
        if not img_b64:
            return None
        img_bytes = base64.b64decode(img_b64)
        partes = [
            types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            _PROMPT_VISION,
        ]
        return _tentar_com_conteudo(partes)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Identificação de tipo
# ---------------------------------------------------------------------------

def _identificar_tipo_via_gemini(texto: str, nome_arquivo: str) -> Optional[str]:
    if not _GEMINI_KEY_LIST:
        return None
    try:
        prompt = f"""Classifique o documento abaixo em uma das categorias:
- NF: Nota Fiscal Eletrônica (DANFE)
- BOLETO: Boleto bancário
- SAP: Pedido de compra SAP (contém número 4500XXXXXX)
- DESCONHECIDO

Nome do arquivo: {nome_arquivo}
Texto (primeiros 2000 chars): {texto[:2000]}

Responda APENAS com uma palavra: NF, BOLETO, SAP ou DESCONHECIDO"""

        resultado = _gemini_generate(prompt, max_tokens=10)
        if resultado:
            resultado = resultado.strip().upper()
            if resultado in ("NF", "BOLETO", "SAP", "DESCONHECIDO"):
                return resultado
        return None
    except Exception:
        return None


def identificar_tipo(texto: str, nome_arquivo: str) -> str:
    tipo_gemini = _identificar_tipo_via_gemini(texto, nome_arquivo)
    if tipo_gemini:
        return tipo_gemini
    texto_lower = texto.lower()
    nome_lower = nome_arquivo.lower()
    if any(t in texto_lower for t in ["danfe", "chave de acesso", "protocolo de autorizacao", "protocolo de autorizacao"]):
        return "NF"
    if re.search(r"\d{44}", nome_arquivo):
        return "NF"
    if re.search(r"n[oº°]\s*do\s*pedido\s*[:\s]*45\d{8}", texto_lower):
        return "SAP"
    if "pedido" in nome_lower or "4500" in nome_arquivo:
        return "SAP"
    if re.search(r"45\d{8}", texto) and "pedido" in texto_lower:
        return "SAP"
    # Boleto — padroes normais
    if "ficha de compensacao" in texto_lower or "linha digitavel" in texto_lower:
        return "BOLETO"
    if "vencimento" in texto_lower and ("beneficiario" in texto_lower or "pagador" in texto_lower):
        return "BOLETO"
    # Boleto — tolerante a OCR impreciso (Unicred, Sofisa escaneados)
    # "fencimento" = OCR de "Vencimento"; "agador" = OCR de "Pagador"
    if re.search(r"[Vvf][aei]+ncimento", texto) and re.search(r"[Pp]?agador", texto):
        return "BOLETO"
    if re.search(r"recibo\s+do\s+pagador", texto_lower):
        return "BOLETO"
    if re.search(r"nosso\s+n[uo]mero", texto_lower) and re.search(r"\d{2}/\d{2}/\d{4}", texto):
        return "BOLETO"
    if "unicred" in texto_lower or "sofisa" in texto_lower or "ficha de caixa" in texto_lower:
        if re.search(r"\d{2}/\d{2}/\d{4}", texto):
            return "BOLETO"
    return "DESCONHECIDO"

def _parse_valor_br(texto_valor: str) -> Optional[float]:
    try:
        limpo = re.sub(r"[^\d,]", "", texto_valor).replace(",", ".")
        partes = limpo.split(".")
        if len(partes) > 2:
            limpo = "".join(partes[:-1]) + "." + partes[-1]
        return float(limpo)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Extração de campos — NF-e
# ---------------------------------------------------------------------------


def _parse_valor_us(texto_valor: str) -> Optional[float]:
    """Parse de valor em formato americano: 313,665.99 -> 313665.99"""
    try:
        limpo = re.sub(r"[^\d,.]", "", texto_valor)
        # Formato americano: virgula=milhar, ponto=decimal
        if "," in limpo and "." in limpo and limpo.rindex(",") < limpo.rindex("."):
            limpo = limpo.replace(",", "")
            return float(limpo)
        return _parse_valor_br(texto_valor)
    except Exception:
        return None

def _extrair_nf_via_gemini(texto: str, doc: DocumentoFiscal) -> bool:
    if not _GEMINI_KEY_LIST:
        return False
    try:
        prompt = f"""Você é um extrator de dados de Notas Fiscais Eletrônicas brasileiras (DANFE/NF-e).
Analise o texto abaixo e retorne APENAS um JSON válido.

Campos:
- numero_nf: número da nota fiscal (apenas dígitos, sem zeros à esquerda, sem pontos). Ex: "7309"
- valor_total: valor total da nota em float. Ex: 586373.69
- quantidade_ton: quantidade em TONELADAS em float. Unidades: TON, TML, T, KG. Ex: 25.388
- vencimento: data de vencimento DD/MM/AAAA. Procure em FATURA/DUPLICATA. Ex: "23/06/2026"
- descricao_produto: descrição do produto principal em DADOS DOS PRODUTOS/SERVIÇOS. Ex: "LINGOTE DE ALUMINIO P1020"
- ncm: código NCM/SH do produto principal (8 dígitos). Ex: "76011000"
- valor_unitario: valor unitário do produto principal em float. Ex: 22511.199
- emitente: razão social do emitente (quem emitiu a NF). Ex: "ABM TRADING IMPORTACAO E EXPORTACAO LTDA"

Se algum campo não for encontrado, use null.

Texto: {texto[:5000]}

Responda APENAS com JSON: {{"numero_nf": "...", "valor_total": ..., "quantidade_ton": ..., "vencimento": "DD/MM/AAAA", "descricao_produto": "...", "ncm": "...", "valor_unitario": ..., "emitente": "..."}}"""

        raw = _gemini_generate(prompt, max_tokens=256)
        if not raw:
            return False

        raw = re.sub(r"```json|```", "", raw.strip()).strip()
        dados = json.loads(raw)

        doc.numero_nf = str(dados.get("numero_nf") or "").lstrip("0") or None
        doc.valor_nf = float(dados["valor_total"]) if dados.get("valor_total") is not None else None
        doc.quantidade_ton = float(dados["quantidade_ton"]) if dados.get("quantidade_ton") is not None else None
        doc.vencimento_nf = dados.get("vencimento") or None
        doc.descricao_produto = dados.get("descricao_produto") or None
        doc.ncm_produto = str(dados.get("ncm") or "") or None
        doc.valor_unitario = float(dados["valor_unitario"]) if dados.get("valor_unitario") is not None else None
        doc.emitente = dados.get("emitente") or None
        return True
    except Exception as e:
        doc.erros.append(f"Gemini NF indisponível ({str(e)[:60]}) — usando regex")
        return False


def extrair_campos_nf(texto: str, doc: DocumentoFiscal):
    if _extrair_nf_via_gemini(texto, doc):
        return

    match = re.search(r"n[oº°]\.?\s*\.?\s*([\d][\d\.]{0,11})", texto, re.IGNORECASE | re.MULTILINE)
    if match:
        doc.numero_nf = match.group(1).replace(".", "").lstrip("0") or "0"

    match = re.search(r"valor\s*total\s*da\s*nota[^\n]*\n([^\n]+)", texto, re.IGNORECASE)
    if match:
        valores = re.findall(r"[\d\.]+,\d{2}", match.group(1).strip())
        if valores:
            doc.valor_nf = _parse_valor_br(valores[-1])

    match = re.search(r"\b(TON|TML|KG)\s+([\d]+[,\.]\d+)\s+[\d]", texto, re.IGNORECASE)
    if match:
        qtd = _parse_valor_br(match.group(2))
        doc.quantidade_ton = qtd if match.group(1).lower() in ("ton", "tml") else (qtd / 1000 if qtd else None)

    match = re.search(r"venc\.?(?:imento)?[\s:]*(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
    if not match:
        match = re.search(r"^\d{3}\s+(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE | re.MULTILINE)
    if match:
        doc.vencimento_nf = match.group(1)

    # Fallback regex para descrição do produto
    if not doc.descricao_produto:
        m = re.search(r'DADOS DOS PRODUTOS.*?\n.*?\d{4,}\s+(.+?)\s+\d{8}', texto, re.IGNORECASE | re.DOTALL)
        if m:
            doc.descricao_produto = m.group(1).strip()[:80]

    # Fallback regex para NCM
    if not doc.ncm_produto:
        m = re.search(r'\b(\d{8})\b', texto)
        if m:
            doc.ncm_produto = m.group(1)

    # Fallback regex para emitente (razão social antes do CNPJ do emitente)
    if not doc.emitente:
        m = re.search(r'RECEBEMOS DE (.+?) OS PRODUTOS', texto, re.IGNORECASE)
        if m:
            doc.emitente = m.group(1).strip()

    if not doc.numero_nf: doc.erros.append("Número da NF não encontrado")
    if doc.valor_nf is None: doc.erros.append("Valor total da NF não encontrado")
    # Fallback formato americano (Dow Brasil): "25,080.0000 KG"
    if doc.quantidade_ton is None:
        m = re.search(r"KG\s+([\d,]+\.[\d]+)", texto, re.IGNORECASE)
        if not m:
            m = re.search(r"([\d,]+\.[\d]+)\s*KG", texto, re.IGNORECASE)
        if m:
            import re as _re2
            raw = m.group(1).replace(",", "")
            try:
                val = float(raw)
                doc.quantidade_ton = round(val / 1000, 5) if val > 100 else val
            except Exception:
                pass
    # Fallback valor total formato americano (maior valor com milhar separado por virgula)
    if doc.valor_nf is None or doc.valor_nf < 1000:
        import re as _re3
        vals = _re3.findall(r"[\d]{1,3}(?:,[\d]{3})+\.[\d]{2}", texto)
        candidatos = []
        for v in vals:
            try:
                candidatos.append(float(v.replace(",", "")))
            except Exception:
                pass
        candidatos = [c for c in candidatos if c > 1000]
        if candidatos:
            doc.valor_nf = max(candidatos)
    # Fallback vencimento formato DD.MM.AAAA (Dow Brasil)
    if not doc.vencimento_nf:
        # Procura data apos a palavra VENCIMENTO ou NUMERO+VENCIMENTO
        m = re.search(r"(?:VENCIMENTO|VENCIM)[^\d]*(\d{2})[./-](\d{2})[./-](\d{4})", texto, re.IGNORECASE)
        if m:
            doc.vencimento_nf = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
        else:
            # Pega a ultima data no formato DD.MM.AAAA (tende a ser vencimento)
            datas = re.findall(r"(\d{2})\.(\d{2})\.(\d{4})", texto)
            datas_futuras = [d for d in datas if int(d[1]) > 6 or int(d[2]) > 2026]
            if datas_futuras:
                d = datas_futuras[0]
                doc.vencimento_nf = f"{d[0]}/{d[1]}/{d[2]}"
            elif datas:
                d = datas[-1]
                doc.vencimento_nf = f"{d[0]}/{d[1]}/{d[2]}"
                doc.vencimento_nf = data_str
    if doc.quantidade_ton is None: doc.erros.append("Quantidade não encontrada na NF")


# ---------------------------------------------------------------------------
# Extração de campos — Boleto
# ---------------------------------------------------------------------------

def _extrair_boleto_via_gemini(texto: str, doc: DocumentoFiscal) -> bool:
    if not _GEMINI_KEY_LIST:
        return False
    try:
        prompt = f"""Você é um extrator de dados de boletos bancários brasileiros.
Analise o texto e retorne APENAS um JSON válido.

Campos:
- valor: valor do documento em float. Pode aparecer como "R$ X 190.153,40" — ignore caracteres extras. Ex: 190153.40
- vencimento: data de vencimento DD/MM/AAAA. Ex: "22/06/2026"
- beneficiario: nome do beneficiário (quem recebe). Ex: "ABM TRADING IMPORTACAO E EXPORTACAO LTDA"
- pagador: nome do pagador (quem paga). Ex: "COLUMBIA DISTRIBUIDORA S/A"

Se algum campo não for encontrado, use null.

Texto: {texto[:3000]}

Responda APENAS com JSON: {{"valor": ..., "vencimento": "DD/MM/AAAA", "beneficiario": "...", "pagador": "..."}}"""

        raw = _gemini_generate(prompt, max_tokens=256)
        if not raw:
            return False

        raw = re.sub(r"```json|```", "", raw.strip()).strip()
        dados = json.loads(raw)

        doc.valor_boleto = float(dados["valor"]) if dados.get("valor") is not None else None
        doc.vencimento_boleto = dados.get("vencimento") or None
        doc.beneficiario = dados.get("beneficiario") or None
        doc.pagador = dados.get("pagador") or None
        return True
    except Exception as e:
        doc.erros.append(f"Gemini Boleto indisponível ({str(e)[:60]}) — usando regex")
        return False


def _extrair_valor_boleto_fallback(texto) -> Optional[float]:
    padroes_label = [
        r"[Vvf][aio]+lor.{0,5}do.{0,5}[Dd]ocumento[^\n]{0,30}\n\s*([\d.]+,\d{2})",
        r"[Ff]encimento[^\n]*\n[\d/]+\s+([\d.]+,\d{2})",
        r"REAL\s+[t|]?\s*([\d]{1,3}(?:\.[\d]{3})+,\d{2})",
        r"[Vv]alor.{0,5}[Dd]ocumento[^\n]{0,20}([\d]{1,3}(?:\.[\d]{3})+,\d{2})",
    ]
    for padrao in padroes_label:
        m = re.search(padrao, texto, re.IGNORECASE | re.MULTILINE)
        if m:
            val = _parse_valor_br(m.group(1))
            if val and val > 1000:
                return val
    candidatos = []
    for m in re.finditer(r"([\d]{1,3}(?:\.[\d]{3})+,\d{2})", texto):
        val = _parse_valor_br(m.group(1))
        ctx = texto[max(0, m.start()-60):m.start()].upper()
        if any(p in ctx for p in ["MORA", "MULTA", "JUROS", "DESCONTO"]):
            continue
        if val and val > 1000:
            candidatos.append(val)
    return max(candidatos) if candidatos else None

def extrair_campos_boleto(texto: str, doc: DocumentoFiscal):
    if _extrair_boleto_via_gemini(texto, doc):
        if doc.valor_boleto is None:
            doc.valor_boleto = _extrair_valor_boleto_fallback(texto)
            if doc.valor_boleto:
                doc.erros = [e for e in doc.erros if "Valor" not in e]
        return

    doc.valor_boleto = _extrair_valor_boleto_fallback(texto)

    match = re.search(r"vencimento\s*[:\|\s]*(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
    if not match:
        match = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
    if match:
        doc.vencimento_boleto = match.group(1)

    match = re.search(r"benefici[aá]rio\s*[:\|\s]*(.{3,80})", texto, re.IGNORECASE)
    if match:
        doc.beneficiario = match.group(1).strip()

    match = re.search(r"pagador\s*[:\|\s]*(.{3,80})", texto, re.IGNORECASE)
    if match:
        doc.pagador = match.group(1).strip()

    if doc.valor_boleto is None: doc.erros.append("Valor do boleto não encontrado")
    if not doc.vencimento_boleto: doc.erros.append("Vencimento do boleto não encontrado")


# ---------------------------------------------------------------------------
# Extração de campos — SAP
# ---------------------------------------------------------------------------

def _extrair_sap_via_gemini(texto: str, nome_arquivo: str, doc: DocumentoFiscal) -> bool:
    if not _GEMINI_KEY_LIST:
        return False
    try:
        prompt = f"""Você é um extrator de dados de pedidos de compra SAP brasileiros.
O texto pode conter caracteres embaralhados. Analise com atenção e retorne APENAS um JSON válido.

Campos:
- numero_pedido: formato 4500XXXXXX (10 dígitos). Ex: "4500034786"
- quantidade_ton: TONELADAS em float. Pode aparecer como "t2,359" ou "2,359t". Ex: 2.359
- valor_liquido: "Valor líquido total do item". IGNORE "Valor líquido" simples. Ex: 50979.76

Se algum campo não for encontrado, use null.

Texto: {texto[:5000]}

Responda APENAS com JSON: {{"numero_pedido": "...", "quantidade_ton": ..., "valor_liquido": ...}}"""

        raw = _gemini_generate(prompt, max_tokens=256)
        if not raw:
            return False

        raw = re.sub(r"```json|```", "", raw.strip()).strip()
        dados = json.loads(raw)

        doc.numero_pedido = str(dados.get("numero_pedido") or "") or None
        doc.quantidade_sap_ton = float(dados["quantidade_ton"]) if dados.get("quantidade_ton") is not None else None
        doc.valor_liquido_sap = float(dados["valor_liquido"]) if dados.get("valor_liquido") is not None else None
        doc.nome_original = Path(nome_arquivo).stem
        return True
    except Exception as e:
        doc.erros.append(f"Gemini SAP indisponível ({str(e)[:60]}) — usando regex")
        return False


def _extrair_quantidade_sap_fallback(texto):
    padroes = [
        r"\bt\s*(\d+[,\.]\d+)",
        r"(\d+[,\.]\d+)\s*t\b",
        r"\bt\s+(\d+[,\.]\d+)\s*\n",
        r"(\d+[,\.]\d{1,3})\s*t\s+Dia",
    ]
    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            val = _parse_valor_br(match.group(1))
            if val and 0.001 < val < 100000:
                return val
    return None


def extrair_campos_sap(texto: str, nome_arquivo: str, doc: DocumentoFiscal):
    if _extrair_sap_via_gemini(texto, nome_arquivo, doc):
        doc.nome_original = doc.nome_original or Path(nome_arquivo).stem
        if doc.quantidade_sap_ton is None:
            doc.quantidade_sap_ton = _extrair_quantidade_sap_fallback(texto)
            if doc.quantidade_sap_ton:
                doc.erros = [e for e in doc.erros if "Quantidade" not in e]
        return

    match = re.search(r"(45\d{8})", texto)
    if match:
        doc.numero_pedido = match.group(1)

    doc.quantidade_sap_ton = _extrair_quantidade_sap_fallback(texto)

    match = re.search(r"valor\s*l[íi]quido\s*total\s*do\s+([\d\.]+,\d{2})", texto, re.IGNORECASE)
    if match:
        doc.valor_liquido_sap = _parse_valor_br(match.group(1))

    doc.nome_original = Path(nome_arquivo).stem

    if not doc.numero_pedido: doc.erros.append("Numero do pedido SAP não encontrado")
    # Fallback para SAP Dow Brasil: "25.080kg" (formato BR, ponto=milhar)
    if doc.quantidade_sap_ton is None:
        m = re.search(r"([\d]{1,3}(?:[.,][\d]{3})+)\s*kg", texto, re.IGNORECASE)
        if m:
            raw = m.group(1)
            # Formato BR: ponto=milhar, virgula=decimal -> 25.080 = 25,080 t
            if "." in raw and "," not in raw:
                # 25.080 -> partes separadas por ponto
                partes = raw.split(".")
                if all(len(p) == 3 for p in partes[1:]):  # milhar
                    raw = raw.replace(".", "")
                    doc.quantidade_sap_ton = float(raw) / 1000
                else:
                    doc.quantidade_sap_ton = float(raw.replace(".", ",").replace(",", "."))
            elif "," in raw:
                doc.quantidade_sap_ton = float(raw.replace(".", "").replace(",", "."))
            else:
                doc.quantidade_sap_ton = float(raw) / 1000
    if doc.quantidade_sap_ton is None: doc.erros.append("Quantidade não encontrada no pedido SAP")


# ---------------------------------------------------------------------------
# Preencher campos a partir de resultado OCR Vision
# ---------------------------------------------------------------------------

def _preencher_campos_de_ocr(doc: DocumentoFiscal, dados_ocr: dict):
    """
    FIX Bug 2: centraliza o preenchimento de campos vindos do OCR Vision,
    com validação e registro de erros por campo.
    """
    tipo = dados_ocr.get("tipo", "DESCONHECIDO")
    doc.tipo = tipo

    if tipo == "NF":
        doc.numero_nf = str(dados_ocr.get("numero_nf") or "").lstrip("0") or None
        doc.valor_nf = float(dados_ocr["valor_total"]) if dados_ocr.get("valor_total") is not None else None
        doc.quantidade_ton = float(dados_ocr["quantidade_ton"]) if dados_ocr.get("quantidade_ton") is not None else None
        doc.vencimento_nf = dados_ocr.get("vencimento")
        if not doc.numero_nf: doc.erros.append("OCR: número da NF não extraído")
        if doc.valor_nf is None: doc.erros.append("OCR: valor total não extraído")
        if doc.quantidade_ton is None: doc.erros.append("OCR: quantidade não extraída")
        if not doc.vencimento_nf: doc.erros.append("OCR: vencimento não extraído")

    elif tipo == "BOLETO":
        doc.valor_boleto = float(dados_ocr["valor"]) if dados_ocr.get("valor") is not None else None
        doc.vencimento_boleto = dados_ocr.get("vencimento")
        doc.beneficiario = dados_ocr.get("beneficiario")
        doc.pagador = dados_ocr.get("pagador")
        if doc.valor_boleto is None: doc.erros.append("OCR: valor do boleto não extraído")
        if not doc.vencimento_boleto: doc.erros.append("OCR: vencimento não extraído")

    elif tipo == "SAP":
        doc.numero_pedido = str(dados_ocr.get("numero_pedido") or "") or None
        doc.quantidade_sap_ton = float(dados_ocr["quantidade_ton"]) if dados_ocr.get("quantidade_ton") is not None else None
        doc.valor_liquido_sap = float(dados_ocr["valor_liquido"]) if dados_ocr.get("valor_liquido") is not None else None
        doc.nome_original = Path(doc.nome_arquivo).stem
        if not doc.numero_pedido: doc.erros.append("OCR: número do pedido não extraído")
        if doc.quantidade_sap_ton is None: doc.erros.append("OCR: quantidade não extraída")

    else:
        doc.erros.append("OCR: documento identificado como DESCONHECIDO pelo Gemini Vision")


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def processar_pdf(caminho: str) -> DocumentoFiscal:
    nome_arquivo = Path(caminho).name
    doc = DocumentoFiscal(caminho=caminho, nome_arquivo=nome_arquivo, tipo="DESCONHECIDO")

    texto = extrair_texto(caminho)

    # PDF escaneado (sem camada de texto extraível)
    if not texto.strip():
        doc.erros.append("PDF escaneado — sem texto extraível, acionando Gemini Vision")
        dados_ocr = _extrair_via_gemini_vision(caminho)

        if dados_ocr is None:
            # Gemini Vision falhou — tenta Tesseract como fallback offline
            doc.erros.append("Gemini Vision indisponível — tentando OCR local (Tesseract)")
            texto_ocr = _extrair_texto_tesseract(caminho)
            if texto_ocr.strip():
                doc.texto_completo = texto_ocr
                doc.tipo = identificar_tipo(texto_ocr, nome_arquivo)
                if doc.tipo == "NF":
                    extrair_campos_nf(texto_ocr, doc)
                elif doc.tipo == "BOLETO":
                    extrair_campos_boleto(texto_ocr, doc)
                elif doc.tipo == "SAP":
                    extrair_campos_sap(texto_ocr, nome_arquivo, doc)
                if doc.tipo != "DESCONHECIDO":
                    doc.erros = [e for e in doc.erros if "Gemini Vision" not in e]
                    doc.erros.append("Identificado via Tesseract OCR (offline)")
            else:
                doc.erros.append(
                    "Tesseract OCR também falhou. Verifique se o Tesseract está instalado "
                    "ou configure as chaves Gemini em Configurações."
                )
            return doc

        if dados_ocr.get("tipo") in ("NF", "BOLETO", "SAP"):
            _preencher_campos_de_ocr(doc, dados_ocr)
        else:
            doc.tipo = "DESCONHECIDO"
            doc.erros.append(
                "Gemini Vision identificou o documento como DESCONHECIDO. "
                "Revise manualmente."
            )

        return doc

    # PDF com texto extraível — fluxo normal
    doc.texto_completo = texto
    doc.tipo = identificar_tipo(texto, nome_arquivo)

    if doc.tipo == "NF":
        extrair_campos_nf(texto, doc)
    elif doc.tipo == "BOLETO":
        extrair_campos_boleto(texto, doc)
    elif doc.tipo == "SAP":
        extrair_campos_sap(texto, nome_arquivo, doc)

    return doc


# ---------------------------------------------------------------------------
# Execução direta (teste via terminal)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: py extractor.py <caminho_do_pdf>")
        sys.exit(1)

    doc = processar_pdf(sys.argv[1])

    print(f"\n{'='*50}")
    print(f"Arquivo : {doc.nome_arquivo}")
    print(f"Tipo    : {doc.tipo}")
    print(f"{'='*50}")

    if doc.tipo == "NF":
        print(f"Número NF     : {doc.numero_nf}")
        print(f"Valor total   : R$ {doc.valor_nf}")
        print(f"Quantidade    : {doc.quantidade_ton} t")
        print(f"Vencimento    : {doc.vencimento_nf}")
    elif doc.tipo == "BOLETO":
        print(f"Valor         : R$ {doc.valor_boleto}")
        print(f"Vencimento    : {doc.vencimento_boleto}")
        print(f"Beneficiário  : {doc.beneficiario}")
        print(f"Pagador       : {doc.pagador}")
    elif doc.tipo == "SAP":
        print(f"Nº Pedido     : {doc.numero_pedido}")
        print(f"Quantidade    : {doc.quantidade_sap_ton} t")
        print(f"Valor líquido : R$ {doc.valor_liquido_sap}")
        print(f"Nome original : {doc.nome_original}")
    else:
        print("⚠️  Arquivo não identificado")

    if doc.erros:
        print(f"\nAvisos/erros:")
        for e in doc.erros:
            print(f"   - {e}")