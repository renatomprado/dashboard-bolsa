import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import zoneinfo
import os

st.set_page_config(page_title="Portfolio Snapshot - B3", layout="wide")

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
    raw = yf.download(unique_tickers, period="2y", interval="1d", auto_adjust=False, progress=False)
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
        t = yf.Ticker(ticker)
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

def build_row_data(ticker, raw_df):
    if raw_df is None or raw_df.empty:
        return None
    
    if len(all_tickers) == 1:
        close_series = raw_df["Close"].dropna()
        high_series = raw_df["High"].dropna()
        low_series = raw_df["Low"].dropna()
        vol_series = raw_df["Volume"].dropna()
    else:
        if ticker not in raw_df["Close"].columns:
            return None
        close_series = raw_df["Close"][ticker].dropna()
        high_series = raw_df["High"][ticker].dropna()
        low_series = raw_df["Low"][ticker].dropna()
        vol_series = raw_df["Volume"][ticker].dropna()

    if len(close_series) < 2:
        return None

    last_price = float(close_series.iloc[-1])
    prev_close = float(close_series.iloc[-2])
    day_high = float(high_series.iloc[-1]) if not high_series.empty else last_price
    day_low = float(low_series.iloc[-1]) if not low_series.empty else last_price
    day_vol = float(vol_series.iloc[-1]) if not vol_series.empty else 0
    
    day_var = ((last_price / prev_close) - 1) * 100

    time_str = "--"
    try:
        t = yf.Ticker(ticker)
        meta = t.history_metadata
        ts = meta.get("regularMarketTime") if isinstance(meta, dict) else None
        if ts:
            dt = datetime.fromtimestamp(ts, tz=sao_paulo_tz)
            time_str = dt.strftime("%d/%m %H:%M")
        else:
            time_str = close_series.index[-1].strftime("%d/%m %H:%M")
    except Exception:
        time_str = close_series.index[-1].strftime("%d/%m %H:%M")

    prev_year_data = close_series[close_series.index.year < current_year]
    ano_base = float(prev_year_data.iloc[-1]) if not prev_year_data.empty else float(close_series.iloc[0])
    ano_var = ((last_price / ano_base) - 1) * 100

    prev_month_data = close_series[
        (close_series.index.year < current_year) | 
        ((close_series.index.year == current_year) & (close_series.index.month < current_month))
    ]
    mes_base = float(prev_month_data.iloc[-1]) if not prev_month_data.empty else float(close_series.iloc[0])
    mes_var = ((last_price / mes_base) - 1) * 100

    if len(prev_month_data) >= 2:
        last_month_idx = prev_month_data.index[-1]
        prev_prev_data = close_series[close_series.index < last_month_idx.replace(day=1)]
        prev_prev_base = float(prev_prev_data.iloc[-1]) if not prev_prev_data.empty else float(prev_month_data.iloc[0])
        mes_ant_var = ((mes_base / prev_prev_base) - 1) * 100
    else:
        mes_ant_var = 0.0

    one_year_ago_date = close_series.index[-1] - pd.DateOffset(years=1)
    past_12m = close_series[close_series.index <= one_year_ago_date]
    base_12m = float(past_12m.iloc[-1]) if not past_12m.empty else float(close_series.iloc[0])
    var_12m = ((last_price / base_12m) - 1) * 100

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
                html_parts.append(f'<td style="padding: 10px 14px; text-align: left; {sticky_left_style} {border_b}"><span style="background: #0284c7; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;">{data["ticker_clean"]}</span></td>')
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
