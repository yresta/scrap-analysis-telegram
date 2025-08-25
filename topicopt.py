import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import MiniBatchKMeans
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
import nltk
import streamlit as st

# Pastikan nltk sudah siap
nltk.download('punkt')

# Load dictionary kata baku
try:
    dictionary_df = pd.read_csv("kata_baku.csv")  # Pastikan path sesuai
    spelling_correction = dict(zip(dictionary_df['tidak_baku'], dictionary_df['kata_baku']))
except Exception as e:
    st.warning(f"Gagal memuat kata_baku.csv: {e}")
    spelling_correction = {}

def correct_spelling(text, corrections):
    if not isinstance(text, str):
        return text
    words = text.split()
    corrected_words = [corrections.get(word, word) for word in words]
    return ' '.join(corrected_words)

def is_unimportant_sentence(text: str) -> bool:
    """Filter kalimat tidak penting/singkat/sapaan/konfirmasi."""
    if not isinstance(text, str):
        return True
    txt = text.strip().lower()
    unimportant_phrases = [
        "siap", "noted", "oke", "ok", "baik", "sip", "thanks", "makasih", "terima kasih",
        "info apa", "info ni", "info nya", "trus ini", "terus ini", "ini saja", "ini aja",
        "ini min", "ini ya", "ini??", "ini?", "ini.", "ini", "sudah", "udah", "iya", "ya", "oh", "ohh"
    ]
    kata_tanya = ['apa','bagaimana','kenapa','siapa','kapan','dimana','mengapa','gimana','kok']
    if len(txt.split()) <= 2 and not any(q in txt for q in kata_tanya):
        if any(phrase == txt or phrase in txt for phrase in unimportant_phrases):
            return True
    return False

def clean_text_for_clustering(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    # Hilangkan URL
    text = re.sub(r'http\S+|www\.\S+', ' ', text)
    # Hilangkan mention dan hashtag
    text = re.sub(r'@\w+', ' ', text)
    text = re.sub(r'#\w+', ' ', text)
    # Perbaiki ejaan
    text = correct_spelling(text, spelling_correction)
    # Hilangkan duplikasi spasi
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_sentence_embeddings(texts, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings

def cluster_texts(texts, num_clusters=15, embedding_type='sentence_transformer'):
    if embedding_type == 'tfidf':
        vectorizer = TfidfVectorizer(stop_words='english')
        X = vectorizer.fit_transform(texts)
    elif embedding_type == 'sentence_transformer':
        X = get_sentence_embeddings(texts)
    else:
        raise ValueError("Invalid embedding_type. Choose 'tfidf' or 'sentence_transformer'.")
    kmeans = MiniBatchKMeans(n_clusters=num_clusters, random_state=0, n_init=10)
    kmeans.fit(X)
    return kmeans.labels_, kmeans.cluster_centers_, X

# def assign_topic_names(cluster_centers, original_texts, labels, embedding_type='sentence_transformer'):
#     topic_names = {}
#     if embedding_type == 'tfidf':
#         for i in range(len(cluster_centers)):
#             topic_names[i] = f"Topik Otomatis {i+1}"
#     elif embedding_type == 'sentence_transformer':
#         model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
#         for i, center in enumerate(cluster_centers):
#             cluster_texts_indices = [j for j, label in enumerate(labels) if label == i]
#             if not cluster_texts_indices:
#                 topic_names[i] = f"Topik Otomatis {i+1} (Kosong)"
#                 continue
#             cluster_texts_embeddings = np.array(
#                 [get_sentence_embeddings([original_texts[idx]])[0] for idx in cluster_texts_indices]
#             )
#             similarities = cosine_similarity([center], cluster_texts_embeddings)[0]
#             closest_text_index_in_cluster = np.argmax(similarities)
#             original_index = cluster_texts_indices[closest_text_index_in_cluster]
#             topic_names[i] = original_texts[original_index][:50] + "..."
#     return topic_names

# ...existing code...

from collections import Counter

# Daftar stopword dan kata tanya (bisa ditambah sesuai kebutuhan)
STOPWORDS = set("""
yang dan di ke dari untuk dengan pada oleh dalam atas sebagai adalah itu ini atau tidak sudah belum bisa akan harus sangat juga karena jadi kalau kalaupun namun tapi serta agar supaya sehingga maka lalu kemudian setelah sebelum sesudah hingga sampai pun
""".split())
KATA_TANYA = set("""
apa siapa kapan mengapa kenapa bagaimana gimana dimana dimanakah bagaimanakah kenapakah apakah
""".split())

def extract_representative_words(texts, top_n=2):
    words = []
    for text in texts:
        # Tokenisasi sederhana
        tokens = re.findall(r'\b\w+\b', text.lower())
        # Filter stopword dan kata tanya
        filtered = [w for w in tokens if w not in STOPWORDS and w not in KATA_TANYA and len(w) > 2]
        words.extend(filtered)
    counter = Counter(words)
    most_common = [w for w, _ in counter.most_common(top_n)]
    return " ".join(most_common) if most_common else "Topik Otomatis"

def assign_topic_names(cluster_centers, original_texts, labels, embedding_type='sentence_transformer'):
    topic_names = {}
    if embedding_type == 'tfidf':
        for i in range(len(cluster_centers)):
            cluster_texts = [original_texts[j] for j, label in enumerate(labels) if label == i]
            topic_names[i] = extract_representative_words(cluster_texts)
    elif embedding_type == 'sentence_transformer':
        for i, center in enumerate(cluster_centers):
            cluster_texts_indices = [j for j, label in enumerate(labels) if label == i]
            if not cluster_texts_indices:
                topic_names[i] = "Topik Otomatis"
                continue
            cluster_texts = [original_texts[idx] for idx in cluster_texts_indices]
            topic_names[i] = extract_representative_words(cluster_texts)
    return topic_names

# ...existing code...

def integrate_clustering_with_keywords(df, topik_keywords, num_auto_clusters=15):
    # Preprocess text for 15
    df['processed_text'] = df['text'].apply(clean_text_for_clustering)
    df = df[~df['processed_text'].apply(is_unimportant_sentence)]  # filter kalimat tidak penting
    
    keyword_categorized_texts = []
    remaining_texts = []
    remaining_indices = []

    for idx, row in df.iterrows():
        text_lc = row['processed_text']
        found_topik = []
        for topik, patterns in topik_keywords.items():
            if patterns and isinstance(patterns[0], list):
                if any(all(keyword in text_lc for keyword in group) for group in patterns):
                    found_topik.append(topik)
            else:
                if any(keyword in text_lc for keyword in patterns):
                    found_topik.append(topik)
        if found_topik:
            spesifik_topik = [t for t in found_topik if t != 'bantuan_umum']
            selected_topik = spesifik_topik[0] if spesifik_topik else 'bantuan_umum'
            keyword_categorized_texts.append({'original_index': idx, 'topic': selected_topik})
        else:
            remaining_texts.append(row['processed_text'])
            remaining_indices.append(idx)

    if remaining_texts:
        auto_labels, cluster_centers, _ = cluster_texts(
            remaining_texts, num_clusters=num_auto_clusters, embedding_type='sentence_transformer'
        )
        auto_topic_names = assign_topic_names(cluster_centers, remaining_texts, auto_labels, embedding_type='sentence_transformer')
        auto_categorized_texts = []
        for i, label in enumerate(auto_labels):
            original_idx = remaining_indices[i]
            auto_categorized_texts.append({'original_index': original_idx, 'topic': auto_topic_names[label]})
    else:
        auto_categorized_texts = []

    final_topics = pd.DataFrame(columns=['original_index', 'topic'])
    if keyword_categorized_texts:
        final_topics = pd.concat([final_topics, pd.DataFrame(keyword_categorized_texts)], ignore_index=True)
    if auto_categorized_texts:
        final_topics = pd.concat([final_topics, pd.DataFrame(auto_categorized_texts)], ignore_index=True)

    df['final_topic'] = 'lainnya'
    for _, row in final_topics.iterrows():
        df.loc[row['original_index'], 'final_topic'] = row['topic']

    return df

if __name__ == '__main__':
    # Contoh penggunaan
    sample_data = {
        'text': [
            'Bagaimana cara verifikasi toko saya?',
            'Dana saya belum masuk rekening, tolong dicek.',
            'Kapan pencairan dana gelombang 2?',
            'Saya tidak bisa login ke aplikasi, ada masalah apa?',
            'Bagaimana cara upload produk massal?',
            'Ada kendala akses web, tidak bisa dibuka.',
            'Apakah ada info terbaru tentang pajak PPN?',
            'Saya ingin bertanya tentang etika penggunaan platform.',
            'Pembayaran saya pending, mohon dibantu.',
            'Barang yang dikirim rusak, bagaimana ini?',
            'Ini topik baru yang belum ada di list keyword sama sekali.',
            'Pesan ini juga tentang topik baru yang mirip dengan yang sebelumnya.',
            'Ini adalah pesan yang sangat berbeda dan harusnya jadi topik baru lagi.',
            'Saya butuh bantuan umum, tidak spesifik.',
            'Ini juga bantuan umum, tapi berbeda konteks dari yang lain.',
            'Verifikasi pembayaran saya gagal, bagaimana solusinya?',
            'Tanda tangan elektronik saya tidak berfungsi.',
            'Bagaimana cara mengubah data toko?',
            'Pengajuan modal saya dibatalkan, kenapa ya?',
            'Ada masalah dengan autentikasi OTP.',
            'Ini pesan tentang topik baru yang mirip dengan pesan nomor 11.',
            'Pesan ini juga mirip dengan pesan nomor 12.',
            'Ini pesan yang sangat unik dan harusnya menjadi topik baru yang berbeda.',
            'Saya tidak bisa mengunggah gambar produk.',
            'Kapan kurir akan menjemput barang?',
            'Bagaimana cara menggunakan fitur siplah?',
            'Status pesanan saya masih menggantung.',
            'Ada pertanyaan umum lainnya.'
        ]
    }
    df_sample = pd.DataFrame(sample_data)

    # Keyword-topik contoh
    topik_keywords_example = {
        "verifikasi_toko": [["verifikasi", "toko"]],
        "dana_belum_masuk": [["dana", "belum", "masuk"]],
        "jadwal_cair_dana": [["kapan", "cair"]],
        "kendala_akses": [["tidak", "bisa", "login"], ["kendala", "akses"]],
        "kendala_upload": [["upload", "produk"], ["unggah", "gambar"]],
        "pajak": [["pajak", "ppn"]],
        "etika_penggunaan": [["etika", "penggunaan"]],
        "pembayaran_dana": ["pembayaran", "pending"],
        "pengiriman_barang": ["barang", "rusak"],
        "bantuan_umum": ["bantuan", "umum", "tanya"]
    }

    df_result = integrate_clustering_with_keywords(df_sample.copy(), topik_keywords_example, num_auto_clusters=3)
    print(df_result[['text', 'final_topic']])
