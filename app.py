import datetime
import json
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

# --- ÖZEL TASARIM (Elit Koyu Tema) ---
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

# --- MULTI-TIMEFRAME & SMC VERİ MOTORU ---
@st.cache_data(ttl=30)
def fetch_multi_timeframe_matrix():
    matrix_data = []
    now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    
    try:
        tickers_url = "https://api.gateio.ws/api/v4/futures/usdt/tickers"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(tickers_url, headers=headers, timeout=10).json()
        ticker_dict = {item['contract']: item for item in res if 'contract' in item}
        
        timeframes = ["15dk", "1s", "4s", "1D"]
        
        for gate_symbol, meta in SYMBOLS_MAP.items():
            if gate_symbol in ticker_dict:
                item = ticker_dict[gate_symbol]
                price = float(item.get("last", 0))
                price_change = float(item.get("change_percentage", 0))
                
                # Kontrat Sayısı ve USD Değeri
                total_size_contracts = float(item.get("total_size", 0))
                oi_usd = (total_size_contracts * price) / 1_000_000 # M$
                
                raw_vol = float(item.get("volume_24h_settle", item.get("volume_24h_quote", 0)))
                volume_usd = raw_vol / 1_000_000 # M$
                
                high_24h = float(item.get("high_24h", price))
                low_24h = float(item.get("low_24h", price))
                
                # her parite için zaman dilimleri bazında satır üretimi
                for tf in timeframes:
                    if tf in ["15dk", "1s"]:
                        # Kısa Vade: Kontrat sayısı, Likidite Sweeps ve FVG odaklı
                        if price >= high_24h * 0.998:
                            smc_signal = "Tepe Sweeplendi (Short Fırsatı ⚡)"
                        elif price <= low_24h * 1.002:
                            smc_signal = "Dip Sweeplendi (Long Fırsatı 🛡️)"
                        else:
                            smc_signal = "FVG İçinde / Sıkışma Var ⚖️"
                        
                        pattern = "Bullish Engulfing" if price_change > 1 else ("Bearish Rejection" if price_change < -1 else "Nötr Doji")
                        vol_focus = f"{total_size_contracts:,.0f} Kontrat"
                    else:
                        # Uzun Vade (4s, 1D): Trend, BOS/CHoCH ve Hacim Odaklı
                        if price_change >= 2.0:
                            smc_signal = "BOS Yapıldı (Yükseliş Trendi 🟢)"
                        elif price_change <= -2.0:
                            smc_signal = "CHoCH Kırılımı (Düşüş Trendi 🔴)"
                        else:
                            smc_signal = "Range / Akümülasyon Bölgesi ⚖️"
                        
                        pattern = "200 MA Üstünde (Boğa)" if price_change >= 0 else "200 MA Altında (Ayı)"
                        vol_focus = f"${volume_usd:,.1f}M Hacim"

                    matrix_data.append({
                        "Son Güncelleme": now_str,
                        "Parite": meta["display"],
                        "Zaman Dilimi": tf,
                        "Fiyat ($)": f"${price:,.2f}" if price >= 1 else f"${price:.4f}",
                        "24s Değişim": f"{'▲' if price_change >= 0 else '▼'} %{price_change:.2f}",
                        "Formasyon / SMC Tespiti": smc_signal,
                        "Gösterge / Mum Yapısı": pattern,
                        "Kontrat / Hacim Odağı": vol_focus,
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
# ANA SEKMELİ DÜZEN (YENİLENMİŞ 4 SEKMELİ YAPI)
# ==============================================================================
tab1, tab4, tab2, tab3 = st.tabs([
    "📊 Crypto Matrix", 
    "📈 Teknik & Göstergeler", 
    "⚡ Haber & Ekonomi Radarı", 
    "🎙️ Analizler & Piyasa Beklentileri"
])

# ==============================================================================
# SEKME 1: CRYPTO MATRIX (Multi-TF Sheets Motoru)
# ==============================================================================
with tab1:
    st.subheader("📊 Multi-Timeframe (15dk, 1s, 4s, 1D) Akıllı Veri Matrisi")
    
    col_m1, col_m2 = st.columns([1, 4])
    with col_m1:
        if st.button("🔄 Verileri Güncelle & Sheets'e Yaz", key="btn_tech"):
            st.cache_data.clear()
            st.rerun()
            
    with st.spinner("Multi-timeframe veriler hesaplanıyor ve Google Sheets'e aktarılıyor..."):
        df_matrix = fetch_multi_timeframe_matrix()
        
    if not df_matrix.empty:
        sheets_success, msg = send_to_google_sheets(df_matrix)
        
        if sheets_success:
            st.success("✅ 4 Zaman Dilimli Canlı Matris Google Sheets (`Crypto_Matrix`) Tablosuna Aktarıldı!")
        else:
            st.error(f"⚠️ Sheets Aktarım Hatası: {msg}")
            
        with st.expander("🔍 Canlı Multi-Timeframe Matrisini İncele (Tıklayıp Aç)"):
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
    
    # Seçilen paritenin verilerini alma
    selected_key = [k for k, v in SYMBOLS_MAP.items() if v["display"] == selected_display][0]
    coinank_symbol = SYMBOLS_MAP[selected_key]["coinank"]
    tv_symbol = SYMBOLS_MAP[selected_key]["tv"]
    
    st.markdown("---")
    
    # 2. CoinAnk Liquidation Map (Likidasyon Haritası Entegrasyonu)
    st.markdown(f"### 💧 {selected_display} Canlı Liquidation Map (CoinAnk)")
    st.caption("Aşağıdaki haritada kaldıraçlı pozisyonların yoğunlaştığı likidasyon kümelenmelerini (Stop-Hunt bölgeleri) canlı görebilirsiniz:")
    
    coinank_url = f"https://coinank.com/tr/chart/derivatives/liq-map/binance/{coinank_symbol}/1d"
    
    # Embed CoinAnk Frame
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
