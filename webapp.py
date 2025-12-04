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
st.set_page_config(page_title="Eldiven Dedektifi (Lens Modu)", page_icon="🏍️", layout="wide")

# 1. Varsayılan Gemini Anahtarı (Kod içinde gömülü - Test için)
default_gemini_key = "AIzaSyD-HpfQU8NwKM9PmzucKbNtVXoYwccIBUQ"

# 2. Secrets Kontrolü (Sunucu ortamı için)
api_key_from_secrets = None
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key_from_secrets = st.secrets["GOOGLE_API_KEY"]
except FileNotFoundError:
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
def ask_gemini(api_key, persona, prompt, images=None, mode="flash"):
    """
    mode: 'flash' veya 'thinking'
    images: Tek bir PIL Image nesnesi veya PIL Image listesi olabilir.
    """
    if not api_key:
        return "⚠️ Hata: API Anahtarı girilmedi."

    try:
        genai.configure(api_key=api_key)
        
        # Model Seçim Mantığı
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
        except: pass

        target_model = None
        def find_best_match(keywords):
            for m in available_models:
                for k in keywords:
                    if k in m.lower(): return m
            return None

        if mode == "thinking":
            target_model = find_best_match(['thinking', 'pro', '1.5'])
            system_instruction = f"Sen '{persona}' rolünde, çoklu bakış açısıyla analiz yapan tek bir otoritesin. Cevapların kendi içinde tutarlı olmalı."
        else:
            target_model = find_best_match(['flash', '1.5', 'pro'])
            system_instruction = f"Sen '{persona}' rolünde hızlı ve net cevap veren bir asistansın."

        if not target_model and available_models:
            target_model = available_models[0]

        # İçerik Hazırlama (Metin + Görseller)
        full_prompt = f"{system_instruction}\n\n{prompt}\n\nLütfen Türkçe cevap ver."
        
        content_parts = [full_prompt]
        
        if images:
            if isinstance(images, list):
                content_parts.extend(images)
            else:
                content_parts.append(images)

            if '1.5' not in target_model and '2.0' not in target_model and 'vision' not in target_model:
                 vision_model = find_best_match(['vision', '1.5', 'flash'])
                 if vision_model: target_model = vision_model

        try:
            model = genai.GenerativeModel(target_model)
            safety = [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                      {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
            
            response = model.generate_content(content_parts, safety_settings=safety)
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
    ai_mode = st.radio("Analiz Modu:", ["⚡ Hızlı Mod (Flash)", "🧠 Derin Düşünen Mod (Thinking)"])
    selected_mode = "flash" if "Flash" in ai_mode else "thinking"
    st.info(f"Aktif Model: **Otomatik ({selected_mode})**")
    
    st.divider()
    
    active_api_key = None
    if api_key_from_secrets:
        st.success("✅ API Anahtarı (Sistem)")
        active_api_key = api_key_from_secrets
    else:
        st.warning("⚠️ Manuel Anahtar Girişi")
        user_key = st.text_input("Google API Key", value=default_gemini_key, type="password")
        if user_key:
            active_api_key = user_key
            st.success("Aktif")
        else:
            st.markdown("[👉 Key Al](https://aistudio.google.com/app/apikey)")

    st.divider()
    st.markdown("### 🔗 Linkler")
    st.link_button("🇹🇷 Trendyol", "https://www.trendyol.com/")
    st.link_button("🌏 AliExpress", "https://www.aliexpress.com/")

# -----------------------------------------------------------------------------
# ARAYÜZ BAŞLIĞI
# -----------------------------------------------------------------------------
st.title(f"⚖️ Eldiven Dedektifi: {ai_mode.split('(')[0]}")
st.markdown("""
**Sertifika Kriteri:** Bu araç, eldivenlerde **EN 13594 Sertifikası** VEYA **CE Belgesi (Uygunluk İşareti)** arar. 
İkisinden biri varsa ürün güvenlik açısından **uygun** kabul edilir.
""")

tab1, tab2 = st.tabs(["🔍 İnternet Taraması", "📷 Lens Modu (Fotoğraftan Tanı & Bul)"])

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
            
            # --- AI KONSEYİ: TEK OTURUM (Tutarlılık İçin) ---
            if active_api_key:
                st.subheader(f"🧠 {ai_mode.split(' ')[2]} Hafıza Konseyi")
                st.caption("Veriler tek bir oturumda, tutarlı bir şekilde analiz ediliyor...")
                
                with st.spinner("Konsey toplanıyor ve ortak karar veriyor..."):
                    council_prompt = f"""
                    Sen Motosiklet Güvenlik Konseyisin. Ürün: '{brand} {model}'
                    
                    Aşağıdaki 4 farklı rolü AYNI ANDA canlandır ve birbirinizle TUTARLI cevaplar verin.
                    
                    KRİTİK KURAL (BAŞKAN İÇİN):
                    Eğer bu ürünün 'EN 13594' sertifikası VEYA 'CE Belgesi' olduğuna dair kesin bir bilgin/kaydın YOKSA, Güvenilirlik Skoru'nu KESİNLİKLE %0 VER.
                    "Malzemesi iyi görünüyor" diye puan verme. Belge yoksa Puan = 0.
                    
                    1. KONSEY BAŞKANI: Genel güven skoru (%0-100) ve tek cümlelik nihai karar.
                    2. MEVZUAT UZMANI: EN 13594 sertifikası VEYA CE belgesi var mı? (Bilgi yoksa 'Veri yok' de).
                    3. MALZEME MÜHENDİSİ: Malzeme koruması yeterli mi?
                    4. ŞÜPHECİ DEDEKTİF: Sahtecilik riski veya kronik sorun var mı?
                    
                    Lütfen cevabı TAM OLARAK aşağıdaki formatta ve başlıklarla ver (Başlıkları değiştirme):
                    
                    [BAŞKAN]
                    **Sertifika Güvenilirlik Skoru:** %XX
                    **Kısa Karar:** ...
                    
                    [MEVZUAT]
                    ...
                    
                    [MÜHENDİS]
                    ...
                    
                    [DEDEKTİF]
                    ...
                    """
                    
                    full_response = ask_gemini(active_api_key, "Motosiklet Güvenlik Konseyi", council_prompt, mode=selected_mode)
                    
                    try:
                        parts = full_response.split('[')
                        p_baskan, p_mevzuat, p_muhendis, p_dedektif = "Veri Yok", "Veri Yok", "Veri Yok", "Veri Yok"
                        
                        for p in parts:
                            if p.startswith("BAŞKAN]"): p_baskan = p.replace("BAŞKAN]", "").strip()
                            elif p.startswith("MEVZUAT]"): p_mevzuat = p.replace("MEVZUAT]", "").strip()
                            elif p.startswith("MÜHENDİS]"): p_muhendis = p.replace("MÜHENDİS]", "").strip()
                            elif p.startswith("DEDEKTİF]"): p_dedektif = p.replace("DEDEKTİF]", "").strip()
                        
                        score_color = "red"
                        if "%0" in p_baskan or " 0" in p_baskan:
                            st.error(f"📊 **Konsey Ortak Kararı:**\n\n{p_baskan}")
                        else:
                            st.info(f"📊 **Konsey Ortak Kararı:**\n\n{p_baskan}")
                        
                        c1, c2, c3 = st.columns(3)
                        with c1: st.info(f"📜 **Mevzuat Uzmanı**\n\n{p_mevzuat}")
                        with c2: st.warning(f"🛠️ **Malzeme Mühendisi**\n\n{p_muhendis}")
                        with c3: st.error(f"🕵️ **Şüpheci Dedektif**\n\n{p_dedektif}")
                            
                    except:
                        st.warning("Format ayrıştırma hatası, ham metin gösteriliyor:")
                        st.write(full_response)
            else:
                st.warning("AI Hafıza sorgusu için anahtar gerekli.")
            
            st.divider()
            
            # --- KLASİK ARAMA ---
            status_container = st.status("🕵️ İnternet Taranıyor...", expanded=True)
            
            # 1. PDF Belge
            st.markdown("### 1. 📄 Resmi Belge (EN 13594 veya CE)")
            auto_query = f"{brand} {model} certificate EN 13594 OR CE Declaration of Conformity filetype:pdf"
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
            forum_query = f'{full_name} motosiklet eldiveni yorum şikayet forum'
            results_forum, _ = search_ddg(forum_query, max_res=4)
            
            if results_forum:
                for res in results_forum:
                    if any(x in res.get('href', '') for x in ['forum', 'sikayet', 'eksi', 'donanimhaber', 'technopat', 'reddit']):
                        st.info(f"🗨️ **Tartışma:** [{res.get('title')}]({res.get('href')})")
                    else:
                        st.caption(f"Sonuç: [{res.get('title')}]({res.get('href')})")
            else:
                st.caption("Forum sonucu yok.")

            status_container.update(label="Tarama Tamamlandı", state="complete", expanded=False)

# =============================================================================
# TAB 2: FOTOĞRAF ANALİZİ (LENS MODU: TANI -> ARA -> ANALİZ ET)
# =============================================================================
with tab2:
    if not active_api_key:
        st.warning("⚠️ Konsey Modu için API Anahtarı şarttır.")
    else:
        st.success("✅ **Lens Modu Hazır:** Etiket olmasa bile ürünü tanıyıp araştırabilirim.")
        
        st.info("""
        📸 **ÖNERİLEN FOTOĞRAFLAR (En az 3 adet yüklemeniz önerilir):**
        1. **Eldivenin Dış Yüzü:** Modeli ve markayı tanımak için.
        2. **Avuç İçi:** Sürtünme bölgelerini ve dikişleri görmek için.
        3. **İç Etiket:** Varsa sertifika kodunu okumak için.
        """)
        
        # State Yönetimi
        if "lens_step" not in st.session_state: st.session_state.lens_step = 1
        if "lens_ai_guess" not in st.session_state: st.session_state.lens_ai_guess = ""
        
        uploaded_files = st.file_uploader("Fotoğrafları Yükle (Çoklu Seçim)", 
                                          type=["jpg", "png", "jpeg", "webp"], 
                                          accept_multiple_files=True)

        # -------------------------------------------
        # ADIM 1: TANI VE TAHMİN ET
        # -------------------------------------------
        if uploaded_files and st.session_state.lens_step == 1:
            if st.button("🔍 Görseli Tara ve Tahmin Et"):
                image_list = [Image.open(f) for f in uploaded_files]
                
                with st.spinner("AI görsellerden model tahmini yapıyor..."):
                    identify_prompt = """
                    Bu fotoğraflardaki motosiklet eldiveninin MARKA ve MODELİNİ tespit et.
                    Logoları oku, tasarım çizgilerini incele.
                    
                    Cevabı SADECE marka ve model ismi olarak ver. (Örn: Revit Sand 4)
                    Eğer emin değilsen 'Bilinmeyen Marka' yaz.
                    """
                    prediction = ask_gemini(active_api_key, "Ürün Tanıma Uzmanı", identify_prompt, image_list, mode="flash").strip()
                    
                    st.session_state.lens_ai_guess = prediction.replace("Marka ve Model:", "").strip()
                    st.session_state.lens_step = 2
                    st.rerun()

        # -------------------------------------------
        # ADIM 2: KULLANICI DOĞRULAMASI
        # -------------------------------------------
        if st.session_state.lens_step == 2:
            st.image([Image.open(f) for f in uploaded_files], width=120, caption="Yüklenenler")
            
            st.divider()
            st.subheader("📝 Model Doğrulama")
            
            col_check1, col_check2 = st.columns([2, 1])
            with col_check1:
                st.info(f"Yapay zeka bu ürünün **{st.session_state.lens_ai_guess}** olduğunu düşünüyor.")
                google_img_link = create_google_images_link(st.session_state.lens_ai_guess)
                st.markdown(f"[🖼️ Google Görseller'de '{st.session_state.lens_ai_guess}' Ara]({google_img_link})")

            with col_check2:
                confirmed_name = st.text_input("Model İsmi Doğru mu? (Yanlışsa Düzeltin):", value=st.session_state.lens_ai_guess)
            
            st.write("")
            
            c_back, c_go = st.columns([1, 4])
            if c_back.button("🔙 Geri"):
                st.session_state.lens_step = 1
                st.rerun()
                
            if c_go.button("🚀 Bu İsimle Analiz Et"):
                # --- İNTERNET ARAŞTIRMASI ---
                found_evidence = "İnternette ek belge bulunamadı."
                with st.status(f"🌐 İnternette '{confirmed_name}' sertifikaları aranıyor...", expanded=False) as status_search:
                    if "Bilinmeyen" not in confirmed_name:
                        cert_query = f"{confirmed_name} EN 13594 certificate pdf"
                        search_results, _ = search_ddg(cert_query, max_res=3)
                        
                        evidence_links = []
                        if search_results:
                            for res in search_results:
                                evidence_links.append(f"- {res.get('title')}: {res.get('href')}")
                            found_evidence = "\n".join(evidence_links)
                        else:
                            st.warning("İnternette doğrudan belge bulunamadı.")
                    status_search.update(label="İnternet Taraması Bitti", state="complete")

                # --- KONSEY ANALİZİ ---
                st.divider()
                with st.spinner(f"Konsey Başkanı '{confirmed_name}' için analiz yapıyor..."):
                    
                    image_list = [Image.open(f) for f in uploaded_files]
                    
                    # ÇAPRAZ KONTROL PROMPT'U
                    council_prompt_img = f"""
                    Sen Motosiklet Güvenlik Konseyisin. 
                    
                    ÜRÜN: {confirmed_name} (Kullanıcı tarafından doğrulandı)
                    
                    BULGULAR:
                    1. Görsel Kanıtlar: Yüklenen fotoğraflar.
                    2. İnternet Arama Sonuçları (Resmi Sertifikalar):
                    {found_evidence}
                    
                    GÖREV: Yüklenen fotoğrafları ve internet bulgularını KARŞILAŞTIRARAK (Cross-Check) analiz yap.
                    
                    KRİTİK ÇELİŞKİ KURALI (BAŞKAN İÇİN):
                    - İnternet sonuçlarında bu modelin sertifikası VAR (Uygun) görünüyor ANCAK yüklenen fotoğraflarda etiket YOKSA veya ürün kalitesiz/replika duruyorsa:
                      -> Karar: "RİSKLİ (REPLİKA ŞÜPHESİ)" ver. Puanı DÜŞÜR.
                      -> Açıklama: "Modelin orijinali sertifikalı ancak fotoğraftaki üründe etiket/kalite eksik." de.
                    
                    - İnternette belge yok VE fotoğrafta da etiket yoksa -> %0 PUAN.
                    
                    - İnternette belge var VE fotoğrafta da etiket/kalite uyuşuyorsa -> YÜKSEK PUAN.
                    
                    Lütfen cevabı TAM OLARAK aşağıdaki formatta ver:
                    
                    [BAŞKAN]
                    **Güvenilirlik Skoru:** %XX
                    **Kısa Karar:** ...
                    
                    [MEVZUAT]
                    ...
                    
                    [MÜHENDİS]
                    ...
                    
                    [DEDEKTİF]
                    ...
                    """
                    full_resp_img = ask_gemini(active_api_key, "Motosiklet Güvenlik Konseyi", council_prompt_img, image_list, mode=selected_mode)
                    
                    try:
                        parts = full_resp_img.split('[')
                        p_baskan, p_mevzuat, p_muhendis, p_dedektif = "Veri Yok", "Veri Yok", "Veri Yok", "Veri Yok"
                        
                        for p in parts:
                            if p.startswith("BAŞKAN]"): p_baskan = p.replace("BAŞKAN]", "").strip()
                            elif p.startswith("MEVZUAT]"): p_mevzuat = p.replace("MEVZUAT]", "").strip()
                            elif p.startswith("MÜHENDİS]"): p_muhendis = p.replace("MÜHENDİS]", "").strip()
                            elif p.startswith("DEDEKTİF]"): p_dedektif = p.replace("DEDEKTİF]", "").strip()
                        
                        if "%0" in p_baskan or " 0" in p_baskan or "Düşük" in p_baskan or "RİSKLİ" in p_baskan:
                            st.error(f"📊 **Konsey Ortak Kararı:**\n\n{p_baskan}")
                        else:
                            st.success(f"📊 **Konsey Ortak Kararı:**\n\n{p_baskan}")
                        
                        c1, c2, c3 = st.columns(3)
                        with c1: st.info(f"📜 **Mevzuat Uzmanı**\n\n{p_mevzuat}")
                        with c2: st.warning(f"🛠️ **Malzeme Mühendisi**\n\n{p_muhendis}")
                        with c3: st.error(f"🕵️ **Şüpheci Dedektif**\n\n{p_dedektif}")
                            
                    except:
                        st.warning("Format hatası, ham metin:")
                        st.write(full_resp_img)
