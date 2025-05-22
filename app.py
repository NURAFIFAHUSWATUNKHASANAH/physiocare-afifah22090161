import streamlit as st
from pymongo import MongoClient
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
import re

# --- Koneksi MongoDB ---
client = MongoClient("mongodb+srv://nraffhswkh:22090161@cluster0.fuxtk8w.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["bigdata"]
collection = db["UTS_BigData"]

# --- Ambil data dari MongoDB ---
data = list(collection.find())

if not data:
    st.warning("❌ Tidak ada data ditemukan di MongoDB.")
    st.stop()

# --- Stopwords Bahasa Indonesia tambahan ---
custom_stopwords = set([
    "dan", "di", "ke", "dari", "yang", "untuk", "dengan", "pada", "adalah", 
    "ini", "itu", "atau", "juga", "karena", "sebagai", "oleh", "dalam", "agar",
    "bisa", "tidak", "anda", "jika", "namun", "dapat", "saat", "berikut", 
    "dilakukan", "seperti", "akan", "selain"
])

# --- Preprocessing awal: Pastikan 'published_at' valid datetime dan ambil tahun ---
for item in data:
    try:
        if "published_at" in item and item["published_at"]:
            if not isinstance(item["published_at"], datetime):
                item["published_at"] = pd.to_datetime(item["published_at"])
            item["year"] = item["published_at"].year
        else:
            # Kalau tidak ada tanggal, set default tahun
            item["published_at"] = datetime(2000, 1, 1)
            item["year"] = 2000
    except Exception as e:
        item["published_at"] = datetime(2000, 1, 1)
        item["year"] = 2000
        st.write(f"⚠️ Error parsing tanggal pada data: {e}")

    # Hitung jumlah kata konten, aman kalau 'content' tidak ada
    content_text = item.get("content", "")
    item["word_count"] = len(re.findall(r'\w+', content_text))

# --- Buat DataFrame ---
df = pd.DataFrame(data)

# Pastikan 'year' ada dan bertipe int
df = df.dropna(subset=["year"])
df["year"] = df["year"].astype(int)

# --- Preprocessing konten artikel ---
def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'\W+', ' ', text)
    words = text.split()
    filtered_words = [word for word in words if word not in custom_stopwords]
    return " ".join(filtered_words)

df["clean_content"] = df["content"].apply(preprocess_text)

# ====================
#       UI Sidebar
# ====================
st.sidebar.title("🔍 Filter Topik Artikel")

available_topics = ["Semua", "Skoliosis", "Lordosis", "Kifosis"]
selected_topic = st.sidebar.selectbox("Pilih Topik Artikel", available_topics)

# ====================
#       Filter Data
# ====================
if selected_topic != "Semua":
    df_filtered = df[
        df["title"].str.contains(selected_topic, case=False, na=False) | 
        df["content"].str.contains(selected_topic, case=False, na=False)
    ]
    st.info(f"📘 Menampilkan artikel dengan topik: **{selected_topic}**")
else:
    df_filtered = df
    st.info("📘 Menampilkan seluruh artikel (tanpa filter topik)")

if df_filtered.empty:
    st.warning("❌ Tidak ditemukan artikel dengan topik tersebut.")
    st.stop()

# ====================
#     Judul Halaman
# ====================
st.title("📊 Visualisasi Artikel Edukasi Kesehatan")

# Debug: tampilkan jumlah data
st.write(f"Jumlah artikel yang ditampilkan: {len(df_filtered)}")

# ====================
# 1. Artikel per Tahun
# ====================
st.subheader("📅 Distribusi Artikel Berdasarkan Tahun Publikasi")
year_count = df_filtered["year"].value_counts().sort_index()

fig1, ax1 = plt.subplots()
ax1.bar(year_count.index.astype(str), year_count.values, color='skyblue')
ax1.set_xlabel("Tahun")
ax1.set_ylabel("Jumlah Artikel")
ax1.set_title("Jumlah Artikel per Tahun")
st.pyplot(fig1)

# ====================
# 2. Word Cloud
# ====================
st.subheader("☁️ Word Cloud Konten Artikel")
all_text = " ".join(df_filtered["clean_content"])
wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_text)

fig2, ax2 = plt.subplots(figsize=(10, 5))
ax2.imshow(wordcloud, interpolation='bilinear')
ax2.axis("off")
st.pyplot(fig2)

# ====================
# 3. Top Word per Tahun
# ====================
st.subheader("🔝 Top Word Paling Sering per Tahun")

top_words_per_year = {}
frequencies = {}

for year in sorted(df_filtered["year"].unique()):
    texts = " ".join(df_filtered[df_filtered["year"] == year]["clean_content"])
    words = texts.split()
    word_freq = pd.Series(words).value_counts()
    if not word_freq.empty:
        top_word = word_freq.idxmax()
        freq = word_freq.max()
        top_words_per_year[year] = top_word
        frequencies[year] = freq

top_words_df = pd.DataFrame({
    "Tahun": list(top_words_per_year.keys()),
    "Top Word": list(top_words_per_year.values()),
    "Frekuensi": list(frequencies.values())
})

fig3, ax3 = plt.subplots(figsize=(10, 5))
bars = ax3.bar(top_words_df["Tahun"].astype(str), top_words_df["Frekuensi"], color='purple')
ax3.set_xlabel("Tahun")
ax3.set_ylabel("Frekuensi")
ax3.set_title("Top Word per Tahun")

for bar, label in zip(bars, top_words_df["Top Word"]):
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2, height + 1, label, ha='center', va='bottom', fontsize=9, rotation=45)

st.pyplot(fig3)

# ====================
# 4. Tabel Artikel (Metadata)
# ====================
st.subheader("📄 Daftar Artikel")
st.dataframe(df_filtered[["title", "published_at", "word_count"]].rename(columns={
    "title": "Judul Artikel",
    "published_at": "Tanggal Publikasi",
    "word_count": "Jumlah Kata"
}))
