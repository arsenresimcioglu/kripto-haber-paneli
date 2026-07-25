import pandas as pd
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Kripto & Makro Haber Radarı", page_icon="⚡", layout="wide"
)

# Google Sheets Canlı CSV Bağlantısı
SHEET_ID = "15oys_jSdW0q8ePdUna0BVirzTyazzsMfvJCcral7VgI"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"


@st.cache_data(ttl=30)  # Verileri 30 saniyede bir otomatik tazeler
def load_data():
  try:
    df = pd.read_csv(CSV_URL)
    return df
  except Exception as e:
    st.error(f"Veri çekilemedi: {e}")
    return pd.DataFrame()


# Başlık Alanı
st.title("⚡ Canlı Haber & Makro Ekonomi Radarı")
st.caption("Investing.com & CoinTelegraph Anlık AI Analiz Paneli")

# Üst Bar: Yenile Butonu
col_refresh, col_status = st.columns([1, 4])
with col_refresh:
  if st.button("🔄 Verileri Yenile"):
    st.cache_data.clear()
    st.rerun()

df = load_data()

if not df.empty:
  # Filtreleme Alanı
  kategoriler = ["Tümü"] + list(df["Kategori (Makro/Kripto)"].dropna().unique())
  secilen_kategori = st.selectbox("📌 Kategori Filtresi", kategoriler)

  if secilen_kategori != "Tümü":
    df_filtered = df[df["Kategori (Makro/Kripto)"] == secilen_kategori]
  else:
    df_filtered = df

  # Son eklenen haberler en üstte görünsün
  df_filtered = df_filtered.iloc[::-1]

  st.markdown("---")

  # Haber Kartları Görünümü (iPad ve Mobil Uyumlu)
  for idx, row in df_filtered.iterrows():
    kategori = str(row.get("Kategori (Makro/Kripto)", "Makro"))
    kategori_emoji = "🌐" if "Makro" in kategori else "🚀"

    with st.container():
      col1, col2 = st.columns([4, 1])

      with col1:
        st.subheader(
            f"{kategori_emoji} {row.get('Olay / Haber Başlığı', 'Başlık Yok')}"
        )
        st.write(
            f"**Tarih / Saat:** `{str(row.get('Tarih / Saat', ''))[:16]}`"
        )

      with col2:
        # Kaynak Linki Butonu
        link = row.get("Kaynak", "")
        if pd.notna(link) and str(link).startswith("http"):
          st.link_button("🔗 Habere Git ↗", str(link))
        else:
          st.caption("Kaynak Yok")

      # Açılır detay paneli (Analiz ve Beklenti)
      with st.expander("🔍 AI Analizi ve Piyasa Etkisi Detayı"):
        st.markdown(
            f"**💡 Beklenti / Piyasa Etkisi:**\n{row.get('Beklenti / Etki', 'Detay Yok')}"
        )
        st.markdown(
            f"**📊 Gerçekleşen Sonuç:**\n{row.get('Gerçekleşen Sonuç', 'Detay Yok')}"
        )

      st.markdown("---")

else:
  st.info("Henüz görüntülenecek haber bulunamadı veya tablo boş.")