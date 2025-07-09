# -----------------------------------------------
#  Aplikasi Streamlit: Sistem Manajemen ASN Non‑Guru
#  Versi diperbaiki (2025‑07‑06) – siap pakai di VS Code
# -----------------------------------------------


# --- IMPORT DASAR & KONFIGURASI -------------------------------------------
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import time

st.set_page_config(page_title="Login Sistem ASN", layout="wide")

# --- AUTENTIKASI GOOGLE SHEETS -------------------------------------------
@st.cache_resource(show_spinner="🔑  Menghubungkan ke Google Sheets …")
def connect_gsheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(
                st.secrets["gcred"], scope)
    client = gspread.authorize(creds)
    sheet  = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/1z8i_J3rylC0w-kuKRu_PZ-UfbgrdF8a9w8i2s5CFjz4"
    )
    return sheet.sheet1

worksheet = connect_gsheet()

# ────────────────────────────────────────────────
#               LOAD / RELOAD DATA
# ────────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    rec = worksheet.get_all_records()
    if not rec:
        return pd.DataFrame()
    df = pd.DataFrame(rec)
    df["TL"]   = pd.to_datetime(df["TL"],  dayfirst=True, errors="coerce")
    df["USIA"] = pd.to_numeric(df["USIA"], errors="coerce")
    return df

def reload_data():
    st.session_state.df = load_data()

if "df" not in st.session_state:
    reload_data()

get_df = lambda: st.session_state.df   # helper cepat

# ------------------ CLUSTERING TOOLS  --------------

def mapping_jabatan(j):
    j = j.upper()
    if any(x in j for x in ["AHLI MUDA","MUDA","KEPALA PUSKESMAS"]):                return "Fungsional Keahlian",58
    if "AHLI MADYA" in j:                                                           return "Fungsional Keahlian",60
    if any(x in j for x in ["AHLI UTAMA","DOKTER SPESIALIS"]):                      return "Fungsional Keahlian",65
    if any(x in j for x in ["TERAMPIL","PENYELIA","ADMINISTRASI","PELAKSANA",
                            "PEREKAYASA", "PEMULA","VERIFIKATOR PAJAK","PENGELOLA KEUANGAN","PENGEMUDI AMBULANCE","PEREKAM MEDIS","PEMULA"]):      return "Fungsional Keterampilan",58
    if any(x in j for x in ["AHLI PERTAMA","PERTAMA"]):                             return "Fungsional Keahlian",58
    return "Lainnya",58

def transform_jabatan(j):
    j = j.upper()
    if any(x in j for x in ["AHLI UTAMA","UTAMA"]): return 4
    if "AHLI MADYA"   in j: return 3
    if any(x in j for x in ["AHLI MUDA","MUDA"]): return 2
    if any(x in j for x in ["AHLI PERTAMA","PERTAMA"]): return 1
    if "PENYELIA"     in j: return 0.9
    if any(x in j for x in ["MAHIR","LANJUTAN/MAHIR"]): return 0.7
    if any(x in j for x in ["TERAMPIL","PELAKSANA/TERAMPIL", "TERAMPIL/PELAKSANA","LANJUTAN","PELAKSANA LANJUTAN"]): return 0.5
    if "PEMULA" in j: return 0.3
    return 0.2

@st.cache_data(show_spinner=False)
def apply_kmeans(df: pd.DataFrame):
    if df.empty: return df
    df = df.copy()
    df["Level Jabatan"]         = df["JABATAN"].apply(transform_jabatan)
    df["Kategori Jabatan"], mp  = zip(*df["JABATAN"].apply(mapping_jabatan))
    df["Masa Pensiun"]          = mp
    df["Sisa Masa Kerja"]       = df["Masa Pensiun"] - df["USIA"].fillna(0)

    X = df[["Sisa Masa Kerja","Level Jabatan"]].dropna()
    if len(X) >= 3:
        km   = KMeans(n_clusters=3, random_state=42, n_init=10)
        df.loc[X.index,"Cluster"] = km.fit_predict(X)
        means = df.groupby("Cluster")["Sisa Masa Kerja"].mean().sort_values()
        mapping = { means.index[0]:"Segera Pensiun",
                    means.index[1]:"Pensiun Menengah",
                    means.index[2]:"Masih Lama Pensiun" }
        df["Kategori Cluster"] = df["Cluster"].map(mapping)
    else:
        df["Kategori Cluster"] = "Data Kurang"
    return df
# ------------------ CSS: LOGIN SAJA ---------------------------------------

# --- CSS LOGIN -------------------------------------------------------------
LOGIN_CSS = """
<style>
    .login-container input {
        text-align: center;
        background: #f5f7fa;
        border: 2px solid #00b4d8;
        border-radius: 20px;
        padding: 10px;
    }
    .login-container button {
        width: 100%;
        padding: 12px;
        border-radius: 20px;
        background: #28a745;
        border: 2px solid #28a745;
        color: #fff;
        font-weight: bold;
    }
</style>
"""

# --- LOGIN PAGE ------------------------------------------------------------
LOGIN_CSS = """
<style>
.login-container input{ text-align:center;background:#f5f7fa;
 border:2px solid #00b4d8;border-radius:20px;padding:10px;}
.login-container button{ width:100%;padding:12px;border-radius:20px;
 background:#28a745;border:2px solid #28a745;color:#fff;font-weight:bold;}
</style>"""

def login():
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        col = st.columns([1,2,1])[1]
        with col:
            st.markdown("#### 👤 Username")
            u = st.text_input("u", key="u", label_visibility="hidden")
            st.markdown("#### 🔒 Password")
            p = st.text_input("p", key="p", type="password", label_visibility="hidden")
            if st.button("Login"):
                if u=="admin" and p=="admin123":
                    st.session_state.logged = True
                    st.rerun()
                else:
                    st.error("❌ Username atau password salah.")
        st.markdown("</div>", unsafe_allow_html=True)

if "logged" not in st.session_state:
    st.session_state.logged = False
if not st.session_state.logged:
    login()
    st.stop()

# # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
#     FUNGSI CRUD UNTUK GOOGLE SHEETS  
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
def get_df():
    data = worksheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
    if not df.empty:
        df = df.drop(columns=["No"], errors="ignore")  # 👉 Tambahkan baris ini
        df["USIA"] = pd.to_numeric(df["USIA"], errors="coerce").fillna(0).astype(int)
    return df

def add_row(rec):
    # Urutan sesuai header kecuali "No"
    kolom_urutan = ["ID PEGAWAI", "NAMA", "GDP", "GELAR BELAKANG", "JABATAN", "JK",
                    "TEMPAT LAHIR", "TL", "KODE OPD", "PENDIDIKAN AWAL",
                    "PENDIDIKAN AKHIR", "USIA", "OPD", "KOMPETENSI"]
    values = [[rec.get(k, "") for k in kolom_urutan]]
    worksheet.append_rows(values, value_input_option="USER_ENTERED", insert_data_option="INSERT_ROWS")
    return True

def update_row(id_pegawai, row):
    sheet_data = worksheet.get_all_values()
    for idx, r in enumerate(sheet_data[1:], start=2):  # data[0] = header, start dari row 2
        if r[0] == id_pegawai:  # Pastikan ID PEGAWAI ada di kolom A (indeks 0)
            worksheet.update(f"A{idx}:N{idx}", [row])  # update 14 kolom (A-N), kolom "No" tetap diabaikan
            return True
    return False

def delete_row(id_pegawai):
    sheet_data = worksheet.get_all_values()
    for idx, r in enumerate(sheet_data[1:], start=2):
        if r[0] == id_pegawai:
            worksheet.delete_rows(idx)
            return True
    return False

#────────────────────────────────────────────────
#                  SIDEBAR MENU
# ────────────────────────────────────────────────
import streamlit as st
from streamlit_option_menu import option_menu
menu_items = [
    "Beranda",
    "Data Pegawai",
    "Visualisasi Clustering",
    "Hasil Cluster",
    "Proyeksi Pensiun",
    "Hasil Visualisasi Magang",
    "Logout"
]

icons_items = [
    "house", "people", "pin-map", "file-earmark-text",
    "file-bar-graph", "person-bounding-box", "box-arrow-left"
]

with st.sidebar:
    page = option_menu(
        None,
        menu_items,
        icons=icons_items,
        styles={
            "container": {"padding": "5!important", "background": "#fff"},
            "icon": {"color": "black", "font-size": "18px"},
            "nav-link": {
                "font-size": "16px",
                "margin": "4px",
                "color": "#000",
                "border-radius": "8px"
            },
            "nav-link-selected": {
                "background": "#28a745",
                "color": "white",
                "font-weight": "bold"
            }
        }
    )

    # Optional: Tampilkan status login di bawah menu
    st.markdown("**👤 Login sebagai:** `admin`")
    
    # Tombol Refresh Data Manual
if st.button("🔄 Refresh Data dari Google Sheets"):
    reload_data()
    st.success("✅ Data berhasil diperbarui.")
    st.rerun()


# Handle Logout Langsung
if page == "Logout":
    st.session_state.logged = False
    st.success("Anda telah logout.")
    st.rerun()

# ────────────────────────────────────────────────
#                    PAGES
# ────────────────────────────────────────────────
# 1️⃣  BERANDA
# ------------------------------------------------
if page == "Beranda":
    df = get_df()
    st.title("📊 Dashboard Kepegawaian ASN")

    total_asn = df.shape[0]
    total_opd = df['OPD'].nunique()
    gender_count = df['JK'].value_counts()

    col1, col2, col3, col4 = st.columns(4)
    col1.markdown("#### 👥 Total ASN")
    col1.success(f"**{total_asn:,} Pegawai**")

    col2.markdown("#### 🏢 Total OPD")
    col2.info(f"**{total_opd:,} OPD**")

    col3.markdown("#### 👨‍💼 Laki-laki")
    col3.warning(f"**{int(gender_count.get('LAKI-LAKI', 0)):,} Orang**")

    col4.markdown("#### 👩‍💼 Perempuan")
    col4.warning(f"**{int(gender_count.get('PEREMPUAN', 0)):,} Orang**")

    # === PIE CHART USIA ===
    usia_bins = [0,25,30,35,40,45,50,55,60,150]
    usia_lbl  = ["<25","26‑30","31‑35","36‑40","41-45","46-50","51‑55","56‑60",">60"]
    df["KELOMPOK_USIA"] = pd.cut(df["USIA"], usia_bins, labels=usia_lbl)

    fig_usia = px.pie(df, names="KELOMPOK_USIA", title="Distribusi ASN berdasarkan Usia")
    st.plotly_chart(fig_usia, use_container_width=True)

    # === BAR CHART GENDER - PENDIDIKAN ===
    st.markdown("### 📊 Komposisi Pegawai Berdasarkan Pendidikan dan Jenis Kelamin")

    # Tambahkan baris ini dulu biar aman
    df['PENDIDIKAN_AKHIR'] = df['PENDIDIKAN AKHIR'].astype(str).str.upper().str.strip()

    pendidikan_gender = df.groupby(['JK', 'PENDIDIKAN_AKHIR']).size().reset_index(name='JUMLAH')
    fig2 = px.bar(pendidikan_gender, 
                x='JUMLAH', 
                y='PENDIDIKAN_AKHIR', 
                color='JK', 
                barmode='stack',
                labels={'JUMLAH': 'Jumlah Pegawai', 'PENDIDIKAN_AKHIR': 'Pendidikan'},
                height=500)
    st.plotly_chart(fig2, use_container_width=True)

        # 📊 Visualisasi Jumlah ASN per OPD
    st.markdown("### 🏢 Jumlah ASN per OPD")

    opd_count = df['OPD'].value_counts().reset_index()
    opd_count.columns = ['OPD', 'JUMLAH']

    st.dataframe(opd_count, use_container_width=True, height=500)

# ────────────────────────────────────────────────
#                    DATA PEGAWAI
# ────────────────────────────────────────────────    
elif page == "Data Pegawai":
    df = get_df()
    st.subheader("👥 Manajemen Data Pegawai")

    aksi = st.radio("Pilih Aksi", ["Tambah Data", "Hapus Data", "Edit Data"], horizontal=True)

    # Tambah Data
    if aksi == "Tambah Data":
        with st.form("add", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                idp = st.text_input("ID Pegawai")
                nama = st.text_input("Nama")
                gdp = st.text_input("GDP")
                gel = st.text_input("Gelar Belakang")
                jab = st.text_input("Jabatan")
                jk = st.selectbox("Jenis Kelamin", ["LAKI-LAKI", "PEREMPUAN"])
            with c2:
                tmp = st.text_input("Tempat Lahir")
                ttl = st.date_input("Tanggal Lahir", datetime.today(), min_value=datetime(1900, 1, 1))
                kod = st.text_input("Kode OPD")
                paw = st.text_input("Pendidikan Awal")
                pak = st.text_input("Pendidikan Akhir")
                usia = st.number_input("Usia", min_value=0, step=1)
                kmp = st.text_input("Kompetensi")
            opd = st.text_input("OPD")
            ok = st.form_submit_button("📂 Simpan")

        if ok:
            rec = {
                "ID PEGAWAI": idp,
                "NAMA": nama,
                "GDP": gdp,
                "GELAR BELAKANG": gel,
                "JABATAN": jab,
                "JK": jk,
                "TEMPAT LAHIR": tmp,
                "TL": ttl.strftime("%d/%m/%Y"),
                "KODE OPD": kod,
                "PENDIDIKAN AWAL": paw,
                "PENDIDIKAN AKHIR": pak,
                "USIA": int(usia),
                "OPD": opd,
                "KOMPETENSI": kmp
            }
            if add_row(rec):
                st.success("Data berhasil ditambahkan ✅")
                st.rerun()

    # Hapus Data
    elif aksi == "Hapus Data":
        if df.empty:
            st.info("Belum ada data!")
        else:
            df["label"] = df["ID PEGAWAI"].astype(str) + " - " + df["NAMA"].astype(str)
            pilih = st.selectbox("Pilih Pegawai", df["label"])
            id_pilih = pilih.split(" - ")[0]
            if st.button("🔝️ Hapus"):
                if delete_row(id_pilih):
                    st.success("✅ Terhapus")
                    st.rerun()

    # Edit Data
    elif aksi == "Edit Data":
        if df.empty:
            st.info("Belum ada data!")
        else:
            st.markdown("### ✏️ Edit Data Pegawai")
            id_list = df["ID PEGAWAI"].unique().tolist()
            selected_id = st.selectbox("Pilih ID Pegawai untuk Diedit", id_list)
            ori = df[df["ID PEGAWAI"] == selected_id]
            if not ori.empty:
                r = ori.iloc[0]
                with st.form("form_edit_data"):
                    c1, c2 = st.columns(2)
                    with c1:
                        idp = st.text_input("ID Pegawai", r["ID PEGAWAI"])
                        nama = st.text_input("Nama", r["NAMA"])
                        gdp = st.text_input("GDP", r["GDP"])
                        gel = st.text_input("Gelar Belakang", r["GELAR BELAKANG"])
                        jab = st.text_input("Jabatan", r["JABATAN"])
                        jk = st.selectbox("Jenis Kelamin", ["LAKI-LAKI", "PEREMPUAN"], 0 if r["JK"].startswith("L") else 1)
                        tmp = st.text_input("Tempat Lahir", r["TEMPAT LAHIR"])
                    with c2:
                        ttl_str = r["TL"]
                        try:
                            ttl_obj = datetime.strptime(ttl_str, "%d/%m/%Y")
                        except:
                            ttl_obj = datetime.today()
                        ttl = st.date_input("Tanggal Lahir", ttl_obj, min_value=datetime(1900, 1, 1))
                        kod = st.text_input("Kode OPD", r["KODE OPD"])
                        paw = st.text_input("Pendidikan Awal", r["PENDIDIKAN AWAL"])
                        pak = st.text_input("Pendidikan Akhir", r["PENDIDIKAN AKHIR"])
                        usia = st.number_input("Usia", 0, 150, int(r["USIA"]))
                        opd = st.text_input("OPD", r["OPD"])
                    kmp = st.text_input("Kompetensi", r["KOMPETENSI"])
                    simpan = st.form_submit_button("📂 Simpan")

                if simpan:
                    row = [idp, nama, gdp, gel, jab, jk, tmp, ttl.strftime("%d/%m/%Y"), kod, paw, pak, int(usia), opd, kmp]
                    if update_row(selected_id, row):
                        st.success("✅ Data berhasil diupdate!")
                        st.rerun()

        # —— Show table + download
    st.divider()
    st.dataframe(get_df(),use_container_width=True)
    st.download_button("📥 Unduh CSV", get_df().to_csv(index=False).encode(),
                    "data_pegawai.csv","text/csv")

    # ✅ Tampilkan tombol link spreadsheet hanya di halaman Tambah Data
    if aksi == "Tambah Data":
        st.markdown("""
        <a href="https://docs.google.com/spreadsheets/d/1z8i_J3rylC0w-kuKRu_PZ-UfbgrdF8a9w8i2s5CFjz4"
        target="_blank">
            <button style="background:#28a745;color:white;padding:10px 20px;
                        border:none;border-radius:8px;font-size:16px;
                        cursor:pointer;">
                📄 Buka Spreadsheet Data Pegawai
            </button>
        </a>
        """, unsafe_allow_html=True)


# 3️⃣  Visualisasi Clustering
# ------------------------------------------------
elif page == "Visualisasi Clustering":
    # Kembalikan DataFrame hasil klaster
    df = apply_kmeans(get_df())     # pastikan hasilnya ada 'Sisa Masa Kerja',
                                    # 'Level Jabatan', dan 'Kategori Cluster'
    # Validasi data
    if df.empty:
        st.warning("Belum ada data.")
    elif not {"Sisa Masa Kerja", "Level Jabatan", "Kategori Cluster"} <= set(df.columns):
        st.warning("Kolom belum lengkap.")
    else:
        # ----------------------------------------
        # 1) Plot utama (seaborn scatter)
        # ----------------------------------------
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.scatterplot(
            data=df,
            x="Sisa Masa Kerja",
            y="Level Jabatan",
            hue="Kategori Cluster",       # ganti jadi 'Cluster' kalau itu nama kolommu
            palette="Set2",
            s=80,
            ax=ax
        )
        # 2) Hitung & plot centroid
        # ----------------------------------------
        # Cara cepat: rata‑rata tiap klaster
        centroids = (
            df.groupby("Kategori Cluster")[["Sisa Masa Kerja", "Level Jabatan"]]
            .mean()
            .reset_index(drop=True)
            .values
        )

        ax.scatter(
            centroids[:, 0],                  # x‑centroid
            centroids[:, 1],                  # y‑centroid
            c="black",
            s=200,
            marker="X",
            label="Centroid"
        )
        # 3) Layout & gaya
        # ----------------------------------------
        ax.set_title(
            "Visualisasi Klaster ASN Berdasarkan Sisa Masa Kerja dan Level Jabatan",
            fontsize=14
        )
        ax.set_xlabel("Sisa Masa Kerja")
        ax.set_ylabel("Level Jabatan")
        ax.grid(True)
        ax.legend()
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)

        # 4) Penjelasan Level Jabatan
        st.markdown("---")
        st.subheader("📘 Keterangan Nilai 'Level Jabatan'")
        st.markdown("""
        Berikut ini adalah konversi nilai numerik untuk `Level Jabatan` berdasarkan jabatan fungsional:
        
        - **4.0** : AHLI UTAMA  
        - **3.0** : AHLI MADYA  
        - **2.0** : AHLI MUDA   
        - **1.0** : AHLI PERTAMA   
        - **0.9** : PENYELIA  
        - **0.7** : MAHIR   
        - **0.5** : TERAMPIL 
        - **0.3** : PEMULA  
        """)


# ────────────────────────────────────────────────
# ==========================================================================

# ------------------ HASIL CLUSTER ------------------
elif page == "Hasil Cluster":          # ← pakai page
    df = apply_kmeans(get_df())        # ← jamin df defined

    st.subheader("📄 Ringkasan Hasil Clustering")
    ringkasan = df.groupby("Kategori Cluster").agg({
        "NAMA": "count",
        "Sisa Masa Kerja": "mean",
        "Level Jabatan": "mean",
        "OPD": pd.Series.nunique
    }).rename(columns={
        "NAMA": "Jumlah Pegawai",
        "Sisa Masa Kerja": "Rata‑rata Sisa Masa Kerja",
        "Level Jabatan": "Rata‑rata Level Jabatan",
        "OPD": "Jumlah OPD"
    })
    st.dataframe(ringkasan, use_container_width=True)

    st.markdown("### 📋 Detail Pegawai per Cluster")
    opsi = sorted(df["Kategori Cluster"].unique())
    pilih = st.multiselect("Pilih cluster:", opsi, default=[])
    if not pilih:
        st.info("Silakan pilih cluster terlebih dahulu.")
    else:
        detail = df[df["Kategori Cluster"].isin(pilih)].sort_values(
                    by="Sisa Masa Kerja")
        st.dataframe(detail[[ "NAMA","JABATAN","OPD","USIA",
                              "Sisa Masa Kerja","Level Jabatan",
                              "Kategori Cluster"]])
        
        
# ------------------ PROYEKSI PENSIUN ------------------
elif page == "Proyeksi Pensiun":
    df = apply_kmeans(get_df())
    st.subheader("📌 Proyeksi Pensiun & Ketersediaan Pengganti")
    
    # --- Slider: Tahun Pensiun ---
    batas_pensiun = st.slider("🎯 Batas Maksimum Sisa Masa Kerja (tahun)", min_value=1, max_value=50, value=5)

    # --- Filter pegawai yang akan pensiun dalam rentang tahun tsb
    df_pensiun = df[df["Sisa Masa Kerja"] <= batas_pensiun]
    st.markdown(f"#### 👴 Daftar Pegawai Akan Pensiun ≤ {batas_pensiun} Tahun")
    st.dataframe(df_pensiun[['NAMA', 'JABATAN', 'OPD', 'USIA', 'Sisa Masa Kerja']])

    # --- Rekap jumlah pensiun berdasarkan jabatan dan OPD
    pensiun_grouped = df_pensiun.groupby(["JABATAN", "OPD","KOMPETENSI","PENDIDIKAN AKHIR"]).size().reset_index(name="Jumlah_Pensiun")

    # --- Slider: Filter Usia ASN muda
    usia_batas = st.slider("🧒 Batas Usia ASN Muda (default < 35)", min_value=25, max_value=45, value=35)
    df_muda = df[df["USIA"] < usia_batas]   

    # --- Rekap ASN muda per jabatan dan OPD
    muda_grouped = df_muda.groupby(["JABATAN", "OPD","KOMPETENSI","PENDIDIKAN AKHIR"]).size().reset_index(name="Jumlah_Muda")

    # --- Gabungkan & analisis ketersediaan pengganti
    df_gap = pd.merge(pensiun_grouped, muda_grouped, on=["JABATAN", "OPD","KOMPETENSI","PENDIDIKAN AKHIR"], how="left")
    df_gap["Jumlah_Muda"] = df_gap["Jumlah_Muda"].fillna(0).astype(int)
    df_gap["Tersedia_Pengganti"] = df_gap["Jumlah_Muda"].apply(lambda x: "Ya" if x > 0 else "Tidak")

    st.markdown("#### 📊 Rekap Pensiun dan Pengganti")
    st.dataframe(df_gap)

    # --- Tombol unduh
    csv_gap = df_gap.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Unduh Rekap Proyeksi Pensiun", data=csv_gap, file_name="proyeksi_pensiun.csv", mime="text/csv")


# ------------------  ------------------
elif page == "Hasil Visualisasi Magang":
    df = apply_kmeans(get_df())
    st.subheader("🌱 Visualisasi Pegawai PNS Non Guru")

    # Bikin Rentang Usia berdasarkan kolom USIA
    bins_usia = [0, 25, 30, 35, 40, 45, 50, 55, 60, 150]
    labels_usia = [
        '< 25 Tahun', '26-30 Tahun', '31-35 Tahun', '36-40 Tahun',
        '41-45 Tahun', '46-50 Tahun', '51-55 Tahun', '56-60 Tahun', '> 60 Tahun'
    ]
    df["Rentang Usia"] = pd.cut(df["USIA"], bins=bins_usia, labels=labels_usia, right=True)

    # Transformasi Rentang Usia ke Skor Numerik
    def transform_rentang_umur(rentang):
        rentang = str(rentang).strip()
        if rentang == '< 25 Tahun': return 1.0
        elif rentang == '26-30 Tahun': return 2.0
        elif rentang == '31-35 Tahun': return 3.0
        elif rentang == '36-40 Tahun': return 4.0
        elif rentang == '41-45 Tahun': return 5.0
        elif rentang == '46-50 Tahun': return 6.0
        elif rentang == '51-55 Tahun': return 7.0
        elif rentang == '56-60 Tahun': return 8.0
        elif rentang == '> 60 Tahun': return 9.0
        else: return 0.0

    df["Level Rentang Umur"] = df["Rentang Usia"].apply(transform_rentang_umur)

    # Mapping Pendidikan Akhir
    mapping_pendidikan = {
        'SARJANA MUDA AKADEMI': 1, 'SARJANA MUDA': 2, 'SEKOLAH MENENGAH ATAS': 3,
        'DIPLOMA I': 4, 'DIPLOMA II': 5, 'DIPLOMA III': 6, 'DIPLOMA IV': 6.5,
        'SARJANA (S1)': 7, 'PASCA SARJANA (S2)': 8, 'DOKTOR (S3)': 9
    }

    df['PENDIDIKAN_AKHIR'] = df['PENDIDIKAN AKHIR'].astype(str).str.upper().str.strip()
    df['PENDIDIKAN_AKHIR_NUM'] = df['PENDIDIKAN_AKHIR'].map(mapping_pendidikan).fillna(0).astype(float)

    # --- HEATMAP --- #
    with st.expander("📊 Heatmap Rata-rata Usia per Pendidikan Akhir dan Level Jabatan"):
        result = df.groupby(['PENDIDIKAN AKHIR', 'Level Jabatan'], as_index=False)['USIA'].mean()
        result.rename(columns={'USIA': 'Rata_rata_Usia'}, inplace=True)

        plt.figure(figsize=(14, 7))
        heatmap_data = result.pivot_table(index='PENDIDIKAN AKHIR', columns='Level Jabatan', values='Rata_rata_Usia')
        sns.heatmap(heatmap_data, annot=True, fmt=".1f", cmap="YlGnBu", linewidths=.5)

        plt.title('Rata-rata Usia Berdasarkan Pendidikan Akhir dan Level Jabatan', fontsize=14)
        plt.xlabel('Level Jabatan (Skor Numerik)')
        plt.ylabel('Pendidikan Akhir')
        plt.tight_layout()
        st.pyplot(plt)

    with st.expander("📊 Heatmap Rata-rata Usia berdasarkan Rentang Usia dan OPD"):
        result_usia_opd = df.groupby(['OPD', 'Rentang Usia'], as_index=False)['USIA'].mean()
        result_usia_opd.rename(columns={'USIA': 'Rata_rata_Usia'}, inplace=True)

        plt.figure(figsize=(18, 14))
        heatmap_data_usia_opd = result_usia_opd.pivot_table(index='OPD', columns='Rentang Usia', values='Rata_rata_Usia')
        sns.heatmap(heatmap_data_usia_opd, annot=True, fmt=".1f", cmap="Oranges", linewidths=.5)

        plt.title('Rata-rata Usia Pegawai Berdasarkan Rentang Usia dan OPD', fontsize=14)
        plt.xlabel('Rentang Usia')
        plt.ylabel('OPD')
        plt.tight_layout()
        st.pyplot(plt)

    with st.expander("📊 Jumlah Pegawai berdasarkan Pendidikan Akhir dan OPD"):
        freq_pendidikan_opd = df.groupby(['OPD', 'PENDIDIKAN_AKHIR']).size().reset_index(name='Jumlah')

        plt.figure(figsize=(18, 14))
        heatmap_freq_pendidikan_opd = freq_pendidikan_opd.pivot_table(index='OPD', columns='PENDIDIKAN_AKHIR', values='Jumlah', fill_value=0)
        sns.heatmap(heatmap_freq_pendidikan_opd, annot=True, fmt=".0f", cmap="YlOrBr", linewidths=.5)

        plt.title('Jumlah Pegawai Berdasarkan Pendidikan Akhir dan OPD', fontsize=14)
        plt.xlabel('Pendidikan Akhir')
        plt.ylabel('OPD')
        plt.tight_layout()
        st.pyplot(plt)



    # # Tombol unduh (opsional)
    # csv_talent = df_talent_muda.to_csv(index=False).encode('utf-8')
    # st.download_button("📥 Unduh Talent Pool", data=csv_talent, file_name="talent_pool_asn.csv", mime="text/csv")
