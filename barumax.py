import streamlit as st
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import asyncio
import nest_asyncio
import re
from collections import Counter

from topicopt import integrate_clustering_with_keywords, clean_text_for_clustering, is_unimportant_sentence

# Apply nest_asyncio untuk Streamlit
nest_asyncio.apply()

# --- KONFIGURASI TELEGRAM ---
api_id = 21469101
api_hash = '3088140cd7e561ecdadcfbd9871cf3f0'
session_name = 'session_utama'
wib = ZoneInfo("Asia/Jakarta")

# --- KONFIGURASI TOPIK ---
topik_keywords = {
    # Topik dengan logika "DAN" (semua kata harus ada)
    "status_bast": [
        ["bast"],
        ["stuck", "bast"]
    ],
    "verifikasi_toko": [
        ["verifikasi", "toko"],
        ["verivikasi", "toko"],
        ["cek", "id", "toko"]
    ],
    "verifikasi_pembayaran": [
        ["verifikasi", "pembayaran"],
        ["verifikasi", "pesanan"],
        ["verivikasi", "pembayaran"],
        ["minta", "verifikasi"],
        ["konfirmasi"],
        ["notif", "error"],
        ["verifikasi"],
        ["verivikasi"]
    ],
    "penerusan_dana": [
        ["penerusan", "dana"],
        ["dana", "diteruskan"],
        ["uang", "diteruskan"],
        ["penerusan"],
        ["diteruskan"],
        ["meneruskan"],
        ["dana", "teruskan"],
        ["uang", "teruskan"],
        ["penyaluran"],
        ["di teruskan"],
        ["salur"]
    ],
    "dana_belum_masuk": [
        ["dana", "belum", "masuk"],
        ["uang", "belum", "masuk"],
        ["dana", "masuk", "belum"],
        ["uang", "masuk", "belum"],
        ["dana", "tidak", "masuk"],
        ["uang", "tidak", "masuk"],
        ["dana", "gagal", "masuk"],
        ["uang", "gagal", "masuk"],
        ["belum", "masuk", "rekening"],
        ["belum", "transfer", "masuk"],
        ["belum", "masuk"]

    ],
    "jadwal_cair_dana": [
        ["bos", "cair"],
        ["bop", "cair"],
        ["jadwal", "cair"],
        ["kapan", "cair"],
        ["gelombang", "2"],
        ["tahap", "2"],
        ["pencairan"]
    ],
    "modal_talangan": [
        ["modal", "talangan"],
        ["modal", "kerja"],
        ["dana", "talangan"],
        ["dana", "kerja"],
        ["modal", "bantuan"],
        ["modal", "usaha"],
        ["modal", "bantuan", "usaha"]
    ],
    "kendala_akses" : [
        ["kendala", "akses"],
        ["gagal", "akses"],
        ["tidak", "bisa", "akses"],
        ["tidak", "bisa", "login"],
        ["tidak", "bisa", "masuk"],
        ["gagal", "login"],
        ["gagal", "masuk"],
        ["gagal", "akses"],
        ["reset", "akun"],
        ["reset", "password"],
        ["ganti", "password"],
        ["ganti", "akun"],
        ["ganti", "email"],
        ["ganti", "nomor"],
        ["ganti", "no hp"],
        ["ganti", "no telepon"],
        ["ganti", "telepon"],
        ["eror", "akses"],
        ["eror", "login"],
        ["eror"],
        ["web", "dibuka"],
        ["gk", "bisa", "masuk"],
        ["belum", "lancar"],
        ["bisa", "diakses"],
        ["gangguan"],
        ["gangguannya"],
        ["belum", "normal", "webnya"],
        ["trobel"],
        ["trobelnya"],
        ["ga", "bisa", "akses"],
        ["ga", "bisa", "log", "in"],
        ["ga", "bisa", "masuk"],
        ["ga", "bisa", "web"],
        ["g", "masuk2"],
        ["gk", "bisa2"],
        ["web", "troubel"],
        ["jaringan"],
        ["belum", "bisa", "masuk", "situs"],
        ["belum", "normal", "web"],
        ["vpn"],
        ["gabisa", "login"],
        ["gabisa", "akses"],
        ["g", "bisa", "akses"],
        ["g", "bisa", "login"],
        ["tidak", "bisa", "di", "buka"],
        ["bermasalah", "login"],
        ["login", "trouble"],
        ["maintenance"],
        ["di block"],
        ["normal"],
        ["error"]
        
    ],
    "kendala_autentikasi": [
        ["kendala", "autentikasi"],
        ["gagal", "autentikasi"],
        ["tidak", "bisa", "autentikasi"],
        ["gagal", "otentikasi"],
        ["tidak", "bisa", "otentikasi"],
        ["authenticator", "reset"], 
        ["autentikasi"],
        ["autentifikasi"],
        ["otentikasi"],
        ["otp", "gagal"],
        ["otp", "tidak", "bisa"],
        ["otp", "tidak", "muncul"],
        ["otp", "tidak", "tampil"],
        ["otp", "tidak", "ada"],
        ["reset", "barcode"],
        ["authenticator"],
        ["aktivasi"]
    ],
    "kendala_upload": [
        ["kendala", "upload"],
        ["gagal", "upload"],
        ["tidak", "bisa", "upload"],
        ["gagal", "unggah"],
        ["tidak", "bisa", "unggah"],
        ["produk", "tidak", "muncul"],
        ["produk", "tidak", "tampil"],
        ["produk", "tidak", "ada"],
        ["produk", "massal"],
        ["produk", "masal"],
        ["template", "upload"],
        ["template", "unggah"],
        ["unggah", "produk"],
        ["menambahkan"],
        ["menambah", "produk"],
        ["tambah", "produk"],
        ["tambah", "barang"],
        ["unggah", "foto"],
        ["unggah", "gambar"],
        ["unggah", "foto", "produk"],
        ["unggah", "gambar", "produk"]
    ],
    "kendala_pengiriman": [
        ["tidak", "bisa", "pengiriman"],
        ["barang", "rusak"],
        ["barang", "hilang"],
        ["status", "pengiriman"]
    ],
    "tanda_tangan_elektronik": [
        ["tanda", "tangan", "elektronik"],
        ["ttd", "elektronik"],
        ["tte"],
        ["ttd"],
        ["tt elektronik"],
        ["e", "sign"],
        ["elektronik", "dokumen"]
    ],
    "ubah_data_toko": [
        ["ubah", "data", "toko"],
        ["edit", "data", "toko"],
        ["ubah", "nama", "toko"],
        ["edit", "nama", "toko"],
        ["ubah", "rekening"],
        ["edit", "rekening"],
        ["ubah", "status", "toko"],
        ["edit", "status", "toko"],
        ["ubah", "status", "umkm"],
        ["edit", "status", "umkm"],
        ["ubah", "status", "pkp"],
        ["ganti"]
    ],
    "akun_pengguna": [
        ["ganti", "email"],
        ["ubah", "email"],
        ["ganti", "nama", "akun"],
        ["ubah", "nama", "akun"],
        ["ganti", "akun"],
        ["ubah", "akun"],
        ["gagal", "ganti", "akun"],
        ["gagal", "ubah", "akun"]
    ],
    "pengajuan_modal": [
        ["pengajuan", "modal"],
        ["ajukan", "modal"],
        ["modal", "kerja"],
        ["dana", "talangan"],
        ["dibatalkan", "pengajuan"],
        ["tidak", "bisa", "ajukan"]
    ],
    "pajak": [
        ["pajak", "ppn"],
        ["pajak", "invoice"],
        ["pajak", "npwp"],
        ["pajak", "penghasilan"],
        ["e-billing"],
        ["dipotong", "pajak"],
        ["pajak", "keluaran"],
        ["potongan", "pajak"],
        ["coretax"],
        ["pajak"],
        ["ppn"],
        ["npwp"],
        ["e-faktur"],
        ["efaktur"],
        ["e-billing"]
    ],
    "etika_penggunaan": [
        ["bendahara", "dapat", "untung"],
        ["bendahara", "dagang"],
        ["bendahara", "etik"],
        ["distributor", "dilarang"],
        ["etik", "distributor"],
        ["etik", "larangan"],
        ["etik", "juknis"],
        ["larangan"]
    ],
    
    # Topik dengan logika "ATAU" (salah satu kata cukup)
    "pembayaran_dana": ["transfer", "dana masuk", "pengembalian", "bayar", "pembayaran", "dana", "dibayar", "notif pembayaran", "transaksi", "expired"],
    "pengiriman_barang": ["pengiriman", "barang rusak", "kapan dikirim", "status pengiriman", "diproses"],
    "penggunaan_siplah": ["pakai siplah", "siplah", "laporan siplah", "pembelanjaan", "tanggal pembelanjaan", "ubah tanggal", "dokumen", "bisa langsung dipakai", "terhubung arkas"],
    "kurir_pengiriman": ["ubah kurir", "ubah jasa kirim", "jasa pengiriman", "jasa kurir"],
    "status": ["cek"],
    "bantuan_umum": ["ijin tanya", "minta tolong", "tidak bisa", "cara", "masalah", "mau tanya", "input", "pkp", "pesanan gantung", "di luar dari arkas", "di bayar dari"],
    "lainnya": []
}

# --- Fungsi Deteksi Pertanyaan ---
def is_question_like(text):
    if pd.isna(text) or not isinstance(text, str): return False
    text = text.strip().lower()
    if "?" in text: return True
    if len(text.split()) < 3: return False
    question_phrases = ["mau tanya", "apa", "apakah", "siapa", "kapan", "bagaimana", "kenapa"]
    return any(phrase in text for phrase in question_phrases)

# --- Fungsi Scraping Aman ---
async def scrape_messages(group, start_dt, end_dt, progress_callback=None):
    all_messages = []
    sender_cache = {}
    try:
        async with TelegramClient(session_name, api_id, api_hash) as client:
            entity = await client.get_entity(group)
            offset_id = 0
            limit = 100

            while True:
                history = await client(GetHistoryRequest(
                    peer=entity, limit=limit, offset_id=offset_id,
                    offset_date=None, max_id=0, min_id=0, add_offset=0, hash=0
                ))
                if not history.messages: break
                messages = history.messages
                msg_date_wib_oldest = messages[-1].date.astimezone(wib)

                # Stop if pesan lebih tua dari start_dt
                if msg_date_wib_oldest < start_dt:
                    messages = [msg for msg in messages if msg.date.astimezone(wib) >= start_dt]

                for msg in messages:
                    if not msg.message or not msg.date or not msg.sender_id: continue
                    msg_date_wib = msg.date.astimezone(wib)
                    if start_dt <= msg_date_wib <= end_dt:
                        sender_id = msg.sender_id
                        sender_name = sender_cache.get(sender_id)
                        if sender_name is None:
                            try:
                                sender = await client.get_entity(sender_id)
                                first_name = sender.first_name or ""
                                last_name = sender.last_name or ""
                                sender_name = f"{first_name} {last_name}".strip() or sender.username or f"User ID: {sender_id}"
                                sender_cache[sender_id] = sender_name
                            except Exception:
                                sender_name = f"User ID: {sender_id}"
                                sender_cache[sender_id] = sender_name
                        all_messages.append({
                            'id': msg.id, 'sender_id': sender_id, 'sender_name': sender_name,
                            'text': msg.message, 'date': msg_date_wib.strftime("%Y-%m-%d %H:%M:%S")
                        })

                if not messages or msg_date_wib_oldest < start_dt:
                    break
                offset_id = messages[-1].id

                if progress_callback:
                    progress_callback(len(all_messages))

    except Exception as e:
        st.error(f"Terjadi kesalahan saat scraping: {e}")
        return None

    return pd.DataFrame(all_messages)

# --- Streamlit UI ---
st.set_page_config(page_title="Scraper & Analisis Telegram", layout="wide")
st.title("🏦 Analisis Topik Pertanyaan Grup Telegram")

group = st.text_input("Masukkan username atau ID grup Telegram:", "@contohgroup")
today = datetime.now(wib).date()
week_ago = today - timedelta(days=7)
col1, col2 = st.columns(2)
with col1:
    start_date_scrape = st.date_input("Scrape dari tanggal", week_ago)
with col2:
    end_date_scrape = st.date_input("Scrape sampai tanggal", today)

# Tombol proses
if st.button("🚀 Mulai Proses dan Analisis"):

    if not group or group == "@contohgroup":
        st.warning("Mohon isi grup Telegram yang valid.")
        st.stop()

    start_dt = datetime.combine(start_date_scrape, datetime.min.time()).replace(tzinfo=wib)
    end_dt = datetime.combine(end_date_scrape, datetime.max.time()).replace(tzinfo=wib)

    progress_bar = st.progress(0, text="Mulai scraping...")

    def update_progress(total_messages):
        # Asumsi maksimal 2000 pesan untuk progress bar
        progress = min(total_messages / 2000, 1.0)
        progress_bar.progress(progress, text=f"Pesan terambil: {total_messages}")

    # Jalankan scraping async dengan run_until_complete
    loop = asyncio.get_event_loop()
    df_all = loop.run_until_complete(scrape_messages(group, start_dt, end_dt, progress_callback=update_progress))

    if df_all is None or df_all.empty:
        st.warning("Tidak ada pesan yang diambil.")
        st.stop()
    else:
        st.success(f"Berhasil mengambil {len(df_all)} pesan mentah.")

    # --- Preprocessing & Deteksi Pertanyaan ---
    df_all['text'] = df_all['text'].str.lower().str.replace(r'http\S+|www\.\S+', '', regex=True)
    df_all = df_all[df_all['text'].str.strip() != '']
    df_all.drop_duplicates(subset=['sender_id', 'text', 'date'], inplace=True)
    df_all = df_all[~df_all['sender_name'].isin(['CS TokoLadang', 'Eko | TokLa', 'Vava'])]
    df_all['is_question'] = df_all['text'].apply(is_question_like)
    df_questions = df_all[df_all['is_question']].copy()
    df_questions['processed_text'] = df_questions['text'].apply(clean_text_for_clustering)
    df_questions = df_questions[~df_questions['processed_text'].apply(is_unimportant_sentence)]

    # --- Tampilkan di Streamlit ---
    st.subheader(f"❓ Ditemukan {len(df_questions)} Pertanyaan")
    st.dataframe(df_questions[['date', 'sender_name', 'text']], use_container_width=True)

    # Analisis topik
    if not df_questions.empty:
        df_for_clustering = df_questions.copy()
        df_for_clustering['text'] = df_for_clustering['processed_text']
        df_questions_with_topics = integrate_clustering_with_keywords(df_for_clustering, topik_keywords, num_auto_clusters=7)

        topik_counter = Counter(df_questions_with_topics["final_topic"])
        st.subheader("📊 Ringkasan Topik")
        summary_data = [{"Topik": t, "Jumlah Pertanyaan": c} for t, c in topik_counter.most_common()]
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
