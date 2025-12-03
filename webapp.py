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
    
    st.header("📚 Veritabanları")
    st.info("Sertifikaları kontrol edebileceğiniz en güvenilir kaynaklar:")
    
    st.markdown("### 🧪 Test Merkezleri")
    st.link_button("📊 MotoCAP (Resmi Test Arşivi)", "https://www.motocap.com.au/products/gloves")
    st.link_button("🏢 NANDO (Onaylı Laboratuvarlar)", "https://ec.europa.eu/growth/tools-databases/nando/index.cfm?fuseaction=directive.notifiedbody&dir_id=155501")
    
    st.markdown("### 🛍️ Güvenilir Mağazalar")
    st.caption("Bu mağazalar ürün özelliklerinde sertifika kodunu mutlaka yazar:")
    st.link_button("🇩🇪 FC-Moto (Almanya)", "https://www.fc-moto.de/")
    st.link_button("🇬🇧 SportsBikeShop (İngiltere)", "https://www.sportsbikeshop.co.uk/")

# -----------------------------------------------------------------------------
# ARAYÜZ
# -----------------------------------------------------------------------------
st.title("🛡️ Motosiklet Eldiveni Dedektifi")
st.markdown("Otomatik tarama çalışmazsa, **Manuel Doğrulama Butonları** devreye girer.")

tab1, tab2 = st.tabs(["🔍 İnternet Araması", "📷 Fotoğraf Analizi (AI)"])

# --- TAB 1: İNTERNET ARAMASI ---
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        brand = st.text_input("Marka", placeholder="Örn: Revit")
    with col2:
        model = st.text_input("Model", placeholder="Örn: Sand 4")
    
    if st.button("🔍 Analiz Et", type="primary"):
        if not brand or not model:
            st.error("Marka ve Model giriniz.")
        else:
            full_name = f"{brand} {model}"
            score = 0
            
            # Durum bildirme
            status_container = st.status("🕵️ İnternet taranıyor...", expanded=True)
            
            # ---------------------------
            # 1. ADIM: MotoCAP
            # ---------------------------
            st.write("---")
            st.markdown("### 1. 🧪 MotoCAP Laboratuvar Testi")
            motocap_query = f"site:motocap.com.au {full_name}"
            results, errors = search_ddg(motocap_query)
            
            found = False
            if results:
                for res in results:
                    if "motocap" in res.get('href', ''):
                        st.success(f"✅ **Kayıt Bulundu:** [{res.get('title')}]({res.get('href')})")
                        score += 50
                        found = True
                        break
            
            if not found:
                st.warning("⚠️ Otomatik taramada sonuç alınamadı.")
                st.link_button(
                    label="👉 Tıkla: MotoCAP Sonuçlarını Kendin Gör",
                    url=create_google_link(motocap_query),
                    type="secondary"
                )

            # ---------------------------
            # 2. ADIM: PDF Belge
            # ---------------------------
            st.write("---")
            st.markdown("### 2. 📄 Resmi Sertifika Belgesi (PDF)")
            doc_query = f"{brand} {model} declaration of conformity filetype:pdf"
            results, errors = search_ddg(doc_query)
            
            found_pdf = False
            if results:
                for res in results:
                    if res.get('href', '').lower().endswith('.pdf'):
                        st.success(f"✅ **PDF Bulundu:** [{res.get('title')}]({res.get('href')})")
                        score += 40
                        found_pdf = True
                        break
            
            if not found_pdf:
                st.warning("⚠️ Otomatik taramada PDF yakalanamadı.")
                st.link_button(
                    label="👉 Tıkla: Resmi PDF Belgelerini Ara",
                    url=create_google_link(doc_query),
                    type="secondary"
                )

            # ---------------------------
            # 3. ADIM: Mağaza Teyidi (YENİ)
            # ---------------------------
            st.write("---")
            st.markdown("### 3. 🛍️ Güvenilir Mağaza Teyidi (FC-Moto & SBS)")
            st.info("Avrupa yasaları gereği bu mağazalar sertifikasız ürüne 'Certified' yazamaz.")
            
            # FC-Moto Araması
            fc_query = f"site:fc-moto.de {full_name} EN 13594"
            results_fc, _ = search_ddg(fc_query)
            
            found_fc = False
            if results_fc:
                for res in results_fc:
                    if "fc-moto" in res.get('href', ''):
                        st.success(f"✅ **FC-Moto Kaydı:** [{res.get('title')}]({res.get('href')})")
                        if score < 50: score += 20
                        found_fc = True
                        break
            
            if not found_fc:
                st.markdown(f"[👉 FC-Moto'da Ara]({create_google_link(fc_query)})", unsafe_allow_html=True)

            # SportsBikeShop Araması
            sbs_query = f"site:sportsbikeshop.co.uk {full_name} CE certified"
            results_sbs, _ = search_ddg(sbs_query)
            
            found_sbs = False
            if results_sbs:
                for res in results_sbs:
                    if "sportsbikeshop" in res.get('href', ''):
                        st.success(f"✅ **SportsBikeShop Kaydı:** [{res.get('title')}]({res.get('href')})")
                        if score < 50: score += 20
                        found_sbs = True
                        break
            
            if not found_sbs:
                st.markdown(f"[👉 SportsBikeShop'ta Ara]({create_google_link(sbs_query)})", unsafe_allow_html=True)

            # ---------------------------
            # 4. ADIM: Genel Kontrol
            # ---------------------------
            st.write("---")
            st.markdown("### 4. 🌍 Genel İnceleme")
            review_query = f"{full_name} motorcycle glove EN 13594 review"
            st.link_button(
                label="👉 Tıkla: İncelemeleri Google'da Gör",
                url=create_google_link(review_query),
                type="secondary"
            )
            
            status_container.update(label="İşlem Tamamlandı", state="complete", expanded=False)
            
            # ---------------------------
            # SONUÇ PUANI
            # ---------------------------
            st.divider()
            if score > 0:
                st.success(f"**Otomatik Sistem Güven Skoru: {score}/100**")
            else:
                st.info("**Otomatik skor hesaplanamadı. Lütfen yukarıdaki '👉 Tıkla' butonlarını kullanarak doğrulayın.**")


# --- TAB 2: GÖRSEL ANALİZ ---
with tab2:
    st.info("Eldivenin etiketini yükleyin, yapay zeka okusun.")
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
                    prompt = "Bu motosiklet eldiveni etiketini analiz et. EN 13594 var mı? Level 1 mi 2 mi? KP var mı? Türkçe özetle."
                    response = model.generate_content([prompt, img])
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Hata: {e}")
