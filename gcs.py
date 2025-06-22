import os
import tempfile
from datetime import datetime, timedelta
import uuid

# Yerel dosya sistemi için klasörler
LOCAL_UPLOAD_FOLDER = 'local_uploads'
LOCAL_GENERATED_FOLDER = 'local_generated'

# Yerel klasörleri oluştur
os.makedirs(LOCAL_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOCAL_GENERATED_FOLDER, exist_ok=True)

print("Local storage system initialized")

# Local Dosya İşlemleri Yardımcı Fonksiyonları
def upload_to_gcs(file_data, filename, folder='uploads'):
    """
    Dosyayı yerel dosya sistemine kaydeder ve URL döndürür.
    """
    try:
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

def download_from_gcs(local_url):
    """
    Yerel dosyadan dosyayı okur.
    """
    try:
        # Yerel dosyadan oku
        if local_url.startswith('/local_files/'):
            local_path = local_url.replace('/local_files/', '')
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

def delete_from_gcs(local_url):
    """
    Yerel dosyayı siler.
    """
    try:
        # Yerel dosyayı sil
        if local_url.startswith('/local_files/'):
            local_path = local_url.replace('/local_files/', '')
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
    Dosya adından yerel URL oluşturur.
    """
    return f"/local_files/{folder}/{filename}"

def create_signed_url(local_url, expiration_minutes=60):
    """
    Yerel dosya için doğrudan URL döndürür.
    """
    try:
        # Yerel dosya için doğrudan URL döndür
        return local_url
        
    except Exception as e:
        print(f"Signed URL creation error: {e}")
        return None
