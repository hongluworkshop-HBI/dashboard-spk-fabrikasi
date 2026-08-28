import json
import math
from typing import Dict

import pandas as pd
import plotly.express as px
import streamlit as st
from openai import OpenAI
from streamlit_gsheets import GSheetsConnection


st.set_page_config(
    page_title="Dashboard SPK Fabrikasi 2026",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
      [data-testid="stMetric"] {
        background: rgba(240, 244, 248, 0.65);
        border: 1px solid rgba(49, 51, 63, 0.12);
        padding: 12px 14px;
        border-radius: 14px;
      }
      .small-note {font-size: 0.86rem; opacity: .72;}
    </style>
    """,
    unsafe_allow_html=True,
)

SHEET_SUMMARY = "RINGKASAN"


def safe_num(value, default=0.0):
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
            if value.startswith("#"):
                return default
        return float(value)
    except Exception:
        return default


def fmt_ton(v):
    return f"{safe_num(v):,.2f} ton"


def fmt_pct(v):
    return f"{safe_num(v) * 100:.2f}%"


@st.cache_data(ttl=300, show_spinner=False)
def load_summary():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(
        worksheet=SHEET_SUMMARY,
        ttl=300,
        header=None,
        usecols=list(range(20)),
        nrows=80,
    )
    for c in range(20):
        if c not in df.columns:
            df[c] = None
    return df.iloc[:, :20]


def matrix_value(df, row_1based, col_1based):
    try:
        return df.iat[row_1based - 1, col_1based - 1]
    except Exception:
        return None


def extract_table(
    df: pd.DataFrame,
    header_row_1based: int,
    first_data_row_1based: int,
    last_data_row_1based: int,
    start_col_1based: int,
    width: int = 7,
):
    headers = []
    for c in range(start_col_1based, start_col_1based + width):
        h = matrix_value(df, header_row_1based, c)
        headers.append(str(h).strip() if h is not None else f"Col{c}")

    rows = []
    for r in range(first_data_row_1based, last_data_row_1based + 1):
        vals = [
            matrix_value(df, r, c)
            for c in range(start_col_1based, start_col_1based + width)
        ]
        name = vals[0] if vals else None
        if name is None or str(name).strip() in ("", "nan", "None"):
            continue
        rows.append(vals)

    out = pd.DataFrame(rows, columns=headers)
    for col in ["SPK", "Total Ton", "Selesai Ton", "Sisa Ton", "Progress", "Nilai SPK Rp"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)
    return out


def load_tables(df):
    return {
        "projects": extract_table(df, 14, 15, 29, 1),
        "vendors": extract_table(df, 14, 15, 29, 9),
        "months": extract_table(df, 33, 34, 36, 1),
        "areas": extract_table(df, 33, 34, 40, 9),
        "spks": extract_table(df, 44, 45, 59, 1),
        "profiles": extract_table(df, 44, 45, 59, 9),
    }


def build_ai_context(kpi: Dict, tables: Dict[str, pd.DataFrame]) -> str:
    compact = {
        "kpi": kpi,
        "top_projects": tables["projects"].head(15).to_dict(orient="records"),
        "top_vendors": tables["vendors"].head(15).to_dict(orient="records"),
        "months": tables["months"].to_dict(orient="records"),
        "areas": tables["areas"].to_dict(orient="records"),
        "largest_remaining_spk": tables["spks"].head(15).to_dict(orient="records"),
        "top_profiles": tables["profiles"].head(15).to_dict(orient="records"),
    }
    return json.dumps(compact, ensure_ascii=False, default=str)


try:
    summary = load_summary()
except Exception as exc:
    st.error("Belum dapat membaca Google Sheets.")
    st.markdown(
        """
        Pastikan **Streamlit Secrets** sudah berisi konfigurasi `[connections.gsheets]`,
        lalu Google Sheet sudah dibagikan ke email Service Account sebagai **Viewer**.
        """
    )
    with st.expander("Detail teknis"):
        st.code(str(exc))
    st.stop()

tables = load_tables(summary)
source_note = matrix_value(summary, 3, 1) or "Sumber data Google Sheets"

kpi = {
    "total_spk": int(safe_num(matrix_value(summary, 5, 2))),
    "total_project": int(safe_num(matrix_value(summary, 5, 4))),
    "total_vendor": int(safe_num(matrix_value(summary, 5, 6))),
    "total_area": int(safe_num(matrix_value(summary, 5, 8))),
    "total_ton": safe_num(matrix_value(summary, 5, 10)),
    "finished_ton": safe_num(matrix_value(summary, 5, 12)),
    "remaining_ton": safe_num(matrix_value(summary, 5, 14)),
    "progress": safe_num(matrix_value(summary, 6, 2)),
    "august_ton": safe_num(matrix_value(summary, 6, 4)),
    "total_qty": int(safe_num(matrix_value(summary, 6, 6))),
    "total_profile": int(safe_num(matrix_value(summary, 6, 8))),
    "spk_value": safe_num(matrix_value(summary, 6, 10)),
    "billing_finished": safe_num(matrix_value(summary, 6, 12)),
    "billing_progress": safe_num(matrix_value(summary, 6, 14)),
}

with st.sidebar:
    st.title("🏗️ SPK Fabrikasi")
    st.caption("加工工作指令分析系统")
    page = st.radio(
        "Menu",
        [
            "Dashboard Utama",
            "Proyek & Vendor",
            "Area & Bulan",
            "SPK Prioritas",
            "Profil Material",
            "AI Analyst",
        ],
    )
    st.divider()
    if st.button("🔄 Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("Data dibaca langsung dari Google Sheets.")

st.title("Dashboard SPK Fabrikasi 2026 | 加工分析看板")
st.markdown(f"<div class='small-note'>{source_note}</div>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("TOTAL SPK / SPK总数", f"{kpi['total_spk']:,}")
c2.metric("TOTAL PROYEK / 项目总数", f"{kpi['total_project']:,}")
c3.metric("TOTAL VENDOR / 供应商总数", f"{kpi['total_vendor']:,}")
c4.metric("TOTAL TONASE / 总吨位", fmt_ton(kpi["total_ton"]))

c5, c6, c7, c8 = st.columns(4)
c5.metric("SELESAI / 已完成", fmt_ton(kpi["finished_ton"]))
c6.metric("SISA / 剩余", fmt_ton(kpi["remaining_ton"]))
c7.metric("PROGRESS / 总进度", fmt_pct(kpi["progress"]))
c8.metric("PROGRESS TAGIHAN / 账单进度", fmt_pct(kpi["billing_progress"]))

st.divider()

if page == "Dashboard Utama":
    left, right = st.columns(2)

    status_df = pd.DataFrame(
        {
            "Status": ["Selesai", "Sisa"],
            "Ton": [kpi["finished_ton"], kpi["remaining_ton"]],
        }
    )
    with left:
        st.subheader("Progress Tonase | 吨位进度")
        fig = px.pie(status_df, names="Status", values="Ton", hole=0.58)
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), legend_orientation="h")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Progress Per Bulan | 每月进度")
        month = tables["months"].copy()
        if not month.empty:
            fig = px.bar(
                month,
                x="Nama",
                y=["Total Ton", "Selesai Ton"],
                barmode="group",
                labels={"value": "Ton", "Nama": "Bulan", "variable": "Kategori"},
            )
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top Proyek Berdasarkan Tonase | 项目吨位排名")
    proj = tables["projects"].head(10)
    if not proj.empty:
        fig = px.bar(
            proj.sort_values("Total Ton"),
            x=["Total Ton", "Selesai Ton"],
            y="Nama",
            orientation="h",
            barmode="group",
            labels={"value": "Ton", "Nama": "Proyek", "variable": "Kategori"},
        )
        st.plotly_chart(fig, use_container_width=True)

elif page == "Proyek & Vendor":
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top Proyek | 项目")
        st.dataframe(tables["projects"], use_container_width=True, hide_index=True)
    with col2:
        st.subheader("Top Vendor | 供应商")
        st.dataframe(tables["vendors"], use_container_width=True, hide_index=True)

    if not tables["vendors"].empty:
        st.subheader("Sisa Tonase Vendor | 供应商剩余吨位")
        vd = tables["vendors"].sort_values("Sisa Ton", ascending=True)
        fig = px.bar(vd, x="Sisa Ton", y="Nama", orientation="h")
        st.plotly_chart(fig, use_container_width=True)

elif page == "Area & Bulan":
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Analisa Area | 区域分析")
        area = tables["areas"]
        if not area.empty:
            fig = px.bar(
                area.sort_values("Total Ton"),
                x=["Total Ton", "Selesai Ton"],
                y="Nama",
                orientation="h",
                barmode="group",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(area, use_container_width=True, hide_index=True)
    with col2:
        st.subheader("Analisa Bulan | 月份分析")
        month = tables["months"]
        if not month.empty:
            fig = px.bar(
                month,
                x="Nama",
                y=["Total Ton", "Selesai Ton", "Sisa Ton"],
                barmode="group",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(month, use_container_width=True, hide_index=True)

elif page == "SPK Prioritas":
    st.subheader("SPK Dengan Sisa Terbesar | 最大剩余SPK")
    spk = tables["spks"].sort_values("Sisa Ton", ascending=False)
    st.dataframe(spk, use_container_width=True, hide_index=True)
    if not spk.empty:
        top = spk.head(10).sort_values("Sisa Ton")
        fig = px.bar(
            top,
            x="Sisa Ton",
            y="Nama",
            orientation="h",
            labels={"Sisa Ton": "Sisa Tonase", "Nama": "SPK"},
        )
        st.plotly_chart(fig, use_container_width=True)

elif page == "Profil Material":
    st.subheader("Profil Dengan Tonase Terbesar | 型材吨位排名")
    pf = tables["profiles"]
    st.dataframe(pf, use_container_width=True, hide_index=True)
    if not pf.empty:
        top = pf.head(15).sort_values("Total Ton")
        fig = px.bar(top, x="Total Ton", y="Nama", orientation="h")
        st.plotly_chart(fig, use_container_width=True)

elif page == "AI Analyst":
    st.subheader("🤖 AI Analyst | AI 数据分析")
    st.caption(
        "AI menganalisis KPI dan tabel ringkasan yang sedang terhubung ke Google Sheets."
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input(
        "Contoh: Vendor mana yang sisa tonasenya paling besar dan harus diprioritaskan?"
    )

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            api_key = None

        if not api_key:
            answer = (
                "OPENAI_API_KEY belum dipasang di Streamlit Secrets. "
                "Tambahkan API key agar AI Analyst aktif."
            )
        else:
            client = OpenAI(api_key=api_key)
            model = st.secrets.get("OPENAI_MODEL", "gpt-5-mini")
            context = build_ai_context(kpi, tables)

            system_instruction = """
Anda adalah AI Analyst untuk sistem fabrikasi baja.
Jawab dalam Bahasa Indonesia yang ringkas, profesional, dan berbasis angka.
Gunakan hanya data JSON yang diberikan. Jangan mengarang nilai yang tidak ada.
Tonase harus ditulis dalam ton. Progress tampilkan sebagai persen.
Jika pengguna meminta prioritas, pertimbangkan sisa tonase besar dan progress rendah.
Jika ada ketidaklengkapan data, jelaskan secara singkat.
"""

            try:
                response = client.responses.create(
                    model=model,
                    instructions=system_instruction,
                    input=(
                        "DATA DASHBOARD:\n"
                        + context
                        + "\n\nPERTANYAAN PENGGUNA:\n"
                        + prompt
                    ),
                )
                answer = response.output_text
            except Exception as exc:
                answer = f"AI belum dapat menjawab. Detail: {exc}"

        with st.chat_message("assistant"):
            st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

st.divider()
st.caption(
    "Sistem: Google Sheets / Google Drive → Streamlit → OpenAI API. "
    "Gunakan akun/service account dengan akses minimum yang diperlukan."
)
