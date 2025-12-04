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

# 1. Varsayılan Gemini Anahtarı (Kod içinde gömülü - Test için)
default_gemini_key = "AIzaSyD-HpfQU8NwKM9PmzucKbNtVXoYwccIBUQ"

# 2. Secrets Kontrolü (Sunucu ortamı için)
api_key_from_secrets = None
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key_from_secrets = st.secrets["GOOGLE_API_KEY"]
except FileNotFoundError:
    # Lokal çalışmada secrets dosyası yoksa hata vermemesi için
    pass

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
    Hata durumunda 404 almamak için API'den mevcut modelleri sorgular ve
    çalışan en uygun modeli dinamik olarak seçer.
    """
    if not api_key:
        return "⚠️ Hata: API Anahtarı girilmedi. Lütfen sol menüden anahtarınızı girin."

    try:
        genai.configure(api_key=api_key)
        
        # 1. ADIM: Mevcut Modelleri Listele
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
        except Exception as e:
            return f"Model listesi alınamadı (API Key hatalı olabilir): {str(e)}"

        # 2. ADIM: İstenen Moda Göre En İyi Modeli Seç
        target_model = None
        
        def find_best_match(keywords):
            for m in available_models:
                for k in keywords:
                    if k in m.lower():
                        return m
            return None

        if mode == "thinking":
            target_model = find_best_match(['thinking', 'pro', '1.5'])
            # GÜNCELLEME: Prompt artık netlik ve kısalık üzerine kurulu
            system_instruction = f"Sen '{persona}' rolünde bir uzmansın. Analizini derin yap ama cevabını SADECE SONUÇ ODAKLI, ÇOK KISA ve MADDELER halinde ver. Lafı uzatma. Kanıt yoksa 'Güvenli' deme."
        else:
            target_model = find_best_match(['flash', '1.5', 'pro'])
            system_instruction = f"Sen '{persona}' rolünde çok kısa ve net cevap veren bir asistansın. Gereksiz detay verme."

        if not target_model and available_models:
            target_model = available_models[0]
            
        if not target_model:
            return "⚠️ Hata: Hesabınızda kullanılabilir hiç model bulunamadı (API Key veya Bölge sorunu)."

        # 3. ADIM: Seçilen Model ile Üret
        try:
            if image:
                is_modern_multimodal = '1.5' in target_model or '2.0' in target_model
                is_legacy_vision = 'vision' in target_model
                
                if not (is_modern_multimodal or is_legacy_vision):
                     vision_model = find_best_match(['vision', '1.5', 'flash'])
                     if vision_model:
                         target_model = vision_model

            model = genai.GenerativeModel(target_model)
            
            full_prompt = f"{system_instruction}\n\nANALİZ EDİLECEK DURUM: {prompt}\n\nLütfen Türkçe cevap ver."
            
            # Tutarlılık için sıcaklığı (temperature) düşürüyoruz
            generation_config = genai.GenerationConfig(temperature=0.3)
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

            if image:
                response = model.generate_content([full_prompt, image], safety_settings=safety_settings, generation_config=generation_config)
            else:
                response = model.generate_content(full_prompt, safety_settings=safety_settings, generation_config=generation_config)
            
            return response.text
            
        except Exception as e:
            return f"Model Hatası ({target_model}): {str(e)}"

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
    st.info(f"Aktif Model: **Otomatik Seçim ({selected_mode})**")
    
    st.divider()
    
    # --- API ANAHTARI GİRİŞ ALANI ---
    active_api_key = None
    
    if api_key_from_secrets:
        st.success("✅ API Anahtarı (Sistem Kayıtlı)")
        active_api_key = api_key_from_secrets
    else:
        st.warning("⚠️ AI Analizi için Anahtar Gerekli")
        user_key = st.text_input("Google API Key", value=default_gemini_key, type="password")
        
        if user_key:
            active_api_key = user_key
            st.success("Anahtar aktif!")
        else:
            st.markdown("[👉 Ücretsiz API Anahtarı Almak İçin Tıkla](https://aistudio.google.com/app/apikey)")

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
            if active_api_key:
                # 1. KONSEY BAŞKANI SKORU
                with st.spinner("Konsey Başkanı hesaplıyor..."):
                    score_prompt = f"""
                    Sen Motosiklet Güvenlik Konseyi Başkanısın.
                    Ürün: {brand} {model}
                    Bu ürünün EN 13594 sertifikası gerçek mi?
                    Cevabı SADECE şu formatta ver, başka bir şey yazma:
                    **Güvenilirlik Skoru:** %XX
                    **Kısa Karar:** (Tek cümle)
                    """
                    score_resp = ask_gemini(active_api_key, "Konsey Başkanı", score_prompt, mode=selected_mode)
                
                st.info(f"📊 **Başkanın Kararı:**\n\n{score_resp}")

                # 2. DETAYLI KONSEY GÖRÜŞLERİ
                st.subheader(f"🧠 {ai_mode.split(' ')[2]} Hafıza Konseyi Detayları")
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.info("📜 **Mevzuat Uzmanı**")
                    with st.spinner("Yasal kayıtlar..."):
                        prompt_1 = f"""'{brand} {model}' EN 13594 sertifikalı mı? Kesin kanıt var mı? Tek cümleyle cevapla."""
                        resp = ask_gemini(active_api_key, "Sertifikasyon Denetçisi", prompt_1, mode=selected_mode)
                        st.write(resp)

                with c2:
                    st.warning("🛠️ **Malzeme Mühendisi**")
                    with st.spinner("Yapısal analiz..."):
                        prompt_2 = f"""'{brand} {model}' malzeme ve koruma kalitesi nasıl? Güvenli mi? Tek cümleyle özetle."""
                        resp = ask_gemini(active_api_key, "Tekstil Mühendisi", prompt_2, mode=selected_mode)
                        st.write(resp)

                with c3:
                    st.error("🕵️ **Şüpheci Dedektif**")
                    with st.spinner("Risk analizi..."):
                        prompt_3 = f"""'{brand} {model}' hakkında sahtecilik veya dayanıklılık şikayeti var mı? Tek cümleyle uyar."""
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

            # 2. Forumlar (GÜNCELLENDİ: Daha geniş arama)
            st.write("---")
            st.markdown("### 2. 🗣️ Kullanıcı Yorumları ve Forumlar")
            # Eski dar arama yerine genel arama yapıyoruz
            forum_query = f'{full_name} motosiklet eldiveni yorum şikayet forum'
            results_forum, _ = search_ddg(forum_query, max_res=4)
            
            if results_forum:
                for res in results_forum:
                    # Başlık veya linkte 'forum', 'şikayet', 'yorum' geçiyorsa göster
                    if any(x in res.get('href', '') for x in ['forum', 'sikayet', 'eksi', 'donanimhaber', 'technopat', 'reddit']):
                        st.info(f"🗨️ **Tartışma Bulundu:** [{res.get('title')}]({res.get('href')})")
                    else:
                        st.caption(f"Genel Sonuç: [{res.get('title')}]({res.get('href')})")
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
            
            # --- GÖRSEL KONSEY BAŞKANI (YENİ EKLENDİ) ---
            st.divider()
            with st.spinner("Konsey Başkanı görseli inceliyor..."):
                score_prompt_img = """
                Bu eldiven görselini analiz et.
                EN 13594 etiketi var mı? Dikişler ve korumalar kaliteli mi?
                Cevabı SADECE şu formatta ver:
                **Görsel Güvenilirlik Skoru:** %XX
                **Kısa Karar:** (Tek cümle)
                """
                score_resp_img = ask_gemini(active_api_key, "Konsey Başkanı", score_prompt_img, img, mode=selected_mode)
            
            st.info(f"📊 **Başkanın Görsel Kararı:**\n\n{score_resp_img}")
            
            st.divider()
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 📜 Mevzuatçı")
                with st.spinner("Etiket okunuyor..."):
                    prompt_img_1 = """Etikette EN 13594, CE, KP var mı? Yoksa neden yok? Tek cümleyle özetle."""
                    resp = ask_gemini(active_api_key, "Gümrük Denetçisi", prompt_img_1, img, mode=selected_mode)
                    st.info(resp)
            
            with col2:
                st.markdown("### 🛠️ Mühendis")
                with st.spinner("Malzeme inceleniyor..."):
                    prompt_img_2 = """Malzeme (deri/file) ve dikişler kaza için güvenli mi? Tek cümleyle teknik yorum yap."""
                    resp = ask_gemini(active_api_key, "Güvenlik Ekipmanı Mühendisi", prompt_img_2, img, mode=selected_mode)
                st.warning(resp)
            
            with col3:
                st.markdown("### 🕵️ Dedektif")
                with st.spinner("Risk analizi..."):
                    prompt_img_3 = """Bu ürün orijinal mi yoksa replika mı duruyor? Şüpheli bir durum var mı? Tek cümleyle uyar."""
                    resp = ask_gemini(active_api_key, "Sahte Ürün Uzmanı", prompt_img_3, img, mode=selected_mode)
                st.error(resp)
            
            st.success("✅ **Konsey Kararı:** Üç görüşü okuyarak nihai kararınızı verin.")
