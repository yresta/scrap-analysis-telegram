import streamlit as st
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import asyncio
import nest_asyncio
import re
from collections import Counter

# Import the new clustering function
from topicopt import integrate_clustering_with_keywords, clean_text_for_clustering, is_unimportant_sentence

# Mengaplikasikan patch untuk event loop asyncio agar bisa berjalan di dalam Streamlit
nest_asyncio.apply()

# --- KONFIGURASI APLIKASI ---
api_id = 21469101  # Ganti dengan API ID Anda jika perlu
api_hash = '3088140cd7e561ecdadcfbd9871cf3f0' # Ganti dengan API Hash Anda jika perlu
session_name = 'session_utama'
wib = ZoneInfo("Asia/Jakarta")

# --- KONFIGURASI ANALISIS TOPIK (MENDUKUNG LOGIKA HYBRID AND/OR) ---
# Cara kerja:
# 1. LOGIKA "DAN" (AND): Jika nilai adalah list di dalam list -> [[kata1, kata2]]
#    Artinya, SEMUA kata dalam sub-list harus ada.
#    Contoh: "verifikasi_toko" akan cocok jika pesan mengandung "verifikasi" DAN "toko".
#
# 2. LOGIKA "ATAU" (OR): Jika nilai adalah list biasa -> [kata1, kata2]
#    Artinya, SALAH SATU kata dalam list sudah cukup untuk cocok.
#    Contoh: "pajak" akan cocok jika pesan mengandung "ppn" ATAU "pajak".
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

# --- TAMPILAN STREAMLIT ---
st.set_page_config(page_title="Scraper & Analisis Telegram", layout="wide")
st.title("🏦 Analisis Topik Pertanyaan Grup Telegram")
st.markdown("---")

# --- INPUT PENGGUNA ---
st.header("⚙️ Pengaturan Scraping")
group = st.text_input("Masukkan username atau ID grup Telegram:", "@contohgroup")
today = datetime.now(wib).date()
week_ago = today - timedelta(days=7)
col1, col2 = st.columns(2)
with col1:
    start_date_scrape = st.date_input("Scrape dari tanggal", week_ago, format="YYYY-MM-DD")
with col2:
    end_date_scrape = st.date_input("Scrape sampai tanggal", today, format="YYYY-MM-DD")
st.markdown("---")


# --- FUNGSI-FUNGSI ---

def is_question_like(text):
    """Mendeteksi apakah sebuah teks terlihat seperti pertanyaan."""
    if pd.isna(text) or not isinstance(text, str): return False
    text = text.strip().lower()
    if "?" in text: return True
    if re.search(r"\bpo[a-z0-9]{10,}\b", text): return True 
    if len(text.split()) < 3: return False
    
    question_phrases =  [
        # ==== 1. Permintaan Informasi Umum ====
        "ada yang tahu", "ada yg tau", "ada yg tahu", "ada yang tau ga", "ada yang tau gak",
        "ada yg punya info", "ada yg punya kabar", "ada kabar ga", "ada berita", "ada yg denger",
        "ada yg liat", "ada yg nemu", "ada yg ngalamin", "ada yang pernah", "yg udah tau",
        "udah ada yang tau", "ada info dong", "ada info gak", "info dong", "info donk",
        "kasih info dong", "kasih tau dong", "denger2 katanya", "bener gak sih",
        "tau ga", "tau gak", "kalian ada info?", "siapa yang tau?", "dengar kabar",
        "kabar terbaru apa", "yang tau share dong", "bisa kasih info?", "ada update?",

        # ==== 2. Tanya Langsung / Izin Bertanya ====
        "mau tanya", "pengen tanya", "pingin tanya", "ingin bertanya", "izin bertanya",
        "izin nanya", "boleh tanya", "boleh nanya", "numpang tanya", "tanya dong",
        "tanya donk", "nanya dong", "nanya ya", "aku mau nanya", "saya mau tanya",
        "penasaran nih", "penasaran banget", "penasaran donk", "mau nanya nih",
        "mau nanya ya", "btw mau tanya", "eh mau tanya", "boleh tau nggak",
        "pingin nanya", "penasaran aja", "bisa tanya gak", "lagi cari info nih",

        # ==== 3. Permintaan Bantuan / Solusi ====
        "minta tolong", "tolong dong", "tolongin dong", "tolong bantu", "bisa bantu",
        "butuh bantuan", "mohon bantuan", "mohon bantuannya", "minta bantuannya",
        "bisa tolong", "perlu bantuan nih", "ada solusi ga", "ada solusi gak",
        "apa solusinya", "gimana solusinya", "solusinya gimana", "ada yang bisa bantu",
        "ada yg bisa bantuin", "bisa bantuin gak", "butuh pertolongan", "bantu dong",
        "help dong", "help me", "minta tolong ya", "bantuin ya", "ada yang bisa nolong",

        # ==== 4. Permintaan Saran / Pendapat ====
        "ada saran", "minta sarannya", "butuh saran", "rekomendasi dong", "rekomendasi donk",
        "minta rekomendasi", "saran dong", "saran donk", "menurut kalian", "menurut agan",
        "gimana menurut kalian", "bagusnya gimana", "lebih baik yang mana", "kalian pilih yang mana",
        "kira-kira lebih bagus mana", "lebih enak mana", "mending yg mana", "menurutmu gimana",
        "kira2 pilih yg mana", "enaknya pilih yg mana", "bantu saran dong", "bantu milih dong",

        # ==== 5. Konfirmasi / Cek Status ====
        "sudah diproses belum", "udah masuk belum", "udah diapprove belum", "kok belum masuk",
        "belum cair ya", "pencairannya kapan", "kapan cair", "gimana prosesnya", "statusnya gimana",
        "sudah dicek belum", "cek status dong", "minta dicek", "mohon dicek", "sampai kapan ya",
        "bener ga", "ini valid gak", "ini udah benar?", "masih pending ya", "belum juga nih",
        "harus nunggu berapa lama", "status pending kah", "udah diproses kah", "masih dalam proses?",
        "sudah disetujui belum", "udah dikirim belum", "cek dulu dong", "konfirmasi dong",

        # ==== 6. Tanya Cara / Langkah ====
        "cara pakainya gimana", "cara pakenya gimana", "cara daftar gimana", "cara aksesnya gimana",
        "gimana caranya", "caranya gimana", "apa langkahnya", "apa tahapannya",
        "gimana stepnya", "step by step dong", "bisa kasih tutorial?", "tutorial dong",
        "cara install gimana", "cara setup gimana", "gimana setupnya", "konfigurasinya gimana",
        "gimana mulai", "cara mulainya gimana", "cara ngisi gimana", "cara input gimana",
        "login gimana", "cara reset gimana", "cara klaim gimana",

        # ==== 7. Kata Tanya Baku ====
        "apa", "apakah", "siapa", "kapan", "mengapa", "kenapa", "kenapa ya", "bagaimana",
        "gimana", "gimana ya", "gimana sih", "di mana", "dimana", "di mana ya", "berapa",
        "knp ya", "knp sih", "knp bisa", "apa ya", "yang mana ya", "kenapa begitu",
        "mengapakah", "kok bisa", "apa itu", "kenapa tidak",

        # ==== 8. Gaya Chat / Singkatan Umum ====
        "gmn ya", "gmn caranya", "gmn dong", "gmna sih", "gmna ini", "blh mnt",
        "mnt bantu", "mnt saran", "mnt info", "cek donk", "ini knp ya", "ini bgmn ya",
        "ini harus gimana", "ga ngerti", "bngung nih", "bingung banget", "bingung gw",
        "bisa dijelasin", "minta penjelasan", "bingung jelasin dong",

        # ==== 9. Seputar Pembayaran / Transaksi ====
        "va belum aktif ya", "va nya apa", "va nya belum keluar", "kode pembayaran mana",
        "kenapa pending", "kenapa gagal", "tf nya masuk belum", "rekeningnya mana",
        "sudah bayar belum", "bayarnya kemana", "no rek nya mana", "status tf nya apa",
        "konfirmasi pembayaran gimana", "bayar pakai apa", "pembayaran berhasil ga", "verifikasi donk",
        "rek belum masuk", "sudah transfer", "sudah tf", "uangnya belum masuk", "status transfer",
        "no pembayaran mana", "kode bayar belum muncul", "tf udah masuk?", "rek sudah benar belum"
    ]
    if any(phrase in text for phrase in question_phrases): return True

    question_words_at_start = ["apa", "apakah", "siapa", "kapan", "mengapa", "kenapa", "bagaimana", "dimana", "berapa"]
    first_two_words = " ".join(text.split()[:2])
    if any(first_two_words.startswith(word) for word in question_words_at_start):
        return True
        
    return False

async def scrape_messages(group, start_dt, end_dt):
    """Scrape pesan dari grup Telegram dalam rentang tanggal tertentu."""
    all_messages = []
    sender_cache = {}
    progress_bar = st.progress(0, text="Menghubungkan ke Telegram...")
    try:
        async with TelegramClient(session_name, api_id, api_hash) as client:
            progress_bar.progress(0.1, text=f"Mengakses grup {group}...")
            entity = await client.get_entity(group)
            offset_id = 0
            limit = 100
            
            while True:
                history = await client(GetHistoryRequest(
                    peer=entity, limit=limit, offset_id=offset_id, offset_date=None,
                    max_id=0, min_id=0, add_offset=0, hash=0
                ))
                if not history.messages: break
                
                messages = history.messages
                msg_date_wib_oldest = messages[-1].date.astimezone(wib)

                # Berhenti jika pesan sudah lebih tua dari tanggal mulai
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
                                sender_name = f"{first_name} {last_name}".strip()
                                if not sender_name:
                                    sender_name = sender.username or f"User ID: {sender_id}"
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
                progress_bar.progress(min(0.9, 0.1 + len(all_messages) / 2000), text=f"Mengambil pesan... Total: {len(all_messages)}")
    
    except Exception as e:
        st.error(f"Terjadi kesalahan saat scraping: {e}")
        return None
        
    progress_bar.progress(1.0, text="Selesai mengambil pesan!")
    return pd.DataFrame(all_messages)

def analyze_all_topics(df_questions):
    """Menganalisis topik dari DataFrame pertanyaan menggunakan logika hybrid (keyword + clustering)."""
    st.markdown("---")
    st.header("📈 Analisis Topik dari Semua Pertanyaan")
    if df_questions.empty:
        st.warning("Tidak ada data pertanyaan yang bisa dianalisis.")
        return

    # --- Tambahkan logika jumlah cluster otomatis berdasarkan range tanggal ---
    # Ambil tanggal awal dan akhir dari data pertanyaan
    if 'date' in df_questions.columns:
        try:
            tanggal_awal = pd.to_datetime(df_questions['date'].min())
            tanggal_akhir = pd.to_datetime(df_questions['date'].max())
            selisih_hari = (tanggal_akhir - tanggal_awal).days + 1
        except Exception:
            selisih_hari = 7
    else:
        selisih_hari = 7

    if 7 <= selisih_hari <= 8:
        num_auto_clusters = 7
    elif selisih_hari > 8:
        num_auto_clusters = 25
    else:
        num_auto_clusters = 7

    # Use the new integrate_clustering_with_keywords function
    df_for_clustering = df_questions.copy()
    df_for_clustering['text'] = df_for_clustering['processed_text']
    df_questions_with_topics = integrate_clustering_with_keywords(df_for_clustering, topik_keywords, num_auto_clusters=num_auto_clusters)

    topik_counter = Counter(df_questions_with_topics["final_topic"])

    st.subheader("Ringkasan Topik Teratas")
    if not topik_counter:
        st.write("Tidak ada topik yang teridentifikasi.")
        return
        
    summary_data = [{"Topik": topik, "Jumlah Pertanyaan": count} for topik, count in topik_counter.most_common()]
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

    st.subheader("Detail Pertanyaan per Topik")
    for topik, count in topik_counter.most_common():
        with st.expander(f"Topik: {topik} ({count} pertanyaan)"):
            questions_for_topic = df_questions_with_topics[df_questions_with_topics["final_topic"] == topik]["text"].tolist()
            for q in questions_for_topic:
                st.markdown(f"- *{q.strip()}*")


if st.button("🚀 Mulai Proses dan Analisis", type="primary", use_container_width=True):
    if not group or group == "@contohgroup":
        st.warning("⚠️ Mohon isi nama grup Telegram yang valid terlebih dahulu.")
        st.stop()

    # Konversi tanggal ke datetime dengan timezone
    start_dt = datetime.combine(start_date_scrape, datetime.min.time()).replace(tzinfo=wib)
    end_dt = datetime.combine(end_date_scrape, datetime.max.time()).replace(tzinfo=wib)

    # Jalankan proses scraping
    df_all = asyncio.run(scrape_messages(group, start_dt, end_dt))

    if df_all is not None and not df_all.empty:
        st.success(f"✅ Berhasil mengambil {len(df_all)} pesan mentah.")

        st.header("🧹 Preprocessing & Deteksi Pertanyaan")
        with st.status("Membersihkan data dan mencari pertanyaan...", expanded=True) as status:
            # Urutkan dan bersihkan data
            df_all = df_all.sort_values('date').reset_index(drop=True)
            df_all['text'] = df_all['text'].str.lower()
            df_all['text'] = df_all['text'].str.replace(r'http\S+|www\.\S+', '', regex=True )
            df_all = df_all[df_all['text'].str.strip() != '']
            df_all.drop_duplicates(subset=['sender_id', 'text', 'date'], keep='first', inplace=True)

            df_all = df_all[~df_all['sender_name'].isin(['CS TokoLadang', 'Eko | TokLa', 'Vava'])]

            
            # Deteksi pertanyaan
            df_all['is_question'] = df_all['text'].apply(is_question_like)
            df_questions = df_all[df_all['is_question']].copy()
            status.update(label="✅ Proses pembersihan dan deteksi selesai!", state="complete")

            df_questions['processed_text'] = df_questions['text'].apply(clean_text_for_clustering)
            df_questions = df_questions[~df_questions['processed_text'].apply(is_unimportant_sentence)]


        # Tampilkan hasil dalam tab
        tab1, tab2 = st.tabs(["❓ Daftar Pertanyaan", "📊 Analisis Topik"])

        with tab1:
            st.subheader(f"❓ Ditemukan {len(df_questions)} Pesan Pertanyaan")
            if not df_questions.empty:
                st.dataframe(df_questions[['date', 'sender_name', 'text']], use_container_width=True)
            else:
                st.info("Tidak ada pesan yang terdeteksi sebagai pertanyaan pada periode ini.")

        with tab2:
            analyze_all_topics(df_questions)

        st.markdown("---")
        st.success("Analisis Selesai!")
