# SIA — Sistema Identificador de Arquivos

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-6.x-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Gemini_AI-2.0_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Tesseract](https://img.shields.io/badge/Tesseract_OCR-5.5-FF6B35?style=for-the-badge)
![Platform](https://img.shields.io/badge/Windows_10%2F11-0078D4?style=for-the-badge&logo=windows&logoColor=white)

**Automação inteligente de documentos fiscais brasileiros com IA e OCR**

[Download](https://github.com/ramon-nsz/SIA-Sistema-Identificador-de-Arquivos/releases/latest) · [Reportar Bug](https://github.com/ramon-nsz/SIA-Sistema-Identificador-de-Arquivos/issues)

---

## Sobre o Projeto

O **SIA (Sistema Identificador de Arquivos)** automatiza a organização de documentos fiscais brasileiros. Desenvolvido para equipes de contas a pagar, elimina o trabalho manual de identificar, casar e combinar NF-e, Boletos e Pedidos SAP em um único fluxo.

**O problema que resolve:** em operações de compras, é comum receber dezenas de PDFs por dia sem organização. O processo manual de identificar cada documento, casar a NF com o pedido SAP (por quantidade) e com o boleto (por valor), e gerar um PDF único consome horas e está sujeito a erros. O SIA faz tudo em segundos.

🎥 **[Veja o sistema em funcionamento](https://www.linkedin.com/posts/ramon-nunes2_python-automa%C3%A7%C3%A3o-intelig%C3%AAnciaartificial-ugcPost-7476397438426214400-odQT)** — vídeo demonstrativo no LinkedIn.

---

## Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| Identificação com IA | Classifica NF-e, Boletos e Pedidos SAP via Gemini AI |
| OCR Offline | Processa documentos escaneados via Tesseract (sem internet) |
| Matching Inteligente | Casa NF x SAP por quantidade (±0,002t) e NF x Boleto por valor (±R$1,00) |
| Geração de PDFs | Combina documentos na ordem: SAP + NF-e + Boleto |
| Dashboard Visual | Gráficos, cards de resumo e tabela do lote processado |
| Relatório Excel | Exporta .xlsx com 4 abas: Lote, Vencimentos, Resumo e Gráficos |
| Configuração Guiada | Setup intuitivo para chave Gemini na primeira abertura |
| Rodízio de Chaves | Alterna entre múltiplas chaves Gemini automaticamente |
| Portátil | Executável único, sem instalação — Tesseract já incluso |

---

## Tecnologias

- **Python 3.10+** — linguagem principal
- **PyQt6** — interface gráfica desktop
- **Google Gemini AI 2.0 Flash** — identificação e extração de campos
- **Tesseract OCR 5.5** — OCR para PDFs escaneados, usado como fallback quando o Gemini não consegue extrair texto de um documento (ex: scans de baixa qualidade)
- **pdfplumber / pypdf / PyMuPDF** — cada biblioteca cobre um tipo de PDF com mais confiabilidade (texto nativo, manipulação de páginas e fallback de extração, respectivamente)
- **openpyxl** — geração de planilhas Excel
- **PyInstaller** — empacotamento em executável Windows

---

## Estrutura de Pastas

```
SIA-Sistema-Identificador-de-Arquivos/
├── main.py                 # Entry point — interface PyQt6
├── src/
│   ├── extractor.py        # Identificação e extração de campos
│   ├── matcher.py          # Casamento NF x SAP x Boleto
│   ├── merger.py            # Combinação de PDFs
│   ├── reporter.py          # Relatório Excel
│   ├── dashboard.py         # Dashboard visual
│   ├── config_manager.py    # Configurações do usuário
│   └── setup_dialog.py      # Tela de configuração inicial
└── tesseract/                # Binários do Tesseract (bundlados)
    ├── tesseract.exe
    └── tessdata/
        ├── por.traineddata
        └── eng.traineddata
```

---

## Instalação e Uso

### Executável (recomendado)

1. Acesse [Releases](https://github.com/ramon-nsz/SIA-Sistema-Identificador-de-Arquivos/releases/latest)
2. Baixe `SIA-v1.0-windows.zip`
3. Extraia e execute `SIA.exe`

### Código-fonte

```bash
git clone https://github.com/ramon-nsz/SIA-Sistema-Identificador-de-Arquivos.git
cd SIA-Sistema-Identificador-de-Arquivos
pip install pyqt6 pdfplumber pypdf pymupdf google-genai pytesseract openpyxl pillow python-dotenv
python main.py
```

---

## Configuração da API Gemini

1. Acesse [aistudio.google.com](https://aistudio.google.com)
2. Faça login com sua conta Google
3. Clique em **Get API key** e depois **Create API key**
4. Abra o SIA, clique no ícone de configurações e cole sua chave

A API Gemini tem camada gratuita com 1.500 requisições/dia — suficiente para uso diário.

---

## Validação

O sistema foi testado com lotes reais de documentos fiscais do meu dia a dia operacional (NF-e, boletos e pedidos SAP de fornecedores diversos), com ajuste iterativo das tolerâncias de matching (quantidade e valor) até refletir corretamente as variações normais do processo fiscal real — como pequenas divergências de ICMS entre o valor do pedido e da nota.

---

## Nomenclatura dos arquivos gerados

```
DDMMAAAA_PEDIDO_4500XXXXXX.pdf
Exemplo: 22062026_PEDIDO_4500034730.pdf
```

---

## Troubleshooting

**Documento retorna "Não identificado"**
- Verifique se a chave Gemini está configurada
- Aguarde o reset da quota (21h de Brasília) ou adicione mais chaves
- O Tesseract OCR é acionado automaticamente como fallback

**Valor do boleto incorreto**
- PDFs digitais têm extração mais precisa que escaneados
- Boletos sem par podem ser anexados manualmente via script pypdf

**Executável bloqueado pelo antivírus**
- Adicione o SIA.exe às exceções — executáveis PyInstaller são frequentemente sinalizados como falso-positivo
- O código-fonte completo está disponível para auditoria

---

## Roadmap

- [x] Identificação automática de NF-e, Boleto e SAP
- [x] OCR offline via Tesseract
- [x] Dashboard visual
- [x] Exportação Excel
- [x] Tela de configuração Gemini
- [x] Executável portátil Windows
- [ ] Suporte a CT-e e NFS-e
- [ ] Histórico de lotes processados
- [ ] Integração com Google Drive
- [ ] Versão macOS/Linux

---

## Nota de Desenvolvimento

Este projeto foi concebido, projetado e validado por mim — definição do problema, regras de negócio (lógica de matching, tolerâncias, fluxo de fallback OCR) e arquitetura em camadas — com apoio do Claude Code (Anthropic) para acelerar a implementação. Acredito que usar ferramentas de IA de forma orquestrada é uma competência técnica relevante hoje, desde que acompanhada de entendimento real do que está sendo construído.

---

## Autor

**Ramon Nunes**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Ramon_Nunes-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ramon-nunes2/) [![GitHub](https://img.shields.io/badge/GitHub-ramon--nsz-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/ramon-nsz)

---

## Licença

Distribuído sob a licença MIT.
