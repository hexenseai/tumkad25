# TUMKAD AI Gelecek Vizyonu Projesi

TUMKAD (Tüm Mühendis Kadınlar Derneği) için yapay zeka destekli gelecek vizyonu projesi. Katılımcıların gelecek vizyonlarını birleştirerek AI destekli hikayeler ve görseller üretir.

## 🚀 Özellikler

- **Katılımcı kayıt sistemi**: WhatsApp numarası ile kayıt
- **AI destekli hikaye üretimi**: Katılımcıların gelecek vizyonlarını birleştiren hikayeler
- **Lumalabs.ai entegrasyonu**: Gerçekçi görsel üretimi
- **Google Cloud Storage**: Güvenli dosya depolama
- **Admin paneli**: Katılımcı ve hikaye yönetimi
- **Paylaşım sistemi**: Hikaye ve görsel paylaşım linkleri

## 📋 Gereksinimler

- Python 3.8+
- Google Cloud Platform hesabı
- Lumalabs.ai API anahtarı
- Flask framework

## 🛠️ Kurulum

### 1. Projeyi Klonlayın
```bash
git clone https://github.com/your-username/tumkad25.git
cd tumkad25
```

### 2. Sanal Ortam Oluşturun
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Google Cloud Kurulumu

#### a) Google Cloud Project Oluşturun
1. [Google Cloud Console](https://console.cloud.google.com/)'a gidin
2. Yeni proje oluşturun
3. Cloud Storage API'yi etkinleştirin
4. Vertex AI API'yi etkinleştirin

#### b) Service Account Oluşturun
1. IAM & Admin > Service Accounts
2. Yeni service account oluşturun
3. Gerekli izinleri verin:
   - Storage Object Admin
   - Vertex AI User
4. JSON key dosyası indirin
5. `api-project-*.json` olarak proje klasörüne koyun

#### c) GCS Bucket Oluşturun
1. Cloud Storage > Buckets
2. Yeni bucket oluşturun (örn: `tumkad25-storage`)
3. Private olarak ayarlayın

### 5. Environment Variables Ayarlayın

#### Windows
```cmd
set GOOGLE_CLOUD_PROJECT=your-project-id
set GCS_BUCKET_NAME=your-bucket-name
set LUMALABS_API_KEY=your-lumalabs-api-key
```

#### Linux/Mac
```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GCS_BUCKET_NAME=your-bucket-name
export LUMALABS_API_KEY=your-lumalabs-api-key
```

### 6. Veritabanını Başlatın
```bash
python app.py
```

## 🔧 Konfigürasyon

### Environment Variables

| Değişken | Açıklama | Örnek |
|----------|----------|-------|
| `GOOGLE_CLOUD_PROJECT` | Google Cloud Project ID | `api-project-974861835731` |
| `GCS_BUCKET_NAME` | GCS Bucket adı | `tumkad25-storage` |
| `LUMALABS_API_KEY` | Lumalabs.ai API anahtarı | `luma-xxx-xxx-xxx` |

### API Anahtarları

#### Lumalabs.ai
1. [Lumalabs.ai](https://lumalabs.ai/)'ye kayıt olun
2. API anahtarınızı alın
3. Environment variable olarak ayarlayın

## 🎯 Kullanım

### 1. Uygulamayı Başlatın
```bash
python app.py
```

### 2. Tarayıcıda Açın
```
http://localhost:5000
```

### 3. Katılımcı Kaydı
- `/register` sayfasından katılımcı kaydı yapın
- WhatsApp numaralarını girin
- Fotoğraf yükleyin

### 4. Hikaye Üretimi
- `/generate_story` sayfasından hikaye üretin
- WhatsApp numaralarını girin
- AI hikaye ve görsel üretecek

### 5. Admin Paneli
- `/admin_login` ile giriş yapın
- Şifre: `tumkad25`
- Katılımcıları ve hikayeleri yönetin

## 📁 Proje Yapısı

```
tumkad25/
├── app.py                 # Ana Flask uygulaması
├── generation.py          # AI hikaye ve görsel üretimi
├── gcs.py                # Google Cloud Storage işlemleri
├── utils.py              # Yardımcı fonksiyonlar
├── requirements.txt      # Python bağımlılıkları
├── templates/            # HTML şablonları
├── static/              # CSS, JS, resimler
└── instance/            # Veritabanı dosyaları
```

## 🔧 API Entegrasyonları

### Google Cloud Services
- **Cloud Storage**: Dosya depolama
- **Vertex AI**: Hikaye üretimi
- **Service Account**: Güvenli erişim

### Lumalabs.ai
- **Character Reference**: Gerçekçi görsel üretimi
- **Asenkron API**: Görsel üretimi
- **Signed URLs**: Güvenli dosya erişimi

## 🎯 Hikaye Üretim Süreci

1. **Katılımcı Analizi**: Gelecek vizyonları analiz edilir
2. **Ortak Temalar**: Vizyonlar birleştirilir
3. **Hikaye Oluşturma**: AI destekli hikaye üretilir
4. **Görsel Üretimi**: Lumalabs.ai ile görsel oluşturulur
5. **Paylaşım**: Hikaye ve görsel paylaşılır

## 🔧 Admin Paneli

- `/admin_login`: Admin girişi
- `/admin`: Katılımcı listesi
- `/admin_stories`: Hikaye yönetimi
- `/debug_descriptions`: Debug araçları

## 🔧 Sorun Giderme

### GCS Bağlantı Sorunları
1. Credentials dosyasının doğru konumda olduğunu kontrol edin
2. GCS bucket'ının oluşturulduğunu kontrol edin
3. Service account'ın gerekli izinlere sahip olduğunu kontrol edin

### Lumalabs.ai Sorunları
1. API key'in doğru olduğunu kontrol edin
2. Signed URL'lerin çalıştığını kontrol edin
3. Character Reference için referans görsellerin mevcut olduğunu kontrol edin

### Veritabanı Sorunları
1. `instance/` klasörünün yazılabilir olduğunu kontrol edin
2. SQLite dosyasının oluşturulduğunu kontrol edin

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 📞 İletişim

TUMKAD - Tüm Mühendis Kadınlar Derneği
- Website: [tumkad.org](https://tumkad.org)
- Email: info@tumkad.org

## 🙏 Teşekkürler

- Flask framework
- Bootstrap CSS framework
- Font Awesome icons
- Google Cloud Platform
- Lumalabs.ai
- Tüm katkıda bulunanlara 