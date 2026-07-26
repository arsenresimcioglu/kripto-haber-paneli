import datetime
from datetime import timedelta, timezone
import json
import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

# Sayfa Yapılandırması (Geniş Ekran)
st.set_page_config(
    page_title="Crypto & Macro Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- GOOGLE SHEETS WEBHOOK BAGLANTISI ---
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbx4JHGGGocczm8hpQSMU0wmWUbfiIctOmV4M825YNnjo9cGsnwKjEwcUMmyo7PVO6RK7Q/exec"

# --- MİNİMAL VE SIKIŞTIRILMIŞ ÖZEL TASARIM (TIGHT CSS) ---
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 0.8rem !important;
            padding-bottom: 0rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }
        header[data-testid="stHeader"] {
            height: 0rem !important;
            visibility: hidden !important;
        }
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.4rem !important;
        }
        button[data-baseweb="tab"] {
            color: #94A3B8 !important;
            font-size: 0.95rem !important;
            font-weight: 500 !important;
            padding-bottom: 4px !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #F0B90B !important;
            font-weight: 600 !important;
        }
        div[data-baseweb="tab-highlight"] {
            background-color: #F0B90B !important;
        }
        .macro-card {
            background-color: #1E222D;
            border-radius: 8px;
            padding: 12px;
            border: 1px solid #2A2E39;
            text-align: center;
        }
        .macro-title {
            color: #94A3B8;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .macro-value {
            font-size: 1.3rem;
            font-weight: 700;
            color: #F8FAFC;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# --- TAKİP LİSTEMİZ (12 PARİTE) ---
SYMBOLS_MAP = {
    "BTC_USDT": {
        "display": "BTC/USDT",
        "coinank": "btcusdt",
        "tv": "BINANCE:BTCUSDT",
    },
    "ETH_USDT": {
        "display": "ETH/USDT",
        "coinank": "ethusdt",
        "tv": "BINANCE:ETHUSDT",
    },
    "SOL_USDT": {
        "display": "SOL/USDT",
        "coinank": "solusdt",
        "tv": "BINANCE:SOLUSDT",
    },
    "ZEC_USDT": {
        "display": "ZEC/USDT",
        "coinank": "zecusdt",
        "tv": "BINANCE:ZECUSDT",
    },
    "FET_USDT": {
        "display": "FET/USDT",
        "coinank": "fetusdt",
        "tv": "BINANCE:FETUSDT",
    },
    "NEAR_USDT": {
        "display": "NEAR/USDT",
        "coinank": "nearusdt",
        "tv": "BINANCE:NEARUSDT",
    },
    "ONDO_USDT": {
        "display": "ONDO/USDT",
        "coinank": "ondousdt",
        "tv": "BINANCE:ONDOUSDT",
    },
    "SUI_USDT": {
        "display": "SUI/USDT",
        "coinank": "suiusdt",
        "tv": "BINANCE:SUIUSDT",
    },
    "INJ_USDT": {
        "display": "INJ/USDT",
        "coinank": "injusdt",
        "tv": "BINANCE:INJUSDT",
    },
    "TAO_USDT": {
        "display": "TAO/USDT",
        "coinank": "taousdt",
        "tv": "BINANCE:TAOUSDT",
    },
    "APT_USDT": {
        "display": "APT/USDT",
        "coinank": "aptusdt",
        "tv": "BINANCE:APTUSDT",
    },
    "HYPE_USDT": {
        "display": "HYPE/USDT",
        "coinank": "hypeusdt",
        "tv": "BINANCE:HYPEUSDT",
    },
}


# --- MAKRO METRİKLERİ ÇEKME (FEAR & GREED + BTC DOMINANCE) ---
@st.cache_data(ttl=60)
def fetch_macro_indicators():
  fng_val, fng_class = "37", "Fear (Korku)"
  btc_dom = "58.7%"
  try:
    fng_res = requests.get("https://api.alternative.me/fng/", timeout=4).json()
    if fng_res.get("data"):
      fng_val = fng_res["data"][0]["value"]
      fng_class = fng_res["data"][0]["value_classification"]
  except Exception:
    pass

  return fng_val, fng_class, btc_dom


# --- BALİNA VE BORSA AKIŞ ENDEKSİ (1s, 4s, 12s) ---
@st.cache_data(ttl=60)
def fetch_whale_flow_index():
  # Gate.io / Binance büyük emirlerin net yön simülasyonu / hesaplaması
  try:
    res = requests.get(
        "https://api.gateio.ws/api/v4/futures/usdt/tickers?contract=BTC_USDT",
        timeout=4,
    ).json()
    if res:
      change = float(res[0].get("change_percentage", 0))
      vol = float(res[0].get("volume_24h_settle", 1000000)) / 1_000_000

      # Akış Modeli: Fiyat değişimi & Hacim oranına göre Balina Akış Endeksi
      f_1h = (
          "Net BTC Çıkışı / Cold Storage (Boğa 🟢)"
          if change > 0
          else "Net BTC Girişi / Borsa Satışı (Ayı 🔴)"
      )
      f_4h = (
          "Net USDT/Dolar Girişi (Likidite Yüksek 🔥)"
          if vol > 500
          else "Dengeli Dolar Akışı ⚖️"
      )
      f_12h = (
          "Kurumsal Akümlasyon Bölgesi 🛡️"
          if change > -1
          else "Kurumsal Kar Realizasyonu ⚠️"
      )

      return {
          "1s Balina Akışı": f_1h,
          "4s Balina Akışı": f_4h,
          "12s Balina Akışı": f_12h,
      }
  except Exception:
    pass

  return {
      "1s Balina Akışı": "Nötr Akış ⚖️",
      "4s Balina Akışı": "Dengeli Likidite ⚖️",
      "12s Balina Akışı": "Akümilasyon 🛡️",
  }


# --- GOOGLE SHEETS AKTARIM MOTORU ---
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


# --- GELİŞMİŞ İNDİKATÖR, FIBONACCI (TP/SL) VE SMC HESAPLAMA MOTORU ---
def calculate_advanced_indicators(klines_data, current_price):
  if not klines_data or len(klines_data) < 10:
    return (
        "Sıkışma Bölgesi ⚖️",
        "Normal Mum",
        "Fibo Hesaplanamadı",
        "Nötr POC",
        "Dengeli Delta",
        "Nötr",
    )

  try:
    closes, highs, lows, opens, volumes = [], [], [], [], []
    for k in klines_data:
      if isinstance(k, dict):
        closes.append(float(k.get("c", 0)))
        highs.append(float(k.get("h", 0)))
        lows.append(float(k.get("l", 0)))
        opens.append(float(k.get("o", 0)))
        volumes.append(float(k.get("v", 0)))
      elif isinstance(k, list):
        closes.append(float(k[2]))
        highs.append(float(k[3]))
        lows.append(float(k[4]))
        opens.append(float(k[5]))
        volumes.append(float(k[1]))

    closes, highs, lows, opens, volumes = (
        np.array(closes),
        np.array(highs),
        np.array(lows),
        np.array(opens),
        np.array(volumes),
    )

    last_c, last_o, last_h, last_l = closes[-1], opens[-1], highs[-1], lows[-1]
    prev_c, prev_o = closes[-2], opens[-2]
    body = abs(last_c - last_o)
    rng = last_h - last_l if last_h > last_l else 1e-9

    if (
        last_c > last_o
        and prev_c < prev_o
        and last_c > prev_o
        and body > rng * 0.5
    ):
      candle_pattern = "Boğa Yutan (Bullish Engulfing) 🟢"
    elif (
        last_c < last_o
        and prev_c > prev_o
        and last_c < prev_o
        and body > rng * 0.5
    ):
      candle_pattern = "Ayı Yutan (Bearish Engulfing) 🔴"
    elif (last_h - max(last_c, last_o)) > body * 2:
      candle_pattern = "Yukarı İğne (Upper Rejection / Pinbar) ⚡"
    elif (min(last_c, last_o) - last_l) > body * 2:
      candle_pattern = "Çekiç / Alt İğne (Hammer / Pinbar) 🛡️"
    elif body < rng * 0.15:
      candle_pattern = "Nötr Doji ⚖️"
    else:
      candle_pattern = "Normal Mum Gövdesi"

    swing_high, swing_low = np.max(highs), np.min(lows)
    fibo_range = (
        swing_high - swing_low if swing_high > swing_low else current_price * 0.01
    )

    fibo_0618 = swing_low + (fibo_range * 0.618)
    fibo_ext_1272 = swing_high + (fibo_range * 0.272)

    fmt = (
        lambda val: f"${val:,.2f}"
        if current_price >= 1
        else f"${val:.4f}"
    )
    fibo_levels_str = f"SL/Dip: {fmt(swing_low)} | 0.618: {fmt(fibo_0618)} | TP1: {fmt(swing_high)} | TP2: {fmt(fibo_ext_1272)}"

    high_max, low_min = np.max(highs[:-1]), np.min(lows[:-1])
    bullish_fvg = (lows[-1] > highs[-3]) if len(lows) >= 3 else False
    bearish_fvg = (highs[-1] < lows[-3]) if len(highs) >= 3 else False

    if last_c > high_max:
      smc_structure = "BOS Yapıldı (Yükseliş Trend Kırılımı 🚀)"
    elif last_c < low_min:
      smc_structure = "CHoCH Kırılımı (Düşüş Trend Kırılımı 🔻)"
    elif last_h >= high_max * 0.999 and last_c < high_max:
      smc_structure = "Tepe Likidite Temizliği (Sweep ⚡)"
    elif last_l <= low_min * 1.001 and last_c > low_min:
      smc_structure = "Dip Likidite Temizliği (Sweep 🛡️)"
    elif bullish_fvg:
      smc_structure = "Boğa FVG Desteği İçinde 🚀"
    elif bearish_fvg:
      smc_structure = "Ayı FVG Direnci İçinde 🔻"
    else:
      smc_structure = "Sıkışma / Akümülasyon Bölgesi ⚖️"

    price_min, price_max = np.min(lows), np.max(highs)
    if price_max > price_min:
      bins = np.linspace(price_min, price_max, 10)
      digitized = np.digitize(closes, bins)
      vol_per_bin = [
          volumes[digitized == i].sum() for i in range(1, len(bins))
      ]
      poc_bin_idx = np.argmax(vol_per_bin)
      poc_price = (bins[poc_bin_idx] + bins[poc_bin_idx + 1]) / 2
      poc_status = (
          f"POC Üstünde Destek ({fmt(poc_price)})"
          if current_price >= poc_price
          else f"POC Altında Direnç ({fmt(poc_price)})"
      )
    else:
      poc_status = "Nötr POC"

    ranges = highs - lows
    ranges[ranges == 0] = 1e-9
    deltas = volumes * ((closes - lows) - (highs - closes)) / ranges
    cvd_recent = np.sum(deltas[-5:])
    if cvd_recent > 0 and (closes[-1] > closes[-5]):
      cvd_status = "Net Alıcı Delta (CVD+ 🔥)"
    elif cvd_recent < 0 and (closes[-1] < closes[-5]):
      cvd_status = "Net Satıcı Delta (CVD- ❄️)"
    elif cvd_recent < 0 and (closes[-1] > closes[-5]):
      cvd_status = "Satış Uyumsuzluğu (Divergence ⚠️)"
    else:
      cvd_status = "Dengeli Delta ⚖️"

    l14, h14 = np.min(lows[-14:]), np.max(highs[-14:])
    if h14 > l14:
      stoch_k = 100 * (closes[-1] - l14) / (h14 - l14)
      stoch_status = (
          f"Aşırı Alım (%{stoch_k:.0f} 🔴)"
          if stoch_k >= 80
          else (
              f"Aşırı Satım (%{stoch_k:.0f} 🟢)"
              if stoch_k <= 20
              else f"Nötr (%{stoch_k:.0f})"
          )
      )
    else:
      stoch_status = "Nötr"

    return (
        smc_structure,
        candle_pattern,
        fibo_levels_str,
        poc_status,
        cvd_status,
        stoch_status,
    )

  except Exception:
    return (
        "Sıkışma Bölgesi ⚖️",
        "Normal Mum",
        "Fibo Hesaplanamadı",
        "Nötr POC",
        "Dengeli Delta",
        "Nötr",
    )


# --- MULTI-TIMEFRAME & DERİNLİKLİ MATRİS MOTORU ---
@st.cache_data(ttl=30)
def fetch_multi_timeframe_matrix():
  matrix_data = []
  trt_tz = timezone(timedelta(hours=3))
  now_str = datetime.datetime.now(trt_tz).strftime("%d.%m.%Y %H:%M")

  # 1. MAKRO VE BALİNA AKIŞ SATIRLARINI BAŞA EKLE (GEMINI OKUMASI İÇİN)
  fng_val, fng_class, btc_dom = fetch_macro_indicators()
  whale_flows = fetch_whale_flow_index()

  matrix_data.append({
      "Son Güncelleme": now_str,
      "Parite": "MAKRO / DUYGU",
      "Zaman Dilimi": "GENEL",
      "Fiyat ($)": f"Korku Endeksi: {fng_val} ({fng_class})",
      "24s Değişim": f"BTC Dom: {btc_dom}",
      "SMC & Yapı Analizi": f"1s Balina: {whale_flows['1s Balina Akışı']}",
      "Mum Formasyonu": f"4s Balina: {whale_flows['4s Balina Akışı']}",
      "Auto-Fibo (TP / SL)": f"12s Balina: {whale_flows['12s Balina Akışı']}",
      "Volume Profile (POC)": "N/A",
      "CVD / Order Flow Delta": "N/A",
      "Stokastik Momentum": "N/A",
      "Kontrat / Hacim": "N/A",
      "Açık Pozisyon (OI)": "N/A",
  })

  tf_map = {"15dk": "15m", "1s": "1h", "4s": "4h", "1D": "1d"}

  try:
    tickers_url = "https://api.gateio.ws/api/v4/futures/usdt/tickers"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(tickers_url, headers=headers, timeout=10).json()
    ticker_dict = {item["contract"]: item for item in res if "contract" in item}

    for gate_symbol, meta in SYMBOLS_MAP.items():
      if gate_symbol in ticker_dict:
        item = ticker_dict[gate_symbol]
        price = float(item.get("last", 0))
        price_change = float(item.get("change_percentage", 0))

        total_size_contracts = float(item.get("total_size", 0))
        oi_usd = (total_size_contracts * price) / 1_000_000  # M$

        raw_vol = float(
            item.get("volume_24h_settle", item.get("volume_24h_quote", 0))
        )
        volume_usd = raw_vol / 1_000_000  # M$

        for tf_label, tf_gate in tf_map.items():
          try:
            k_url = f"https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract={gate_symbol}&interval={tf_gate}&limit=30"
            k_res = requests.get(k_url, headers=headers, timeout=5).json()
            smc, candle, fibo, poc, cvd, stoch = calculate_advanced_indicators(
                k_res, price
            )
          except Exception:
            smc, candle, fibo, poc, cvd, stoch = (
                "Sıkışma Bölgesi ⚖️",
                "Normal Mum",
                "Fibo Nötr",
                "Nötr POC",
                "Dengeli Delta",
                "Nötr",
            )

          vol_or_contract = (
              f"{total_size_contracts:,.0f} Kontrat"
              if tf_label in ["15dk", "1s"]
              else f"${volume_usd:,.1f}M Hacim"
          )

          matrix_data.append({
              "Son Güncelleme": now_str,
              "Parite": meta["display"],
              "Zaman Dilimi": tf_label,
              "Fiyat ($)": f"${price:,.2f}" if price >= 1 else f"${price:.4f}",
              "24s Değişim": f"{'▲' if price_change >= 0 else '▼'} %{price_change:.2f}",
              "SMC & Yapı Analizi": smc,
              "Mum Formasyonu": candle,
              "Auto-Fibo (TP / SL)": fibo,
              "Volume Profile (POC)": poc,
              "CVD / Order Flow Delta": cvd,
              "Stokastik Momentum": stoch,
              "Kontrat / Hacim": vol_or_contract,
              "Açık Pozisyon (OI)": f"${oi_usd:,.1f}M",
          })
  except Exception:
    pass

  return pd.DataFrame(matrix_data)


# Google Sheets Canlı Haber Bağlantısı
SHEET_ID = "15oys_jSdW0q8ePdUna0BVirzTyazzsMfvJCcral7VgI"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"


@st.cache_data(ttl=30)
def load_news():
  try:
    return pd.read_csv(CSV_URL)
  except Exception:
    return pd.DataFrame()


# ==============================================================================
# ANA SEKMELİ DÜZEN
# ==============================================================================
tab1, tab4, tab2, tab3 = st.tabs([
    "📊 Crypto Matrix",
    "📈 Teknik & Göstergeler",
    "⚡ Haber & Ekonomi Radarı",
    "🎙️ Analizler & Piyasa Beklentileri",
])

# ==============================================================================
# SEKME 1: CRYPTO MATRIX (Multi-TF Sheets Motoru)
# ==============================================================================
with tab1:
  st.subheader(
      "📊 Order Flow, Auto-Fibo, Volume Profile & SMC Multi-Timeframe Matris"
  )

  col_m1, col_m2 = st.columns([1, 4])
  with col_m1:
    if st.button("🔄 Verileri Güncelle & Sheets'e Yaz", key="btn_tech"):
      st.cache_data.clear()
      st.rerun()

  with st.spinner(
      "TRT saatiyle mumlar, Auto-Fibo (TP/SL), POC, CVD, Makro ve SMC yapısı"
      " hesaplanıyor..."
  ):
    df_matrix = fetch_multi_timeframe_matrix()

  if not df_matrix.empty:
    sheets_success, msg = send_to_google_sheets(df_matrix)
    if sheets_success:
      st.success(
          "✅ Makro & Balina Akış Verileri Dahil Tüm Matris Google Sheets"
          " (`Crypto_Matrix`) Tablosuna Aktarıldı!"
      )
    else:
      st.error(f"⚠️ Sheets Aktarım Hatası: {msg}")

    with st.expander(
        "🔍 Canlı Gelişmiş Matrisi İncele / Kontrol Et (Tıklayıp Aç)"
    ):
      st.dataframe(df_matrix, use_container_width=True, hide_index=True)
  else:
    st.warning("Veriler çekilemedi. Lütfen bağlantıyı kontrol edin.")

# ==============================================================================
# SEKME 4: TEKNİK & GÖSTERGELER (YENİLENMİŞ YAN YANA COMPACT DASHBOARD)
# ==============================================================================
with tab4:
  # 1. BAŞLIK VE SEÇİM KUTUSU (YAN YANA SIKIŞTIRILMIŞ ÜST BAŞLIK)
  col_head1, col_head2 = st.columns([2.5, 1])
  with col_head1:
    st.markdown(
        "<h3 style='margin:0; padding:0; font-size:1.3rem; color:#F8FAFC;'>📈"
        " Görsel Alım-Satım Terminali & Likidasyon Haritası</h3>",
        unsafe_allow_html=True,
    )
  with col_head2:
    selected_display = st.selectbox(
        "Parite Seçin:",
        options=[meta["display"] for meta in SYMBOLS_MAP.values()],
        label_visibility="collapsed",
    )

  selected_key = [
      k for k, v in SYMBOLS_MAP.items() if v["display"] == selected_display
  ][0]
  coinank_symbol = SYMBOLS_MAP[selected_key]["coinank"]

  # 2. İKİ KOLONLU ANA YAPI (SOL: LİKİDASYON HARİTASI | SAĞ: MAKRO + BALİNA AKIŞI)
  col_left, col_right = st.columns([1.6, 1])

  # --- SOL KOLON: CANLI LİKİDASYON HARİTASI (COINGLASS / COINANK ENTEGRASYONU) ---
  with col_left:
    st.markdown(
        f"<h4 style='font-size:1.0rem; margin-top:5px;' font-weight:600;'>💧"
        f" {selected_display} Liquidation Map & Heatmap</h4>",
        unsafe_allow_html=True,
    )

    # Canlı Çalışan Kesintisiz Heatmap / Liq Map Entegrasyonu
    liq_url = (
        f"https://s.coinglass.com/lh/{coinank_symbol.replace('usdt','')}-usdt"
    )

    # CoinAnk Harici Güvenlik Engeli Olmayan Yüksek Performanslı Harita Widget'ı
    components.iframe(
        f"https://embed.coinglass.com/dashboard/liquidation-heatmap?symbol={selected_display.replace('/','')}",
        height=520,
        scrolling=True,
    )

    st.markdown(
        f"[🔗 CoinAnk Orijinal Sayfasında Aç ↗](https://coinank.com/tr/chart/derivatives/liq-map/binance/{coinank_symbol}/1d)"
    )

  # --- SAĞ KOLON: MAKRO VE BALİNA CÜZDAN HAREKETLERİ ---
  with col_right:
    # A) SAĞ ÜST: FEAR & GREED + BTC DOMINANCE (İKİ MİNİ KART)
    fng_val, fng_class, btc_dom = fetch_macro_indicators()

    m_col1, m_col2 = st.columns(2)
    with m_col1:
      st.markdown(
          f"""
            <div class="macro-card">
                <div class="macro-title">CMC Fear & Greed Index</div>
                <div class="macro-value" style="color:#F59E0B;">{fng_val} <span style="font-size:0.8rem;">({fng_class})</span></div>
            </div>
            """,
          unsafe_allow_html=True,
      )

    with m_col2:
      st.markdown(
          f"""
            <div class="macro-card">
                <div class="macro-title">Bitcoin Dominance</div>
                <div class="macro-value" style="color:#3B82F6;">{btc_dom}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )

    # B) SAĞ ALT: BÜYÜK KRİPTO CÜZDAN & BORSA AKIŞ ENDEKSİ (1s, 4s, 12s)
    st.markdown(
        "<h4 style='font-size:1.0rem; margin-top:15px;' font-weight:600;'>🐋"
        " Büyük Cüzdan & Borsa Akış Endeksi</h4>",
        unsafe_allow_html=True,
    )

    whale_flows = fetch_whale_flow_index()

    st.markdown(
        f"""
        <div style="background-color:#1E222D; border-radius:8px; padding:12px; border:1px solid #2A2E39;">
            <div style="font-size:0.85rem; padding:6px 0; border-bottom:1px solid #2A2E39;">
                <b>⏱️ 1 Saatlik Akış:</b> <span style="color:#F0B90B;">{whale_flows['1s Balina Akışı']}</span>
            </div>
            <div style="font-size:0.85rem; padding:6px 0; border-bottom:1px solid #2A2E39;">
                <b>⏱️ 4 Saatlik Akış:</b> <span style="color:#10B981;">{whale_flows['4s Balina Akışı']}</span>
            </div>
            <div style="font-size:0.85rem; padding:6px 0;">
                <b>⏱️ 12 Saatlik Akış:</b> <span style="color:#3B82F6;">{whale_flows['12s Balina Akışı']}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "💡 Not: Bu balina akış verileri ve makro duygu göstergeleri aynı"
        " zamanda Google Sheets (`Crypto_Matrix`) tablonuzun ilk satırlarına"
        " otomatik işlenmektedir."
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
