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
    
    st.header("🕵️ Derin Arama Modu")
    st.info("""
    Otomatik aramalar Çinli sitelerde (Scoyco vb.) yetersiz kalabilir.
    
    Bu durumda **'Derin Arama Linkleri'** bölümündeki butonları kullanın. Bu butonlar Google'ın özel komutlarını (filetype:pdf, site:...) kullanarak gizli dosyaları bulur.
    """)
    
    st.markdown("### 🔗 Hızlı Linkler")
    st.link_button("🇹🇷 Trendyol'da Ara", "https://www.trendyol.com/")
    st.link_button("🌏 AliExpress Sertifika Kontrol", "https://www.aliexpress.com/")

# -----------------------------------------------------------------------------
# ARAYÜZ
# -----------------------------------------------------------------------------
st.title("🛡️ Motosiklet Eldiveni Dedektifi")
st.markdown("Otomatik sonuç bulunamazsa **Derin Arama Butonları** devreye girer.")

tab1, tab2 = st.tabs(["🔍 İnternet Araması", "📷 Fotoğraf Analizi (AI)"])

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
            
            status_container = st.status("🕵️ İnternet taranıyor...", expanded=True)
            
            # ---------------------------
            # 1. ADIM: Otomatik Tarama (Hızlı Bakış)
            # ---------------------------
            st.write("---")
            st.markdown("### 1. 🤖 Otomatik Hızlı Tarama")
            
            # Tek bir geniş kapsamlı sorgu ile şansımızı deneyelim
            # Örn: "Scoyco MC29 certificate pdf"
            auto_query = f"{brand} {model} certificate EN 13594 filetype:pdf"
            results_auto, _ = search_ddg(auto_query, max_res=3)
            
            if results_auto:
                for res in results_auto:
                    st.success(f"✅ **Otomatik Bulunan Belge:** [{res.get('title')}]({res.get('href')})")
                    score += 50
            else:
                st.warning("⚠️ Robot otomatik belge bulamadı. Manuel 'Derin Arama' gerekiyor.")

            status_container.update(label="Otomatik tarama bitti, manuel seçenekler aşağıda:", state="complete", expanded=False)

            # ---------------------------
            # 2. ADIM: Derin Arama Butonları (Kritik Kısım)
            # ---------------------------
            st.write("---")
            st.error("👇 **Otomatik Aramalar Başarısızsa Bunlara Tıkla** 👇")
            st.markdown("Bu butonlar, Google'ın özel komutlarını kullanarak gizli dosyaları arar.")
            
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("##### 📄 PDF & Katalog Arama")
                # filetype:pdf komutuyla sadece PDF belgelerini arar
                q_pdf = f'{brand} {model} "declaration of conformity" filetype:pdf'
                st.link_button("1. Uygunluk Beyanı (PDF) Ara", create_google_link(q_pdf))
                
                # catalog komutuyla ürün kataloğunu arar
                q_cat = f'{brand} motorcycle gloves catalogue pdf'
                st.link_button("2. Marka Kataloğunu Ara", create_google_link(q_cat))

            with c2:
                st.markdown("##### 🌏 Resmi Site & İmaj Arama")
                # site: komutuyla sadece markanın kendi sitesini tarar
                # Marka isminden boşlukları silip domain tahmini yapıyoruz (scoyco -> scoyco.com)
                domain_guess = brand.replace(" ", "").lower() + ".com"
                q_site = f'site:{domain_guess} "EN 13594"'
                st.link_button(f"3. {domain_guess} İçini Tara", create_google_link(q_site))
                
                # Görsel arama için link (Sertifika resimlerini bulmak için)
                q_img = f'{brand} {model} EN 13594 certificate label'
                img_search_url = f"https://www.google.com/search?q={urllib.parse.quote(q_img)}&tbm=isch"
                st.link_button("4. Sertifika Resimlerini Ara", img_search_url)

            st.info("💡 **İpucu:** 4. butona tıklayıp Görsellerde gezinin. Genellikle sertifika kağıdının fotoğrafını çeken kullanıcıları orada bulursunuz.")

            # ---------------------------
            # 3. ADIM: Türkiye Pazarı
            # ---------------------------
            st.write("---")
            st.markdown("### 3. 🇹🇷 Satıcı Beyanları")
            tr_query = f'site:trendyol.com OR site:hepsiburada.com "{full_name}" "EN 13594"'
            st.link_button("👉 Trendyol/Hepsiburada Yorumlarını Ara", create_google_link(tr_query))


# --- TAB 2: GÖRSEL ANALİZ ---
with tab2:
    st.info("İnternette bulamıyorsanız tek çare: **Etiketi çekip buraya yüklemek.**")
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
                    prompt = "Bu motosiklet eldiveni etiketini analiz et. EN 13594 var mı? Level 1 mi 2 mi? KP var mı? Ürün markası bilinmedik olsa bile etiketi güvenli duruyor mu? Türkçe özetle."
                    response = model.generate_content([prompt, img])
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Hata: {e}")
