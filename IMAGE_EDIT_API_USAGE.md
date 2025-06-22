# OpenAI Images API Edit Endpoint Integration (gpt-image-1)

Bu dokümantasyon, OpenAI Images API edit endpoint'ini kullanarak 2-4 katılımcının fotoğraflarından anti-aging uygulanmış futuristik grup selfie görselleri oluşturma özelliğini açıklar.

## 🎯 Özellikler

- **Anti-aging Efektleri**: Katılımcıları 2040 yılında doğal ve genç görünümde gösterir
- **Minimal Futuristik Aksesuarlar**: Akıllı gözlükler, minimal teknoloji takıları
- **Gerçekçi Görünüm**: Yüksek kaliteli, gerçekçi insan yüzleri ve cilt dokuları
- **Temiz Arka Plan**: Düz, sade arka plan (karmaşık manzara yok)
- **Profesyonel Atmosfer**: Başarılı ve doğal ifadeler
- **Grup Selfie**: 2-4 katılımcı için optimize edilmiş grup fotoğrafları
- **16:9 Format**: Geniş ekran oranında grup kompozisyonu
- **Çoklu Görsel Desteği**: gpt-image-1 modeli ile birden fazla görseli array olarak işleme
- **Görsel Remix**: Hikaye ve selfie görsellerini birleştirme
- **Seamless Kompozisyon**: Selfie'nin hikaye görselinin alt 1/3'ünde yer alması

## 🔧 Teknik Detaylar

### API Endpoint
```
POST https://api.openai.com/v1/images/edits
```

### Desteklenen Parametreler
- **model**: `gpt-image-1` (zorunlu)
- **image**: Array of base64 encoded images (2-16 görsel)
- **size**: `1024x576` (16:9 geniş ekran formatı)
- **quality**: `high` (yüksek kalite)
- **output_format**: `png` (PNG formatında çıktı)
- **n**: `1` (tek görsel)

### Görsel Gereksinimleri
- **Format**: PNG, WebP, JPG (desteklenir)
- **Maksimum Dosya Boyutu**: 50MB per image
- **Maksimum Görsel Sayısı**: 16 (biz 2-4 kullanıyoruz)
- **Boyut**: 1024x576 piksel (16:9 oranı, otomatik dönüştürülür)

## 📝 Kullanım

### Grup Selfie (2-4 Katılımcı)

```python
from generation import generate_group_futuristic_selfie_with_image_edit

# 2-4 katılımcı (minimum 2 gerekli)
participants = [
    MockParticipant("Ayşe Demir", "https://example.com/ayse.jpg"),
    MockParticipant("Mehmet Kaya", "https://example.com/mehmet.jpg"),
    MockParticipant("Fatma Öz", "https://example.com/fatma.jpg"),
    MockParticipant("Ali Yılmaz", "https://example.com/ali.jpg")
]

story = "Bu ekip 2040 yılında sürdürülebilir enerji çözümleri geliştiriyor."

# Grup selfie oluştur
image_data = generate_group_futuristic_selfie_with_image_edit(participants, story)
```

### Görsel Remix (Hikaye + Selfie)

```python
from generation import remix_images_with_image_edit

# Hikaye ve selfie görsellerini birleştir
story_image_data = b"story_image_binary_data"  # Hikaye görseli
selfie_image_data = b"selfie_image_binary_data"  # Selfie görseli

# Remix işlemi
final_image_data = remix_images_with_image_edit(story_image_data, selfie_image_data)
```

### Kompozisyon Detayları
- **Üst 2/3**: Hikaye görseli (futuristik teknoloji ortamı)
- **Alt 1/3**: Selfie görseli (katılımcıların grup fotoğrafı)
- **Geçiş**: Seamless ve doğal geçiş
- **Kalite**: Her iki görselin kalitesi korunur

### Katılımcı Limitleri
- **Minimum**: 2 katılımcı (zorunlu)
- **Maksimum**: 4 katılımcı (otomatik olarak ilk 4'ü alır)
- **Fotoğraf Gereksinimi**: Her katılımcının geçerli bir fotoğraf URL'si olmalı

## 🎨 Prompt Mühendisliği

### Ana Prompt Yapısı
```
Transform these [N] people into a realistic futuristic group selfie from 2040 with anti-aging effects.

Participants: [Katılımcı İsimleri]

Requirements:
- Create a realistic group selfie showing all participants together in 2040
- Apply subtle anti-aging technology to make everyone look naturally younger and more vibrant
- Add minimal futuristic clothing and accessories (smart glasses, subtle tech jewelry)
- Use plain, solid background (no complex scenery or technology)
- Maintain highly realistic appearance of all people
- Professional but approachable atmosphere
- High-quality, detailed image with realistic skin textures and facial features
- Everyone should look confident and successful but natural
- Group composition should be natural and engaging
- Ensure all participants are clearly visible and well-integrated
- Focus on realistic human appearance with subtle future enhancements
- Keep the background simple and clean

Story context: [Hikaye metni]

Create a photorealistic group selfie that shows these professionals in 2040 with subtle anti-aging technology and minimal futuristic styling, maintaining realistic human appearance.
```

## 🔄 İşlem Akışı

1. **Katılımcı Kontrolü**: 2-4 katılımcı kontrolü yapılır
2. **Fotoğraf İndirme**: Tüm katılımcı fotoğrafları URL'lerden indirilir
3. **16:9 Format Dönüştürme**: PIL kullanılarak 16:9 oranında kırpılır
4. **Boyutlandırma**: 1024x576 boyutuna getirilir (16:9 oranı)
5. **Base64 Encoding**: Tüm görseller base64'e çevrilir
6. **Array Oluşturma**: Görseller array formatında hazırlanır
7. **API Çağrısı**: gpt-image-1 modeli ile API'ye gönderilir (1024x576)
8. **Sonuç İşleme**: Base64 response'u binary data'ya çevrilir
9. **Döndürme**: Binary image data olarak döndürülür

## ⚠️ Hata Yönetimi

### Yaygın Hatalar
- **Yetersiz Katılımcı**: 2'den az katılımcı durumunda işlem durdurulur
- **API Key Eksik**: `OPENAI_API_KEY` environment variable kontrol edilir
- **Fotoğraf Erişim Hatası**: HTTP 200 olmayan yanıtlar yakalanır
- **Görsel Format Hatası**: PNG dönüştürme işlemi hata kontrolü
- **API Limit Aşımı**: Rate limiting ve timeout yönetimi (120 saniye)

### Fallback Mekanizması
- Yetersiz katılımcı durumunda `None` döndürülür
- API hatası durumunda `None` döndürülür
- Detaylı hata mesajları konsola yazdırılır
- Ana pipeline sadece hikaye görseli ile devam eder

## 🧪 Test Etme

```bash
# Test script'ini çalıştır
python test_image_edit.py
```

### Test Gereksinimleri
- `OPENAI_API_KEY` environment variable set edilmeli
- Gerçek fotoğraf URL'leri kullanılmalı (2-4 adet)
- İnternet bağlantısı gerekli

## 📊 Performans

### Zaman Aşımı
- **Fotoğraf İndirme**: 30 saniye per image
- **16:9 Format Dönüştürme**: 5 saniye per image
- **API Çağrısı**: 120 saniye (gpt-image-1 için daha uzun)
- **Toplam İşlem**: ~155-185 saniye (4 katılımcı için)

### Bellek Kullanımı
- **Görsel İşleme**: ~2.3MB per image (1024x576 PNG)
- **Base64 Encoding**: ~3.1MB per image
- **API Yanıtı**: ~1.5-3MB (1024x576 oluşturulan görsel)

## 🔒 Güvenlik

- API anahtarları environment variable'larda saklanır
- Fotoğraf URL'leri güvenli HTTP/HTTPS protokolleri kullanır
- Geçici dosyalar otomatik olarak temizlenir
- Base64 encoding güvenli veri transferi sağlar

## 🚀 gpt-image-1 Avantajları

### DALL-E 2'ye Göre Üstünlükler
- **Çoklu Görsel Desteği**: Birden fazla görseli array olarak işleyebilir
- **Daha Uzun Prompt**: 32,000 karaktere kadar prompt desteği
- **Yüksek Kalite**: Daha detaylı ve kaliteli görsel üretimi
- **Gelişmiş Kompozisyon**: Grup fotoğrafları için daha iyi kompozisyon
- **Base64 Response**: Doğrudan görsel data erişimi

### Sınırlamalar
- **Daha Yavaş**: İşlem süresi daha uzun (120 saniye)
- **Daha Pahalı**: API maliyeti daha yüksek
- **Karmaşık Setup**: Çoklu görsel işleme gerektirir

## 📞 Destek

Herhangi bir sorun yaşarsanız:
1. Hata mesajlarını kontrol edin
2. API anahtarınızın geçerli olduğundan emin olun
3. En az 2 katılımcı fotoğrafı olduğunu doğrulayın
4. Fotoğraf URL'lerinin erişilebilir olduğunu kontrol edin
5. İnternet bağlantınızı kontrol edin
6. gpt-image-1 modelinin hesabınızda aktif olduğunu doğrulayın 