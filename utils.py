import io
import os
from PIL import Image
from gcs import create_signed_url

def normalize_phone(phone):
    digits = ''.join(filter(str.isdigit, phone or ''))
    if digits.startswith('0'):
        digits = digits[1:]
    # Türkiye numarası ise ve 10 haneli ise başına 90 ekle
    if len(digits) == 10 and digits.startswith('5'):
        digits = '90' + digits
    return digits


def get_participant_reference_images(participants):
    """
    Katılımcıların fotoğraflarını referans görsel olarak hazırlar.
    GCS URL'leri için signed URL oluşturur.
    """
    reference_images = []
    
    for participant in participants:
        if participant.photo_path and participant.photo_path.startswith('https://storage.googleapis.com/'):
            # GCS URL'si için signed URL oluştur
            signed_url = create_signed_url(participant.photo_path, expiration_minutes=60)
            if signed_url:
                reference_images.append({
                    'name': participant.name,
                    'image_url': signed_url
                })
                print(f"Signed URL created for {participant.name}: {signed_url[:50]}...", flush=True)
            else:
                print(f"Failed to create signed URL for {participant.name}", flush=True)
        else:
            print(f"No valid GCS URL for {participant.name}: {participant.photo_path}", flush=True)
    
    return reference_images


def apply_template_to_image_data(image_data):
    """
    Üretilen görsele şablonu uygular.
    final_image_data'yı 2:3 oranında yerleştirir ve 9:16 canvas'ın ortasında konumlandırır.
    """
    try:
        # AI görselini yükle
        ai_img = Image.open(io.BytesIO(image_data))
        ai_img = ai_img.convert('RGBA')
        
        # AI görselini 2:3 oranında işle (1080x1620)
        ai_img = ai_img.resize((1080, 1620), Image.Resampling.LANCZOS)
        
        # 9:16 boyutunda canvas oluştur (1080x1920)
        canvas = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
        
        # AI görselini canvas'ın ortasında konumlandır
        # 1920 - 1620 = 300 pixel boşluk, 150 pixel üstte 150 pixel altta
        y_position = 150
        canvas.paste(ai_img, (0, y_position), ai_img)
        
        # Şablonu yükle
        template_path = os.path.join('static', 'images', 'Gorsel-sablon.png')
        if os.path.exists(template_path):
            template_img = Image.open(template_path).convert('RGBA')
            template_img = template_img.resize((1080, 1920), Image.Resampling.LANCZOS)
            
            # Şablonu canvas'ın üzerine yerleştir
            final_image = Image.alpha_composite(canvas, template_img)
            
            # Son çıktıyı bytes olarak kaydet
            final_image_buffer = io.BytesIO()
            final_image.convert('RGB').save(final_image_buffer, format='PNG')
            return final_image_buffer.getvalue()
        
        return image_data
        
    except Exception as e:
        print(f"Template application error: {e}", flush=True)
        return image_data
