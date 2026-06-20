import streamlit as st
from streamlit_folium import st_folium
import folium
import requests
import json
import os
from math import radians, cos, sin, asin, sqrt

st.set_page_config(page_title="MekanBul", page_icon="🗺️", layout="centered")

# 🔑 GOOGLE API ANAHTARINIZI BURAYA YAPIŞTIRIN
GOOGLE_API_KEY = "AIzaSyAUQ005Ck_RrVCLDjBAAvx6e1oia-EH99o"

# 📝 DOSYA VERİTABANLARI (JSON)
YORUM_DOSYASI = "uygulama_yorumlari.json"
FAVORILER_DOSYASI = "uygulama_favorileri.json"

# --- 🎨 UYGULAMA İÇİ ÖZEL CSS TASARIM DOKUNUŞLARI ---
st.markdown("""
    <style>
    /* Ana başlık stili */
    .ana-baslik {
        font-size: 36px !important;
        font-weight: 800 !important;
        color: #FF4B4B;
        text-align: center;
        margin-bottom: 5px;
    }
    .alt-baslik {
        font-size: 16px !important;
        color: #777777;
        text-align: center;
        margin-bottom: 25px;
    }
    /* Mekan Kartları Tasarımı */
    .mekan-kart {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #FF4B4B;
        margin-bottom: 15px;
    }
    /* Durum Rozetleri */
    .rozet-acik {
        background-color: #D4EDDA;
        color: #155724;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 13px;
    }
    .rozet-kapali {
        background-color: #F8D7DA;
        color: #721C24;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 13px;
    }
    </style>
""", unsafe_allow_html=True)

# --- YEREL VERİ YÖNETİM FONKSİYONLARI ---
def veriyi_yukle(dosya_adi):
    if os.path.exists(dosya_adi):
        with open(dosya_adi, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

def veriyi_kaydet(dosya_adi, veri):
    with open(dosya_adi, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

# --- 📏 MESAFE HESAPLAMA ---
def mesafe_hesapla(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 
    km = c * r
    if km < 1:
        return f"🚶 {int(km * 1000)}m"
    return f"🚗 {round(km, 1)}km"

def mesafe_saf_km(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    a = sin((lat2-lat1)/2)**2 + cos(lat1) * cos(lat2) * sin((lon2-lon1)/2)**2
    return 2 * asin(sqrt(a)) * 6371

# 🛰️ GOOGLE TABANLI ADRES VE KONUM ARAMA MOTORU
def google_ile_konum_ara(arama_metni):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.location,places.formattedAddress"
    }
    payload = {
        "textQuery": arama_metni,
        "languageCode": "tr"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200 and "places" in response.json() and len(response.json()["places"]) > 0:
            en_iyi_sonuc = response.json()["places"][0]
            loc = en_iyi_sonuc["location"]
            tam_ad = en_iyi_sonuc["formattedAddress"]
            return float(loc["latitude"]), float(loc["longitude"]), tam_ad
        return None
    except:
        return None

# --- 🛰️ GOOGLE PLACES API BAĞLANTISI ---
def google_mekanlari_kesfet(lat, lon, kategori_turu):
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.rating,places.userRatingCount,places.formattedAddress,places.location,places.photos,places.currentOpeningHours,places.primaryType,places.reviews"
    }
    payload = {
        "includedTypes": [kategori_turu],
        "maxResultCount": 15,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": 1500.0 
            }
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json().get("places", [])
        return []
    except:
        return []

# --- UYGULAMA BAŞLANGIÇ AYARLARI ---
if 'enlem' not in st.session_state:
    st.session_state.enlem = 39.9208
    st.session_state.boylam = 32.8541

# Tasarım Başlıkları
st.markdown("<div class='ana-baslik'>🗺️ MekanBul</div>", unsafe_allow_html=True)
st.markdown("<div class='alt-baslik'>Şehrin En İyi Noktalarını Keşfetmeye Başla</div>", unsafe_allow_html=True)

# 📱 TABS MANTIĞI
sekme_kesfet, sekme_favoriler = st.tabs(["🔍 Etrafımı Keşfet", "❤️ Favori Mekanlarım"])

tüm_yorumlar = veriyi_yukle(YORUM_DOSYASI)
tüm_favoriler = veriyi_yukle(FAVORILER_DOSYASI)

# ==================== SEKME 1: KEŞFET ====================
with sekme_kesfet:
    
    # Şık Arama Kartı
    with st.container(border=True):
        st.write("🔍 **Nereye Gitmek İstersiniz?**")
        arama_kutusu = st.text_input("Şehir, ilçe veya meydan adı yazın...", placeholder="Örn: Beşiktaş, İstanbul", key="arama_input", label_visibility="collapsed")
        if st.button("🚀 Haritada Ara ve Oraya Işınlan", use_container_width=True):
            if arama_kutusu:
                arama_sonucu = google_ile_konum_ara(arama_kutusu)
                if arama_sonucu:
                    yeni_lat, yeni_lon, tam_ad = arama_sonucu
                    st.session_state.enlem = yeni_lat
                    st.session_state.boylam = yeni_lon
                    st.success(f"📍 Başarıyla şuraya geçildi: {tam_ad.split(',')[0]}")
                    st.rerun()
                else:
                    st.error("Konum bulunamadı. Lütfen daha net yazın.")

    st.write("")
    
    # 📌 MODERN KATEGORİ SEÇİM ALANI
    st.write("📌 **Mekan Türü Seçin:**")
    
    kategoriler = [
        {"etiket": "☕ Kafe", "api_adi": "cafe", "icon": "coffee"},
        {"etiket": "🍔 Restoran", "api_adi": "restaurant", "icon": "cutlery"},
        {"etiket": "💊 Eczane", "api_adi": "pharmacy", "icon": "plus-sign"},
        {"etiket": "🏨 Otel", "api_adi": "hotel", "icon": "home"},
        {"etiket": "⛽ Akaryakıt", "api_adi": "gas_station", "icon": "road"}
    ]
    
    if 'secili_kategori' not in st.session_state:
        st.session_state.secili_kategori = "restaurant"
        
    # Yan yana 5 kategori butonu
    kat_kolonlari = st.columns(5)
    for i, kat in enumerate(kategoriler):
        is_selected = st.session_state.secili_kategori == kat["api_adi"]
        btn_type = "primary" if is_selected else "secondary"
        
        if kat_kolonlari[i].button(kat["etiket"], key=f"kat_{kat['api_adi']}", type=btn_type, use_container_width=True):
            st.session_state.secili_kategori = kat["api_adi"]
            st.rerun()

    # 🔀 FİLTRELEME VE SIRALAMA BARLARI
    with st.expander("⚙️ Filtreleme ve Sıralama Ayarları"):
        fil_col1, fil_col2 = st.columns(2)
        sirala_secim = fil_col1.selectbox(
            "Sıralama Ölçütü", 
            ["Mesafeye Göre (En Yakın)", "Puana Göre (En Yüksek)", "Yorum Sayısına Göre (En Popüler)"]
        )
        sadece_aciklar = fil_col2.checkbox("🟢 Sadece Şu An Açık Olanları Göster", value=False)

    # API'den mekanları çek
    ham_mekanlar = google_mekanlari_kesfet(st.session_state.enlem, st.session_state.boylam, st.session_state.secili_kategori)
    
    islenmis_mekanlar = []
    for mekan in ham_mekanlar:
        loc = mekan.get("location", {})
        m_lat, m_lng = loc.get("latitude"), loc.get("longitude")
        if not m_lat or not m_lng: continue
        
        uzaklik_metni = mesafe_hesapla(st.session_state.enlem, st.session_state.boylam, m_lat, m_lng)
        uzaklik_saf = mesafe_saf_km(st.session_state.enlem, st.session_state.boylam, m_lat, m_lng)
        
        open_now = mekan.get("currentOpeningHours", {}).get("openNow", None)
        if sadece_aciklar and open_now is False:
            continue
            
        mekan["uzaklik_metni"] = uzaklik_metni
        mekan["uzaklik_saf"] = uzaklik_saf
        islenmis_mekanlar.append(mekan)

    if sirala_secim == "Puana Göre (En Yüksek)":
        islenmis_mekanlar = sorted(islenmis_mekanlar, key=lambda x: x.get("rating", 0), reverse=True)
    elif sirala_secim == "Yorum Sayısına Göre (En Popüler)":
        islenmis_mekanlar = sorted(islenmis_mekanlar, key=lambda x: x.get("userRatingCount", 0), reverse=True)
    else: 
        islenmis_mekanlar = sorted(islenmis_mekanlar, key=lambda x: x.get("uzaklik_saf", 0))

    # HARİTA ÇİZİMİ
    st.write("📍 **Harita Üzerindeki Konumunuz:**")
    m = folium.Map(location=[st.session_state.enlem, st.session_state.boylam], zoom_start=14)
    folium.Marker([st.session_state.enlem, st.session_state.boylam], popup="Buradasınız", icon=folium.Icon(color="blue", icon="user")).add_to(m)

    guncel_icon = next((k["icon"] for k in kategoriler if k["api_adi"] == st.session_state.secili_kategori), "star")

    for mekan in islenmis_mekanlar:
        loc = mekan.get("location", {})
        folium.Marker(
            [loc.get("latitude"), loc.get("longitude")], 
            popup=mekan.get("displayName", {}).get("text"), 
            icon=folium.Icon(color="red", icon=guncel_icon)
        ).add_to(m)

    harita_verisi = st_folium(m, width=700, height=350)
    if harita_verisi and harita_verisi.get("last_clicked"):
        st.session_state.enlem = harita_verisi["last_clicked"]["lat"]
        st.session_state.boylam = harita_verisi["last_clicked"]["lng"]
        st.rerun()

    # MEKAN LİSTELEME ALANI
    st.subheader(f"✨ Yakındaki Sonuçlar ({len(islenmis_mekanlar)} Mekan)")
    
    if islenmis_mekanlar:
        for mekan in islenmis_mekanlar:
            mekan_id = mekan.get("id")
            isim = mekan.get("displayName", {}).get("text", "Bilinmeyen Yer")
            g_puan = mekan.get("rating", 0.0)
            toplam_oy = mekan.get("userRatingCount", 0)
            adres = mekan.get("formattedAddress", "Adres yok.")
            photos = mekan.get("photos", [])
            open_now = mekan.get("currentOpeningHours", {}).get("openNow", None)
            google_yorumları = mekan.get("reviews", [])
            
            durum_html = "<span class='rozet-acik'>🟢 ŞU AN AÇIK</span>" if open_now is True else "<span class='rozet-kapali'>🔴 ŞU AN KAPALI</span>" if open_now is False else "<span style='color:gray;'>⏳ Durum Bilinmiyor</span>"
            
            # Kart Başlığı
            with st.container(border=True):
                col_title, col_fav_btn = st.columns([5, 2])
                col_title.markdown(f"### 🏪 {isim}")
                
                fav_durum = "❤️ Favorilerimde" if mekan_id in tüm_favoriler else "🤍 Favoriye Ekle"
                if col_fav_btn.button(fav_durum, key=f"fav_btn_{mekan_id}", use_container_width=True):
                    if mekan_id in tüm_favoriler:
                        del tüm_favoriler[mekan_id]
                    else:
                        tüm_favoriler[mekan_id] = {"isim": isim, "adres": adres, "puan": g_puan, "lat": mekan.get("location", {}).get("latitude"), "lng": mekan.get("location", {}).get("longitude")}
                    veriyi_kaydet(FAVORILER_DOSYASI, tüm_favoriler)
                    st.rerun()

                # 📊 SKOR KARTLARI (METRİKLER)
                m_col1, m_col2, m_col3 = st.columns(3)
                m_col1.metric(label="⭐ Google Puanı", value=f"{g_puan} / 5")
                m_col2.metric(label="📏 Uzaklık", value=mekan['uzaklik_metni'])
                m_col3.metric(label="👥 Değerlendirme", value=f"{toplam_oy} Kişi")
                
                st.markdown(f"**Durum:** {durum_html}", unsafe_allow_html=True)
                st.markdown(f"📍 **Adres:** {adres}")

                if photos:
                    foto_url = f"https://places.googleapis.com/v1/{photos[0].get('name')}/media?maxHeightPx=400&maxWidthPx=600&key={GOOGLE_API_KEY}"
                    st.image(foto_url, use_container_width=True)
                
                # --- HATA DÜZELTİLEN ALAN (with yerine if kullanıldı) ---
                yorumları_goster = st.checkbox("💬 Mekan Yorumlarını Göster / Gizle", key=f"chk_{mekan_id}")
                if yorumları_goster:
                    # Google Canlı Yorumları
                    st.markdown("##### 🌐 Google Haritalar Kullanıcı Yorumları:")
                    if google_yorumları:
                        for g_yorum in google_yorumları[:2]:
                            yazar = g_yorum.get("authorAttribution", {}).get("displayName", "Google Kullanıcısı")
                            y_puan = g_yorum.get("rating", 5)
                            y_metni = g_yorum.get("text", {}).get("text", "")
                            zaman_metni = g_yorum.get("relativePublishTimeDescription", "Yakın zamanda")
                            if y_metni:
                                st.info(f"⭐ {y_puan}/5 | **{yazar}** ({zaman_metni})\n\n\"{y_metni}\"")
                    else:
                        st.caption("Google yorumu bulunamadı.")

                    # Uygulama İçi Yorumlar
                    st.markdown("##### 💬 Uygulama İçi Kullanıcı Yorumları:")
                    if mekan_id in tüm_yorumlar and len(tüm_yorumlar[mekan_id]) > 0:
                        for y in tüm_yorumlar[mekan_id]:
                            st.success(f"👤 **{y['isim']}** ({'⭐'*int(y['puan'])})\n\n{y['yorum']}")
                    else:
                        st.caption("Henüz buraya uygulama içinden yorum yapılmamış.")
                    
                    # Yeni Yorum Ekleme Formu
                    st.markdown("##### ✍️ Yorum Yaz:")
                    k_adi = st.text_input("Adınız", key=f"name_{mekan_id}", placeholder="İsminiz...")
                    k_yorum = st.text_area("Yorumunuz", key=f"text_{mekan_id}", placeholder="Mekan hakkındaki düşünceleriniz...")
                    k_puan = st.slider("Puanınız", 1, 5, 5, key=f"slider_{mekan_id}")
                    
                    if st.button("Yorumu Gönder", key=f"btn_{mekan_id}"):
                        if k_yorum:
                            if mekan_id not in tüm_yorumlar: tüm_yorumlar[mekan_id] = []
                            tüm_yorumlar[mekan_id].append({"isim": k_adi if k_adi else "Anonim", "yorum": k_yorum, "puan": k_puan})
                            veriyi_kaydet(YORUM_DOSYASI, tüm_yorumlar)
                            st.success("Yorumunuz başarıyla yayınlandı!")
                            st.rerun()
                # --- DÜZELTME BİTTİ ---
            st.write("") 
    else:
        st.info("Kriterlere uygun mekan bulunamadı.")

# ==================== SEKME 2: FAVORİLER ====================
with sekme_favoriler:
    st.markdown("### ❤️ Kaydettiğiniz Özel Yerler")
    if tüm_favoriler:
        for f_id, f_bilgi in list(tüm_favoriler.items()):
            with st.container(border=True):
                st.write(f"### 🏪 {f_bilgi['isim']}")
                st.caption(f"📍 {f_bilgi['adres']} | ⭐ Puan: {f_bilgi['puan']}")
                
                col_fav1, col_fav2 = st.columns(2)
                if col_fav1.button("🗺️ Haritada Konuma Git", key=f"go_map_{f_id}", use_container_width=True):
                    st.session_state.enlem = f_bilgi["lat"]
                    st.session_state.boylam = f_bilgi["lng"]
                    st.rerun()
                if col_fav2.button("❌ Favorilerden Çıkar", key=f"del_fav_{f_id}", use_container_width=True):
                    del tüm_favoriler[f_id]
                    veriyi_kaydet(FAVORILER_DOSYASI, tüm_favoriler)
                    st.rerun()
    else:
        st.info("Henüz hiçbir mekanı favorilerinize eklemediniz.")