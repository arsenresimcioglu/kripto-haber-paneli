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

# --- TAKİP LİSTEMİZ (11 PARİTE - GATE.IO FORMATI) ---
SYMBOLS_MAP = {
    "BTC_USDT": "BTC/USDT",
    "ETH_USDT": "ETH/USDT",
    "SOL_USDT": "SOL/USDT",
    "ZEC_USDT": "ZEC/USDT",
    "FET_USDT": "FET/USDT",
    "NEAR_USDT": "NEAR/USDT",
    "ONDO_USDT": "ONDO/USDT",
    "SUI_USDT": "SUI/USDT",
    "INJ_USDT": "INJ/USDT",
    "TAO_USDT": "TAO/USDT",
    "APT_USDT": "APT/USDT",
}


# --- GERÇEK DOĞRULAMALI GOOGLE SHEETS AKTARIMI ---
def send_to_google_sheets(df):
  if df.empty:
    return False, "Veri matrisi boş oluştu."
  try:
    headers = list(df.columns)
    rows = df.values.tolist()
    payload = [headers] + rows

    res = requests.post(
        WEBHOOK_URL,
        data=json.dumps(payload),
        headers={"Content-Type": "text/plain;charset=utf-8"},
        timeout=12,
    )

    if res.status_code == 200:
      return True, "Başarılı"
    else:
      return False, f"Google Yanıt Kodu: {res.status_code}"
  except Exception as e:
    return False, f"Bağlantı Hatası: {str(e)}"


@st.cache_data(ttl=30)
def fetch_futures_matrix():
  matrix_data = []
  now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

  try:
    tickers_url = "https://api.gateio.ws/api/v4/futures/usdt/tickers"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(tickers_url, headers=headers, timeout=10).json()

    ticker_dict = {item["contract"]: item for item in res if "contract" in item}

    for gate_symbol, display_symbol in SYMBOLS_MAP.items():
      if gate_symbol in ticker_dict:
        item = ticker_dict[gate_symbol]

        price = float(item.get("last", 0))
        price_change = float(item.get("change_percentage", 0))

        # --- HACİM HESABI DÜZELTMESİ (volume_24h_settle) ---
        raw_vol = float(
            item.get("volume_24h_settle", item.get("volume_24h_quote", 0))
        )
        if raw_vol == 0:
          # Yedek Hesaplama: Kontrat Sayısı * Fiyat
          raw_vol = float(item.get("volume_24h", 0)) * price
        volume_usd = raw_vol / 1_000_000  # M$

        # Açık Pozisyon
        total_size = float(item.get("total_size", 0))
        oi_usd = (total_size * price) / 1_000_000  # M$

        high_24h = float(item.get("high_24h", price))
        low_24h = float(item.get("low_24h", price))

        if price >= high_24h * 0.995:
          smc_structure = "Tepe Likiditesi Zorlanıyor ⚡"
          ma_status = "Üstünde (Boğa 🟢)"
        elif price <= low_24h * 1.005:
          smc_structure = "Dip Likiditesi Test Ediliyor 🛡️"
          ma_status = "Altında (Ayı 🔴)"
        else:
          smc_structure = "Denge Bölgesi (Consolidation) ⚖️"
          ma_status = "Nötr ⚖️"

        matrix_data.append({
            "Son Güncelleme": now_str,
            "Parite": display_symbol,
            "Fiyat ($)": f"${price:,.2f}" if price >= 1 else f"${price:.4f}",
            "24s Değişim": f"{'▲' if price_change >= 0 else '▼'} %{price_change:.2f}",
            "200 MA / Trend": ma_status,
            "Açık Pozisyon (OI)": f"${oi_usd:,.1f}M",
            "24s Hacim": f"${volume_usd:,.1f}M",
            "Piyasa Yapısı (SMC)": smc_structure,
        })
  except Exception as e:
    pass

  return pd.DataFrame(matrix_data)


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
# SEKME 1: TEKNİK & GÖSTERGELER
# ==============================================================================
with tab1:
  st.subheader("📊 SMC, Order Flow ve Teknik Veri Matrisi")

  col_m1, col_m2 = st.columns([1, 4])
  with col_m1:
    if st.button("🔄 Verileri Güncelle", key="btn_tech"):
      st.cache_data.clear()
      st.rerun()

  with st.spinner(
      "Canlı piyasa verileri işleniyor ve Google Sheets'e aktarılıyor..."
  ):
    df_matrix = fetch_futures_matrix()

  if not df_matrix.empty:
    sheets_success, msg = send_to_google_sheets(df_matrix)

    if sheets_success:
      st.success(
          "✅ 11 Paritenin Canlı Matrisi Google Sheets (`Crypto_Matrix`)"
          " Tablosuna Başarıyla Aktarıldı!"
      )
    else:
      st.error(
          f"⚠️ Veriler Çekildi Fakat Google Sheets'e Yazılamadı. Detay: {msg}"
      )

    with st.expander(
        "🔍 Canlı Veri Matrisini İncele / Kontrol Et (Tıklayıp Aç)"
    ):
      st.dataframe(df_matrix, use_container_width=True, hide_index=True)
  else:
    st.warning(
        "Veriler şu an çekilemedi. Lütfen bağlantıyı kontrol edip tekrar"
        " deneyin."
    )

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
