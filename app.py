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

# --- 📏 MESAFE HESAPLAMA (Haversine Formülü) ---
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

# --- 🛰️ GOOGLE PLACES API BAĞLANTISI (Yorumlar Alanı Eklendi) ---
def google_mekanlari_kesfet(lat, lon, kategori_turu):
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        # 🌟 KRİTİK: Maskeye 'places.reviews' ekleyerek Google yorumlarını da istiyoruz
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

st.title("🗺️ MekanBul: Keşif Platformu")

# 📱 TABS (SEKMELER) MANTIĞI
sekme_kesfet, sekme_favoriler = st.tabs(["🔍 Etrafımı Keşfet", "❤️ Favori Mekanlarım"])

tüm_yorumlar = veriyi_yukle(YORUM_DOSYASI)
tüm_favoriler = veriyi_yukle(FAVORILER_DOSYASI)

# ==================== SEKME 1: KEŞFET ====================
with sekme_kesfet:
    
    st.write("🔍 **Gitmek İstediğiniz Yeri Aratın:**")
    arama_kutusu = st.text_input("Örn: Kadıköy, Alsancak, Beşiktaş veya Şehir ismi...", placeholder="Yazın ve Ara'ya basın...", key="arama_input")
    if st.button("Haritada Ara & Işınlan"):
        if arama_kutusu:
            arama_sonucu = google_ile_konum_ara(arama_kutusu)
            if arama_sonucu:
                yeni_lat, yeni_lon, tam_ad = arama_sonucu
                st.session_state.enlem = yeni_lat
                st.session_state.boylam = yeni_lon
                st.success(f"📍 Şuraya ışınlanıldı: {tam_ad}")
                st.rerun()
            else:
                st.error("Aradığınız konum bulunamadı. Lütfen daha belirgin yazın.")
        else:
            st.warning("Lütfen aramak istediğiniz yeri yazın.")

    st.markdown("---")
    
    # 📌 KATEGORİ SEÇİM ALANI
    st.write("📌 **Ne Arıyorsunuz?**")
    kat_kolonlari = st.columns(5)
    
    kategoriler = [
        {"etiket": "☕ Kafe", "api_adi": "cafe", "icon": "coffee"},
        {"etiket": "🍔 Restoran", "api_adi": "restaurant", "icon": "cutlery"},
        {"etiket": "💊 Eczane", "api_adi": "pharmacy", "icon": "plus-sign"},
        {"etiket": "🏨 Otel", "api_adi": "hotel", "icon": "home"},
        {"etiket": "⛽ Akaryakıt", "api_adi": "gas_station", "icon": "road"}
    ]
    
    if 'secili_kategori' not in st.session_state:
        st.session_state.secili_kategori = "restaurant"
        
    for i, kat in enumerate(kategoriler):
        if kat_kolonlari[i].button(kat["etiket"]):
            st.session_state.secili_kategori = Math = kat["api_adi"]
            st.rerun()

    # 🔀 FİLTRELEME VE SIRALAMA BARLARI
    st.markdown("---")
    fil_col1, fil_col2 = st.columns(2)
    
    sirala_secim = fil_col1.selectbox(
        "Sıralama Ölçütü", 
        ["Mesafeye Göre (En Yakın)", "Puana Göre (En Yüksek)", "Yorum Sayısına Göre (En Popüler)"]
    )
    sadece_aciklar = fil_col2.checkbox("🟢 Sadece Şu An Açık Olanlar")

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
    st.write("📍 **Haritadaki Konumunuz:**")
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

    harita_verisi = st_folium(m, width=350, height=300)
    if harita_verisi and harita_verisi.get("last_clicked"):
        st.session_state.enlem = harita_verisi["last_clicked"]["lat"]
        st.session_state.boylam = harita_verisi["last_clicked"]["lng"]
        st.rerun()

    # MEKAN LİSTELEME ALANI
    st.subheader(f"✨ Sonuçlar ({len(islenmis_mekanlar)} Mekan Listelendi)")
    
    if islenmis_mekanlar:
        for mekan in islenmis_mekanlar:
            mekan_id = mekan.get("id")
            isim = mekan.get("displayName", {}).get("text", "Bilinmeyen Yer")
            g_puan = mekan.get("rating", "-")
            toplam_oy = mekan.get("userRatingCount", 0)
            adres = mekan.get("formattedAddress", "Adres yok.")
            photos = mekan.get("photos", [])
            open_now = mekan.get("currentOpeningHours", {}).get("openNow", None)
            google_yorumları = mekan.get("reviews", []) # 🌟 Google yorum listesi
            
            durum_metni = "🟢 Açık" if open_now is True else "🔴 Kapalı" if open_now is False else "⏳ Bilgi Yok"
            
            with st.expander(f"🏪 {isim} ({mekan['uzaklik_metni']}) — ⭐ {g_puan}"):
                
                # ❤️ FAVORİ BUTONU
                fav_durum = "❤️ Favorilerimde" if mekan_id in tüm_favoriler else "🤍 Favorilerime Ekle"
                if st.button(fav_durum, key=f"fav_btn_{mekan_id}"):
                    if mekan_id in tüm_favoriler:
                        del tüm_favoriler[mekan_id]
                    else:
                        tüm_favoriler[mekan_id] = {"isim": isim, "adres": adres, "puan": g_puan, "lat": mekan.get("location", {}).get("latitude"), "lng": mekan.get("location", {}).get("longitude")}
                    veriyi_kaydet(FAVORILER_DOSYASI, tüm_favoriler)
                    st.rerun()

                if photos:
                    foto_url = f"https://places.googleapis.com/v1/{photos[0].get('name')}/media?maxHeightPx=300&maxWidthPx=400&key={GOOGLE_API_KEY}"
                    st.image(foto_url, use_container_width=True)
                
                st.write(f"📍 **Adres:** {adres}")
                st.write(f"⏰ **Durum:** {durum_metni} | 👥 **Google Popülerliği:** {toplam_oy} Değerlendirme")
                
                # 🌟 YENİ: GOOGLE CANLI YORUMLARI GÖSTERME ALANI 🌟
                st.markdown("---")
                st.write("🌐 **Google Haritalar Kullanıcı Yorumları:**")
                if google_yorumları:
                    # En fazla 3 yorum gösterelim (Sayfa şişmesin diye)
                    for g_yorum in google_yorumları[:3]:
                        yazar = g_yorum.get("authorAttribution", {}).get("displayName", "Google Kullanıcısı")
                        y_puan = g_yorum.get("rating", 5)
                        y_metni = g_yorum.get("text", {}).get("text", "")
                        zaman_metni = g_yorum.get("relativePublishTimeDescription", "Yakın zamanda")
                        
                        if y_metni: # Eğer boş yorum değilse göster
                            st.warning(f"⭐ {y_puan}/5 | 👤 **{yazar}** ({zaman_metni})\n\n\"{y_metni}\"")
                else:
                    st.caption("Google'dan bu mekan için yorum alınamadı.")

                # Uygulama İçi Yerel Yorumlar
                st.markdown("---")
                st.write("💬 **Uygulama İçi Kullanıcı Yorumları:**")
                if mekan_id in tüm_yorumlar and len(tüm_yorumlar[mekan_id]) > 0:
                    for y in tüm_yorumlar[mekan_id]:
                        st.info(f"👤 **{y['isim']}** ({'⭐'*int(y['puan'])})\n\n{y['yorum']}")
                else:
                    st.caption("Henüz buraya uygulama içinden yorum yapılmamış. İlk yorumu siz yapın!")
                
                st.write("✍_ **Yorum Ekle:**")
                k_adi = st.text_input("Adınız", key=f"name_{mekan_id}")
                k_yorum = st.text_area("Yorumunuz", key=f"text_{mekan_id}")
                k_puan = st.slider("Puanınız", 1, 5, 5, key=f"slider_{mekan_id}")
                
                if st.button("Yorumu Gönder", key=f"btn_{mekan_id}"):
                    if k_yorum:
                        if mekan_id not in tüm_yorumlar: tüm_yorumlar[mekan_id] = []
                        tüm_yorumlar[mekan_id].append({"isim": k_adi if k_adi else "Anonim", "yorum": k_yorum, "puan": k_puan})
                        veriyi_kaydet(YORUM_DOSYASI, tüm_yorumlar)
                        st.success("Yorum eklendi!")
                        st.rerun()
    else:
        st.info("Kriterlere uygun mekan bulunamadı.")

# ==================== SEKME 2: FAVORİLER ====================
with sekme_favoriler:
    st.subheader("❤️ Kaydettiğiniz Yerler")
    if tüm_favoriler:
        for f_id, f_bilgi in list(tüm_favoriler.items()):
            with st.container(border=True):
                st.write(f"### 🏪 {f_bilgi['isim']}")
                st.write(f"⭐ Google Puanı: {f_bilgi['puan']} | 📍 Adres: {f_bilgi['adres']}")
                
                col_fav1, col_fav2 = st.columns(2)
                if col_fav1.button("🗺️ Haritada Bu Konuma Git", key=f"go_map_{f_id}"):
                    st.session_state.enlem = f_bilgi["lat"]
                    st.session_state.boylam = f_bilgi["lng"]
                    st.rerun()
                if col_fav2.button("❌ Favorilerden Çıkar", key=f"del_fav_{f_id}"):
                    del tüm_favoriler[f_id]
                    veriyi_kaydet(FAVORILER_DOSYASI, tüm_favoriler)
                    st.rerun()
    else:
        st.info("Henüz hiçbir mekanı favorilerinize eklemediniz.")