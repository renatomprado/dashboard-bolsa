import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime
from curl_cffi import requests as cffi_requests
import zoneinfo
import os
from urllib.parse import quote

st.set_page_config(page_title="Dashboard Bolsa RMP", layout="wide")

# Yahoo Finance bloqueia/limita requisições vindas do IP compartilhado do
# Streamlit Cloud. Uma sessão que imita um navegador real (curl_cffi) contorna
# esse bloqueio; sem ela, yf.Ticker cai nos fallbacks (ex.: horário "~").
YF_SESSION = cffi_requests.Session(impersonate="chrome")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.txt")

ALL_AVAILABLE_COLUMNS = [
    "Ativo",
    "Nome",
    "Último",
    "Dia (%)",
    "Data/Hora",
    "Mín. Dia",
    "Máx. Dia",
    "Volume",
    "Fech. Ant.",
    "Mês (%)",
    "Mês Ant. (%)",
    "Ano (%)",
    "12 Meses (%)"
]

# --- FUNÇÕES DE PERSISTÊNCIA DO ARQUIVO TXT ---
def load_config():
    default_config = {
        "titulo": "Snapshot de Mercado - B3",
        "zebra": True,
        "linhas_divisorias": True,
        "colunas": ALL_AVAILABLE_COLUMNS,
        "grupos": [
            {
                "nome": "Ações B3",
                "cor": "#1e3a5f",
                "tickers": ["PETR4.SA", "VALE3.SA", "ITUB4.SA"]
            },
            {
                "nome": "Fundos Imobiliários (FIIs)",
                "cor": "#143a2f",
                "tickers": ["HGLG11.SA", "KNRI11.SA", "MXRF11.SA"]
            },
            {
                "nome": "Moedas & Índices",
                "cor": "#3b2d54",
                "tickers": ["BRL=X", "^BVSP"]
            }
        ]
    }
    
    if not os.path.exists(CONFIG_FILE):
        save_config(
            default_config["titulo"],
            default_config["zebra"],
            default_config["linhas_divisorias"],
            default_config["colunas"],
            default_config["grupos"]
        )
        return default_config

    titulo = default_config["titulo"]
    zebra = True
    linhas_divisorias = True
    colunas = ALL_AVAILABLE_COLUMNS
    grupos = []
    current_group = None

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                if line.startswith("[") and line.endswith("]"):
                    if current_group:
                        grupos.append(current_group)
                    group_name = line[1:-1].strip()
                    current_group = {"nome": group_name, "cor": "#1e293b", "tickers": []}
                    continue
                
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip().lower()
                    val = val.strip()

                    if current_group:
                        if key == "cor":
                            current_group["cor"] = val
                        elif key == "tickers":
                            raw_tickers = [t.strip().upper() for t in val.replace("\n", ",").split(",") if t.strip()]
                            current_group["tickers"] = raw_tickers
                    else:
                        if key == "titulo":
                            titulo = val
                        elif key == "zebra":
                            zebra = val.lower() in ["true", "1", "sim"]
                        elif key in ["linhas_divisorias", "linhasdivisorias"]:
                            linhas_divisorias = val.lower() in ["true", "1", "sim"]
                        elif key == "colunas":
                            parsed_cols = [c.strip() for c in val.split(",") if c.strip() in ALL_AVAILABLE_COLUMNS]
                            if parsed_cols:
                                colunas = parsed_cols

            if current_group:
                grupos.append(current_group)
    except Exception as e:
        st.error(f"Erro ao ler {CONFIG_FILE}: {e}")
        return default_config

    return {
        "titulo": titulo,
        "zebra": zebra,
        "linhas_divisorias": linhas_divisorias,
        "colunas": colunas,
        "grupos": grupos if grupos else default_config["grupos"]
    }

def save_config(titulo, zebra, linhas_divisorias, colunas, grupos):
    lines = [
        "# ==========================================",
        "# CONFIGURAÇÕES GERAIS VISUAIS",
        "# ==========================================",
        f"titulo = {titulo}",
        f"zebra = {'true' if zebra else 'false'}",
        f"linhas_divisorias = {'true' if linhas_divisorias else 'false'}",
        f"colunas = {', '.join(colunas)}",
        "",
        "# ==========================================",
        "# GRUPOS DE ATIVOS E CORES",
        "# ==========================================",
        ""
    ]
    for g in grupos:
        lines.append(f"[{g['nome']}]")
        lines.append(f"cor = {g['cor']}")
        lines.append(f"tickers = {', '.join(g['tickers'])}")
        lines.append("")

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

config_data = load_config()

# --- PAINEL LATERAL: CONFIGURAÇÕES GERAIS ---
st.sidebar.header("⚙️ Configurações Gerais")

app_title = st.sidebar.text_input("Título do Painel", value=config_data["titulo"])
enable_zebra = st.sidebar.checkbox("Ativar Cores Intercaladas (Zebra A/B)", value=config_data["zebra"])
enable_dividers = st.sidebar.checkbox("Linhas Divisórias Fortes", value=config_data["linhas_divisorias"])

# Seletor de Colunas Visíveis
st.sidebar.markdown("---")
st.sidebar.header("👁️ Exibição de Colunas")
selected_columns = st.sidebar.multiselect(
    "Colunas Visíveis na Tabela:",
    options=ALL_AVAILABLE_COLUMNS,
    default=config_data["colunas"]
)
if not selected_columns:
    selected_columns = ["Ativo", "Último", "Dia (%)"]

st.sidebar.markdown("---")
st.sidebar.header("📁 Grupos de Ativos")

configured_groups = []
all_tickers = []

for idx, group in enumerate(config_data["grupos"], 1):
    with st.sidebar.expander(f"Grupo {idx}: {group['nome']}", expanded=True):
        g_name = st.text_input(f"Nome do Grupo {idx}", value=group["nome"], key=f"g_name_{idx}")
        g_color = st.color_picker(f"Cor de Destaque", value=group["cor"], key=f"g_color_{idx}")
        tickers_str = "\n".join(group["tickers"])
        g_tickers_raw = st.text_area(f"Tickers (um por linha)", value=tickers_str, height=90, key=f"g_tickers_{idx}")
        
        g_tickers = [t.strip().upper() for t in g_tickers_raw.replace(",", "\n").splitlines() if t.strip()]
        
        configured_groups.append({
            "nome": g_name,
            "cor": g_color,
            "tickers": g_tickers
        })
        all_tickers.extend(g_tickers)

# Botões de Ação
col_save, col_reload = st.sidebar.columns(2)
with col_save:
    if st.button("💾 Salvar TXT", use_container_width=True):
        save_config(app_title, enable_zebra, enable_dividers, selected_columns, configured_groups)
        st.sidebar.success("Configurações salvas no config.txt!")
with col_reload:
    if st.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()

# Título nativo do Streamlit (sempre visível e estável)
st.title(f"📊 {app_title}")

# --- CONSULTA RÁPIDA EM LOTE ---
@st.cache_data(ttl=300)
def fetch_all_data(tickers_list):
    if not tickers_list:
        return None
    unique_tickers = list(set(tickers_list))
    raw = yf.download(unique_tickers, period="2y", interval="1d", auto_adjust=False, progress=False, session=YF_SESSION)
    return raw

@st.cache_data(ttl=86400)
def get_asset_short_name(ticker):
    custom_names = {
        "BRL=X": "Dólar Comercial",
        "EURBRL=X": "Euro Comercial",
        "^BVSP": "Índice Bovespa",
        "BTC-USD": "Bitcoin USD"
    }
    if ticker in custom_names:
        return custom_names[ticker]
    try:
        t = yf.Ticker(ticker, session=YF_SESSION)
        meta = t.history_metadata
        if isinstance(meta, dict) and meta.get("shortName"):
            return meta.get("shortName")
        info = t.info
        return info.get("shortName") or info.get("longName") or ticker.replace(".SA", "")
    except Exception:
        return ticker.replace(".SA", "")

raw_data = fetch_all_data(all_tickers)

now = datetime.now()
current_year = now.year
current_month = now.month
sao_paulo_tz = zoneinfo.ZoneInfo("America/Sao_Paulo")

def fmt_clean_num(val, ticker=""):
    if val is None or pd.isna(val):
        return "--"
    if ticker == "^BVSP":
        return f"{val:,.0f}".replace(",", ".")
    return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_volume(vol):
    if vol is None or pd.isna(vol) or vol == 0:
        return "--"
    if vol >= 1_000_000_000:
        v = vol / 1_000_000_000
        return f"{v:,.2f} B".replace(",", "X").replace(".", ",").replace("X", ".")
    elif vol >= 1_000_000:
        v = vol / 1_000_000
        return f"{v:,.2f} M".replace(",", "X").replace(".", ",").replace("X", ".")
    elif vol >= 1_000:
        v = vol / 1_000
        return f"{v:,.1f} K".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{vol:,.0f}".replace(",", ".")

def fmt_br_pct(val):
    if val is None or pd.isna(val):
        return '<span style="color: #94a3b8;">--</span>'
    formatted = f"{abs(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if val > 0.0001:
        return f'<span style="color: #10b981; font-weight: 600;">+{formatted}%</span>'
    elif val < -0.0001:
        return f'<span style="color: #ef4444; font-weight: 600;">-{formatted}%</span>'
    return '<span style="color: #94a3b8;">0,00%</span>'

def get_price_series(ticker, raw_df):
    """Retorna close/adj_close/high/low/volume (Series) para o ticker, ou None se indisponível."""
    if raw_df is None or raw_df.empty:
        return None

    if len(all_tickers) == 1:
        close_series = raw_df["Close"].dropna()
        adj_close_series = raw_df["Adj Close"].dropna() if "Adj Close" in raw_df else close_series
        high_series = raw_df["High"].dropna()
        low_series = raw_df["Low"].dropna()
        vol_series = raw_df["Volume"].dropna()
    else:
        if ticker not in raw_df["Close"].columns:
            return None
        close_series = raw_df["Close"][ticker].dropna()
        if "Adj Close" in raw_df and ticker in raw_df["Adj Close"].columns:
            adj_close_series = raw_df["Adj Close"][ticker].dropna()
        else:
            adj_close_series = close_series
        high_series = raw_df["High"][ticker].dropna()
        low_series = raw_df["Low"][ticker].dropna()
        vol_series = raw_df["Volume"][ticker].dropna()

    if len(close_series) < 2:
        return None

    if len(adj_close_series) < 2:
        adj_close_series = close_series

    return close_series, adj_close_series, high_series, low_series, vol_series

MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

@st.cache_data(ttl=86400)
def get_dividend_history(ticker):
    try:
        return yf.Ticker(ticker, session=YF_SESSION).dividends
    except Exception:
        return pd.Series(dtype=float)

def build_monthly_history(ticker, raw_df, months=12):
    """Retorna lista de (rótulo do mês, variação % c/ Adj Close, último preço bruto do mês,
    data do mês, rendimento/dividendo pago em R$ por cota naquele mês)."""
    series = get_price_series(ticker, raw_df)
    if series is None:
        return None
    close_series, adj_close_series, _, _, _ = series

    monthly_adj = adj_close_series.resample("ME").last()
    monthly_raw = close_series.resample("ME").last()
    monthly_pct = monthly_adj.pct_change().dropna() * 100
    monthly_pct = monthly_pct.tail(months)

    dividends = get_dividend_history(ticker)

    rows = []
    for idx, val in monthly_pct.items():
        raw_price = float(monthly_raw.loc[idx]) if idx in monthly_raw.index else None
        month_divs = dividends[(dividends.index.year == idx.year) & (dividends.index.month == idx.month)]
        dividend_sum = float(month_divs.sum()) if not month_divs.empty else 0.0
        rows.append((f"{MESES_PT[idx.month - 1]}/{idx.year}", float(val), raw_price, idx, dividend_sum))
    return rows

@st.cache_data(ttl=60)
def get_market_time(ticker):
    """Retorna o horário da última cotação (regularMarketTime) ou None se indisponível."""
    try:
        t = yf.Ticker(ticker, session=YF_SESSION)
        meta = t.history_metadata
        ts = meta.get("regularMarketTime") if isinstance(meta, dict) else None
        if ts is None:
            return None
        if isinstance(ts, (int, float)):
            # yfinance mais antigo: epoch Unix.
            dt = datetime.fromtimestamp(ts, tz=sao_paulo_tz)
        else:
            # yfinance atual: já vem como Timestamp com fuso embutido.
            dt = pd.Timestamp(ts).tz_convert(sao_paulo_tz)
        return dt.strftime("%d/%m %H:%M")
    except Exception:
        return None

def build_row_data(ticker, raw_df):
    series = get_price_series(ticker, raw_df)
    if series is None:
        return None
    close_series, adj_close_series, high_series, low_series, vol_series = series

    last_price = float(close_series.iloc[-1])
    prev_close = float(close_series.iloc[-2])
    day_high = float(high_series.iloc[-1]) if not high_series.empty else last_price
    day_low = float(low_series.iloc[-1]) if not low_series.empty else last_price
    day_vol = float(vol_series.iloc[-1]) if not vol_series.empty else 0
    
    day_var = ((last_price / prev_close) - 1) * 100

    # Metadata (regularMarketTime) às vezes falha por bloqueio/rate-limit do Yahoo
    # no IP do Streamlit Cloud. Nesse caso, close_series.index[-1] é a data do
    # candle diário (sempre 00:00) — um fallback pior do que mostrar a hora atual.
    time_str = get_market_time(ticker)
    if time_str is None:
        time_str = f"~{datetime.now(tz=sao_paulo_tz).strftime('%d/%m %H:%M')}"

    # Variações de período usam Adj Close (preço ajustado por dividendos/rendimentos),
    # para refletir retorno total do investimento e não só a variação nominal da cotação.
    adj_last = float(adj_close_series.iloc[-1])

    prev_year_data = adj_close_series[adj_close_series.index.year < current_year]
    ano_base = float(prev_year_data.iloc[-1]) if not prev_year_data.empty else float(adj_close_series.iloc[0])
    ano_var = ((adj_last / ano_base) - 1) * 100

    prev_month_data = adj_close_series[
        (adj_close_series.index.year < current_year) |
        ((adj_close_series.index.year == current_year) & (adj_close_series.index.month < current_month))
    ]
    mes_base = float(prev_month_data.iloc[-1]) if not prev_month_data.empty else float(adj_close_series.iloc[0])
    mes_var = ((adj_last / mes_base) - 1) * 100

    if len(prev_month_data) >= 2:
        last_month_idx = prev_month_data.index[-1]
        prev_prev_data = adj_close_series[adj_close_series.index < last_month_idx.replace(day=1)]
        prev_prev_base = float(prev_prev_data.iloc[-1]) if not prev_prev_data.empty else float(prev_month_data.iloc[0])
        mes_ant_var = ((mes_base / prev_prev_base) - 1) * 100
    else:
        mes_ant_var = 0.0

    one_year_ago_date = adj_close_series.index[-1] - pd.DateOffset(years=1)
    past_12m = adj_close_series[adj_close_series.index <= one_year_ago_date]
    base_12m = float(past_12m.iloc[-1]) if not past_12m.empty else float(adj_close_series.iloc[0])
    var_12m = ((adj_last / base_12m) - 1) * 100

    asset_name = get_asset_short_name(ticker)

    return {
        "ticker_clean": ticker.replace(".SA", ""),
        "name": asset_name,
        "last_price": fmt_clean_num(last_price, ticker),
        "day_var": day_var,
        "time": time_str,
        "day_low": fmt_clean_num(day_low, ticker),
        "day_high": fmt_clean_num(day_high, ticker),
        "volume": fmt_volume(day_vol),
        "prev_close": fmt_clean_num(prev_close, ticker),
        "mes_var": mes_var,
        "mes_ant_var": mes_ant_var,
        "ano_var": ano_var,
        "var_12m": var_12m
    }

# --- TELA DE DETALHE: VARIAÇÃO MENSAL DO ATIVO (via clique no código + query param) ---
selected_ticker = st.query_params.get("ticker")

if selected_ticker:
    display_ticker = selected_ticker.replace(".SA", "")
    asset_name = get_asset_short_name(selected_ticker)

    st.html('<a href="?" style="color: #94a3b8; font-size: 14px; text-decoration: none;">&larr; Voltar ao painel</a>')
    st.title(f"📈 {display_ticker} — {asset_name}")
    st.subheader("Variação dos últimos 12 meses")

    monthly_rows = None
    if selected_ticker in all_tickers:
        monthly_rows = build_monthly_history(selected_ticker, raw_data, months=12)

    if not monthly_rows:
        st.warning("Sem dados suficientes para este ativo (ou ele não está mais em nenhum grupo configurado).")
    else:
        # Tabela: mais recente -> mais antigo, esquerda para direita.
        table_rows = list(reversed(monthly_rows))
        header_cells = "".join(
            f'<th style="padding: 10px 14px; text-align: right; border-bottom: 2px solid #334155; white-space: nowrap;">{mes}</th>'
            for mes, _, _, _, _ in table_rows
        )
        var_cells = "".join(
            f'<td style="padding: 10px 14px; border-bottom: 1px solid #334155; text-align: right; white-space: nowrap;">{fmt_br_pct(pct)}</td>'
            for _, pct, _, _, _ in table_rows
        )
        price_cells = "".join(
            f'<td style="padding: 10px 14px; border-bottom: 1px solid #334155; text-align: right; white-space: nowrap; color: #cbd5e1;">{fmt_clean_num(price, selected_ticker)}</td>'
            for _, _, price, _, _ in table_rows
        )
        dividend_cells = "".join(
            f'<td style="padding: 10px 14px; border-bottom: 1px solid #334155; text-align: right; white-space: nowrap; color: #cbd5e1;">{fmt_clean_num(div, "") if div > 0 else "--"}</td>'
            for _, _, _, _, div in table_rows
        )
        st.html(f'''
        <div style="max-width: 100%; overflow-x: auto; border-radius: 8px; border: 1px solid #1e293b; background: #0b1120; margin-top: 10px;">
        <table style="border-collapse: collapse; font-family: sans-serif; font-size: 14px; color: #f1f5f9;">
        <thead>
        <tr style="background-color: #0f172a; color: #94a3b8; font-weight: 600;">
            <th style="padding: 10px 14px; text-align: left; border-bottom: 2px solid #334155; position: sticky; left: 0; background-color: #0f172a; z-index: 5; white-space: nowrap;">Mês</th>
            {header_cells}
        </tr>
        </thead>
        <tbody>
        <tr style="background-color: #0f172a;">
            <td style="padding: 10px 14px; border-bottom: 1px solid #334155; position: sticky; left: 0; background-color: #0f172a; z-index: 5; font-weight: 600; white-space: nowrap;">Variação (%)</td>
            {var_cells}
        </tr>
        <tr style="background-color: #1e293b;">
            <td style="padding: 10px 14px; border-bottom: 1px solid #334155; position: sticky; left: 0; background-color: #1e293b; z-index: 5; font-weight: 600; white-space: nowrap;">Último Preço</td>
            {price_cells}
        </tr>
        <tr style="background-color: #0f172a;">
            <td style="padding: 10px 14px; border-bottom: 1px solid #334155; position: sticky; left: 0; background-color: #0f172a; z-index: 5; font-weight: 600; white-space: nowrap;">Rendimento (R$)</td>
            {dividend_cells}
        </tr>
        </tbody>
        </table>
        </div>
        ''')

        st.subheader("Gráfico de preços")
        # Eixo categórico (não temporal) com ordem explícita: evita o "nice scale" do
        # Vega-Lite estender o eixo para além do último mês com dado, e mantém os
        # rótulos em português ("Set/2025") em vez do nome do mês em inglês.
        meses_ordem = [mes for mes, _, _, _, _ in monthly_rows]
        chart_df = pd.DataFrame({
            "Mês": meses_ordem,
            "Preço": [price for _, _, price, _, _ in monthly_rows],
        })
        chart = alt.Chart(chart_df).mark_line(point=True, color="#0284c7").encode(
            x=alt.X("Mês:N", sort=meses_ordem, title=None),
            y=alt.Y("Preço:Q", title="Preço (R$)", scale=alt.Scale(zero=False)),
            tooltip=["Mês", "Preço"]
        )
        st.altair_chart(chart, use_container_width=True)

    st.stop()

# --- MONTAGEM DA TABELA HTML: FREEZE HEADER E FREEZE FIRST COLUMN ---
border_color = "#334155" if enable_dividers else "#1e293b"

alignments = {
    "Ativo": "left",
    "Nome": "left",
    "Último": "right",
    "Dia (%)": "right",
    "Data/Hora": "right",
    "Mín. Dia": "right",
    "Máx. Dia": "right",
    "Volume": "right",
    "Fech. Ant.": "right",
    "Mês (%)": "right",
    "Mês Ant. (%)": "right",
    "Ano (%)": "right",
    "12 Meses (%)": "right"
}

html_parts = []

# Container com rolagem e altura máxima para manter a grade congelada
html_parts.append("""
<div style="width: 100%; max-height: calc(100vh - 160px); overflow: auto; border-radius: 8px; border: 1px solid #1e293b; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); background: #0b1120; margin-top: 10px;">
<table style="width: 100%; border-collapse: separate; border-spacing: 0; font-family: sans-serif; font-size: 14px; color: #f1f5f9;">
""")

# Cabeçalho da Tabela (Freeze Header: sticky top: 0)
html_parts.append('<thead>')
html_parts.append('<tr style="background-color: #0f172a; color: #94a3b8; font-weight: 600;">')

for idx, col in enumerate(selected_columns):
    align = alignments.get(col, "right")
    extra_border = f"border-right: 2px solid {border_color};" if col == "Fech. Ant." and enable_dividers else ""
    
    # Primeira coluna: Freeze Top + Freeze Left (z-index 40)
    if idx == 0:
        html_parts.append(f'<th style="padding: 12px 14px; text-align: {align}; position: sticky; top: 0; left: 0; background-color: #0f172a; z-index: 40; border-bottom: 2px solid #334155; border-right: 2px solid #334155; box-shadow: 2px 0 5px rgba(0,0,0,0.3); white-space: nowrap;">{col}</th>')
    else:
        html_parts.append(f'<th style="padding: 12px 10px; text-align: {align}; {extra_border} position: sticky; top: 0; background-color: #0f172a; z-index: 20; border-bottom: 2px solid #334155; white-space: nowrap;">{col}</th>')

html_parts.append('</tr>')
html_parts.append('</thead>')

# Corpo da Tabela
html_parts.append('<tbody>')

row_counter = 0

for group in configured_groups:
    if not group["tickers"]:
        continue
    
    g_color = group["cor"]
    colspan = len(selected_columns)
    
    # Faixa de grupo (Sticky left para manter visível em scroll horizontal)
    html_parts.append(f"""
    <tr style="background-color: {g_color}; color: #ffffff; font-weight: bold; font-size: 13px; text-transform: uppercase;">
        <td colspan="{colspan}" style="padding: 10px 14px; text-align: left; position: sticky; left: 0; border-top: 2px solid #334155; border-bottom: 1px solid #334155; z-index: 15;">
            📁 {group['nome']}
        </td>
    </tr>
    """)

    for ticker in group["tickers"]:
        data = build_row_data(ticker, raw_data)
        if not data:
            continue
        
        if enable_zebra:
            bg_color = "#1e293b" if row_counter % 2 == 1 else "#0f172a"
        else:
            bg_color = "#0b1120"
        
        row_counter += 1
        border_b = f"border-bottom: 1px solid {border_color};"

        html_parts.append(f'<tr style="background-color: {bg_color};">')
        
        for idx, col in enumerate(selected_columns):
            extra_border = f"border-right: 2px solid {border_color};" if col == "Fech. Ant." and enable_dividers else ""
            
            # Freeze Left na primeira coluna de dados
            if idx == 0:
                sticky_left_style = f"position: sticky; left: 0; background-color: {bg_color}; z-index: 10; border-right: 2px solid #334155; box-shadow: 2px 0 5px rgba(0,0,0,0.3);"
            else:
                sticky_left_style = ""

            if col == "Ativo":
                ticker_href = quote(ticker, safe="")
                html_parts.append(f'<td style="padding: 10px 14px; text-align: left; {sticky_left_style} {border_b}"><a href="?ticker={ticker_href}" style="text-decoration: none;"><span style="background: #0284c7; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; cursor: pointer;">{data["ticker_clean"]}</span></a></td>')
            elif col == "Nome":
                html_parts.append(f'<td style="padding: 10px 10px; text-align: left; color: #cbd5e1; font-weight: 500; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; {border_b}">{data["name"]}</td>')
            elif col == "Último":
                html_parts.append(f'<td style="padding: 10px 10px; text-align: right; font-weight: bold; color: #ffffff; {border_b}">{data["last_price"]}</td>')
            elif col == "Dia (%)":
                html_parts.append(f'<td style="padding: 10px 10px; text-align: right; {border_b}">{fmt_br_pct(data["day_var"])}</td>')
            elif col == "Data/Hora":
                html_parts.append(f'<td style="padding: 10px 10px; text-align: right; color: #94a3b8; font-size: 13px; {border_b}">{data["time"]}</td>')
            elif col == "Mín. Dia":
                html_parts.append(f'<td style="padding: 10px 10px; text-align: right; color: #cbd5e1; {border_b}">{data["day_low"]}</td>')
            elif col == "Máx. Dia":
                html_parts.append(f'<td style="padding: 10px 10px; text-align: right; color: #cbd5e1; {border_b}">{data["day_high"]}</td>')
            elif col == "Volume":
                html_parts.append(f'<td style="padding: 10px 10px; text-align: right; color: #cbd5e1; font-weight: 500; {border_b}">{data["volume"]}</td>')
            elif col == "Fech. Ant.":
                html_parts.append(f'<td style="padding: 10px 10px; text-align: right; color: #cbd5e1; {extra_border} {border_b}">{data["prev_close"]}</td>')
            elif col == "Mês (%)":
                html_parts.append(f'<td style="padding: 10px 10px; text-align: right; {border_b}">{fmt_br_pct(data["mes_var"])}</td>')
            elif col == "Mês Ant. (%)":
                html_parts.append(f'<td style="padding: 10px 10px; text-align: right; {border_b}">{fmt_br_pct(data["mes_ant_var"])}</td>')
            elif col == "Ano (%)":
                html_parts.append(f'<td style="padding: 10px 10px; text-align: right; {border_b}">{fmt_br_pct(data["ano_var"])}</td>')
            elif col == "12 Meses (%)":
                html_parts.append(f'<td style="padding: 10px 10px; text-align: right; padding-right: 14px; {border_b}">{fmt_br_pct(data["var_12m"])}</td>')
        
        html_parts.append('</tr>')

html_parts.append('</tbody>')
html_parts.append('</table>')
html_parts.append('</div>')

final_html = "".join(html_parts)

if hasattr(st, "html"):
    st.html(final_html)
else:
    st.markdown(final_html, unsafe_allow_html=True)
