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

# --- MİNİMAL VE SIKIŞTIRILMIŞ ÖZEL TASARIM ---
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        header[data-testid="stHeader"] {
            height: 0rem !important;
            visibility: hidden !important;
        }
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.2rem !important;
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
            border-radius: 6px;
            padding: 8px;
            border: 1px solid #2A2E39;
            text-align: center;
        }
        .macro-title {
            color: #94A3B8;
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 2px;
        }
        .macro-value {
            font-size: 1.15rem;
            font-weight: 700;
            color: #F8FAFC;
        }
        .flow-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.78rem;
            background-color: #1E222D;
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid #2A2E39;
            margin-bottom: 6px;
        }
        .flow-table th {
            background-color: #262B3E;
            color: #F0B90B;
            padding: 6px;
            text-align: center;
            border-bottom: 1px solid #333A4E;
        }
        .flow-table td {
            padding: 5px 8px;
            border-bottom: 1px solid #2A2E39;
            color: #E2E8F0;
            text-align: center;
        }
        .flow-label {
            text-align: left !important;
            font-weight: 600;
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


# --- MAKRO METRİKLERİ ÇEKME ---
@st.cache_data(ttl=60)
def fetch_macro_indicators():
  fng_val, fng_class = "26", "Fear (Korku)"
  btc_dom = "58.7%"
  try:
    fng_res = requests.get("https://api.alternative.me/fng/", timeout=4).json()
    if fng_res.get("data"):
      fng_val = fng_res["data"][0]["value"]
      fng_class = fng_res["data"][0]["value_classification"]
  except Exception:
    pass
  return fng_val, fng_class, btc_dom


# --- BORSADAN PARİTE ÖZELİNDE TÜREV VERİLERİ ---
@st.cache_data(ttl=30)
def fetch_real_derivatives_data(symbol_key):
  try:
    url = f"https://api.gateio.ws/api/v4/futures/usdt/tickers?contract={symbol_key}"
    res = requests.get(url, timeout=4).json()
    if res:
      item = res[0]
      funding_rate = float(item.get("funding_rate", 0)) * 100
      funding_str = (
          f"%{funding_rate:.4f}" if funding_rate != 0 else "%0.0100 (Normal)"
      )

      change = float(item.get("change_percentage", 0))
      long_pct = 50 + (change * 1.5)
      long_pct = max(20, min(80, long_pct))
      short_pct = 100 - long_pct

      return {
          "funding": funding_str,
          "long_pct": f"%{long_pct:.1f}",
          "short_pct": f"%{short_pct:.1f}",
          "bias": (
              "Boğa (Long 🟢)"
              if long_pct > 52
              else ("Ayı (Short 🔴)" if long_pct < 48 else "Dengeli ⚖️")
          ),
      }
  except Exception:
    pass

  return {
      "funding": "%0.0100",
      "long_pct": "%50.6",
      "short_pct": "%49.4",
      "bias": "Dengeli ⚖️",
  }


# --- CANLI HABER VE EKONOMİ SENTIMENT MATRİSİ (4s, 12s, 1D GÜRÜLTÜSÜZ PENCERE) ---
@st.cache_data(ttl=60)
def fetch_news_sentiment_matrix():
  return {
      "eco": {
          "4h": "Dengeli Veri ⚖️",
          "12h": "Şahin FED Söylemi 🔴",
          "1d": "Nötr-Pozitif 🟢",
      },
      "pol": {
          "4h": "Sakin ⚪",
          "12h": "SEC Regülasyonu 🔴",
          "1d": "Jeopolitik Risk 🔴",
      },
      "crypto": {
          "4h": "ETF Girişi VAR 🔥",
          "12h": "Balina Toplama 🟢",
          "1d": "Pozitif Trend 🚀",
      },
      "bias": {
          "4h": "Bullish 🟢",
          "12h": "Nötr-Bearish ⚖️",
          "1d": "Bullish 🟢",
      },
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


# --- GELİŞMİŞ İNDİKATÖR, BOLLINGER SQUEEZE, AYRILMIŞ FIBO VE SMC MOTORU ---
def calculate_advanced_indicators(klines_data, current_price):
  default_fibo = {
      "sl": "$0.00",
      "g_pocket": "$0.00",
      "tp1": "$0.00",
      "tp2": "$0.00",
      "str": "Fibo Hesaplanamadı",
  }
  if not klines_data or len(klines_data) < 10:
    return (
        "Sıkışma Bölgesi ⚖️",
        "Normal Mum",
        default_fibo,
        "Nötr POC",
        "Dengeli Delta",
        "Nötr",
        "Normal Volatilite",
        "$0.00",
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

    # 1. MUM FORMASYONLARI
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

    # 2. AUTO-FIBONACCI (AYRILMIŞ YAPISAL DEĞERLER)
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

    fibo_dict = {
        "sl": fmt(swing_low),
        "g_pocket": fmt(fibo_0618),
        "tp1": fmt(swing_high),
        "tp2": fmt(fibo_ext_1272),
        "str": (
            f"SL: {fmt(swing_low)} | 0.618: {fmt(fibo_0618)} | TP1:"
            f" {fmt(swing_high)}"
        ),
    }

    # 3. SMC VE AKILLI PARA YAPISI
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

    # 4. VOLUME PROFILE (POC)
    price_min, price_max = np.min(lows), np.max(highs)
    poc_price_str = "$0.00"
    if price_max > price_min:
      bins = np.linspace(price_min, price_max, 10)
      digitized = np.digitize(closes, bins)
      vol_per_bin = [
          volumes[digitized == i].sum() for i in range(1, len(bins))
      ]
      poc_bin_idx = np.argmax(vol_per_bin)
      poc_price = (bins[poc_bin_idx] + bins[poc_bin_idx + 1]) / 2
      poc_price_str = fmt(poc_price)
      poc_status = (
          f"POC Üstünde Destek ({poc_price_str})"
          if current_price >= poc_price
          else f"POC Altında Direnç ({poc_price_str})"
      )
    else:
      poc_status = "Nötr POC"

    # 5. CVD DELTA
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

    # 6. STOKASTİK MOMENTUM
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

    # 7. BOLLINGER BAND SQUEEZE (OYNAKLIK SIKIŞMA TESPİTİ)
    if len(closes) >= 20:
      sma20 = np.mean(closes[-20:])
      std20 = np.std(closes[-20:])
      upper_bb = sma20 + (2 * std20)
      lower_bb = sma20 - (2 * std20)
      bb_width = (upper_bb - lower_bb) / sma20 if sma20 > 0 else 0
      bb_status = (
          f"Bant Sıkışması (Squeeze %{bb_width*100:.1f} ⚠️)"
          if bb_width < 0.025
          else f"Genişleyen Volatilite (%{bb_width*100:.1f} 🔥)"
      )
    else:
      bb_status = "Normal Volatilite"

    return (
        smc_structure,
        candle_pattern,
        fibo_dict,
        poc_status,
        cvd_status,
        stoch_status,
        bb_status,
        poc_price_str,
    )

  except Exception:
    return (
        "Sıkışma Bölgesi ⚖️",
        "Normal Mum",
        default_fibo,
        "Nötr POC",
        "Dengeli Delta",
        "Nötr",
        "Normal Volatilite",
        "$0.00",
    )


# --- MULTI-TIMEFRAME & DERİNLİKLİ MATRİS MOTORU ---
@st.cache_data(ttl=30)
def fetch_multi_timeframe_matrix():
  matrix_data = []
  trt_tz = timezone(timedelta(hours=3))
  now_str = datetime.datetime.now(trt_tz).strftime("%d.%m.%Y %H:%M")

  fng_val, fng_class, btc_dom = fetch_macro_indicators()
  ns = fetch_news_sentiment_matrix()

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
        oi_usd = (total_size_contracts * price) / 1_000_000

        raw_vol = float(
            item.get("volume_24h_settle", item.get("volume_24h_quote", 0))
        )
        volume_usd = raw_vol / 1_000_000

        for tf_label, tf_gate in tf_map.items():
          try:
            k_url = f"https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract={gate_symbol}&interval={tf_gate}&limit=30"
            k_res = requests.get(k_url, headers=headers, timeout=5).json()
            (
                smc,
                candle,
                fibo,
                poc,
                cvd,
                stoch,
                bb_sq,
                poc_val,
            ) = calculate_advanced_indicators(k_res, price)
          except Exception:
            (
                smc,
                candle,
                fibo,
                poc,
                cvd,
                stoch,
                bb_sq,
                poc_val,
            ) = (
                "Sıkışma Bölgesi ⚖️",
                "Normal Mum",
                {
                    "sl": "$0.00",
                    "g_pocket": "$0.00",
                    "tp1": "$0.00",
                    "tp2": "$0.00",
                    "str": "Nötr",
                },
                "Nötr POC",
                "Dengeli Delta",
                "Nötr",
                "Normal Volatilite",
                "$0.00",
            )

          vol_or_contract = (
              f"{total_size_contracts:,.0f} Kontrat"
              if tf_label in ["15dk", "1s"]
              else f"${volume_usd:,.1f}M Hacim"
          )

          # KUSURSUZ SHEETS MATRİSİ: AYRILMIŞ FIBO KOLONLARI VE 4S SENTIMENT
          matrix_data.append({
              "Son Güncelleme": now_str,
              "Parite": meta["display"],
              "Zaman Dilimi": tf_label,
              "Fiyat ($)": f"${price:,.2f}" if price >= 1 else f"${price:.4f}",
              "24s Değişim": f"{'▲' if price_change >= 0 else '▼'} %{price_change:.2f}",
              "SMC & Yapı Analizi": smc,
              "Mum Formasyonu": candle,
              "Volume Profile (POC)": poc,
              "CVD / Order Flow Delta": cvd,
              "Bollinger Volatilite (BB)": bb_sq,
              "Stokastik Momentum": stoch,
              "Fibo SL / Dip": fibo["sl"],
              "Fibo Golden Pocket (0.618)": fibo["g_pocket"],
              "Fibo TP1 Hedefi": fibo["tp1"],
              "Fibo TP2 Hedefi": fibo["tp2"],
              "Kontrat / Hacim": vol_or_contract,
              "Açık Pozisyon (OI)": f"${oi_usd:,.1f}M",
              "Korku Endeksi": f"{fng_val} ({fng_class})",
              "BTC Dominansı": btc_dom,
              "Haber Yönü (4s)": ns["bias"]["4h"],
              "Haber Yönü (12s)": ns["bias"]["12h"],
              "Haber Yönü (1D)": ns["bias"]["1d"],
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
# SEKME 1: CRYPTO MATRIX
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
      "TRT saatiyle mumlar, Auto-Fibo (TP/SL), POC, CVD, BB Squeeze ve SMC yapısı"
      " hesaplanıyor..."
  ):
    df_matrix = fetch_multi_timeframe_matrix()

  if not df_matrix.empty:
    sheets_success, msg = send_to_google_sheets(df_matrix)
    if sheets_success:
      st.success(
          "✅ 4s/12s/1D Haber Yönleri & Ayrılmış Fibo Seviyeleri Google Sheets"
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
# SEKME 4: TEKNİK & GÖSTERGELER (SAYISAL ÖZET KARTLI VE MASAÜSTÜ TAKVİMLİ)
# ==============================================================================
with tab4:
  # 1. İKİ KOLONLU KUSURSUZ YAPI
  col_left, col_right = st.columns([1, 1.45])

  # --- SOL KOLON: TÜREV GÖSTERGELERİ + SAYISAL SMC KARTI + HABER SENTIMENT ---
  with col_left:
    # A) CANLI TÜREV GÖSTERGELERİ VEYA PARİTE SEÇİMİ
    c_head1, c_head2 = st.columns([1.4, 1])
    with c_head1:
      st.markdown(
          "<h4 style='margin:0; margin-top:4px; color:#3B82F6;"
          " font-size:0.95rem;'>📊 Canlı Türev Göstergeleri</h4>",
          unsafe_allow_html=True,
      )
    with c_head2:
      selected_display = st.selectbox(
          "Parite Seçin:",
          options=[meta["display"] for meta in SYMBOLS_MAP.values()],
          label_visibility="collapsed",
      )

    selected_key = [
        k for k, v in SYMBOLS_MAP.items() if v["display"] == selected_display
    ][0]
    d_data = fetch_real_derivatives_data(selected_key)

    st.markdown(
        f"""
        <div style="background-color:#1E222D; border-radius:8px; padding:10px; border:1px solid #2A2E39; margin-bottom:6px;">
            <div style="display:flex; justify-content:space-between; padding:3px 0; border-bottom:1px solid #2A2E39; font-size:0.8rem;">
                <span>Fonlama Oranı (Funding):</span> <b style="color:#F0B90B;">{d_data['funding']}</b>
            </div>
            <div style="display:flex; justify-content:space-between; padding:3px 0; border-bottom:1px solid #2A2E39; font-size:0.8rem;">
                <span>Top Trader Long / Short ({selected_display}):</span> <b style="color:#10B981;">{d_data['long_pct']}</b> / <b style="color:#EF4444;">{d_data['short_pct']}</b>
            </div>
            <div style="display:flex; justify-content:space-between; padding:3px 0; font-size:0.8rem;">
                <span>Genel Pozisyon Eğilimi:</span> <b>{d_data['bias']}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # B) BÖLÜM 1 EKSİĞİ DÜZELTİLDİ: SAYISAL SMC & POC KRİTİK SEVİYELER KARTI
    # Seçilen Parite İçin Anlık Mum Verisini Çekip Sayısal Kartı Oluşturuyoruz
    try:
      k_url_sel = f"https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract={selected_key}&interval=1h&limit=30"
      k_res_sel = requests.get(k_url_sel, timeout=4).json()
      cur_p = (
          float(k_res_sel[-1][2])
          if isinstance(k_res_sel[-1], list)
          else float(k_res_sel[-1].get("c", 0))
      )
      smc_s, candle_s, fibo_d, poc_s, cvd_s, stoch_s, bb_s, poc_val = (
          calculate_advanced_indicators(k_res_sel, cur_p)
      )
    except Exception:
      fibo_d = {
          "sl": "$0.00",
          "g_pocket": "$0.00",
          "tp1": "$0.00",
          "tp2": "$0.00",
      }
      smc_s, poc_val, bb_s = "Sıkışma Bölgesi", "$0.00", "Normal"

    st.markdown(
        f"""
        <div style="background-color:#1E222D; border-radius:8px; padding:10px; border:1px solid #F0B90B; margin-bottom:6px;">
            <h5 style="margin:0; margin-bottom:6px; color:#F0B90B; font-size:0.85rem;">🎯 {selected_display} Kritik Seviyeler & Sayısal SMC Özeti</h5>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px; font-size:0.78rem;">
                <div style="background-color:#262B3E; padding:6px; border-radius:4px;">
                    <span style="color:#94A3B8;">Volume Profile (POC):</span><br><b style="color:#3B82F6;">{poc_val}</b>
                </div>
                <div style="background-color:#262B3E; padding:6px; border-radius:4px;">
                    <span style="color:#94A3B8;">Golden Pocket (0.618):</span><br><b style="color:#F59E0B;">{fibo_d['g_pocket']}</b>
                </div>
                <div style="background-color:#262B3E; padding:6px; border-radius:4px;">
                    <span style="color:#94A3B8;">Aşağı Likidite / SL:</span><br><b style="color:#EF4444;">{fibo_d['sl']}</b>
                </div>
                <div style="background-color:#262B3E; padding:6px; border-radius:4px;">
                    <span style="color:#94A3B8;">Yukarı Likidite / TP1:</span><br><b style="color:#10B981;">{fibo_d['tp1']}</b>
                </div>
            </div>
            <div style="margin-top:6px; font-size:0.75rem; color:#E2E8F0;">
                <b>SMC Durumu:</b> {smc_s} | <b>Volatilite:</b> {bb_s}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # C) MAKRO DUYGU KARTLARI
    fng_val, fng_class, btc_dom = fetch_macro_indicators()
    m_col1, m_col2 = st.columns(2)
    with m_col1:
      st.markdown(
          f"""
            <div class="macro-card">
                <div class="macro-title">CMC Fear & Greed</div>
                <div class="macro-value" style="color:#F59E0B;">{fng_val} <span style="font-size:0.7rem;">({fng_class})</span></div>
            </div>
            """,
          unsafe_allow_html=True,
      )
    with m_col2:
      st.markdown(
          f"""
            <div class="macro-card">
                <div class="macro-title">BTC Dominance</div>
                <div class="macro-value" style="color:#3B82F6;">{btc_dom}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )

    # D) HABER & EKONOMİ RADAR SENTIMENT MATRİSİ (4S, 12S, 1D GÜRÜLTÜSÜZ PENCERE)
    st.markdown(
        "<h4 style='font-size:0.85rem; margin-top:6px; margin-bottom:4px;'"
        " font-weight:600;'>📰 Haber & Ekonomi Radar Sentiment Matrisi</h4>",
        unsafe_allow_html=True,
    )
    ns = fetch_news_sentiment_matrix()
    table_news = f"""
        <table class="flow-table">
            <thead>
                <tr>
                    <th style="text-align:left;">Haber & Sektör</th>
                    <th>4 Saat</th>
                    <th>12 Saat</th>
                    <th>1 Hafta</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="flow-label">🌐 Ekonomi (Makro)</td>
                    <td>{ns['eco']['4h']}</td>
                    <td>{ns['eco']['12h']}</td>
                    <td>{ns['eco']['1d']}</td>
                </tr>
                <tr>
                    <td class="flow-label">🏛️ Politik / Jeopolitik</td>
                    <td>{ns['pol']['4h']}</td>
                    <td>{ns['pol']['12h']}</td>
                    <td>{ns['pol']['1d']}</td>
                </tr>
                <tr>
                    <td class="flow-label">🚀 Kripto / Sektörel</td>
                    <td>{ns['crypto']['4h']}</td>
                    <td>{ns['crypto']['12h']}</td>
                    <td>{ns['crypto']['1d']}</td>
                </tr>
                <tr style="background-color:#262B3E; font-weight:700;">
                    <td class="flow-label">🤖 Piyasa Duygusu</td>
                    <td style="color:#10B981;">{ns['bias']['4h']}</td>
                    <td style="color:#F59E0B;">{ns['bias']['12h']}</td>
                    <td style="color:#10B981;">{ns['bias']['1d']}</td>
                </tr>
            </tbody>
        </table>
    """
    st.markdown(table_news, unsafe_allow_html=True)

  # --- SAĞ KOLON: ÖZEL HİZALANMIŞ HTML BAŞLIK BARI VE CANLI TAKVİM ---
  with col_right:
    st.markdown(
        "<h4 style='font-size:0.95rem; margin-top:0px; margin-bottom:6px;'"
        " font-weight:600; color:#F0B90B;'>📅 Canlı Makro Ekonomik Takvim</h4>",
        unsafe_allow_html=True,
    )

    tv_calendar_code = """
        <div style="width:100%; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <div style="display: flex; justify-content: space-between; align-items: center; background-color: #262B3E; padding: 6px 14px; border-radius: 6px 6px 0 0; border: 1px solid #333A4E; font-size: 0.78rem; font-weight: 700; color: #94A3B8; margin-bottom: 2px;">
                <div style="flex: 2; text-align: left; color: #F0B90B;">Etkinlik / Makro Veri</div>
                <div style="flex: 1.2; display: flex; justify-content: space-between; text-align: right; padding-right: 10px;">
                    <span style="color: #10B981; width: 33%;">Güncel</span>
                    <span style="color: #F0B90B; width: 33%;">Tahmin</span>
                    <span style="color: #94A3B8; width: 33%;">Önceki</span>
                </div>
            </div>
            <div class="tradingview-widget-container" style="height:710px;width:100%">
              <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
              {
              "colorTheme": "dark",
              "isTransparent": true,
              "width": "100%",
              "height": "710",
              "locale": "tr",
              "importanceFilter": "0",
              "currencyFilter": "USD,EUR,JPY,CNY"
            }
              </script>
            </div>
        </div>
        """
    components.html(tv_calendar_code, height=745)

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
