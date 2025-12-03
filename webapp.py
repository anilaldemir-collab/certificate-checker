import streamlit as st
from duckduckgo_search import DDGS
import threading
from PIL import Image
import google.generativeai as genai
import time

# -----------------------------------------------------------------------------
# 1. SAYFA YAPILANDIRMASI
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Motosiklet Eldiveni Dedektifi",
    page_icon="🏍️",
    layout="centered"
)

# -----------------------------------------------------------------------------
# 2. API KEY YÖNETİMİ
# -----------------------------------------------------------------------------
# Streamlit Cloud'da "Secrets" kısmından anahtarı çeker.
# Eğer sunucuda yoksa (yerel çalışma), sol menüden kullanıcıdan ister.
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    with st.sidebar:
        st.header("⚙️ Ayarlar")
        st.warning("⚠️ Sistemde tanımlı API Key bulunamadı.")
        api_key = st.text_input("Google AI API Key", type="password")
        st.markdown("[Ücretsiz API Key Almak İçin Tıkla](https://aistudio.google.com/app/apikey)")

# -----------------------------------------------------------------------------
# 3. ARAYÜZ BAŞLIĞI
# -----------------------------------------------------------------------------
st.title("🛡️ Motosiklet Eldiveni Dedektifi")
st.markdown("""
Bu araç, motosiklet eldiveninizin **EN 13594 Güvenlik Sertifikasına** sahip olup olmadığını anlamanız için iki yöntem sunar:
1. **İnternet Taraması:** Marka ve modeli veritabanlarında arar.
2. **AI Görsel Analizi:** Eldivenin fotoğrafını yapay zeka ile inceler.
""")

# Sekmeleri oluştur
tab1, tab2 = st.tabs(["🔍 İnternet Araması", "📷 Fotoğraf Analizi (AI)"])

# -----------------------------------------------------------------------------
# 4. SEKME 1: İNTERNET ARAMASI (DUCKDUCKGO)
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("Marka & Model Sorgulama")
    st.info("Robot engellemelerine takılmamak için DuckDuckGo arama motoru kullanılır.")
    
    col1, col2 = st.columns(2)
    with col1:
        brand = st.text_input("Marka", placeholder="Örn: Revit, Knox")
    with col2:
        model = st.text_input("Model", placeholder="Örn: Sand 4, Handroid")
    
    # Arama Butonu
    if st.button("🔍 İnterneti Tara", type="primary"):
        if not brand or not model:
            st.error("Lütfen hem Marka hem de Model ismini giriniz.")
        else:
            full_name = f"{brand} {model}"
            score = 0
            
            # Durum çubuğu (Status Bar) ile işlemi göster
            with st.status("🕵️ İnternet taranıyor, kanıtlar toplanıyor...", expanded=True) as status:
                
                # --- Arama Yardımcı Fonksiyonu ---
                def search_ddg(query, max_res=3):
                    """DuckDuckGo üzerinden arama yapar ve sonuçları liste döner."""
                    results_list = []
                    try:
                        with DDGS() as ddgs:
                            # ddgs.text() bir generator döner, listeye çeviriyoruz
                            results_list = list(ddgs.text(query, max_results=max_res))
                    except Exception as e:
                        # Hata olursa sessizce devam et
                        pass
                    return results_list

                # --- ADIM 1: MotoCAP Veritabanı ---
                st.write("📂 MotoCAP veritabanı kontrol ediliyor...")
                # 'site:' operatörü ile sadece belirli sitede arama yapıyoruz
                motocap_query = f"site:motocap.com.au {full_name}"
                moto_results = search_ddg(motocap_query)
                
                found_moto = False
                if moto_results:
                    for res in moto_results:
                        link = res.get('href', '')
                        title = res.get('title', 'Başlıksız')
                        # Sonuç gerçekten o siteye mi ait kontrolü
                        if "motocap.com.au" in link:
                            st.success(f"✅ **MotoCAP Test Kaydı Bulundu:** [{title}]({link})")
                            score += 50
                            found_moto = True
                            break
                
                if not found_moto:
                    st.warning("❌ MotoCAP veritabanında bu modelin kaydı bulunamadı.")

                # --- ADIM 2: Resmi Belge (PDF) ---
                st.write("📄 Resmi sertifika belgeleri (PDF) aranıyor...")
                # 'filetype:pdf' operatörü ile sadece PDF dosyalarını arıyoruz
                doc_query = f"{brand} {model} declaration of conformity filetype:pdf"
                pdf_results = search_ddg(doc_query, max_res=4)
                
                found_pdf = False
                if pdf_results:
                    for res in pdf_results:
                        link = res.get('href', '')
                        title = res.get('title', 'Belge')
                        if link.lower().endswith(".pdf"):
                            st.success(f"✅ **Resmi Belge (PDF) Bulundu:** [{title}]({link})")
                            score += 40
                            found_pdf = True
                            break
                
                if not found_pdf:
                    st.warning("❌ Doğrudan bir PDF sertifika dosyası bulunamadı.")

                # --- ADIM 3: İnceleme ve Standart Referansı ---
                st.write("🌍 Kullanıcı incelemeleri ve ürün sayfaları taranıyor...")
                review_query = f"{full_name} motorcycle glove EN 13594 review"
                review_results = search_ddg(review_query, max_res=5)
                
                found_std = False
                if review_results:
                    for res in review_results:
                        body_text = res.get('body', '').lower()
                        title_text = res.get('title', '').lower()
                        link = res.get('href', '')
                        
                        # Metin içinde standart kodu geçiyor mu?
                        if "en 13594" in body_text or "en 13594" in title_text or "ce certified" in body_text:
                            st.info(f"ℹ️ **Referans Bulundu:** [{res.get('title')}]({link})")
                            # Eğer daha önce hiç puan almadıysa buradan küçük puan ver
                            if score < 50: 
                                score += 15
                            found_std = True
                            break 
                
                status.update(label="Tarama Tamamlandı!", state="complete", expanded=False)

            # --- SONUÇ KARTI ---
            st.divider()
            
            # Skorlama Mantığı
            if score >= 50:
                st.balloons()
                st.success(f"### 🛡️ SONUÇ: GÜVENLİ (SERTİFİKALI)\n**Güven Skoru: {score}/100**\n\nBu ürünün laboratuvar testleri veya resmi sertifikaları doğrulandı.")
            elif score >= 15:
                st.warning(f"### ⚠️ SONUÇ: KANITLAR YETERSİZ\n**Güven Skoru: {score}/100**\n\nBazı sitelerde sertifikalı olduğu yazıyor ancak resmi belge veya laboratuvar kaydı bulunamadı. Lütfen görsel analiz sekmesini kullanın.")
            else:
                st.error(f"### ⛔ SONUÇ: BULUNAMADI\n**Güven Skoru: {score}/100**\n\nİnternette bu modelin sertifikalı olduğuna dair güvenilir bir iz yok.")


# -----------------------------------------------------------------------------
# 5. SEKME 2: GÖRSEL ANALİZ (GOOGLE GEMINI AI)
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("Yapay Zeka Görsel Analizi")
    st.markdown("""
    Eldivenin içindeki etiketin veya eldivenin dıştan fotoğrafını yükleyin. 
    **Google Gemini AI**, üzerindeki işaretleri okuyarak yorumlasın.
    """)
    
    uploaded_file = st.file_uploader("Fotoğraf Yükle (JPG, PNG)", type=["jpg", "png", "jpeg"])

    if uploaded_file is not None:
        # Resmi göster
        image = Image.open(uploaded_file)
        st.image(image, caption='Yüklenen Fotoğraf', use_container_width=True)
        
        analyze_btn = st.button("🤖 AI İle Analiz Et", type="primary")
        
        if analyze_btn:
            if not api_key:
                st.error("HATA: API Key bulunamadı. Lütfen sol menüden veya sistem ayarlarından ekleyin.")
            else:
                with st.spinner('Yapay zeka görüntüyü inceliyor... (Bu işlem 5-10 saniye sürebilir)'):
                    try:
                        # AI Modelini Yapılandır
                        genai.configure(api_key=api_key)
                        ai_model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        # AI'ya gönderilecek komut (Prompt)
                        prompt = """
                        Sen uzman bir motosiklet güvenlik ekipmanı danışmanısın.
                        Bu fotoğraftaki eldiveni veya etiketi detaylıca analiz et.
                        Lütfen Türkçe ve maddeler halinde şu soruları cevapla:

                        1. **ETİKET ANALİZİ:** Fotoğrafta bir etiket varsa, üzerinde 'EN 13594' yazısı veya 'Motosikletli Sürücü İkonu' (kare içinde motor süren adam) var mı?
                        2. **SEVİYE TESPİTİ:** 'Level 1', 'Level 2' veya 'KP' (Knuckle Protection) ibareleri okunuyor mu?
                        3. **MALZEME:** Eldivenin malzemesi neye benziyor? (Deri, tekstil, file vb.) Güvenli duruyor mu?
                        4. **KORUMA:** Yumruk (tarak kemiği) koruması veya avuç içi koruyucusu (slider) görüyor musun?
                        5. **SONUÇ KARARI:** Sence bu eldiven sertifikalı mı yoksa sadece aksesuar mı? Neden?
                        """
                        
                        # AI'dan cevap al
                        response = ai_model.generate_content([prompt, image])
                        
                        # Cevabı yazdır
                        st.markdown("### 📝 AI Analiz Raporu")
                        st.write(response.text)
                        
                    except Exception as e:
                        st.error(f"Bir hata oluştu. Lütfen API anahtarını kontrol edin veya başka bir fotoğraf deneyin.\nHata Mesajı: {e}")
