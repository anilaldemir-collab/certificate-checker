import streamlit as st
from googlesearch import search
import threading
from PIL import Image
import google.generativeai as genai
import time

# Sayfa Ayarları
st.set_page_config(page_title="Eldiven Dedektifi", page_icon="🏍️", layout="centered")

# --- API KEY YÖNETİMİ (GİZLİ ANAHTAR) ---
# Önce sistemin gizli ayarlarından (Secrets) anahtarı çekmeye çalışıyoruz.
# Eğer orada yoksa (lokal test için) kenar çubuğundan istiyoruz.
api_key = None

if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    # Eğer sunucuda secret ayarlanmamışsa manuel giriş iste (Test amaçlı)
    with st.sidebar:
        st.warning("⚠️ Sistemde kayıtlı API Key bulunamadı.")
        api_key = st.text_input("Manuel API Key Girişi", type="password")

# --- BAŞLIK ---
st.title("🏍️ Motosiklet Eldiveni Dedektifi")
st.markdown("Marka/Model girin veya fotoğraf yükleyin, güvenliğini analiz edelim.")

# --- SEKME SİSTEMİ ---
tab1, tab2 = st.tabs(["🔍 İnternet Araması", "📷 Fotoğraf Analizi (AI)"])

# --- TAB 1: İNTERNET ARAMASI ---
with tab1:
    st.subheader("İnternet Tarama Modu")
    col1, col2 = st.columns(2)
    with col1:
        brand = st.text_input("Marka", placeholder="Örn: Revit")
    with col2:
        model = st.text_input("Model", placeholder="Örn: Sand 4")
    
    if st.button("🔍 İnterneti Tara", type="primary"):
        if not brand or not model:
            st.error("Lütfen marka ve model giriniz.")
        else:
            full_name = f"{brand} {model}"
            score = 0
            st.info(f"🕵️ '{full_name}' için internet taranıyor...")
            
            # 1. MotoCAP
            st.markdown("### 1. MotoCAP Testi")
            motocap_query = f"site:motocap.com.au {full_name}"
            found_moto = False
            try:
                # search fonksiyonu bazen mobilde yavaş olabilir, try-except iyidir
                for url in search(motocap_query, num_results=2):
                    if "motocap" in url:
                        st.success(f"✅ Kayıt Bulundu: [Link]({url})")
                        score += 50
                        found_moto = True
                if not found_moto:
                    st.warning("❌ MotoCAP kaydı bulunamadı.")
            except Exception as e:
                st.error(f"Arama hatası: {e} (Lütfen tekrar deneyin)")

            # 2. PDF Belge
            st.markdown("### 2. Resmi Belge (PDF)")
            doc_query = f'"{brand}" "{model}" "Declaration of Conformity" filetype:pdf'
            found_pdf = False
            try:
                for url in search(doc_query, num_results=2):
                    if ".pdf" in url:
                        st.success(f"✅ Belge Bulundu: [Link]({url})")
                        score += 40
                        found_pdf = True
                if not found_pdf:
                    st.warning("❌ PDF bulunamadı.")
            except:
                pass

            # SONUÇ
            st.divider()
            if score >= 50:
                st.balloons()
                st.success(f"**SONUÇ: GÜVENLİ (SERTİFİKALI) - Skor: {score}**")
            elif score >= 40:
                st.warning(f"**SONUÇ: GÜÇLÜ KANIT VAR AMA TEST EKSİK - Skor: {score}**")
            else:
                st.error(f"**SONUÇ: RİSKLİ / BELİRSİZ - Skor: {score}**")

# --- TAB 2: GÖRSEL ANALİZ ---
with tab2:
    st.subheader("Yapay Zeka Analizi")
    st.info("Eldivenin etiketini veya kendisini yükleyin. AI sizin için sertifikayı okusun.")
    
    uploaded_file = st.file_uploader("Fotoğraf Yükle", type=["jpg", "png", "jpeg"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption='Yüklenen Fotoğraf', use_column_width=True)
        
        if st.button("🤖 AI İle Analiz Et"):
            if not api_key:
                st.error("Sistemde API Key tanımlı değil. Lütfen yönetici ile iletişime geçin.")
            else:
                with st.spinner('Yapay zeka görüntüyü inceliyor...'):
                    try:
                        genai.configure(api_key=api_key)
                        ai_model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        prompt = """
                        Sen bir motosiklet güvenlik uzmanısın. Bu fotoğraftaki eldiveni veya etiketi analiz et.
                        Türkçe cevap ver. Şunlara bak:
                        1. Etikette 'EN 13594' yazısı veya Motosikletli Sürücü İkonu var mı?
                        2. 'Level 1' veya 'Level 2' ibaresi var mı?
                        3. Malzeme kalitesi nasıl görünüyor?
                        4. Yumruk koruması (Knuckle Protection) var mı?
                        5. Sonuç: Sertifikalı mı değil mü? (Emin değilsen belirt)
                        """
                        response = ai_model.generate_content([prompt, image])
                        st.markdown("### 📝 AI Raporu")
                        st.write(response.text)
                    except Exception as e:
                        st.error(f"Bir hata oluştu. API kotası dolmuş olabilir veya resim okunamadı.\nHata: {e}")
