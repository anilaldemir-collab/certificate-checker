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
st.set_page_config(page_title="Eldiven Dedektifi (Konsey Modu)", page_icon="🏍️", layout="wide")

# API Anahtarı Kontrolü
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]

# -----------------------------------------------------------------------------
# FONKSİYONLAR
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

def ask_ai_persona(api_key, persona, prompt, image=None):
    """
    Belirli bir uzmanlık alanına göre AI'ya soru sorar.
    Model isimlerini ezbere denemek yerine, API'den aktif model listesini çekip
    en uygun olanı (Flash > Pro > Legacy) dinamik olarak seçer.
    """
    try:
        genai.configure(api_key=api_key)
        
        full_prompt = f"""
        GÖREV: Sen '{persona}' rolünde bir uzmansın.
        Aşağıdaki veriyi bu role uygun olarak analiz et.
        Kısa, net ve eleştirel ol. Türkçe cevap ver.
        
        ANALİZ EDİLECEK: {prompt}
        """
        
        # 1. Hesabın erişebildiği TÜM modelleri listele
        # (Bu işlem 404 hatasını önler çünkü sadece var olanları deneriz)
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
        except Exception as e:
            return f"Model listesi alınamadı: {str(e)}"

        # 2. En iyi modeli akıllıca seç
        target_model_name = None
        
        # Öncelik 1: 1.5 Flash (En hızlı ve güncel)
        for m in available_models:
            if 'flash' in m.lower() and '1.5' in m:
                target_model_name = m
                break
        
        # Öncelik 2: 1.5 Pro (Daha zeki)
        if not target_model_name:
            for m in available_models:
                if 'pro' in m.lower() and '1.5' in m:
                    target_model_name = m
                    break
        
        # Öncelik 3: Gemini Pro (Eski kararlı sürüm - Vision/Text ayrımı olabilir)
        if not target_model_name:
            if image:
                # Resim varsa 'vision' yeteneği olanı bul
                for m in available_models:
                    if 'vision' in m.lower():
                        target_model_name = m
                        break
            else:
                # Resim yoksa standart pro
                for m in available_models:
                    if 'gemini-pro' in m and 'vision' not in m:
                        target_model_name = m
                        break
        
        # Hiçbiri yoksa listenin ilkini al (Son çare)
        if not target_model_name and available_models:
            target_model_name = available_models[0]
            
        if not target_model_name:
            return "⚠️ Hata: Hesabınızda kullanılabilir aktif bir AI modeli bulunamadı."

        # 3. Seçilen model ile üret
        model = genai.GenerativeModel(target_model_name)
        
        if image:
            response = model.generate_content([full_prompt, image])
        else:
            response = model.generate_content(full_prompt)
        
        return response.text 

    except Exception as e:
        return f"Beklenmeyen Hata: {str(e)}"

# -----------------------------------------------------------------------------
# KENAR ÇUBUĞU
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Ayarlar")
    
    if not api_key:
        st.info("ℹ️ Konsey Modu (3 Uzman) için API anahtarı gerekir.")
        st.markdown("[👉 Ücretsiz API Anahtarı Almak İçin Tıkla](https://aistudio.google.com/app/apikey)")
        user_key = st.text_input("Google API Key", type="password")
        if user_key:
            api_key = user_key
            st.success("Anahtar tanımlandı!")
    else:
        st.success("✅ AI Konseyi Hazır")

    st.divider()
    st.markdown("### 🔗 Hızlı Linkler")
    st.link_button("🇹🇷 Trendyol", "https://www.trendyol.com/")
    st.link_button("🌏 AliExpress", "https://www.aliexpress.com/")

# -----------------------------------------------------------------------------
# ARAYÜZ BAŞLIĞI
# -----------------------------------------------------------------------------
st.title("⚖️ Motosiklet Eldiveni Dedektifi: Uzmanlar Konseyi")
st.markdown("Eldiveninizi **3 Farklı Yapay Zeka Uzmanı** aynı anda analiz etsin.")

tab1, tab2 = st.tabs(["🔍 İnternet Taraması (Anahtarsız)", "📷 Fotoğraf Analizi (Konsey Modu)"])

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
            if api_key:
                st.subheader("🧠 Yapay Zeka Hafıza Konseyi")
                st.caption("Google'ın veri bankasındaki bilgiler 3 farklı açıdan sorgulanıyor...")
                
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.info("📜 **Mevzuat Uzmanı**")
                    with st.spinner("Yasal kayıtlar taranıyor..."):
                        resp = ask_ai_persona(api_key, "Sertifikasyon Denetçisi", 
                            f"'{brand} {model}' eldiveni yasal olarak EN 13594 sertifikasına sahip bilinen bir model mi? Kesin kanıt var mı?")
                        st.write(resp)

                with c2:
                    st.warning("🛠️ **Malzeme Mühendisi**")
                    with st.spinner("Yapısal analiz yapılıyor..."):
                        resp = ask_ai_persona(api_key, "Tekstil Mühendisi", 
                            f"'{brand} {model}' eldiveninin malzeme kalitesi ve koruma yapısı (yumruk, avuç içi) teknik olarak yeterli biliniyor mu?")
                        st.write(resp)

                with c3:
                    st.error("🕵️ **Şüpheci Dedektif**")
                    with st.spinner("Risk analizi yapılıyor..."):
                        resp = ask_ai_persona(api_key, "Şüpheci Tüketici Hakları Uzmanı", 
                            f"'{brand} {model}' hakkında 'çabuk yırtıldı', 'sahte sertifika' gibi şikayetler veya şaibeler var mı? Dürüst ol.")
                        st.write(resp)
            
            st.divider()
            
            # --- KLASİK ARAMA ---
            status_container = st.status("🕵️ İnternet Taranıyor...", expanded=True)
            
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
# TAB 2: FOTOĞRAF ANALİZİ (KONSEY MODU)
# =============================================================================
with tab2:
    if not api_key:
        st.warning("⚠️ Konsey Modu için API Anahtarı şarttır.")
    else:
        st.success("✅ Konsey Toplandı: Etiketin veya Eldivenin fotoğrafını yükleyin.")
        uploaded_file = st.file_uploader("Eldiven veya Etiket Fotoğrafı Yükle", type=["jpg", "png", "jpeg"])

        if uploaded_file and st.button("🤖 Konseyi Topla ve Analiz Et"):
            img = Image.open(uploaded_file)
            
            st.divider()
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 📜 Mevzuatçı (Marka/Model Tespiti)")
                with st.spinner("Görsel taranıyor..."):
                    prompt_regulation = """
                    1. Fotoğrafta bir etiket varsa EN 13594, CE kodlarını oku.
                    2. EĞER ETİKET YOKSA: Eldivenin tasarımından Marka ve Modelini görsel olarak tespit et (Örn: "Bu tasarım Revit Sand 4 modeline benziyor").
                    3. Tespit ettiğin bu modelin yasal olarak sertifikalı olup olmadığını bilgi bankandan kontrol et.
                    """
                    resp = ask_ai_persona(api_key, "Gümrük ve Sertifikasyon Denetçisi", prompt_regulation, img)
                    st.info(resp)
            
            with col2:
                st.markdown("### 🛠️ Mühendis (Yapısal Analiz)")
                with st.spinner("Malzeme inceleniyor..."):
                    prompt_engineer = """
                    Fotoğraftaki ürünün (veya tespit ettiğin modelin) malzeme kalitesini (deri, tekstil, file) ve koruma parçalarını incele.
                    Bu yapı, EN 13594 standartlarını karşılayacak kadar güvenli duruyor mu? Dikişler ve korumalar sağlam mı?
                    """
                    resp = ask_ai_persona(api_key, "Güvenlik Ekipmanı Mühendisi", prompt_engineer, img)
                    st.warning(resp)
            
            with col3:
                st.markdown("### 🕵️ Dedektif (Sahtecilik & Geçmiş)")
                with st.spinner("Piyasa araştırması..."):
                    prompt_detective = """
                    1. Bu ürünün marka/modelini görselden kesin olarak tanımaya çalış.
                    2. Bu modelin piyasada 'replikası' (sahtesi) yaygın mı? Fotoğraftaki ürün orijinal mi duruyor yoksa replika emareleri (dikiş hatası, font kayması) var mı?
                    3. İnternet hafızanda bu modelle ilgili bilinen bir güvenlik şikayeti var mı?
                    """
                    resp = ask_ai_persona(api_key, "Sahte Ürün ve Piyasa Uzmanı", prompt_detective, img)
                    st.error(resp)
            
            st.success("✅ **Konsey Kararı:** Üç görüşü okuyarak nihai kararınızı verin.")
