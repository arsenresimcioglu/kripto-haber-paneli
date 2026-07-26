import datetime
import json
import pandas as pd
import requests
import streamlit as st

# Sayfa Yapılandırması (Geniş Ekran)
st.set_page_config(
    page_title="Crypto & Macro Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- GOOGLE SHEETS WEBHOOK BAGLANTISI ---
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbx4JHGGGocczm8hpQSMU0wmWUbfiIctOmV4M825YNnjo9cGsnwKjEwcUMmyo7PVO6RK7Q/exec"

# --- ÖZEL TASARIM ---
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
        }
        header[data-testid="stHeader"] {
            height: 2rem !important;
            background-color: transparent !important;
        }
        button[data-baseweb="tab"] {
            color: #94A3B8 !important;
            font-size: 1.05rem !important;
            font-weight: 500 !important;
            padding-bottom: 8px !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #F0B90B !important;
            font-weight: 600 !important;
        }
        div[data-baseweb="tab-highlight"] {
            background-color: #F0B90B !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# --- TAKİP LİSTEMİZ (11 PARİTE) ---
SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "ZECUSDT",
    "FETUSDT",
    "NEARUSDT",
    "ONDOUSDT",
    "SUIUSDT",
    "INJUSDT",
    "TAOUSDT",
    "APTUSDT",
]


# --- GOOGLE SHEETS'E VERİ GÖNDERME FONKSİYONU ---
def send_to_google_sheets(df):
  if df.empty:
    return False
  try:
    # Google Sheets için 2D Matris Hazırlığı
    headers = list(df.columns)
    rows = df.values.tolist()
    payload = [headers] + rows

    res = requests.post(
        WEBHOOK_URL,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    return res.status_code == 200
  except Exception:
    return False


# --- BİNANCE FUTURES CANLI VERİ MOTORU ---
@st.cache_data(ttl=30)
def fetch_futures_matrix():
  matrix_data = []
  now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

  for symbol in SYMBOLS:
    try:
      # 1. Canlı Fiyat ve 24s Ticker Bilgisi
      ticker_url = (
          f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"
      )
      t_res = requests.get(ticker_url, timeout=5).json()

      price = float(t_res.get("lastPrice", 0))
      price_change = float(t_res.get("priceChangePercent", 0))
      volume_quote = float(t_res.get("quoteVolume", 0)) / 1_000_000  # M$

      # 2. Açık Pozisyon (Open Interest - OI)
      oi_url = (
          f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
      )
      oi_res = requests.get(oi_url, timeout=5).json()
      open_interest_contracts = float(oi_res.get("openInterest", 0))
      oi_value_usd = (open_interest_contracts * price) / 1_000_000  # M$

      # 3. 4 Saatlik Mumlar (200 MA ve SMC Yapısı)
      klines_url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=4h&limit=200"
      k_res = requests.get(klines_url, timeout=5).json()

      if len(k_res) >= 200:
        closes = [float(k[4]) for k in k_res]
        ma200 = sum(closes) / 200
        ma_status = "Üstünde (Boğa 🟢)" if price > ma200 else "Altında (Ayı 🔴)"

        recent_highs = max([float(k[2]) for k in k_res[-5:]])
        recent_lows = min([float(k[3]) for k in k_res[-5:]])

        if price >= recent_highs * 0.998:
          smc_structure = "Tepe Likiditesi Zorlanıyor ⚡"
        elif price <= recent_lows * 1.002:
          smc_structure = "Dip Likiditesi Test Ediliyor 🛡️"
        else:
          smc_structure = "Denge Bölgesi (Consolidation) ⚖️"
      else:
        ma_status = "Veri Yetersiz"
        smc_structure = "Nötr"

      matrix_data.append({
          "Son Güncelleme": now_str,
          "Parite": symbol.replace("USDT", "/USDT"),
          "Fiyat ($)": f"${price:,.2f}" if price >= 1 else f"${price:.4f}",
          "24s Değişim": f"{'▲' if price_change >= 0 else '▼'} %{price_change:.2f}",
          "200 MA (4H)": ma_status,
          "Açık Pozisyon (OI)": f"${oi_value_usd:,.1f}M",
          "24s Hacim": f"${volume_quote:,.1f}M",
          "Piyasa Yapısı (SMC)": smc_structure,
      })
    except Exception:
      continue

  df = pd.DataFrame(matrix_data)

  # Otomatik Google Sheets'e Yazma
  if not df.empty:
    send_to_google_sheets(df)

  return df


# Google Sheets Canlı Haber Bağlantısı
SHEET_ID = "15oys_jSdW0q8ePdUna0BVirzTyazzsMfvJCcral7VgI"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"


@st.cache_data(ttl=30)
def load_news():
  try:
    df = pd.read_csv(CSV_URL)
    return df
  except Exception:
    return pd.DataFrame()


# --- ANA SEKMELİ DÜZEN ---
tab1, tab2, tab3 = st.tabs([
    "📊 Teknik & Göstergeler (SMC / Order Flow)",
    "⚡ Haber & Ekonomi Radarı",
    "🎙️ Analizler & Piyasa Beklentileri",
])

# ==============================================================================
# SEKME 1: TEKNİK & GÖSTERGELER (Canlı Veri Matrisi)
# ==============================================================================
with tab1:
  st.subheader("📊 SMC, Order Flow ve Teknik Veri Matrisi")

  col_m1, col_m2 = st.columns([1, 4])
  with col_m1:
    if st.button("🔄 Verileri Güncelle", key="btn_tech"):
      st.cache_data.clear()
      st.rerun()

  with st.spinner(
      "Binance Futures verileri çekiliyor ve Google Sheets'e işleniyor..."
  ):
    df_matrix = fetch_futures_matrix()

  if not df_matrix.empty:
    st.success("✅ Veriler güncellendi ve Google Sheets'e otomatik aktarıldı!")
    st.dataframe(df_matrix, use_container_width=True, hide_index=True)
  else:
    st.warning("Veriler şu an çekilemedi. Lütfen bağlantınızı kontrol edin.")

# ==============================================================================
# SEKME 2: HABER & EKONOMİ RADARI
# ==============================================================================
with tab2:
  st.subheader("⚡ Canlı Haber & Makro Ekonomi Radarı")

  c_btn, c_space = st.columns([1, 3])
  with c_btn:
    if st.button("🔄 Akışı Yenile", key="btn_news"):
      st.cache_data.clear()
      st.rerun()

  df_news = load_news()

  if not df_news.empty:
    kategoriler = ["Tümü"] + list(
        df_news["Kategori (Makro/Kripto)"].dropna().unique()
    )
    kat_secimi = st.selectbox("Kategori Filtresi:", kategoriler)

    if kat_secimi != "Tümü":
      df_news = df_news[df_news["Kategori (Makro/Kripto)"] == kat_secimi]

    df_news = df_news.iloc[::-1]

    st.markdown("---")

    for idx, row in df_news.iterrows():
      kategori = str(row.get("Kategori (Makro/Kripto)", "Makro"))
      emoji = "🌐" if "Makro" in kategori else "🚀"

      st.markdown(f"### {emoji} {row.get('Olay / Haber Başlığı', 'Başlık Yok')}")
      st.caption(f"🕒 Tarih / Saat: {str(row.get('Tarih / Saat', ''))[:16]}")

      link = row.get("Kaynak", "")
      if pd.notna(link) and str(link).startswith("http"):
        st.link_button("🔗 Habere Git ↗", str(link))

      with st.expander("💡 AI Analizi ve Piyasa Etkisi Detayı"):
        st.write(
            f"**Beklenti / Etki:**\n{row.get('Beklenti / Etki', 'Detay Yok')}"
        )
        st.write(
            f"**Gerçekleşen Sonuç:**\n{row.get('Gerçekleşen Sonuç', 'Detay Yok')}"
        )

      st.markdown("---")
  else:
    st.info("Haber akışı henüz yüklenemedi veya Google Sheets boş.")

# ==============================================================================
# SEKME 3: ANALİZLER & PİYASA BEKLENTİLERİ
# ==============================================================================
with tab3:
  st.subheader("🎙️ Günlük Video Analizleri & Makro Hedefler")
  st.info(
      "🛠️ Bu sekmede video özetleri, altın/petrol/borsa hedefleri yer alacak."
  )
