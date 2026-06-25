# SIA — Sistema Identificador de Arquivos

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-6.x-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Gemini_AI-2.0_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Tesseract](https://img.shields.io/badge/Tesseract_OCR-5.5-FF6B35?style=for-the-badge)
![Release](https://img.shields.io/github/v/release/ramon-nsz/SIA-Sistema-Identificador-de-Arquivos?style=for-the-badge&color=blue)
![Platform](https://img.shields.io/badge/Windows_10%2F11-0078D4?style=for-the-badge&logo=windows&logoColor=white)

**Automacao inteligente de documentos fiscais brasileiros com IA e OCR**

[Download](https://github.com/ramon-nsz/SIA-Sistema-Identificador-de-Arquivos/releases/latest) · [Reportar Bug](https://github.com/ramon-nsz/SIA-Sistema-Identificador-de-Arquivos/issues)

</div>

---

## Sobre o Projeto

O **SIA (Sistema Identificador de Arquivos)** automatiza a organizacao de documentos fiscais brasileiros. Desenvolvido para equipes de contas a pagar, elimina o trabalho manual de identificar, casar e combinar NF-e, Boletos e Pedidos SAP em um unico fluxo.

**O problema que resolve:** em operacoes de compras, e comum receber dezenas de PDFs por dia sem organizacao. O processo manual de identificar cada documento, casar a NF com o pedido SAP (por quantidade) e com o boleto (por valor), e gerar um PDF unico consome horas e esta sujeito a erros. O SIA faz tudo em segundos.

---

## Funcionalidades

| Funcionalidade | Descricao |
|---|---|
| Identificacao com IA | Classifica NF-e, Boletos e Pedidos SAP via Gemini AI |
| OCR Offline | Processa documentos escaneados via Tesseract (sem internet) |
| Matching Inteligente | Casa NF x SAP por quantidade (0.002t) e NF x Boleto por valor (R$1,00) |
| Geracao de PDFs | Combina documentos na ordem: SAP + NF-e + Boleto |
| Dashboard Visual | Graficos, cards de resumo e tabela do lote processado |
| Relatorio Excel | Exporta .xlsx com 4 abas: Lote, Vencimentos, Resumo e Graficos |
| Configuracao Guiada | Setup intuitivo para chave Gemini na primeira abertura |
| Rodizio de Chaves | Alterna entre multiplas chaves Gemini automaticamente |
| Portavel | Executavel unico, sem instalacao — Tesseract ja incluso |

---

## Tecnologias

- **Python 3.10+** — linguagem principal
- **PyQt6** — interface grafica desktop
- **Google Gemini AI 2.0 Flash** — identificacao e extracao de campos
- **Tesseract OCR 5.5** — OCR para PDFs escaneados (bundlado)
- **pdfplumber / pypdf / PyMuPDF** — processamento de PDFs
- **openpyxl** — geracao de planilhas Excel
- **PyInstaller** — empacotamento em executavel Windows

---

## Estrutura de Pastas
SIA-Sistema-Identificador-de-Arquivos/

├── main.py                  # Entry point — interface PyQt6

├── src/

│   ├── extractor.py         # Identificacao e extracao de campos

│   ├── matcher.py           # Casamento NF x SAP x Boleto

│   ├── merger.py            # Combinacao de PDFs

│   ├── reporter.py          # Relatorio Excel

│   ├── dashboard.py         # Dashboard visual

│   ├── config_manager.py    # Configuracoes do usuario

│   └── setup_dialog.py      # Tela de configuracao inicial

└── tesseract/               # Binarios do Tesseract (bundlados)

├── tesseract.exe

└── tessdata/

├── por.traineddata

└── eng.traineddata
---

## Instalacao e Uso

### Executavel (recomendado)

1. Acesse [Releases](https://github.com/ramon-nsz/SIA-Sistema-Identificador-de-Arquivos/releases/latest)
2. Baixe `SIA-v1.0-windows.zip`
3. Extraia e execute `SIA.exe`

### Codigo-fonte

```bash
git clone https://github.com/ramon-nsz/SIA-Sistema-Identificador-de-Arquivos.git
cd SIA-Sistema-Identificador-de-Arquivos
pip install pyqt6 pdfplumber pypdf pymupdf google-genai pytesseract openpyxl pillow python-dotenv
python main.py
```

---

## Configuracao da API Gemini

1. Acesse [aistudio.google.com](https://aistudio.google.com)
2. Faca login com sua conta Google
3. Clique em **Get API key** e depois **Create API key**
4. Abra o SIA, clique no icone de configuracoes e cole sua chave

A API Gemini tem camada gratuita com 1.500 requisicoes/dia — suficiente para uso diario.

---

## Nomenclatura dos arquivos gerados
DDMMAAAA_PEDIDO_4500XXXXXX.pdf
Exemplo: `22062026_PEDIDO_4500034730.pdf`

---

## Troubleshooting

**Documento retorna "Nao identificado"**
- Verifique se a chave Gemini esta configurada
- Aguarde o reset da quota (21h de Brasilia) ou adicione mais chaves
- O Tesseract OCR e acionado automaticamente como fallback

**Valor do boleto incorreto**
- PDFs digitais tem extracao mais precisa que escaneados
- Boletos sem par podem ser anexados manualmente via script pypdf

**Executavel bloqueado pelo antivirus**
- Adicione o SIA.exe as excecoes — executaveis PyInstaller sao frequentemente sinalizados como falso-positivo
- O codigo-fonte completo esta disponivel para auditoria

---

## Roadmap

- [x] Identificacao automatica de NF-e, Boleto e SAP
- [x] OCR offline via Tesseract
- [x] Dashboard visual
- [x] Exportacao Excel
- [x] Tela de configuracao Gemini
- [x] Executavel portavel Windows
- [ ] Suporte a CT-e e NFS-e
- [ ] Historico de lotes processados
- [ ] Integracao com Google Drive
- [ ] Versao macOS/Linux

---

## Autor

**Ramon Nunes**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Ramon_Nunes-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ramon-nunes2/)
[![GitHub](https://img.shields.io/badge/GitHub-ramon--nsz-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/ramon-nsz)

---

## Licenca

Distribuido sob a licenca MIT.
