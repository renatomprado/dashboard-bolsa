# Dashboard Bolsa

Painel de acompanhamento de mercado (B3, FIIs, moedas, índices) feito em [Streamlit](https://streamlit.io/), com cotações via [yfinance](https://github.com/ranaroussi/yfinance).

## Funcionalidades

- Tabela com header e primeira coluna congelados (freeze), zebra e grupos de ativos coloridos
- Variação do dia, mês, mês anterior, ano e 12 meses
- Grupos de ativos e aparência configuráveis pela barra lateral, persistidos em `config.txt`

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Configuração

Edite `config.txt` diretamente ou use a barra lateral do próprio app (botão "Salvar TXT") para alterar título, colunas visíveis, cores e tickers de cada grupo.
