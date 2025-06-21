from google.cloud import storage
import os
import tempfile
from datetime import datetime, timedelta

# Google Cloud Storage konfigürasyonu
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'tumkad25-storage')
GCS_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', 'api-project-974861835731')

# GCS client'ı başlat
try:
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    print(f"GCS bucket '{GCS_BUCKET_NAME}' başarıyla bağlandı")
except Exception as e:
    print(f"GCS bucket bağlantı hatası: {e}")
    bucket = None


# GCS Dosya İşlemleri Yardımcı Fonksiyonları
def upload_to_gcs(file_data, filename, folder='uploads'):
    """
    Dosyayı GCS'e yükler ve public URL döndürür.
    """
    try:
        if not bucket:
            print("GCS bucket bağlantısı yok")
            return None
        
        # GCS'de dosya yolu oluştur
        gcs_path = f"{folder}/{filename}"
        blob = bucket.blob(gcs_path)
        
        # Dosyayı yükle
        blob.upload_from_string(file_data, content_type='image/png')
        
        # Public URL oluştur
        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{gcs_path}"
        
        print(f"Dosya GCS'e yüklendi: {public_url}")
        return public_url
        
    except Exception as e:
        print(f"GCS upload error: {e}")
        return None

def download_from_gcs(gcs_url):
    """
    GCS'den dosyayı indirir ve geçici dosya olarak kaydeder.
    """
    try:
        if not bucket:
            print("GCS bucket bağlantısı yok")
            return None
        
        # URL'den blob path'ini çıkar
        if gcs_url.startswith(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/"):
            blob_path = gcs_url.replace(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/", "")
        else:
            blob_path = gcs_url
        
        blob = bucket.blob(blob_path)
        
        # Geçici dosya oluştur
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        blob.download_to_filename(temp_file.name)
        
        return temp_file.name
        
    except Exception as e:
        print(f"GCS download error: {e}")
        return None

def delete_from_gcs(gcs_url):
    """
    GCS'den dosyayı siler.
    """
    try:
        if not bucket:
            print("GCS bucket bağlantısı yok")
            return False
        
        # URL'den blob path'ini çıkar
        if gcs_url.startswith(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/"):
            blob_path = gcs_url.replace(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/", "")
        else:
            blob_path = gcs_url
        
        blob = bucket.blob(blob_path)
        blob.delete()
        
        print(f"Dosya GCS'den silindi: {gcs_url}")
        return True
        
    except Exception as e:
        print(f"GCS delete error: {e}")
        return False

def get_gcs_file_url(filename, folder='uploads'):
    """
    Dosya adından GCS URL'si oluşturur.
    """
    return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{folder}/{filename}"

def create_signed_url(gcs_url, expiration_minutes=60):
    """
    GCS dosyası için signed URL oluşturur.
    Lumalabs.ai gibi harici servisler için geçici erişim sağlar.
    """
    try:
        if not bucket:
            print("GCS bucket bağlantısı yok")
            return None
        
        # URL'den blob path'ini çıkar
        if gcs_url.startswith(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/"):
            blob_path = gcs_url.replace(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/", "")
        else:
            blob_path = gcs_url
        
        blob = bucket.blob(blob_path)
        
        # Blob'un var olup olmadığını kontrol et
        if not blob.exists():
            print(f"Blob does not exist: {blob_path}")
            return None
        
        # Signed URL oluştur
        expiration = datetime.utcnow() + timedelta(minutes=expiration_minutes)
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=expiration,
            method="GET"
        )
        
        print(f"Signed URL created for {blob_path}")
        return signed_url
        
    except Exception as e:
        print(f"Signed URL creation error: {e}")
        return None
