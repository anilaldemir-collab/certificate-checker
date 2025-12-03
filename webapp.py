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
st.set_page_config(page_title="Eldiven Dedektifi", page_icon="🏍️", layout="centered")

api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    # Sidebar'ı aşağıda tekrar tanımlayacağımız için burayı geçici tutuyoruz
    pass 

# -----------------------------------------------------------------------------
# FONKSİYONLAR
# -----------------------------------------------------------------------------
def create_google_link(query):
    """Sorguyu tıklanabilir Google linkine çevirir."""
    encoded_query = urllib.parse.quote(query)
    return f"https://www.google.com/search?q={encoded_query}"

@st.cache_data(show_spinner=False)
def search_ddg(query, max_res=3):
    """
    Güçlendirilmiş Arama: Standart yol engellenirse 'Lite' ve 'HTML' 
    modlarını deneyerek engellemeyi aşmaya çalışır. Sonuçları önbelleğe alır.
    """
    backends = ['api', 'html', 'lite'] 
    debug_errors = []

    for backend in backends:
        try:
            time.sleep(random.uniform(0.3, 1.0))
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_res, backend=backend))
                if results:
                    return results, None
        except Exception as e:
            debug_errors.append(f"{backend} modu hatası: {str(e)}")
            continue
            
    return [], debug_errors

# -----------------------------------------------------------------------------
# KENAR ÇUBUĞU (BİLGİ & AYARLAR)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Ayarlar")
    if not api_key:
        st.warning("⚠️ API Key yok (AI çalışmaz).")
        api_key = st.text_input("Google API Key", type="password")
        st.markdown("[👉 Ücretsiz Key Al](https://aistudio.google.com/app/apikey)")

    st.divider()
    
    st.header("💡 İpuçları")
    st.info("""
    **Neden Yorumları Çekemiyoruz?**
    Trendyol/Hepsiburada botları engeller. 
    
    **Yeni Çözüm:**
    1. **Forum Taraması:** Kullanıcıların gerçek tartışmalarını bulur.
    2. **AI Hafızası:** Google'ın yapay zekasına bu modelin geçmişini sorar.
    """)
    
    st.markdown("### 🔗 Hızlı Linkler")
    st.link_button("🇹🇷 Trendyol'da Ara", "https://www.trendyol.com/")
    st.link_button("🌏 AliExpress Sertifika Kontrol", "https://www.aliexpress.com/")

# -----------------------------------------------------------------------------
# ARAYÜZ
# -----------------------------------------------------------------------------
st.title("🛡️ Motosiklet Eldiveni Dedektifi")
st.markdown("Otomatik tarama, **Forum Dedektifi** ve **AI Danışmanı** devrede.")

tab1, tab2 = st.tabs(["🔍 İnternet & AI Taraması", "📷 Fotoğraf Analizi (Kesin Çözüm)"])

# --- TAB 1: İNTERNET ARAMASI ---
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
            score = 0
            
            # --- AI HAFIZA SORGUSU (YENİ) ---
            if api_key:
                with st.status("🧠 Yapay Zeka Hafızası Sorgulanıyor...", expanded=True) as status_ai:
                    try:
                        genai.configure(api_key=api_key)
                        model_ai = genai.GenerativeModel('gemini-1.5-flash')
                        prompt_knowledge = f"""
                        Motosiklet ekipmanları konusunda uzman bir asistansın.
                        Kullanıcı '{brand} {model}' model eldiveni soruyor.
                        Kendi bilgi bankanı (eğitim verini) tara ve şunları cevapla:
                        1. Bu marka/model bilindik bir model mi?
                        2. Geçmişte bu modelin 'EN 13594' sertifikası olduğuna dair bir bilgin var mı?
                        3. Kullanıcılar arasında bu modelin koruması hakkında genel kanı nedir? (Güvenli mi, dayanıksız mı?)
                        Lütfen çok kısa ve net Türkçe cevap ver. Kesin bilgi yoksa "Veri tabanımda kesin bilgi yok" de.
                        """
                        response = model_ai.generate_content(prompt_knowledge)
                        st.info("🤖 **AI Danışman Görüşü:**")
                        st.write(response.text)
                        status_ai.update(label="AI Analizi Tamamlandı", state="complete", expanded=False)
                    except Exception as e:
                        st.error(f"AI Hatası: {e}")
            
            st.write("---")
            
            status_container = st.status("🕵️ İnternet ve Forumlar Taranıyor...", expanded=True)
            
            # ---------------------------
            # 1. ADIM: Otomatik Sertifika Taraması
            # ---------------------------
            st.markdown("### 1. 📄 Sertifika Belgesi Kontrolü")
            auto_query = f"{brand} {model} certificate EN 13594 filetype:pdf"
            results_auto, _ = search_ddg(auto_query, max_res=3)
            
            if results_auto:
                for res in results_auto:
                    st.success(f"✅ **Belge Bulundu:** [{res.get('title')}]({res.get('href')})")
                    score += 50
            else:
                st.warning("⚠️ Doğrudan PDF sertifika belgesi bulunamadı.")

            # ---------------------------
            # 2. ADIM: Forum Dedektifi (YENİ)
            # ---------------------------
            st.write("---")
            st.markdown("### 2. 🗣️ Forum Dedektifi (Kullanıcı Tartışmaları)")
            st.caption("Motosiklet.net, Technopat ve Facebook gruplarındaki tartışmalar:")
            
            # Forumlarda spesifik arama
            forum_query = f'site:motosiklet.net OR site:technopat.net OR site:facebook.com "{full_name}" koruma'
            results_forum, _ = search_ddg(forum_query, max_res=5)
            
            if results_forum:
                for res in results_forum:
                    st.info(f"🗨️ **Tartışma:** [{res.get('title')}]({res.get('href')})\n\n_{res.get('body')}_")
            else:
                st.info("Bu model hakkında forumlarda özel bir tartışma bulunamadı.")

            # ---------------------------
            # 3. ADIM: Pazar Yeri Manuel Linkleri
            # ---------------------------
            st.write("---")
            st.markdown("### 3. 🛍️ Pazar Yeri Kontrolü")
            st.caption("Yorumları en iyi kendi sitesinde görebilirsiniz:")
            
            c1, c2 = st.columns(2)
            with c1:
                st.link_button("👉 Trendyol Yorumları", create_google_link(f'site:trendyol.com "{full_name}" yorum'))
            with c2:
                st.link_button("👉 Hepsiburada Soru-Cevap", create_google_link(f'site:hepsiburada.com "{full_name}" soru'))

            status_container.update(label="Tarama Bitti", state="complete", expanded=False)


# --- TAB 2: GÖRSEL ANALİZ ---
with tab2:
    st.success("💡 **İPUCU:** En kesin sonuç için eldivenin içindeki etiketin fotoğrafını çekip buraya yükleyin. AI sizin için okuyacaktır.")
    uploaded_file = st.file_uploader("Resim Yükle", type=["jpg", "png", "jpeg"])

    if uploaded_file and st.button("🤖 AI İle Analiz Et"):
        if not api_key:
            st.error("API Key Eksik.")
        else:
            with st.spinner('Analiz ediliyor...'):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    img = Image.open(uploaded_file)
                    
                    prompt = """
                    Bu motosiklet eldiveni etiketini analiz et. 
                    EN 13594 var mı? Level 1 mi 2 mi? KP var mı? 
                    Ürün markası bilinmedik olsa bile etiketi güvenli duruyor mu? 
                    Türkçe özetle.
                    """
                    
                    response = model.generate_content([prompt, img])
                    st.markdown("### 📝 AI Etiket Raporu")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Hata: {e}")
