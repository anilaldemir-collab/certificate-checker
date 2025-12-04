import streamlit as st
from duckduckgo_search import DDGS
from PIL import Image
import google.generativeai as genai
import time
import urllib.parse
import random

# -----------------------------------------------------------------------------
# AYARLAR
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Eldiven Dedektifi (Thinking AI)", page_icon="🏍️", layout="wide")

# Varsayılan Gemini Anahtarı (Kod içinde gömülü)
default_gemini_key = "AIzaSyD-HpfQU8NwKM9PmzucKbNtVXoYwccIBUQ"

# -----------------------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# -----------------------------------------------------------------------------
def create_google_link(query):
    encoded_query = urllib.parse.quote(query)
    return f"https://www.google.com/search?q={encoded_query}"

@st.cache_data(show_spinner=False)
def search_ddg(query, max_res=3):
    backends = ['api', 'html', 'lite'] 
    for backend in backends:
        try:
            time.sleep(random.uniform(0.3, 1.0))
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_res, backend=backend))
                if results: return results, None
        except: continue
    return [], ["Bağlantı hatası"]

# --- GELİŞMİŞ GOOGLE GEMINI FONKSİYONU ---
def ask_gemini(api_key, persona, prompt, image=None, mode="flash"):
    """
    mode: 'flash' (Hızlı) veya 'thinking' (Akıl Yürütme)
    """
    if not api_key:
        return "⚠️ Hata: API Anahtarı girilmedi. Lütfen sol menüden anahtarınızı girin."

    try:
        genai.configure(api_key=api_key)
        
        # Model Seçim Mantığı
        if mode == "thinking":
            # Düşünen/Güçlü modeller listesi
            models_to_try = [
                'gemini-2.0-flash-thinking-exp-01-21',
                'gemini-2.0-flash-thinking-exp',       
                'gemini-1.5-pro-latest',
                'gemini-1.5-pro',
                'gemini-1.5-pro-001'
            ]
            system_instruction = f"Sen '{persona}' rolünde, adım adım düşünen (Chain of Thought) ve detaylı analiz yapan bir uzmansın. Cevap vermeden önce tüm olasılıkları değerlendir."
        else:
            # Hızlı modeller listesi
            models_to_try = [
                'gemini-1.5-flash', 
                'gemini-1.5-flash-latest',
                'gemini-1.5-flash-001'
            ]
            system_instruction = f"Sen '{persona}' rolünde hızlı ve net cevap veren bir asistansın."

        full_prompt = f"{system_instruction}\n\nANALİZ EDİLECEK DURUM: {prompt}\n\nLütfen Türkçe cevap ver."
        
        last_err = ""
        
        for m_name in models_to_try:
            try:
                model = genai.GenerativeModel(m_name)
                
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]

                if image:
                    response = model.generate_content([full_prompt, image], safety_settings=safety_settings)
                else:
                    response = model.generate_content(full_prompt, safety_settings=safety_settings)
                
                return response.text
            except Exception as e:
                last_err = str(e)
                continue
                
        if mode == "thinking":
            return f"⚠️ Düşünen modeller yoğun, Hızlı Mod deneniyor...\n\n" + ask_gemini(api_key, persona, prompt, image, mode="flash")
            
        return f"Yapay Zeka Bağlantı Hatası: {last_err}"

    except Exception as e:
        return f"Kritik Hata: {str(e)}"

# -----------------------------------------------------------------------------
# KENAR ÇUBUĞU (AYARLAR)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("🧠 Zeka Ayarları")
    
    # Model Seçimi
    ai_mode = st.radio(
        "Analiz Modu Seçin:", 
        ["⚡ Hızlı Mod (Flash)", "🧠 Derin Düşünen Mod (Thinking)"],
        help="Hızlı Mod anlık cevap verir. Derin Düşünen Mod, Gemini Pro veya Thinking modellerini kullanarak daha detaylı analiz yapar."
    )
    
    selected_mode = "flash" if "Flash" in ai_mode else "thinking"
    st.info(f"Aktif Model: **Google Gemini {selected_mode.capitalize()}**")
    
    st.divider()
    
    # --- API ANAHTARI GİRİŞ ALANI ---
    active_api_key = None
    
    if api_key_from_secrets:
        st.success("✅ API Anahtarı (Sistem Kayıtlı)")
        active_api_key = api_key_from_secrets
    else:
        st.warning("⚠️ AI Analizi için Anahtar Gerekli")
        user_key = st.text_input("Google API Key", type="password", placeholder="Anahtarınızı buraya yapıştırın")
        if user_key:
            active_api_key = user_key
            st.success("Anahtar tanımlandı!")
        else:
            # Eğer kullanıcı girmezse varsayılan gömülü anahtarı kullan (Test için)
            active_api_key = default_gemini_key
            st.info("Otomatik test anahtarı kullanılıyor.")

    st.divider()
    st.markdown("### 🔗 Hızlı Linkler")
    st.link_button("🇹🇷 Trendyol", "https://www.trendyol.com/")
    st.link_button("🌏 AliExpress", "https://www.aliexpress.com/")

# -----------------------------------------------------------------------------
# ARAYÜZ BAŞLIĞI
# -----------------------------------------------------------------------------
st.title(f"⚖️ Eldiven Dedektifi: {ai_mode.split('(')[0]}")
st.markdown(f"**{ai_mode}** kullanılarak güvenlik analizi yapılıyor.")

tab1, tab2 = st.tabs(["🔍 İnternet Taraması", "📷 Fotoğraf Analizi (Konsey Modu)"])

# =============================================================================
# TAB 1: İNTERNET TARAMASI
# =============================================================================
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        brand = st.text_input("Marka", placeholder="Örn: Scoyco")
    with col2:
        model = st.text_input("Model", placeholder="Örn: MC29")
    
    if st.button("🔍 Analiz Et", type="primary"):
        if not brand or not model:
            st.error("Marka ve Model giriniz.")
        else:
            full_name = f"{brand} {model}"
            
            # --- AI KONSEYİ: HAFIZA SORGUSU ---
            st.subheader(f"🧠 {ai_mode.split(' ')[2]} Hafıza Konseyi")
            if active_api_key:
                st.caption("Google'ın devasa veri bankası sorgulanıyor...")
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.info("📜 **Mevzuat Uzmanı**")
                    with st.spinner("Yasal kayıtlar taranıyor..."):
                        # Üç tırnak kullanarak string hatasını önledik
                        prompt_1 = f"""'{brand} {model}' eldiveni yasal olarak EN 13594 sertifikasına sahip bilinen bir model mi? Kesin kanıt var mı?"""
                        resp = ask_gemini(active_api_key, "Sertifikasyon Denetçisi", prompt_1, mode=selected_mode)
                        st.write(resp)

                with c2:
                    st.warning("🛠️ **Malzeme Mühendisi**")
                    with st.spinner("Yapısal analiz yapılıyor..."):
                        # Üç tırnak kullanımı
                        prompt_2 = f"""'{brand} {model}' eldiveninin malzeme kalitesi ve koruma yapısı (yumruk, avuç içi) teknik olarak yeterli biliniyor mu?"""
                        resp = ask_gemini(active_api_key, "Tekstil Mühendisi", prompt_2, mode=selected_mode)
                        st.write(resp)

                with c3:
                    st.error("🕵️ **Şüpheci Dedektif**")
                    with st.spinner("Risk analizi yapılıyor..."):
                        # Üç tırnak kullanımı
                        prompt_3 = f"""'{brand} {model}' hakkında 'çabuk yırtıldı', 'sahte sertifika' gibi şikayetler veya şaibeler var mı? Dürüst ve eleştirel ol."""
                        resp = ask_gemini(active_api_key, "Şüpheci Tüketici Hakları Uzmanı", prompt_3, mode=selected_mode)
                        st.write(resp)
            else:
                st.warning("AI Hafıza sorgusu için lütfen sol menüden API Anahtarı giriniz.")
            
            st.divider()
            
            # --- KLASİK ARAMA ---
            status_container = st.status("🕵️ İnternet Taranıyor (DuckDuckGo)...", expanded=True)
            
            # 1. PDF Belge
            st.markdown("### 1. 📄 Resmi Belge Kontrolü")
            auto_query = f"{brand} {model} certificate EN 13594 filetype:pdf"
            results_auto, _ = search_ddg(auto_query, max_res=3)
            
            if results_auto:
                for res in results_auto:
                    st.success(f"✅ **Belge Bulundu:** [{res.get('title')}]({res.get('href')})")
            else:
                st.warning("⚠️ Otomatik PDF bulunamadı.")
                st.link_button("👉 Manuel PDF Ara", create_google_link(auto_query))

            # 2. Forumlar
            st.write("---")
            st.markdown("### 2. 🗣️ Kullanıcı Yorumları")
            forum_query = f'site:motosiklet.net OR site:technopat.net OR site:facebook.com "{full_name}" koruma'
            results_forum, _ = search_ddg(forum_query, max_res=3)
            
            if results_forum:
                for res in results_forum:
                    st.info(f"🗨️ **Konu:** [{res.get('title')}]({res.get('href')})")
            else:
                st.caption("Forum tartışması bulunamadı.")

            status_container.update(label="Tarama Tamamlandı", state="complete", expanded=False)

# =============================================================================
# TAB 2: FOTOĞRAF ANALİZİ
# =============================================================================
with tab2:
    if not active_api_key:
        st.warning("⚠️ Konsey Modu için API Anahtarı şarttır. Lütfen sol menüden giriniz.")
    else:
        st.success(f"✅ Hazır: **{ai_mode}** kullanılarak görsel analiz edilecek.")
        uploaded_file = st.file_uploader("Eldiven Etiketini Yükle", type=["jpg", "png", "jpeg"])

        if uploaded_file and st.button("🤖 Konseyi Topla ve Analiz Et"):
            img = Image.open(uploaded_file)
            
            st.divider()
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 📜 Mevzuatçı")
                with st.spinner("Etiket kodları okunuyor..."):
                    # Üç tırnak kullanımı
                    prompt_img_1 = """Bu etiketteki EN 13594, CE, Level 1/2, KP, CAT II gibi ibareleri kontrol et. Eksik veya sahte duran bir kod var mı?"""
                    resp = ask_gemini(active_api_key, "Gümrük Denetçisi", prompt_img_1, img, mode=selected_mode)
                    st.info(resp)
            
            with col2:
                st.markdown("### 🛠️ Mühendis")
                with st.spinner("Dikiş ve malzeme inceleniyor..."):
                    # Üç tırnak kullanımı
                    prompt_img_2 = """Fotoğraftaki ürünün dikiş kalitesi, malzeme türü (deri/file) ve koruma parçalarının yerleşimi güvenli mi? Kaza anında dağılır mı?"""
                    resp = ask_gemini(active_api_key, "Güvenlik Ekipmanı Mühendisi", prompt_img_2, img, mode=selected_mode)
                st.warning(resp)
            
            with col3:
                st.markdown("### 🕵️ Dedektif")
                with st.spinner("Piyasa araştırması..."):
                    # Üç tırnak kullanımı
                    prompt_img_3 = """Bu etiketin yazı tipi, baskı kalitesi veya duruşunda 'replika' veya 'ucuz Çin malı' hissi veren bir detay var mı? Güvenmeli miyiz?"""
                    resp = ask_gemini(active_api_key, "Sahte Ürün Uzmanı", prompt_img_3, img, mode=selected_mode)
                st.error(resp)
            
            st.success("✅ **Konsey Kararı:** Üç görüşü okuyarak nihai kararınızı verin.")
