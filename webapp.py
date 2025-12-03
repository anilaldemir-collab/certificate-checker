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
    
    st.header("🌏 Çinli/Hintli Üreticiler")
    st.info("""
    Bu üreticiler (Scoyco, Pro-Biker vb.) sertifikalarını genelde resmi sitelerinin **"Certificates"** veya **"About Us"** kısmında PDF listesi olarak yayınlar.
    
    Bot şimdi bu özel sayfaları da tarayacak.
    """)
    
    st.markdown("### 🔗 Manuel Kontrol Linkleri")
    st.link_button("🇹🇷 Trendyol'da Ara", "https://www.trendyol.com/")
    st.link_button("🌏 AliExpress Sertifika Kontrol", "https://www.aliexpress.com/")

# -----------------------------------------------------------------------------
# ARAYÜZ
# -----------------------------------------------------------------------------
st.title("🛡️ Motosiklet Eldiveni Dedektifi")
st.markdown("Çinli ve yerel üreticiler için **Gelişmiş Resmi Site Taraması** eklendi.")

tab1, tab2 = st.tabs(["🔍 İnternet Araması", "📷 Fotoğraf Analizi (AI)"])

# --- TAB 1: İNTERNET ARAMASI ---
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        brand = st.text_input("Marka", placeholder="Örn: Scoyco, Masontex")
    with col2:
        model = st.text_input("Model", placeholder="Örn: MC29, M30")
    
    if st.button("🔍 Analiz Et", type="primary"):
        if not brand or not model:
            st.error("Marka ve Model giriniz.")
        else:
            full_name = f"{brand} {model}"
            score = 0
            
            # Durum bildirme
            status_container = st.status("🕵️ İnternet taranıyor...", expanded=True)
            
            # ---------------------------
            # 1. ADIM: Üretici Resmi Sitesi (YENİ ÖZELLİK)
            # ---------------------------
            st.write("---")
            st.markdown("### 1. 🌏 Üretici Resmi Sitesi Taraması")
            st.caption("Çinli/Hintli üreticilerin 'Certificate' sayfaları aranıyor...")
            
            # Markanın resmi sitesindeki sertifika sayfasını bulmaya çalış
            # Örn: "Scoyco official website certificate EN 13594"
            official_query = f'{brand} motorcycle gloves official website certificate "EN 13594"'
            results_off, _ = search_ddg(official_query, max_res=4)
            
            found_off = False
            if results_off:
                for res in results_off:
                    title = res.get('title', '')
                    link = res.get('href', '')
                    # Eğer başlıkta Certificate veya CE geçiyorsa
                    if "certif" in title.lower() or "declaration" in title.lower() or "ce" in title.lower():
                        st.success(f"✅ **Üretici Belgesi Bulundu:** [{title}]({link})")
                        score += 60 # Resmi siteden belge bulmak en güçlü kanıttır
                        found_off = True
                        break
            
            if not found_off:
                st.warning("⚠️ Üreticinin resmi sitesinde doğrudan bir sertifika sayfası bulunamadı.")
                st.link_button(
                    label=f"👉 Tıkla: {brand} Resmi Sitesini Google'da Ara",
                    url=create_google_link(f'{brand} official website motorcycle gloves'),
                    type="secondary"
                )

            # ---------------------------
            # 2. ADIM: Yerel Pazar (Trendyol, Hepsiburada vb.)
            # ---------------------------
            st.write("---")
            st.markdown("### 2. 🇹🇷 Türkiye Pazarı Taraması")
            
            tr_query = f'site:trendyol.com OR site:hepsiburada.com OR site:n11.com "{full_name}" "EN 13594"'
            results_tr, errors = search_ddg(tr_query, max_res=5)
            
            found_tr = False
            if results_tr:
                for res in results_tr:
                    title = res.get('title', '')
                    link = res.get('href', '')
                    st.success(f"✅ **Satıcı Beyanı (TR):** [{title}]({link})")
                    if score < 60: score += 30 
                    found_tr = True
                    break
            
            if not found_tr:
                st.info("ℹ️ Türkiye sitelerinde sertifika beyanı bulunamadı.")

            # ---------------------------
            # 3. ADIM: PDF Belge
            # ---------------------------
            st.write("---")
            st.markdown("### 3. 📄 Resmi Belge (Global)")
            
            doc_query = f"{brand} {model} declaration of conformity filetype:pdf"
            results, _ = search_ddg(doc_query)
            
            found_pdf = False
            if results:
                for res in results:
                    if res.get('href', '').lower().endswith('.pdf'):
                        st.success(f"✅ **PDF Bulundu:** [{res.get('title')}]({res.get('href')})")
                        if score < 60: score += 50
                        found_pdf = True
                        break
            
            if not found_pdf:
                st.info("ℹ️ Doğrudan PDF dosyası bulunamadı.")

            status_container.update(label="İşlem Tamamlandı", state="complete", expanded=False)
            
            # ---------------------------
            # SONUÇ PUANI
            # ---------------------------
            st.divider()
            if score > 50:
                st.balloons()
                st.success(f"**Otomatik Sistem Güven Skoru: {score}/100 (GÜVENLİ)**\n\nResmi kaynaklarda sertifika izine rastlandı.")
            elif score > 0:
                st.warning(f"**Otomatik Sistem Güven Skoru: {score}/100 (ORTA)**\n\nSadece satıcı beyanları var. Lütfen etiketi kontrol edin.")
            else:
                st.error("**HİÇBİR VERİ BULUNAMADI**")
                st.info("""
                İnternette bu model için sertifika izi yok. Bu durum, düşük bütçeli markalarda yaygındır.
                
                👉 **En kesin çözüm: Yandaki '📷 Fotoğraf Analizi' sekmesine geçip etiketi okutun.**
                """)


# --- TAB 2: GÖRSEL ANALİZ ---
with tab2:
    st.info("Bilinmedik markalar için EN GÜVENİLİR YÖNTEM budur. Etiketin fotoğrafını çekip yükleyin.")
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
