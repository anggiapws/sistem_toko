import streamlit as st
import pandas as pd
from datetime import datetime, date
import io
import barcode
from barcode.writer import ImageWriter

# --- Hilangkan import pyzbar, webrtc_streamer, cv2, av ---


st.markdown("""
<style>
/* === Sidebar biru dengan padding dan shadow === */
[data-testid="stSidebar"] {
    background-color: #87CEEB !important;
    color: white !important;
    padding: 1rem;
    box-shadow: 2px 0 8px rgba(0,0,0,0.1);
}

/* === Sembunyikan radio button === */
div[role="radiogroup"] > label > input[type="radio"] {
    display: none;
}

/* === Gaya tombol menu (label) === */
div[role="radiogroup"] > label {
    background-color: rgba(0, 51, 102, 0.4);
    border: 1.5px solid #ffffff60;
    border-radius: 6px;
    margin-bottom: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: white !important;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    transition: background-color 0.2s ease, border 0.2s ease;
    width: 100%;
    box-sizing: border-box;
    min-height: 38px;
}

/* === Hover efek biru tua === */
div[role="radiogroup"] > label:hover {
    background-color: #003366;
    border-color: #003366;
    color: #e0e7ff;
}

/* === Aktif (terpilih) === */
div[role="radiogroup"] > label[aria-checked="true"] {
    background-color: #002244;
    border-color: #002244;
    box-shadow: 0 0 4px rgba(0,34,68,0.7);
    font-weight: bold;
    color: white;
}

/* === Scroll horizontal untuk dataframe === */
.element-container:has(.dataframe) {
    overflow-x: auto;
}
</style>
""", unsafe_allow_html=True)

# === Inisialisasi session state ===
if "barang" not in st.session_state:
    st.session_state.barang = []  # List dict: {Kode, Nama, Jenis, Harga Beli, Harga Jual, Stok}
if "jenis_list" not in st.session_state:
    st.session_state.jenis_list = []
if "kode_list" not in st.session_state:
    st.session_state.kode_list = []
if "transaksi_aktif" not in st.session_state:
    st.session_state.transaksi_aktif = []  # keranjang sekarang
if "riwayat_transaksi" not in st.session_state:
    st.session_state.riwayat_transaksi = []  # riwayat transaksi selesai
if "pengeluaran" not in st.session_state:
    st.session_state.pengeluaran = []

# Fungsi cari barang by kode
def cari_barang_by_kode(kode):
    for b in st.session_state.barang:
        if b["Kode"] == kode:
            return b
    return None


st.sidebar.title("Menu Utama")
menu = st.sidebar.radio("", [
    "Input Barang", 
    "Output Barang", 
    "Transaksi Bulanan", 
    "Keuntungan"
])

# === MENU: INPUT BARANG ===
if menu == "Input Barang":
    st.header("Input Barang Baru")

    with st.form("form_input_barang"):
        col1, col2 = st.columns(2)

        with col1:
            nama = st.text_input("Nama Barang")
            jenis_opsi = st.session_state.jenis_list.copy()
            jenis_opsi.append("Tambah Jenis Baru")
            jenis_pilih = st.selectbox("Jenis Barang", jenis_opsi)

            if jenis_pilih == "Tambah Jenis Baru":
                jenis_final = st.text_input("Masukkan Jenis Baru").strip()
            else:
                jenis_final = jenis_pilih

            kode_opsi = st.session_state.kode_list.copy()
            kode_opsi.append("Tambah Kode Baru")
            kode_pilih = st.selectbox("Kode Barang", kode_opsi)

            if kode_pilih == "Tambah Kode Baru":
                kode_input = st.text_input("Masukkan Kode Baru (manual input)")
            else:
                kode_input = kode_pilih

            stok = st.number_input("Stok Awal", min_value=0, step=1)

        with col2:
            st.markdown("### Barcode (opsional: hanya preview jika sudah ada kode)")
            if kode_input:
                try:
                    CODE128 = barcode.get_barcode_class('code128')
                    barcode_img = CODE128(kode_input, writer=ImageWriter(), add_checksum=False)
                    buffer = io.BytesIO()
                    barcode_img.write(buffer)
                    buffer.seek(0)
                    st.image(buffer, caption=f"Barcode: {kode_input}", use_container_width=True)
                except Exception as e:
                    st.warning("Tidak bisa generate barcode untuk kode ini.")

            harga_beli = st.number_input("Harga Modal (Rp)", min_value=0, step=1000, format="%d")
            harga_jual = st.number_input("Harga Jual (Rp)", min_value=0, step=1000, format="%d")

        submit = st.form_submit_button("Simpan Barang")

        if submit:
            if not nama or not jenis_final or not kode_input:
                st.error("❗ Semua kolom wajib diisi.")
            else:
                barang_baru = {
                    "Kode": kode_input,
                    "Nama": nama,
                    "Jenis": jenis_final,
                    "Harga Beli": harga_beli,
                    "Harga Jual": harga_jual,
                    "Stok": stok,
                }
                st.session_state.barang.append(barang_baru)

                if jenis_final not in st.session_state.jenis_list:
                    st.session_state.jenis_list.append(jenis_final)
                if kode_input not in st.session_state.kode_list:
                    st.session_state.kode_list.append(kode_input)

                st.success(f"Barang '{nama}' berhasil disimpan.")

    if st.session_state.barang:
        st.markdown("---")
        st.subheader("Daftar Barang")
        df = pd.DataFrame(st.session_state.barang)
        st.dataframe(df.style.format({"Harga Beli": "{:,.0f}", "Harga Jual": "{:,.0f}", "Stok": "{:d}"}), use_container_width=True)

# === MENU: OUTPUT BARANG ===
elif menu == "Output Barang":
    st.header("Kasir - Tambah ke Keranjang & Bayar")

    kode_barang_tersedia = [b["Kode"] for b in st.session_state.barang]
    pilih_kode_manual = st.selectbox("Pilih Kode Barang (Manual)", [""] + kode_barang_tersedia)

    kode_terpilih = pilih_kode_manual

    produk = cari_barang_by_kode(kode_terpilih) if kode_terpilih else None

    if produk:
        st.markdown("### Detail Produk")
        col_det1, col_det2 = st.columns(2)
        with col_det1:
            st.write(f"**Nama:** {produk['Nama']}")
            st.write(f"**Jenis:** {produk['Jenis']}")
            st.write(f"**Stok Tersedia:** {produk['Stok']}")
        with col_det2:
            st.write(f"**Harga Jual:** Rp {produk['Harga Jual']:,}")

        jumlah_beli = st.number_input("Jumlah Beli", min_value=1, max_value=produk["Stok"], step=1)

        if st.button("Tambah ke Keranjang"):
            if jumlah_beli > produk["Stok"]:
                st.error("Jumlah beli melebihi stok tersedia!")
            else:
                idx_keranjang = next((i for i, item in enumerate(st.session_state.transaksi_aktif) if item["Kode"] == produk["Kode"]), -1)
                if idx_keranjang >= 0:
                    # Update jumlah dan total di keranjang
                    st.session_state.transaksi_aktif[idx_keranjang]["Jumlah"] += jumlah_beli
                    st.session_state.transaksi_aktif[idx_keranjang]["Total"] = st.session_state.transaksi_aktif[idx_keranjang]["Jumlah"] * produk["Harga Jual"]
                else:
                    # Tambah baru di keranjang
                    st.session_state.transaksi_aktif.append({
                        "Kode": produk["Kode"],
                        "Nama": produk["Nama"],
                        "Harga Satuan": produk["Harga Jual"],
                        "Jumlah": jumlah_beli,
                        "Total": produk["Harga Jual"] * jumlah_beli
                    })
                st.success(f"{produk['Nama']} x{jumlah_beli} ditambahkan ke keranjang.")

    st.markdown("### Keranjang Belanja")
    if st.session_state.transaksi_aktif:
        df_keranjang = pd.DataFrame(st.session_state.transaksi_aktif)
        st.dataframe(df_keranjang.style.format({"Harga Satuan": "{:,.0f}", "Total": "{:,.0f}"}), use_container_width=True)

        total_bayar = df_keranjang["Total"].sum()
        st.markdown(f"**Total Bayar:** Rp {total_bayar:,}")

        bayar = st.number_input("Jumlah Pembayaran (Rp)", min_value=0, step=1000, format="%d")

        kembalian = bayar - total_bayar if bayar >= total_bayar else 0
        st.markdown(f"**Kembalian:** Rp {kembalian:,}")

        if st.button("Selesaikan Transaksi"):
            if bayar < total_bayar:
                st.error("Pembayaran kurang.")
            else:
                # Kurangi stok barang sesuai jumlah di keranjang
                for item in st.session_state.transaksi_aktif:
                    barang_ = cari_barang_by_kode(item["Kode"])
                    if barang_:
                        barang_["Stok"] -= item["Jumlah"]
                        if barang_["Stok"] < 0:
                            barang_["Stok"] = 0  # Jangan negatif

                # Simpan transaksi ke riwayat
                st.session_state.riwayat_transaksi.append({
                    "Tanggal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Detail": st.session_state.transaksi_aktif.copy(),
                    "Total Bayar": total_bayar,
                    "Bayar": bayar,
                    "Kembalian": kembalian
                })
                st.session_state.transaksi_aktif.clear()
                st.success("Transaksi berhasil diselesaikan.")
    else:
        st.info("Keranjang belanja masih kosong.")

# === MENU: TRANSAKSI BULANAN ===
elif menu == "Transaksi Bulanan":
    st.header("Riwayat Transaksi Bulanan")

    if not st.session_state.riwayat_transaksi:
        st.info("Belum ada transaksi yang tercatat.")
    else:
        df_trx = pd.DataFrame(st.session_state.riwayat_transaksi)
        df_trx["Bulan"] = pd.to_datetime(df_trx["Tanggal"]).dt.to_period("M")

        bulan_tersedia = df_trx["Bulan"].unique().tolist()
        bulan_terpilih = st.selectbox("Pilih Bulan", bulan_tersedia)

        df_filter = df_trx[df_trx["Bulan"] == bulan_terpilih]

        for i, trx in enumerate(df_filter.itertuples(), 1):
            st.markdown(f"### Transaksi #{len(df_filter) - i + 1} - {trx.Tanggal}")
            df_detail = pd.DataFrame(trx.Detail)
            st.dataframe(df_detail.style.format({"Harga Satuan": "{:,.0f}", "Total": "{:,.0f}"}), use_container_width=True)
            st.markdown(f"**Total Bayar:** Rp {trx._4:,}")
            st.markdown(f"**Bayar:** Rp {trx._5:,}")
            st.markdown(f"**Kembalian:** Rp {trx._6:,}")
            st.markdown("---")

# === MENU: KEUNTUNGAN ===
elif menu == "Keuntungan":
    st.header("Laporan Keuntungan Harian (Berdasarkan Harga Modal)")

    if not st.session_state.riwayat_transaksi:
        st.info("Belum ada transaksi.")
    else:
        data_laba = []

        for trx in st.session_state.riwayat_transaksi:
            tanggal = trx["Tanggal"][:10]
            total_keuntungan_hari_ini = 0

            for item in trx["Detail"]:
                kode = item["Kode"]
                jumlah = item["Jumlah"]
                harga_jual = item["Harga Satuan"]

                # Cari harga beli dari data barang
                barang_data = next((b for b in st.session_state.barang if b["Kode"] == kode), None)
                harga_beli = barang_data["Harga Beli"] if barang_data else 0

                # Hitung keuntungan untuk item ini
                keuntungan_item = (harga_jual - harga_beli) * jumlah
                total_keuntungan_hari_ini += keuntungan_item

            data_laba.append({"Tanggal": tanggal, "Keuntungan": total_keuntungan_hari_ini})

        df_laba = pd.DataFrame(data_laba)
        df_laba = df_laba.groupby("Tanggal").sum().reset_index()

        st.dataframe(df_laba.style.format({"Keuntungan": "Rp {:,.0f}"}), use_container_width=True)

        st.markdown(f"### 💰 Total Keuntungan: Rp {df_laba['Keuntungan'].sum():,.0f}")


    with st.form("form_pengeluaran"):
        tanggal = st.date_input("Tanggal", value=date.today())
        deskripsi = st.text_input("Deskripsi Pengeluaran")
        jumlah_pengeluaran = st.number_input("Jumlah Pengeluaran (Rp)", min_value=0, step=1000, format="%d")
        submit = st.form_submit_button("Simpan Pengeluaran")

        if submit:
            if not deskripsi or jumlah_pengeluaran <= 0:
                st.error("Mohon isi deskripsi dan jumlah pengeluaran dengan benar.")
            else:
                st.session_state.pengeluaran.append({
                    "Tanggal": tanggal.strftime("%Y-%m-%d"),
                    "Deskripsi": deskripsi,
                    "Jumlah": jumlah_pengeluaran
                })
                st.success("Pengeluaran berhasil disimpan.")

    if st.session_state.pengeluaran:
        st.markdown("---")
        st.subheader("Riwayat Pengeluaran")
        df_pengeluaran = pd.DataFrame(st.session_state.pengeluaran)
        st.dataframe(df_pengeluaran.style.format({"Jumlah": "{:,.0f}"}), use_container_width=True)
