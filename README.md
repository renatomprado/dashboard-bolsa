# Dashboard Bolsa RMP

Painel de acompanhamento de mercado (B3, FIIs, moedas, índices, cripto) feito em [Streamlit](https://streamlit.io/), com cotações via [yfinance](https://github.com/ranaroussi/yfinance).

No ar em: https://dashboard-bolsa.streamlit.app/

## Funcionalidades

- Tabela com header e primeira coluna congelados (freeze), zebra e grupos de ativos coloridos
- Variação do dia, mês, mês anterior, ano e 12 meses — Mês/Mês Ant. usam o preço de fechamento; Ano e 12 Meses usam Adj Close (preço ajustado por dividendos/rendimentos), refletindo o retorno total do investimento
- Clique no código de um ativo para abrir uma tela com o histórico dos últimos 12 meses: variação, último preço e rendimento/dividendo pago em cada mês (tabela horizontal + gráfico de linha)
- Grupos de ativos e aparência configuráveis pela barra lateral, persistidos em `config.txt`

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Configuração

Edite `config.txt` diretamente ou use a barra lateral do próprio app (botão "Salvar TXT") para alterar título, colunas visíveis, cores e tickers de cada grupo.

## Deploy

Publicado no Streamlit Community Cloud, conectado a este repositório. Todo push na branch `master` reimplanta automaticamente (leva cerca de 1-2 minutos). Mudar `requirements.txt` faz reinstalar as dependências no próximo deploy; segredos/chaves de API (se algum dia precisar) vão em Settings → Secrets do Streamlit Cloud, nunca no `config.txt` ou no git.
