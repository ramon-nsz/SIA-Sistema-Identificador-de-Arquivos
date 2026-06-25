# 📊 Análise de Defeitos de Fabricação — Power BI

> Trabalho acadêmico desenvolvido para a disciplina de **Inteligência de Negócios**

---

## 📋 Sobre o Projeto

Este projeto consiste em um dashboard interativo desenvolvido no **Power BI** para análise de defeitos de fabricação em processos de controle de qualidade industrial.

A proposta foi transformar um dataset de defeitos simulados em **insights acionáveis**, cobrindo três dimensões principais: volume de defeitos, impacto financeiro e padrões temporais.

---

## 📁 Estrutura do Repositório

```
📦 analise-defeitos-fabricacao
 ┣ 📊 Trabalho_BI.pbix         # Dashboard Power BI
 ┣ 📄 defects_data.csv         # Dataset original (CSV)
 ┣ 📄 defects_data.xlsx        # Dataset original (Excel)
 ┣ 📄 Defeitos_de_fabricação.pdf  # Documentação do dataset
 ┗ 📖 README.md
```

---

## 🗂️ Sobre o Dataset

| Coluna | Descrição |
|---|---|
| `defect_id` | Identificador único do defeito |
| `product_id` | Identificador do produto |
| `defect_type` | Tipo do defeito (cosmético, funcional, estrutural) |
| `defect_description` | Descrição detalhada |
| `defect_date` | Data de detecção |
| `defect_location` | Localização no produto (superfície, componente) |
| `severity` | Nível de severidade (menor, moderado, crítico) |
| `inspect_method` | Método de inspeção (visual, automatizado) |
| `repair_action` | Ação corretiva tomada |
| `repair_cost` | Custo de reparo (moeda local) |

---

## 📈 Estrutura do Dashboard

### Página 1 — Dashboard Geral
Visão panorâmica da operação de qualidade.

- **KPIs**: Custo Total · Total de Defeitos · Custo Médio
- **Gráfico de linhas**: Evolução do custo total ao longo do tempo
- **Gráfico de barras horizontais**: Total de defeitos por tipo
- **Gráfico de colunas agrupadas**: Total de defeitos por severidade
- **Gráficos de área**: Evolução temporal de cada KPI

### Página 2 — Custos
Análise financeira aprofundada.

- **KPIs**: Impacto Financeiro Total · Custo Médio
- **Gráfico de colunas**: Custo total por nível de severidade
- **Gráfico de área**: Sazonalidade mensal dos custos
- **Gráficos de área**: Evolução de Custo Total e Custo Médio

---

## 🔍 Principais Insights

- 📉 **Redução de 20%** no custo total entre janeiro e junho de 2024 ($87 mil → $70 mil)
- ⚡ **Queda mais abrupta** registrada entre março e abril: de $85 mil para $68 mil em um único mês
- 🔄 **Padrão oscilatório** identificado ao longo do semestre, sugerindo ciclos de produção ou sazonalidade no processo fabril
- 📊 **Média do período**: $77 mil — com os últimos dois meses abaixo da média, reforçando a tendência de queda

---

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Uso |
|---|---|
| Power BI Desktop | Desenvolvimento do dashboard |
| DAX | Criação das medidas (Custo Total, Total Defeitos, Custo Médio) |
| Power Query | Transformação e modelagem dos dados |
| Excel / CSV | Dataset fonte |

---

## 🏗️ Modelo de Dados

O modelo é composto por uma única tabela (`defects_data`) com as seguintes **medidas DAX**:

```dax
[Custo Total]    -- Soma dos custos de reparo
[Total Defeitos] -- Contagem de registros de defeitos
[Custo Médio]    -- Custo Total / Total Defeitos
```

Dimensões utilizadas nos visuais: `defect_type`, `severity`, `defect_date` (com hierarquia Ano → Mês → Dia).

---

## 👥 Equipe

> Trabalho realizado em grupo — disciplina de Inteligência de Negócios

<!-- Adicione os nomes dos integrantes do grupo abaixo -->
- Fernando Stievano
- Marcello Raitz Debortoli
- Gabriel Araújo Lima

---

## 📚 Referência

- Dataset: [Manufacturing Defects — Kaggle](https://www.kaggle.com/datasets/fahmidachowdhury/manufacturing-defects)
- Ferramenta: [Microsoft Power BI](https://powerbi.microsoft.com)

---

<p align="center">Desenvolvido para fins acadêmicos e educacionais</p>
