from google.cloud import storage
import os
import tempfile
from datetime import datetime, timedelta
import uuid

# Google Cloud Storage konfigürasyonu
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'tumkad25-storage')
GCS_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', 'api-project-974861835731')

# Yerel dosya sistemi için klasörler
LOCAL_UPLOAD_FOLDER = 'local_uploads'
LOCAL_GENERATED_FOLDER = 'local_generated'

# Yerel klasörleri oluştur
os.makedirs(LOCAL_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOCAL_GENERATED_FOLDER, exist_ok=True)

# GCS client'ı başlat
bucket = None
try:
    # Google Cloud credentials kontrol et
    credentials_path = os.path.join(os.getcwd(), 'api-project-974861835731-14fb4124b1b2.json')
    if os.path.exists(credentials_path):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        print(f"Google Cloud credentials loaded from: {credentials_path}")
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    print(f"GCS bucket '{GCS_BUCKET_NAME}' başarıyla bağlandı")
except Exception as e:
    print(f"GCS bucket bağlantı hatası: {e}")
    print("Yerel dosya sistemi kullanılacak")
    bucket = None


# GCS Dosya İşlemleri Yardımcı Fonksiyonları
def upload_to_gcs(file_data, filename, folder='uploads'):
    """
    Dosyayı GCS'e yükler ve public URL döndürür.
    GCS bağlantısı yoksa yerel dosya sistemi kullanır.
    """
    try:
        if bucket:
            # GCS kullan
            gcs_path = f"{folder}/{filename}"
            blob = bucket.blob(gcs_path)
            blob.upload_from_string(file_data, content_type='image/png')
            public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{gcs_path}"
            print(f"Dosya GCS'e yüklendi: {public_url}")
            return public_url
        else:
            # Yerel dosya sistemi kullan
            local_folder = LOCAL_UPLOAD_FOLDER if folder == 'uploads' else LOCAL_GENERATED_FOLDER
            local_path = os.path.join(local_folder, filename)
            
            with open(local_path, 'wb') as f:
                f.write(file_data)
            
            # Yerel URL oluştur
            local_url = f"/local_files/{folder}/{filename}"
            print(f"Dosya yerel olarak kaydedildi: {local_path}")
            return local_url
        
    except Exception as e:
        print(f"Upload error: {e}")
        return None

def download_from_gcs(gcs_url):
    """
    GCS'den dosyayı indirir ve geçici dosya olarak kaydeder.
    """
    try:
        if bucket and gcs_url.startswith('https://storage.googleapis.com/'):
            # GCS'den indir
            if gcs_url.startswith(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/"):
                blob_path = gcs_url.replace(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/", "")
            else:
                blob_path = gcs_url
            
            blob = bucket.blob(blob_path)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            blob.download_to_filename(temp_file.name)
            return temp_file.name
        else:
            # Yerel dosyadan oku
            if gcs_url.startswith('/local_files/'):
                local_path = gcs_url.replace('/local_files/', '')
                if local_path.startswith('uploads/'):
                    full_path = os.path.join(LOCAL_UPLOAD_FOLDER, local_path.replace('uploads/', ''))
                elif local_path.startswith('generated/'):
                    full_path = os.path.join(LOCAL_GENERATED_FOLDER, local_path.replace('generated/', ''))
                else:
                    full_path = local_path
                
                if os.path.exists(full_path):
                    return full_path
                else:
                    print(f"Local file not found: {full_path}")
                    return None
        
    except Exception as e:
        print(f"Download error: {e}")
        return None

def delete_from_gcs(gcs_url):
    """
    GCS'den dosyayı siler.
    """
    try:
        if bucket and gcs_url.startswith('https://storage.googleapis.com/'):
            # GCS'den sil
            if gcs_url.startswith(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/"):
                blob_path = gcs_url.replace(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/", "")
            else:
                blob_path = gcs_url
            
            blob = bucket.blob(blob_path)
            blob.delete()
            print(f"Dosya GCS'den silindi: {gcs_url}")
            return True
        else:
            # Yerel dosyayı sil
            if gcs_url.startswith('/local_files/'):
                local_path = gcs_url.replace('/local_files/', '')
                if local_path.startswith('uploads/'):
                    full_path = os.path.join(LOCAL_UPLOAD_FOLDER, local_path.replace('uploads/', ''))
                elif local_path.startswith('generated/'):
                    full_path = os.path.join(LOCAL_GENERATED_FOLDER, local_path.replace('generated/', ''))
                else:
                    full_path = local_path
                
                if os.path.exists(full_path):
                    os.remove(full_path)
                    print(f"Yerel dosya silindi: {full_path}")
                    return True
                else:
                    print(f"Local file not found: {full_path}")
                    return False
        
    except Exception as e:
        print(f"Delete error: {e}")
        return False

def get_gcs_file_url(filename, folder='uploads'):
    """
    Dosya adından GCS URL'si oluşturur.
    """
    if bucket:
        return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{folder}/{filename}"
    else:
        return f"/local_files/{folder}/{filename}"

def create_signed_url(gcs_url, expiration_minutes=60):
    """
    GCS dosyası için signed URL oluşturur.
    Lumalabs.ai gibi harici servisler için geçici erişim sağlar.
    """
    try:
        if bucket and gcs_url.startswith('https://storage.googleapis.com/'):
            # GCS signed URL oluştur
            if gcs_url.startswith(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/"):
                blob_path = gcs_url.replace(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/", "")
            else:
                blob_path = gcs_url
            
            blob = bucket.blob(blob_path)
            
            if not blob.exists():
                print(f"Blob does not exist: {blob_path}")
                return None
            
            expiration = datetime.utcnow() + timedelta(minutes=expiration_minutes)
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET"
            )
            
            print(f"Signed URL created for {blob_path}")
            return signed_url
        else:
            # Yerel dosya için doğrudan URL döndür
            return gcs_url
        
    except Exception as e:
        print(f"Signed URL creation error: {e}")
        return None
