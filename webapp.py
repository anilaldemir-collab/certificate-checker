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

def create_google_images_link(query):
    encoded_query = urllib.parse.quote(query)
    return f"https://www.google.com/search?tbm=isch&q={encoded_query}"

@st.cache_data(show_spinner=False)
def search_ddg_global(query, max_res=5):
    """
    Dünya genelinde (Region: wt-wt) detaylı arama yapar.
    Birden fazla backend deneyerek engelleri aşmaya çalışır.
    """
    backends = ['api', 'html', 'lite'] 
    for backend in backends:
        try:
            time.sleep(random.uniform(0.5, 1.5)) # Robot yakalanmamak için bekleme
            with DDGS() as ddgs:
                # region='wt-wt' -> World Wide (Tüm Dünya)
                results = list(ddgs.text(query, region='wt-wt', max_results=max_res, backend=backend))
                if results: return results, None
        except: continue
    return [], ["Bağlantı hatası"]

def deep_research_product(product_name):
    """
    Ürün için birden fazla teknik terimle çapraz arama yapar ve sonuçları birleştirir.
    """
    # Farklı teknik terimlerle arama varyasyonları
    search_variations = [
        f"{product_name} EN 13594 certificate filetype:pdf",      # PDF Sertifika
        f"{product_name} declaration of conformity",               # Uygunluk Beyanı
        f"{product_name} technical data sheet motorcycle glove",    # Teknik Veri
        f"{product_name} CE certification documents",              # CE Belgeleri
        f'site:motocap.com.au "{product_name}"'                   # MotoCAP Veritabanı
    ]
    
    all_findings = []
    seen_links = set()
    
    progress_bar = st.progress(0)
    
    for i, query in enumerate(search_variations):
        results, _ = search_ddg_global(query, max_res=3)
        if results:
            for res in results:
                link = res.get('href', '')
                if link not in seen_links:
                    seen_links.add(link)
                    all_findings.append(f"- [{res.get('title')}]({link}): {res.get('body')}")
        
        # İlerleme çubuğunu güncelle
        progress_bar.progress((i + 1) / len(search_variations))
        
    progress_bar.empty() # Çubuğu gizle
    
    if not all_findings:
        return "Detaylı küresel taramada doğrudan bir belgeye rastlanmadı."
    
    return "\n".join(all_findings[:10]) # En alakalı 10 sonucu döndür

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
    
    if st.button("🔍 Küresel Araştırma Başlat", type="primary"):
        if not brand or not model:
            st.error("Marka ve Model giriniz.")
        else:
            full_name = f"{brand} {model}"
            
            # --- AI KONSEYİ: TEK OTURUM ---
            if active_api_key:
                st.subheader(f"🧠 {ai_mode.split(' ')[2]} Hafıza Konseyi")
                
                # DERİN ARAŞTIRMA (INTERNET)
                with st.status(f"🌍 Dünya genelinde '{full_name}' belgeleri taranıyor...", expanded=True) as status_box:
                    st.write("PDF Sertifikalar aranıyor...")
                    internet_findings = deep_research_product(full_name)
                    st.write("Teknik Veri Sayfaları kontrol ediliyor...")
                    # Biraz gecikme ekleyerek kullanıcının işlemi görmesini sağlıyoruz
                    time.sleep(0.5) 
                    st.write("Veriler toparlanıyor...")
                    status_box.update(label="Küresel Tarama Tamamlandı", state="complete", expanded=False)

                st.divider()
                st.caption("Toplanan veriler Konsey tarafından analiz ediliyor...")
                
                with st.spinner("Konsey Kararı Hazırlanıyor..."):
                    council_prompt = f"""
                    Sen Motosiklet Güvenlik Konseyisin. Ürün: '{brand} {model}'
                    
                    Aşağıdaki 4 farklı rolü AYNI ANDA canlandır ve birbirinizle TUTARLI cevaplar verin.
                    
                    GİRDİLER (İNTERNET BULGULARI):
                    {internet_findings}
                    
                    KRİTİK DEĞERLENDİRME KURALI (BAŞKAN İÇİN):
                    1. BULGULARDA KANIT VARSA: İnternet bulgularında 'Certificate', 'Declaration of Conformity', 'EN 13594' geçen bir PDF veya resmi sayfa varsa -> %100 GÜVENİLİR.
                    2. İÇ BİLGİ (KNOWLEDGE): Bulgularda yoksa bile, sen bu markanın (Örn: {brand}) Avrupa standartlarında üretim yaptığını biliyorsan -> %80-90 GÜVENİLİR.
                    3. BELİRSİZLİK: Hem bulgu yok hem de marka bilinmiyorsa -> %0 VER.
                    
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
            
            # Bulunan linkleri göster
            if "internet_findings" in locals() and len(internet_findings) > 50:
                with st.expander("🌍 Bulunan Küresel Kaynaklar (Detay)"):
                    st.markdown(internet_findings)

# =============================================================================
# TAB 2: FOTOĞRAF ANALİZİ (LENS MODU: TANI -> KONTROL ET -> ANALİZ ET)
# =============================================================================
with tab2:
    if not active_api_key:
        st.warning("⚠️ Konsey Modu için API Anahtarı şarttır.")
    else:
        st.success("✅ **Lens Modu Hazır:** Etiket olmasa bile ürünü tanıyıp araştırabilirim.")
        
        st.info("""
        📸 **ÖNERİLEN FOTOĞRAFLAR:**
        * En iyi sonuç için eldivenin markasını/modelini gösteren farklı açılardan (dış yüz, iç etiket) fotoğraflar yükleyin.
        """)
        
        # State Yönetimi
        if "lens_step" not in st.session_state: st.session_state.lens_step = 1
        if "lens_ai_guess" not in st.session_state: st.session_state.lens_ai_guess = ""
        if "lens_manual_mode" not in st.session_state: st.session_state.lens_manual_mode = False
        if "rejected_guesses" not in st.session_state: st.session_state.rejected_guesses = [] 
        
        uploaded_files = st.file_uploader("Fotoğrafları Yükle (Çoklu Seçim)", 
                                          type=["jpg", "png", "jpeg", "webp"], 
                                          accept_multiple_files=True)

        # -------------------------------------------
        # ADIM 1: TANI VE TAHMİN ET (Sıfırdan Başla)
        # -------------------------------------------
        if uploaded_files and st.session_state.lens_step == 1:
            # Yeni yüklemede hafızayı temizle
            if st.button("🔍 Görseli Tara ve Model Tahmini Yap"):
                st.session_state.rejected_guesses = [] # Sıfırla
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
                    st.session_state.lens_manual_mode = False
                    st.rerun()

        # -------------------------------------------
        # ADIM 2: KULLANICI DOĞRULAMASI & TEKRAR DENE
        # -------------------------------------------
        if st.session_state.lens_step == 2:
            st.image([Image.open(f) for f in uploaded_files], width=120, caption="Yüklenenler")
            st.divider()
            
            st.subheader("📝 Yapay Zeka Tahmini")
            
            # Tahmin Gösterimi
            st.info(f"Tespit Edilen Model: **{st.session_state.lens_ai_guess}**")
            
            # Görsel doğrulama linki
            google_img_link = create_google_images_link(st.session_state.lens_ai_guess)
            st.markdown(f"[🖼️ Google Görseller'de Kontrol Et]({google_img_link})")
            
            st.write("---")
            st.write("### Bu model ismi doğru mu?")

            confirmed_name = None
            run_analysis = False

            # BUTON GRUBU
            c_yes, c_retry, c_edit = st.columns(3)
            
            # 1. DOĞRU (Analize Geç)
            if c_yes.button("✅ Evet, Doğru"):
                confirmed_name = st.session_state.lens_ai_guess
                run_analysis = True
            
            # 2. TEKRAR DENE (Otomatik Yeni Tahmin - YENİ ÖZELLİK)
            if c_retry.button("🔄 Yanlış, Tekrar Tahmin Et"):
                # Mevcut tahmini 'yasaklılar' listesine ekle
                st.session_state.rejected_guesses.append(st.session_state.lens_ai_guess)
                image_list = [Image.open(f) for f in uploaded_files]
                
                with st.spinner("AI farklı bir olasılık düşünüyor..."):
                    # Yasaklı listesini prompt'a ekle
                    rejected_str = ", ".join(st.session_state.rejected_guesses)
                    retry_prompt = f"""
                    Bu fotoğraftaki eldivenin markasını ve modelini tekrar tahmin et.
                    
                    DİKKAT: Daha önce şu tahminleri yaptın ve YANLIŞTI: {rejected_str}
                    Lütfen bunları tekrar söyleme. Başka hangi model olabilir? Daha dikkatli bak.
                    
                    Cevabı SADECE marka ve model ismi olarak ver.
                    """
                    new_prediction = ask_gemini(active_api_key, "Ürün Tanıma Uzmanı", retry_prompt, image_list, mode="flash").strip()
                    
                    st.session_state.lens_ai_guess = new_prediction.replace("Marka ve Model:", "").strip()
                    st.rerun()

            # 3. DÜZENLE (Manuel Giriş)
            if c_edit.button("✏️ Elle Düzenle"):
                st.session_state.lens_manual_mode = True
                st.rerun()

            # Manuel mod açıksa giriş kutusunu göster
            if st.session_state.lens_manual_mode:
                st.warning("Doğru ismi aşağıya yazın:")
                manual_name = st.text_input("Marka/Model:", value=st.session_state.lens_ai_guess)
                if st.button("🚀 Bu İsimle Analiz Et"):
                    confirmed_name = manual_name
                    run_analysis = True

            # --- ANALİZ İŞLEMİ (Ortak) ---
            if run_analysis and confirmed_name:
                
                st.divider()
                st.subheader(f"🔍 '{confirmed_name}' Analiz Ediliyor...")
                
                # 1. DERİN İNTERNET ARAŞTIRMASI (Global)
                found_evidence = "İnternette ek belge bulunamadı."
                with st.status(f"🌐 Küresel veritabanları taranıyor...", expanded=True) as status_search:
                    if "Bilinmeyen" not in confirmed_name:
                        # Burada yeni deep_research fonksiyonunu kullanıyoruz
                        found_evidence = deep_research_product(confirmed_name)
                    
                    status_search.update(label="Küresel Tarama Bitti", state="complete", expanded=False)

                # 2. KONSEY ANALİZİ
                with st.spinner(f"Konsey Başkanı verileri birleştiriyor..."):
                    
                    image_list = [Image.open(f) for f in uploaded_files]
                    
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
            
            # Resetleme butonu (En altta)
            st.divider()
            if st.button("🔄 Yeni Bir Ürün Tara"):
                st.session_state.lens_step = 1
                st.session_state.lens_manual_mode = False
                st.session_state.rejected_guesses = []
                st.rerun()
