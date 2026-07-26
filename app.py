import datetime
from datetime import timezone, timedelta
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
SYMBOLS_MAP = {
    "BTC_USDT": {"display": "BTC/USDT", "coinank": "btcusdt", "tv": "BINANCE:BTCUSDT"},
    "ETH_USDT": {"display": "ETH/USDT", "coinank": "ethusdt", "tv": "BINANCE:ETHUSDT"},
    "SOL_USDT": {"display": "SOL/USDT", "coinank": "solusdt", "tv": "BINANCE:SOLUSDT"},
    "ZEC_USDT": {"display": "ZEC/USDT", "coinank": "zecusdt", "tv": "BINANCE:ZECUSDT"},
    "FET_USDT": {"display": "FET/USDT", "coinank": "fetusdt", "tv": "BINANCE:FETUSDT"},
    "NEAR_USDT": {"display": "NEAR/USDT", "coinank": "nearusdt", "tv": "BINANCE:NEARUSDT"},
    "ONDO_USDT": {"display": "ONDO/USDT", "coinank": "ondousdt", "tv": "BINANCE:ONDOUSDT"},
    "SUI_USDT": {"display": "SUI/USDT", "coinank": "suiusdt", "tv": "BINANCE:SUIUSDT"},
    "INJ_USDT": {"display": "INJ/USDT", "coinank": "injusdt", "tv": "BINANCE:INJUSDT"},
    "TAO_USDT": {"display": "TAO/USDT", "coinank": "taousdt", "tv": "BINANCE:TAOUSDT"},
    "APT_USDT": {"display": "APT/USDT", "coinank": "aptusdt", "tv": "BINANCE:APTUSDT"}
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
            headers={'Content-Type': 'text/plain;charset=utf-8'},
            timeout=12
        )
        if res.status_code == 200:
            return True, "Başarılı"
        else:
            return False, f"Google Yanıt Kodu: {res.status_code}"
    except Exception as e:
        return False, f"Bağlantı Hatası: {str(e)}"

# --- GELİŞMİŞ İNDİKATÖR, MUM VE SMC HESAPLAMA MOTORU ---
def calculate_advanced_indicators(klines_data, current_price):
    """Her zaman dilimi için mum formasyonu, SMC, POC, CVD ve Momentum hesaplar."""
    if not klines_data or len(klines_data) < 10:
        return "Sıkışma / Akümülasyon ⚖️", "Gövdede Göreceli Mum", "Nötr POC", "Dengeli Delta", "Nötr"

    try:
        closes, highs, lows, opens, volumes = [], [], [], [], []
        for k in klines_data:
            if isinstance(k, dict):
                closes.append(float(k.get('c', 0)))
                highs.append(float(k.get('h', 0)))
                lows.append(float(k.get('l', 0)))
                opens.append(float(k.get('o', 0)))
                volumes.append(float(k.get('v', 0)))
            elif isinstance(k, list):
                closes.append(float(k[2]))
                highs.append(float(k[3]))
                lows.append(float(k[4]))
                opens.append(float(k[5]))
                volumes.append(float(k[1]))

        closes = np.array(closes)
        highs = np.array(highs)
        lows = np.array(lows)
        opens = np.array(opens)
        volumes = np.array(volumes)

        # 1. MUM FORMASYONU TESPİTİ
        last_c, last_o, last_h, last_l = closes[-1], opens[-1], highs[-1], lows[-1]
        prev_c, prev_o = closes[-2], opens[-2]
        body = abs(last_c - last_o)
        rng = last_h - last_l if last_h > last_l else 1e-9

        if last_c > last_o and prev_c < prev_o and last_c > prev_o and body > rng * 0.5:
            candle_pattern = "Boğa Yutan (Bullish Engulfing) 🟢"
        elif last_c < last_o and prev_c > prev_o and last_c < prev_o and body > rng * 0.5:
            candle_pattern = "Ayı Yutan (Bearish Engulfing) 🔴"
        elif (last_h - max(last_c, last_o)) > body * 2:
            candle_pattern = "Yukarı İğne (Upper Rejection / Pinbar) ⚡"
        elif (min(last_c, last_o) - last_l) > body * 2:
            candle_pattern = "Çekiç / Alt İğne (Hammer / Pinbar) 🛡️"
        elif body < rng * 0.15:
            candle_pattern = "Nötr Doji ⚖️"
        else:
            candle_pattern = "Normal Mum Gövdesi"

        # 2. SMC & YAPI ANALİZİ (BOS, CHoCH, FVG, Sweeps)
        high_max = np.max(highs[:-1])
        low_min = np.min(lows[:-1])
        
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

        # 3. VOLUME PROFILE (POC - Point of Control)
        price_min, price_max = np.min(lows), np.max(highs)
        if price_max > price_min:
            bins = np.linspace(price_min, price_max, 10)
            digitized = np.digitize(closes, bins)
            vol_per_bin = [volumes[digitized == i].sum() for i in range(1, len(bins))]
            poc_bin_idx = np.argmax(vol_per_bin)
            poc_price = (bins[poc_bin_idx] + bins[poc_bin_idx + 1]) / 2
            poc_status = f"POC Üstünde Destek (${poc_price:,.2f})" if current_price >= poc_price else f"POC Altında Direnç (${poc_price:,.2f})"
        else:
            poc_status = "Nötr POC"

        # 4. CVD (Cumulative Volume Delta)
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

        # 5. STOKASTİK MOMENTUM OSİLATÖRÜ
        l14, h14 = np.min(lows[-14:]), np.max(highs[-14:])
        if h14 > l14:
            stoch_k = 100 * (closes[-1] - l14) / (h14 - l14)
            if stoch_k >= 80:
                stoch_status = f"Aşırı Alım (%{stoch_k:.0f} 🔴)"
            elif stoch_k <= 20:
                stoch_status = f"Aşırı Satım (%{stoch_k:.0f} 🟢)"
            else:
                stoch_status = f"Nötr (%{stoch_k:.0f})"
        else:
            stoch_status = "Nötr"

        return smc_structure, candle_pattern, poc_status, cvd_status, stoch_status

    except Exception:
        return "Sıkışma / Akümülasyon ⚖️", "Gövdede Göreceli Mum", "Nötr POC", "Dengeli Delta", "Nötr"

# --- MULTI-TIMEFRAME & DERİNLİKLİ MATRİS MOTORU ---
@st.cache_data(ttl=30)
def fetch_multi_timeframe_matrix():
    matrix_data = []
    
    # TÜRKİYE SAATİ (UTC+3) TANIMLAMASI
    trt_tz = timezone(timedelta(hours=3))
    now_str = datetime.datetime.now(trt_tz).strftime("%d.%m.%Y %H:%M")
    
    tf_map = {"15dk": "15m", "1s": "1h", "4s": "4h", "1D": "1d"}
    
    try:
        tickers_url = "https://api.gateio.ws/api/v4/futures/usdt/tickers"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(tickers_url, headers=headers, timeout=10).json()
        ticker_dict = {item['contract']: item for item in res if 'contract' in item}
        
        for gate_symbol, meta in SYMBOLS_MAP.items():
            if gate_symbol in ticker_dict:
                item = ticker_dict[gate_symbol]
                price = float(item.get("last", 0))
                price_change = float(item.get("change_percentage", 0))
                
                total_size_contracts = float(item.get("total_size", 0))
                oi_usd = (total_size_contracts * price) / 1_000_000 # M$
                
                raw_vol = float(item.get("volume_24h_settle", item.get("volume_24h_quote", 0)))
                volume_usd = raw_vol / 1_000_000 # M$
                
                # Her Parite İçin 4 Zaman Dilimi Bağımsız Hesaplanır
                for tf_label, tf_gate in tf_map.items():
                    try:
                        k_url = f"https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract={gate_symbol}&interval={tf_gate}&limit=30"
                        k_res = requests.get(k_url, headers=headers, timeout=5).json()
                        
                        smc, candle, poc, cvd, stoch = calculate_advanced_indicators(k_res, price)
                    except Exception:
                        smc, candle, poc, cvd, stoch = "Sıkışma Bölgesi ⚖️", "Normal Mum", "Nötr POC", "Dengeli Delta", "Nötr"
                    
                    vol_or_contract = f"{total_size_contracts:,.0f} Kontrat" if tf_label in ["15dk", "1s"] else f"${volume_usd:,.1f}M Hacim"

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
                        "Stokastik Momentum": stoch,
                        "Kontrat / Hacim": vol_or_contract,
                        "Açık Pozisyon (OI)": f"${oi_usd:,.1f}M"
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
        df = pd.read_csv(CSV_URL)
        return df
    except Exception:
        return pd.DataFrame()

# ==============================================================================
# ANA SEKMELİ DÜZEN (4 SEKMELİ ELİT YAPI)
# ==============================================================================
tab1, tab4, tab2, tab3 = st.tabs([
    "📊 Crypto Matrix", 
    "📈 Teknik & Göstergeler", 
    "⚡ Haber & Ekonomi Radarı", 
    "🎙️ Analizler & Piyasa Beklentileri"
])

# ==============================================================================
# SEKME 1: CRYPTO MATRIX (Gelişmiş Multi-TF Sheets Motoru)
# ==============================================================================
with tab1:
    st.subheader("📊 Order Flow, Volume Profile & SMC Multi-Timeframe Akıllı Matris")
    
    col_m1, col_m2 = st.columns([1, 4])
    with col_m1:
        if st.button("🔄 Verileri Güncelle & Sheets'e Yaz", key="btn_tech"):
            st.cache_data.clear()
            st.rerun()
            
    with st.spinner("TRT saatiyle mumlar, POC, CVD, Mum Formasyonları ve SMC yapısı hesaplanıyor..."):
        df_matrix = fetch_multi_timeframe_matrix()
        
    if not df_matrix.empty:
        sheets_success, msg = send_to_google_sheets(df_matrix)
        
        if sheets_success:
            st.success("✅ Tüm Sütunlar ve TSİ Saat Bilgisiyle Canlı Matris Google Sheets (`Crypto_Matrix`) Tablosuna Aktarıldı!")
        else:
            st.error(f"⚠️ Sheets Aktarım Hatası: {msg}")
            
        with st.expander("🔍 Canlı Gelişmiş Matrisi İncele / Kontrol Et (Tıklayıp Aç)"):
            st.dataframe(df_matrix, use_container_width=True, hide_index=True)
    else:
        st.warning("Veriler çekilemedi. Lütfen bağlantıyı kontrol edin.")

# ==============================================================================
# SEKME 4: TEKNİK & GÖSTERGELER (GÖRSEL TRADING TERMINALI)
# ==============================================================================
with tab4:
    st.subheader("📈 Görsel Alım-Satım Terminali & Likidasyon Haritası")
    
    # 1. Kripto Varlık Seçim Kutusu
    selected_display = st.selectbox(
        "🎯 Analiz Etmek İstediğiniz Kripto Varlığı Seçin:",
        options=[meta["display"] for meta in SYMBOLS_MAP.values()]
    )
    
    selected_key = [k for k, v in SYMBOLS_MAP.items() if v["display"] == selected_display][0]
    coinank_symbol = SYMBOLS_MAP[selected_key]["coinank"]
    tv_symbol = SYMBOLS_MAP[selected_key]["tv"]
    
    st.markdown("---")
    
    # 2. CoinAnk Liquidation Map
    st.markdown(f"### 💧 {selected_display} Canlı Liquidation Map (CoinAnk)")
    st.caption("Aşağıdaki haritada kaldıraclı pozisyonların yoğunlaştığı likidasyon kümelenmelerini (Stop-Hunt bölgeleri) canlı görebilirsiniz:")
    
    coinank_url = f"https://coinank.com/tr/chart/derivatives/liq-map/binance/{coinank_symbol}/1d"
    components.iframe(coinank_url, height=650, scrolling=True)
    
    st.markdown("---")
    
    # 3. TradingView Profesyonel Grafik Embed
    st.markdown(f"### 📉 {selected_display} Canlı Fiyat & Hacim Grafiği")
    
    tv_widget_code = f"""
    <div class="tradingview-widget-container" style="height:600px;width:100%">
      <div id="tradingview_chart" style="height:calc(100% - 32px);width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
      "autosize": true,
      "symbol": "{tv_symbol}",
      "interval": "60",
      "timezone": "Europe/Istanbul",
      "theme": "dark",
      "style": "1",
      "locale": "tr",
      "toolbar_bg": "#f1f3f6",
      "enable_publishing": false,
      "hide_side_toolbar": false,
      "allow_symbol_change": true,
      "container_id": "tradingview_chart"
    }}
      );
      </script>
    </div>
    """
    components.html(tv_widget_code, height=600)

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
        kategoriler = ["Tümü"] + list(df_news["Kategori (Makro/Kripto)"].dropna().unique())
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
                st.write(f"**Beklenti / Etki:**\n{row.get('Beklenti / Etki', 'Detay Yok')}")
                st.write(f"**Gerçekleşen Sonuç:**\n{row.get('Gerçekleşen Sonuç', 'Detay Yok')}")
                
            st.markdown("---")
    else:
        st.info("Haber akışı henüz yüklenemedi veya Google Sheets boş.")

# ==============================================================================
# SEKME 3: ANALİZLER & PİYASA BEKLENTİLERİ
# ==============================================================================
with tab3:
    st.subheader("🎙️ Günlük Video Analizleri & Makro Hedefler")
    st.info("🛠️ Bu sekmede video özetleri, altın/petrol/borsa hedefleri yer alacak.")
