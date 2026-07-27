import datetime
from datetime import timedelta, timezone
import json
import re
import time
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

# SAYFA YAPILANDIRMASI
st.set_page_config(
    page_title="Crypto & Macro Terminal V2.0",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# STYLES / CSS
st.markdown(
    """
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    header[data-testid="stHeader"] { visibility: hidden; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.5rem !important; }
    .stButton>button { width: 100%; background-color: #1E293B; color: #F8FAFC; border: 1px solid #334155; font-weight: 600; border-radius: 8px; }
    .stButton>button:hover { background-color: #334155; border-color: #38BDF8; color: #38BDF8; }
    </style>
""",
    unsafe_allow_html=True,
)

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbx4JHGGGocczm8hpQSMU0wmWUbfiIctOmV4M825YNnjo9cGsnwKjEwcUMmyo7PVO6RK7Q/exec"
TELEGRAM_TOKEN = "8844757455:AAELoord_Vd3KnxfqgE6MzI0fAXN5ik6H2E"
TELEGRAM_CHAT_ID = "6884767698"

SYMBOLS_MAP = {
    "BTC_USDT": {
        "display": "BTC/USDT",
        "binance": "BTCUSDT",
        "threshold": 500000,
        "tag": "BTC",
    },
    "ETH_USDT": {
        "display": "ETH/USDT",
        "binance": "ETHUSDT",
        "threshold": 500000,
        "tag": "ETH",
    },
    "SOL_USDT": {
        "display": "SOL/USDT",
        "binance": "SOLUSDT",
        "threshold": 250000,
        "tag": "SOL",
    },
    "SUI_USDT": {
        "display": "SUI/USDT",
        "binance": "SUIUSDT",
        "threshold": 250000,
        "tag": "SUI",
    },
    "ZEC_USDT": {
        "display": "ZEC/USDT",
        "binance": "ZECUSDT",
        "threshold": 100000,
        "tag": "ZEC",
    },
    "FET_USDT": {
        "display": "FET/USDT",
        "binance": "FETUSDT",
        "threshold": 100000,
        "tag": "FET",
    },
    "NEAR_USDT": {
        "display": "NEAR/USDT",
        "binance": "NEARUSDT",
        "threshold": 100000,
        "tag": "NEAR",
    },
    "ONDO_USDT": {
        "display": "ONDO/USDT",
        "binance": "ONDOUSDT",
        "threshold": 100000,
        "tag": "ONDO",
    },
    "INJ_USDT": {
        "display": "INJ/USDT",
        "binance": "INJUSDT",
        "threshold": 100000,
        "tag": "INJ",
    },
    "TAO_USDT": {
        "display": "TAO/USDT",
        "binance": "TAOUSDT",
        "threshold": 100000,
        "tag": "TAO",
    },
    "APT_USDT": {
        "display": "APT/USDT",
        "binance": "APTUSDT",
        "threshold": 100000,
        "tag": "APT",
    },
    "HYPE_USDT": {
        "display": "HYPE/USDT",
        "binance": "HYPEUSDT",
        "threshold": 100000,
        "tag": "HYPE",
    },
}


def send_telegram_alert(message):
  try:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    requests.post(url, json=payload, timeout=5)
  except Exception as e:
    print(f"Telegram Hatası: {e}")


def fetch_onchain_whale_alerts():
  onchain_data = {}
  try:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }
    res = requests.get("https://t.me/s/whale_alert", headers=headers, timeout=6)
    if res.status_code == 200:
      soup = BeautifulSoup(res.text, "html.parser")
      messages = soup.find_all("div", class_="tgme_widget_message_text")

      for msg in messages[-15:]:
        text = msg.get_text(separator=" ")

        for sym_key, meta in SYMBOLS_MAP.items():
          tag = meta["tag"]
          if f"#{tag}" in text or f" {tag} " in text:
            if "to #Binance" in text or "to #Exchange" in text:
              direction = "Borsaya Giriş (Satış Riski 🚨)"
            elif "from #Binance" in text or "from #Exchange" in text:
              direction = "Soğuk Cüzdana Çıkış (Toplama 🛡️)"
            else:
              direction = "Cüzdandan Cüzdana Transfer 🔄"

            usd_match = re.search(r"\(([\d,]+)\s*USD\)", text)
            usd_val = usd_match.group(1) if usd_match else "Büyük Transfer"

            summary = f"{direction} [${usd_val}]"
            onchain_data[meta["display"]] = summary
  except Exception as e:
    print(f"On-Chain Hatası: {e}")

  return onchain_data


def fetch_whale_trades_15m(binance_symbol, threshold):
  try:
    end_time = int(time.time() * 1000)
    start_time = end_time - (15 * 60 * 1000)

    url = f"https://fapi.binance.com/fapi/v1/aggTrades?symbol={binance_symbol}&startTime={start_time}&endTime={end_time}&limit=1000"
    res = requests.get(url, timeout=5).json()

    whale_buy_usd = 0.0
    whale_sell_usd = 0.0

    if isinstance(res, list):
      for trade in res:
        price = float(trade.get("p", 0))
        qty = float(trade.get("q", 0))
        trade_val = price * qty

        if trade_val >= threshold:
          is_buyer_maker = trade.get("m", False)
          if is_buyer_maker:
            whale_sell_usd += trade_val
          else:
            whale_buy_usd += trade_val

    net_whale = whale_buy_usd - whale_sell_usd
    if net_whale > 0:
      return f"+${net_whale/1_000_000:.2f}M (Net Alım 🟢)"
    elif net_whale < 0:
      return f"-${abs(net_whale)/1_000_000:.2f}M (Net Satım 🔴)"
    else:
      return "$0.00M (Sakin ⚖️)"
  except Exception:
    return "$0.00M (Nötr)"


def fetch_macro_indicators():
  fng_val, fng_class = "26", "Fear"
  try:
    res = requests.get("https://api.alternative.me/fng/", timeout=4).json()
    if res.get("data"):
      fng_val = res["data"][0]["value"]
      fng_class = res["data"][0]["value_classification"]
  except Exception:
    pass
  return fng_val, fng_class, "58.7%"


def detect_single_candle_pattern(o, c, h, l):
  body = abs(c - o)
  rng = h - l if h > l else 1e-9
  upper_wick = h - max(c, o)
  lower_wick = min(c, o) - l
  if body > rng * 0.7:
    return "Güçlü Marubozu 🚀" if c > o else "Güçlü Marubozu 🔻"
  elif upper_wick > body * 2:
    return "Düşüş Pinbar (Upper Rejection) ⚡"
  elif lower_wick > body * 2:
    return "Yükseliş Pinbar (Hammer) 🛡️"
  elif body < rng * 0.15:
    return "Doji / Kararsız Mum ⚖️"
  elif c > o:
    return "Boğa Mumu 🟢"
  else:
    return "Ayı Mumu 🔴"


def calculate_advanced_indicators(klines_data, current_price):
  if not klines_data or len(klines_data) < 10:
    return (
        "Sıkışma Bölgesi ⚖️",
        "Normal Mum",
        "Doji ⚖️",
        "Nötr ⚖️",
        {"sl": "$0.00", "g_pocket": "$0.00", "tp1": "$0.00", "tp2": "$0.00"},
        "Nötr POC",
        "Dengeli Delta",
        "Nötr",
        "Normal Volatilite",
        "$0.00",
        0.0,
    )

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
  prev_c, prev_o, prev_h, prev_l = closes[-2], opens[-2], highs[-2], lows[-2]

  body_0 = abs(last_c - last_o)
  rng_0 = last_h - last_l if last_h > last_l else 1e-9
  if (
      last_c > last_o
      and prev_c < prev_o
      and last_c > prev_o
      and body_0 > rng_0 * 0.5
  ):
    candle_pattern_c0 = "Boğa Yutan (Bullish Engulfing) 🟢"
  elif (
      last_c < last_o
      and prev_c > prev_o
      and last_c < prev_o
      and body_0 > rng_0 * 0.5
  ):
    candle_pattern_c0 = "Ayı Yutan (Bearish Engulfing) 🔴"
  else:
    candle_pattern_c0 = detect_single_candle_pattern(
        last_o, last_c, last_h, last_l
    )

  c1_prev2_c, c1_prev2_o = closes[-3], opens[-3]
  body_1 = abs(prev_c - prev_o)
  rng_1 = prev_h - prev_l if prev_h > prev_l else 1e-9
  if (
      prev_c > prev_o
      and c1_prev2_c < c1_prev2_o
      and prev_c > c1_prev2_o
      and body_1 > rng_1 * 0.5
  ):
    c1_candle_pattern = "Boğa Yutan (Bullish Engulfing) 🟢"
  elif (
      prev_c < prev_o
      and c1_prev2_c > c1_prev2_o
      and prev_c < c1_prev2_o
      and body_1 > rng_1 * 0.5
  ):
    c1_candle_pattern = "Ayı Yutan (Bearish Engulfing) 🔴"
  else:
    c1_candle_pattern = detect_single_candle_pattern(
        prev_o, prev_c, prev_h, prev_l
    )

  c3_range = np.max(highs[-4:-1]) - np.min(lows[-4:-1])
  if closes[-2] > np.max(highs[-5:-2]):
    pa_context = "Kırılım Gerçekleşti 🚀"
  elif closes[-2] > np.max(highs[-5:-2]) and last_l <= np.max(highs[-5:-2]):
    pa_context = "Kırılım ➔ Re-Test Onayı ⚡"
  elif (highs[-2] > np.max(highs[-5:-2])) and closes[-2] < np.max(highs[-5:-2]):
    pa_context = "Reddetme / FVG Tepkisi 🔻"
  elif c3_range < current_price * 0.008:
    pa_context = "Sıkışma / Daralma ⚠️"
  else:
    pa_context = "Nötr Akümülasyon ⚖️"

  swing_high, swing_low = np.max(highs), np.min(lows)
  fibo_range = (
      swing_high - swing_low if swing_high > swing_low else current_price * 0.01
  )
  fibo_0618 = swing_low + (fibo_range * 0.618)
  fmt = lambda val: f"${val:,.2f}" if current_price >= 1 else f"${val:.4f}"
  fibo_dict = {
      "sl": fmt(swing_low),
      "g_pocket": fmt(fibo_0618),
      "tp1": fmt(swing_high),
      "tp2": fmt(swing_high + (fibo_range * 0.272)),
  }

  high_max, low_min = np.max(highs[:-1]), np.min(lows[:-1])
  if last_c > high_max:
    smc = "BOS Yapıldı (Yükseliş Trend Kırılımı 🚀)"
  elif last_c < low_min:
    smc = "CHoCH Kırılımı (Düşüş Trend Kırılımı 🔻)"
  elif last_h >= high_max * 0.999 and last_c < high_max:
    smc = "Tepe Likidite Temizliği (Sweep ⚡)"
  elif last_l <= low_min * 1.001 and last_c > low_min:
    smc = "Dip Likidite Temizliği (Sweep 🛡️)"
  else:
    smc = "Sıkışma / Akümülasyon Bölgesi ⚖️"

  price_min, price_max = np.min(lows), np.max(highs)
  poc_val = "$0.00"
  if price_max > price_min:
    bins = np.linspace(price_min, price_max, 10)
    digitized = np.digitize(closes, bins)
    vol_per_bin = [volumes[digitized == i].sum() for i in range(1, len(bins))]
    poc_price = (bins[np.argmax(vol_per_bin)] + bins[np.argmax(vol_per_bin) + 1]) / 2
    poc_val = fmt(poc_price)
    poc_status = (
        f"POC Üstünde ({poc_val})"
        if current_price >= poc_price
        else f"POC Altında ({poc_val})"
    )
  else:
    poc_status = "Nötr POC"

  deltas = (
      volumes
      * ((closes - lows) - (highs - closes))
      / (highs - lows + 1e-9)
  )
  cvd_recent = np.sum(deltas[-5:])
  cvd_status = (
      "Net Alıcı Delta (CVD+ 🔥)"
      if cvd_recent > 0
      else "Net Satıcı Delta (CVD- ❄️)"
  )

  l14, h14 = np.min(lows[-14:]), np.max(highs[-14:])
  stoch_status = (
      f"Aşırı Alım (%{100*(closes[-1]-l14)/(h14-l14):.0f})"
      if h14 > l14 and (100 * (closes[-1] - l14) / (h14 - l14)) >= 80
      else "Nötr"
  )

  sma20 = np.mean(closes[-20:])
  bb_width = (4 * np.std(closes[-20:])) / sma20 if sma20 > 0 else 0
  bb_status = (
      f"Bant Sıkışması (%{bb_width*100:.1f} ⚠️)"
      if bb_width < 0.025
      else "Normal Volatilite"
  )

  return (
      smc,
      candle_pattern_c0,
      c1_candle_pattern,
      pa_context,
      fibo_dict,
      poc_status,
      cvd_status,
      stoch_status,
      bb_status,
      poc_val,
      bb_width,
  )


def run_cron_update():
  matrix_data = []
  trt_tz = timezone(timedelta(hours=3))
  now_str = datetime.datetime.now(trt_tz).strftime("%d.%m.%Y %H:%M")
  fng_val, fng_class, btc_dom = fetch_macro_indicators()
  tf_map = {"15dk": "15m", "1s": "1h", "4s": "4h", "1D": "1d"}

  onchain_map = fetch_onchain_whale_alerts()

  try:
    res = requests.get(
        "https://api.gateio.ws/api/v4/futures/usdt/tickers", timeout=10
    ).json()
    ticker_dict = {item["contract"]: item for item in res if "contract" in item}

    for gate_symbol, meta in SYMBOLS_MAP.items():
      if gate_symbol in ticker_dict:
        item = ticker_dict[gate_symbol]
        price = float(item.get("last", 0))
        price_change = float(item.get("change_percentage", 0))
        total_size = float(item.get("total_size", 0))
        oi_usd = (total_size * price) / 1_000_000
        vol_usd = (
            float(item.get("volume_24h_settle", item.get("volume_24h_quote", 0)))
            / 1_000_000
        )

        threshold = meta.get("threshold", 100000)
        whale_delta_str = fetch_whale_trades_15m(meta["binance"], threshold)
        onchain_info = onchain_map.get(
            meta["display"], "Aktivite Yok / Sakin ⚖️"
        )

        for tf_label, tf_gate in tf_map.items():
          try:
            k_res = requests.get(
                f"https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract={gate_symbol}&interval={tf_gate}&limit=30",
                timeout=5,
            ).json()
            (
                smc,
                c0,
                c1,
                pa,
                fibo,
                poc,
                cvd,
                stoch,
                bb,
                poc_val,
                bb_w,
            ) = calculate_advanced_indicators(k_res, price)

            if tf_label == "15dk":
              formatted_price = (
                  f"${price:,.2f}" if price >= 1 else f"${price:.4f}"
              )

              if bb_w <= 0.007:
                alert_msg = (
                    f"⚠️ <b>VOLATİLİTE SIKIŞMASI (SQUEEZE)</b>\n\n"
                    f"<b>Parite:</b> {meta['display']}\n"
                    f"<b>Fiyat:</b> {formatted_price}\n"
                    f"<b>Squeeze Oranı:</b> %{bb_w*100:.2f}\n"
                    f"<b>15dk Balina Tahta Delta:</b> {whale_delta_str}\n"
                    f"<b>On-Chain Akış:</b> {onchain_info}\n"
                    f"<b>Önceki Mum (C-1):</b> {c1}\n\n"
                    f"⚡ <i>Büyük patlama/kırılım yaklaşıyor!</i>"
                )
                send_telegram_alert(alert_msg)

              if "Sweep" in smc:
                alert_msg = (
                    f"🛡️ <b>LİKİDİTE TEMİZLİĞİ (SWEEP) DETECTED</b>\n\n"
                    f"<b>Parite:</b> {meta['display']}\n"
                    f"<b>Fiyat:</b> {formatted_price}\n"
                    f"<b>Yapı Durumu:</b> {smc}\n"
                    f"<b>15dk Balina Tahta Delta:</b> {whale_delta_str}\n"
                    f"<b>On-Chain Akış:</b> {onchain_info}\n"
                    f"<b>PA Context:</b> {pa}\n\n"
                    f"🔥 <i>Tuzak hareketi sonrası dönüş fırsatı!</i>"
                )
                send_telegram_alert(alert_msg)

          except Exception:
            smc, c0, c1, pa, poc, cvd, stoch, bb, poc_val = (
                "Sıkışma",
                "Normal",
                "Doji",
                "Nötr",
                "Nötr",
                "Nötr",
                "Nötr",
                "Normal",
                "$0.00",
            )
            fibo = {
                "sl": "$0.00",
                "g_pocket": "$0.00",
                "tp1": "$0.00",
                "tp2": "$0.00",
            }

          matrix_data.append({
              "Son Güncelleme": now_str,
              "Parite": meta["display"],
              "Zaman Dilimi": tf_label,
              "Fiyat ($)": f"${price:,.2f}" if price >= 1 else f"${price:.4f}",
              "24s Değişim": (
                  f"{'▲' if price_change >= 0 else '▼'} %{price_change:.2f}"
              ),
              "SMC & Yapı Analizi": smc,
              "Önceki Mum Formasyonu (C-1)": c1,
              "Son 3 Mum Yapısı (PA Context)": pa,
              "15dk Balina Hacim Delta": whale_delta_str,
              "On-Chain Cüzdan Akışı (Whale Alert)": onchain_info,
              "Aktif Mum (C-0)": c0,
              "Volume Profile (POC)": poc,
              "CVD / Order Flow Delta": cvd,
              "Bollinger Volatilite (BB)": bb,
              "Stokastik Momentum": stoch,
              "Fibo SL / Dip": fibo["sl"],
              "Fibo Golden Pocket (0.618)": fibo["g_pocket"],
              "Fibo TP1 Hedefi": fibo["tp1"],
              "Fibo TP2 Hedefi": fibo["tp2"],
              "Kontrat / Hacim": (
                  f"{total_size:,.0f} Kontrat"
                  if tf_label in ["15dk", "1s"]
                  else f"${vol_usd:,.1f}M Hacim"
              ),
              "Açık Pozisyon (OI)": f"${oi_usd:,.1f}M",
              "Korku Endeksi": f"{fng_val} ({fng_class})",
              "BTC Dominansı": btc_dom,
              "Haber Yönü (4s)": "Bullish 🟢",
              "Haber Yönü (12s)": "Nötr-Bearish ⚖️",
              "Haber Yönü (1D)": "Bullish 🟢",
          })
  except Exception as e:
    print(f"Hata: {e}")

  if matrix_data:
    df = pd.DataFrame(matrix_data)
    payload = [list(df.columns)] + df.values.tolist()
    res = requests.post(
        WEBHOOK_URL,
        data=json.dumps(payload),
        headers={"Content-Type": "text/plain;charset=utf-8"},
        timeout=12,
    )
    return res.status_code
  return None


# STREAMLIT ÜST BAŞLIK & TETO
col_title, col_btn = st.columns([3, 1])

with col_title:
  st.title("⚡ Crypto & Macro Terminal V2.0")

with col_btn:
  st.write("")
  if st.button("🔄 Verileri Hemen Güncelle"):
    with st.spinner("Sheets & Telegram güncelleniyor..."):
      status = run_cron_update()
      if status == 200:
        st.success("✅ Veriler Google Sheets'e aktarıldı!")
      else:
        st.error("⚠️ Güncelleme hatası.")

# TAB SEKMELERİ RESTORE EDİLDİ
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Crypto Matrix (Canlı Tablo)",
    "📅 Canlı Ekonomik Takvim & Makro Ajanda (3 Yıldız Volatilite)",
    "📈 TradingView & Likidasyon Isı Haritası",
    "📰 Haber Akışı & Duyarlılık",
])

with tab1:
  st.markdown("### 🔍 Canlı Crypto Matrix Veri Akışı")
  # Embedded Google Sheets View
  sheets_iframe = """
    <iframe src="https://docs.google.com/spreadsheets/d/e/2PACX-1vT5N7B8-Gv_Y-wI4I-f2J3R2cK8XN-Z5X/pubhtml?widget=true&amp;headers=false" 
            width="100%" height="650" frameborder="0"></iframe>
    """
  components.html(sheets_iframe, height=660)

with tab2:
  st.markdown("### 📅 Canlı Ekonomik Takvim & Makro Ajanda")
  eco_calendar_html = """
    <iframe src="https://sslecal2.investing.com?columns=exc_flags,exc_currency,importance,event,actual,forecast,previous&category=_all&importance=2,3&features=datepicker,timezone&countries=5,72,17,43,37,6&calType=week&timeZone=8" 
            width="100%" height="650" frameborder="0" allowtransparency="true" marginwidth="0" marginheight="0"></iframe>
    """
  components.html(eco_calendar_html, height=660)

with tab3:
  col_chart1, col_chart2 = st.columns(2)
  with col_chart1:
    st.markdown("### 📈 TradingView Canlı Grafik")
    tv_html = """
        <div class="tradingview-widget-container" style="height:100%;width:100%">
          <div id="tradingview_chart" style="height:550px;width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({
            "autosize": true,
            "symbol": "BINANCE:BTCUSDT",
            "interval": "15",
            "timezone": "Europe/Istanbul",
            "theme": "dark",
            "style": "1",
            "locale": "tr",
            "toolbar_bg": "#f1f3f6",
            "enable_publishing": false,
            "container_id": "tradingview_chart"
          });
          </script>
        </div>
        """
    components.html(tv_html, height=560)

  with col_chart2:
    st.markdown("### 🔥 Likidasyon Isı Haritası & Tahta Derinliği")
    coinglass_html = """
        <iframe src="https://www.coinglass.com/pro/futures/LiquidationHeatMap" width="100%" height="550" frameborder="0"></iframe>
        """
    components.html(coinglass_html, height=560)

with tab4:
  st.markdown("### 📰 Piyasa Duyarlılığı & Haber Radarı")
  fng_val, fng_class, btc_dom = fetch_macro_indicators()

  m1, m2, m3 = st.columns(3)
  m1.metric("Korku & Açgözlülük Endeksi", f"{fng_val} ({fng_class})")
  m2.metric("BTC Dominansı", btc_dom)
  m3.metric("Terminal Durumu", "V2.0 Canlı 🚀")

  st.markdown("---")
  st.info(
      "💡 **İpucu:** Sistemimiz hem tahtadaki $500K / $250K / $100K üzeri balina"
      " emirlerini hem de @whale_alert üzerindeki devasa zincir üstü (On-Chain)"
      " transferleri 15 dakikalık periyotlarla tarayarak canlı tabloya işler."
  )
