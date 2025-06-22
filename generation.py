# Generation module for collaborative story creation
import requests
import os
import base64
import time
import json
from utils import apply_template_to_image_data
from gcs import download_from_gcs
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API konfigürasyonu - basit requests kullanarak
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

def call_openai_api(messages, model="gpt-4o", max_tokens=500, temperature=0.8):
    """
    OpenAI API'yi doğrudan requests ile çağırır
    """
    try:
        if not OPENAI_API_KEY:
            return None
            
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            print(f"OpenAI API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"OpenAI API call error: {e}")
        return None

def call_gpt4_vision_api(messages, model="gpt-4o", max_tokens=1000, temperature=0.7):
    """
    GPT-4 Vision API'yi doğrudan requests ile çağırır
    """
    try:
        if not OPENAI_API_KEY:
            return None
            
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            print(f"GPT-4 Vision API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"GPT-4 Vision API call error: {e}")
        return None

def generate_futuristic_selfie_with_image_edit(participants, story):
    """
    Bu fonksiyon artık kullanılmıyor. Sadece grup selfie destekleniyor.
    En az 2 katılımcı gerekli.
    """
    print("Single participant selfie is deprecated. Using group selfie instead.")
    return generate_group_futuristic_selfie_with_image_edit(participants, story)

def generate_individual_vision_story(participant):
    """
    Adım 1: Her katılımcı için ayrı ayrı gelecek vizyonu hikayesi oluşturur.
    """
    try:
        if not OPENAI_API_KEY:
            print("OpenAI API key not configured")
            return f"{participant.name} teknoloji alanında uzmanlaşmış bir kadın mühendis olarak 2040 yılında {participant.future_impact} vizyonunu gerçekleştirmeyi planlıyor."
        
        prompt = f"""
        Bu kişinin bilgilerini analiz ederek, 2035 yılında gerçekleştirmek istediği gelecek vizyonunun tanımlamasını oluştur. Neyi yapmak istediğini ve nasıl bir dönüşüm başlatmak istediğini *kişi bilgilerini* kullanarak detaylandır.
        
        Kişi Bilgileri:
        - İsim: {participant.name}
        - Meslek/Uzmanlık: {participant.profession}
        - Sektör: {participant.sector}
        - Teknik İlgi Alanı: {participant.technical_interest}
        - Gelecek Vizyonu (2035): {participant.future_impact}
        
        Görev:
        1. Bu kişinin verdiği bilgileri analiz et.
        2. 2035 yılında bu kişinin nasıl bir vizyon ile nasıl bir dönüşüm başlatmak istediğini anla.
        3. 1 paragraf uzunluğunda özet bir şekilde yaz.
        4. Anlatım gerçekçi ama vizyoner olmalı
        5. Kişinin güçlü yanlarını vizyonu güçlendirecek şekilde kullan.
        6. Teknoloji ile birlikte inovasyon temasını işle
        7. Türkçe yaz
        
        Gelecek vizyonu metni, bu kişinin 2035'te nasıl bir teknoloji ile inovatif dönüşüm hayal ettiğini ve bunun parçası olabileceğini(uzman ya da öncüsü) göstermeli.
        """
        
        messages = [
            {"role": "system", "content": "Sen katılımcıların gelecek vizyonlarını daha kapsamlı ve düzgün hale getiren bir AI asistanısın. Her kişinin potansiyelini analiz ederek 2035 yılında gerçekleştirmek istediği vizyonu daha iyi şekilde tanımla."},
            {"role": "user", "content": prompt}
        ]
        
        story = call_openai_api(messages, max_tokens=500, temperature=0.8)
        return story if story else f"{participant.name} teknoloji alanında uzmanlaşmış bir kadın mühendis olarak 2040 yılında {participant.future_impact} vizyonunu gerçekleştirmeyi planlıyor."
        
    except Exception as e:
        print(f"Individual vision story generation error: {e}")
        return f"{participant.name} teknoloji alanında uzmanlaşmış bir profesyonel olarak 2040 yılında {participant.future_impact} hedefini gerçekleştirmeyi planlıyor."

def create_collaborative_future_story(individual_stories):
    """
    Adım 2: Katılımcıların bireysel hikayelerini birleştirerek ortak gelecek vizyonu hikayesi oluşturur.
    """
    try:
        if not OPENAI_API_KEY:
            print("OpenAI API key not configured")
            return "Katılımcılar birlikte geleceği şekillendiren bir teknoloji projesi geliştirdi."
        
        stories_text = "\n\n".join([f"{name}:\n{story}" for name, story in individual_stories])
        
        prompt = f"""
        Bu katılımcıların bireysel gelecek vizyonlarını analiz ederek, 2035 yılında birlikte gerçekleştirebilecekleri ortak bir gelecek vizyonu hikayesi oluştur.
        
        Bireysel Vizyonlar:
        {stories_text}
        
        Görev:
        1. Her katılımcının vizyonunu analiz et
        2. Bu vizyonların nasıl birleşebileceğini ve birbirini nasıl tamamlayabileceğini bul
        3. Ortak bir gelecek vizyonu oluştur - kişisel detaylardan ziyade vizyonların birleşimi önemli
        4. 2035 yılında geçen, dünyayı değiştiren bir teknoloji destekli inovasyon projesi hikayesi yaz.
        5. Hikaye 1 paragraf uzunluğunda olmalı.
        6. Türkçe yaz
        7. Hikaye şu yapıda olmalı:
           - Hedef: Teknolojik zorluklar ve vizyonların nasıl bir araya geldiği.
           - Proje: Başarı hikayesinin nasıl bir proje ile gerçekleştirileceği.
           - Sonuç: Proje sonucunda neyi nasıl yaparak dünyayı değiştirir.
        
        ÖNEMLİ: Kişisel detaylar ve kişilerin rolünden ziyade vizyonların birleşiminden gelecek için daha iyi bir vizyon oluştur. 
        Hikaye, bu vizyonların nasıl birleşerek daha güçlü bir gelecek vizyonu oluşturduğunu göstermeli.
        """
        
        messages = [
            {"role": "system", "content": "Sen gelecek vizyonlarını birleştiren bir AI asistanısın. Farklı vizyonları analiz ederek ortak bir gelecek hikayesi oluşturursun."},
            {"role": "user", "content": prompt}
        ]
        
        story = call_openai_api(messages, max_tokens=800, temperature=0.8)
        return story if story else "Katılımcılar birlikte geleceği şekillendiren bir teknoloji projesi geliştirdi."
        
    except Exception as e:
        print(f"Collaborative story generation error: {e}")
        return "Katılımcılar birlikte geleceği şekillendiren bir teknoloji projesi geliştirdi."

def create_story_visual_prompt(story):
    """
    Adım 3: Hikayeyi görsel bir karede anlatabilecek photorealistic gelecek vizyonunu iyi betimleyen prompt oluşturur.
    """
    try:
        if not OPENAI_API_KEY:
            print("OpenAI API key not configured")
            return "Photorealistic futuristic technology workspace in 2035, innovative project visualization, holographic displays, advanced equipment, professional lighting"
        
        prompt = f"""
        Bu hikayeden yola çıkarak, hikayeyi görsel bir karede anlatabilecek photorealistic gelecek vizyonunu iyi betimleyen bir prompt oluştur.
        
        Hikaye:
        {story}
        
        Görsel Prompt Gereksinimleri:
        - 2:3 oranında (portrait format)
        - Photorealistic, yüksek kaliteli.
        - Kişi isimlerine yer verme.
        - Gerçekçi yapıda, ilüstratif görsel oluştur.
        - 2035 yılı futuristik teknoloji ortamı
        - Hikayenin içeriğini ve vizyonunu illustre eden görsel elementler
        - Teknoloji ile toplumsal ilerleme ve yenilik teması
        - Projenin dünya üzerindeki etkisini gösteren görsel ipuçları.
        - Dramatik aydınlatma ve kompozisyon.
        - İnovatif ve çığır açan teknoloji atmosferi.
        - Görselin önemli detayları üst bölümde görselin 2/3 kısmını kaplayacak şekilde olsun.
        - Kişisel detaylarla çok ilgilenme, odak hikayenin vizyonu ve yaşam ile topluma etkisi olmalı.
        
        Prompt'u İngilizce olarak oluştur ve sadece görsel betimlemeleri içersin.
        """
        
        messages = [
            {"role": "system", "content": "Sen görsel prompt oluşturan bir AI asistanısın. Hikayeleri analiz ederek görsel betimlemeler oluşturursun."},
            {"role": "user", "content": prompt}
        ]
        
        visual_prompt = call_openai_api(messages, max_tokens=300, temperature=0.7)
        return visual_prompt if visual_prompt else "Photorealistic futuristic technology workspace in 2040, innovative project visualization, holographic displays, advanced equipment, professional lighting"
        
    except Exception as e:
        print(f"Story visual prompt creation error: {e}")
        return "Photorealistic futuristic technology workspace in 2040, innovative project visualization, holographic displays, advanced equipment, professional lighting"

def generate_image_with_dalle(prompt, aspect_ratio="1:1"):
    """
    OpenAI DALL-E API kullanarak görsel üretir.
    """
    try:
        if not OPENAI_API_KEY:
            print("OpenAI API key not configured")
            return None
        
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "dall-e-3",
            "prompt": prompt,
            "size": "1024x1024" if aspect_ratio == "1:1" else "1024x1792" if aspect_ratio == "2:3" else "1024x1024",
            "quality": "hd",
            "n": 1
        }
        
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            image_url = result["data"][0]["url"]
            
            # Görseli indir
            img_response = requests.get(image_url, timeout=30)
            if img_response.status_code == 200:
                return img_response.content
            else:
                print(f"Failed to download image: {img_response.status_code}")
                return None
        else:
            print(f"DALL-E API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"DALL-E image generation error: {e}")
        return None

def generate_image_with_imagen(prompt, aspect_ratio="1:1"):
    """
    Google Vertex AI Imagen 4 Preview API kullanarak görsel üretir.
    vertexai paketi kullanır.
    """
    try:
        import vertexai
        from vertexai.generative_models import ImageGenerationModel
        
        # Google Cloud Project ID al
        GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')
        if not GOOGLE_CLOUD_PROJECT:
            print("Google Cloud Project ID not configured")
            return None
        
        # Vertex AI'yi initialize et
        vertexai.init(
            project=GOOGLE_CLOUD_PROJECT,
            location="us-central1"
        )
        
        # Aspect ratio'ya göre boyut belirle
        if aspect_ratio == "1:1":
            width, height = 1024, 1024
        elif aspect_ratio == "2:3":
            width, height = 1024, 1536
        else:
            width, height = 1024, 1024
        
        # Imagen model'ini al
        model = ImageGenerationModel.from_pretrained("imagen-4-preview")
        
        # Image generation parametreleri
        generation_config = {
            "sample_count": 1,
            "aspect_ratio": aspect_ratio,
            "safety_filter_level": "block_some"
        }
        
        # Image üret
        response = model.generate_images(
            prompt=prompt,
            generation_config=generation_config
        )
        
        # Response'dan image data'sını çıkar
        if response and len(response) > 0:
            # İlk image'ı al
            image = response[0]
            
            # Image'ı bytes olarak al
            if hasattr(image, 'image_bytes'):
                return image.image_bytes
            elif hasattr(image, '_image_bytes'):
                return image._image_bytes
            else:
                # Alternatif olarak PIL Image'ı bytes'a çevir
                import io
                img_buffer = io.BytesIO()
                image.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                return img_buffer.getvalue()
        
        print("No image data found in Vertex AI response")
        return None
        
    except ImportError:
        print("vertexai package not installed. Please install it with: pip install vertexai")
        return None
    except Exception as e:
        print(f"Vertex AI Imagen image generation error: {e}")
        return None

def generate_image_unified(prompt, aspect_ratio="1:1", provider="dalle"):
    """
    Birleşik görsel üretim fonksiyonu. Farklı provider'lar arasında geçiş yapabilir.
    
    Args:
        prompt (str): Görsel üretim promptu
        aspect_ratio (str): Görsel oranı ("1:1", "2:3", vb.)
        provider (str): Provider seçimi ("dalle", "imagen")
    
    Returns:
        bytes: Üretilen görsel verisi
    """
    try:
        print(f"🖼️  Generating image with {provider.upper()}...")
        
        if provider.lower() == "dalle":
            return generate_image_with_dalle(prompt, aspect_ratio)
        elif provider.lower() == "imagen":
            return generate_image_with_imagen(prompt, aspect_ratio)
        else:
            print(f"❌ Unknown provider: {provider}. Using DALL-E as fallback.")
            return generate_image_with_dalle(prompt, aspect_ratio)
            
    except Exception as e:
        print(f"Unified image generation error: {e}")
        return None

def generate_selfie_with_gpt4_vision(participants, story):
    """
    GPT-4 Vision kullanarak katılımcı fotoğraflarından selfie görseli oluşturur.
    """
    try:
        if not OPENAI_API_KEY:
            print("OpenAI API key not configured")
            return None
        
        # Katılımcı fotoğraflarını base64'e çevir
        image_contents = []
        for participant in participants:
            if participant.photo_path:
                try:
                    # Yerel dosyadan fotoğrafı oku
                    image_file_path = download_from_gcs(participant.photo_path)
                    if image_file_path:
                        # Dosyayı oku
                        with open(image_file_path, 'rb') as f:
                            image_data = f.read()
                        
                        image_data = base64.b64encode(image_data).decode('utf-8')
                        image_contents.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        })
                        
                        # Geçici dosyayı temizle
                        try:
                            os.remove(image_file_path)
                        except:
                            pass
                except Exception as e:
                    print(f"Error downloading photo for {participant.name}: {e}")
        
        if not image_contents:
            print("No participant photos available")
            return None
        
        prompt = f"""
        Bu katılımcıların fotoğraflarını kullanarak 2040 yılında birlikte çekilmiş bir grup selfie görseli oluştur.
        
        Hikaye: {story}
        
        Gereksinimler:
        - Photorealistic grup selfie
        - 2040 yılı futuristik ortam
        - Katılımcıların hikayedeki rollerine göre giyim tarzları
        - Sci-fi ışıltı ve ekipmanlar takıyor olmalılar
        - Anti-aging yaklaşım (genç ve dinamik görünüm)
        - Profesyonel ama vizyoner atmosfer
        - Teknolojik aksesuarlar ve ışıltılar
        - Başarılı ve güvenli ifadeler
        - Futuristik arka plan
        - Yüksek kaliteli, detaylı görsel
        - 2:3 oranında (portrait format)
        
        Katılımcıların yüz özelliklerini koruyarak gelecekteki hallerini oluştur.
        """
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ] + image_contents
            }
        ]
        
        # GPT-4 Vision ile görsel oluştur
        result = call_gpt4_vision_api(messages, model="gpt-4o", max_tokens=1000, temperature=0.7)
        
        if result:
            # Sonuçtan görsel URL'sini çıkar (eğer varsa)
            # Bu kısım GPT-4 Vision'ın görsel üretme yeteneğine bağlı
            # Şimdilik DALL-E ile fallback yapalım
            fallback_prompt = f"Photorealistic group selfie of professionals in futuristic attire, sci-fi lighting, advanced technology accessories, anti-aging appearance, 2040 setting"
            return generate_image_with_dalle(fallback_prompt, "2:3")
        
        return None
        
    except Exception as e:
        print(f"GPT-4 Vision selfie generation error: {e}")
        return None

def remix_images_with_image_edit(story_image_data, selfie_image_data):
    """
    gpt-image-1 kullanarak hikaye görseli ile selfie görselini remix eder.
    Selfie, story'nin alt kısmında daha az yer kaplayacak şekilde yerleştirilir.
    """
    try:
        if not OPENAI_API_KEY:
            print("OpenAI API key not configured")
            return story_image_data
        
        # Görselleri 2:3 oranında işle (1024x1536)
        from PIL import Image
        import io
        
        # Story image'ı işle
        story_img = Image.open(io.BytesIO(story_image_data))
        story_img = story_img.resize((1024, 1536), Image.Resampling.LANCZOS)
        story_buffer = io.BytesIO()
        story_img.save(story_buffer, format='PNG')
        story_buffer.seek(0)
        processed_story = story_buffer.getvalue()
        
        # Selfie image'ı işle
        selfie_img = Image.open(io.BytesIO(selfie_image_data))
        selfie_img = selfie_img.resize((1024, 1536), Image.Resampling.LANCZOS)
        selfie_buffer = io.BytesIO()
        selfie_img.save(selfie_buffer, format='PNG')
        selfie_buffer.seek(0)
        processed_selfie = selfie_buffer.getvalue()
        
        # OpenAI Images API edit endpoint'ini kullan (gpt-image-1)
        # multipart/form-data formatında gönder
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        # Form data hazırla
        files = [
            ('image[]', ('story.png', processed_story, 'image/png')),
            ('image[]', ('selfie.png', processed_selfie, 'image/png'))
        ]
        
        data = {
            'model': 'gpt-image-1',
            'quality': 'high',
            'prompt': f"""Combine these two images into a single composition:

1. Top 3/4: Story image (futuristic technology workspace/vision)
2. Bottom 1/4: Group selfie image (participants in futuristic setting)

CRITICAL REQUIREMENTS:
- DO NOT alter, modify, or change the content of either provided image
- DO NOT add new elements, objects, or people that are not in the original images
- DO NOT change colors, lighting, or details within the existing images
- ONLY fill gaps and create seamless transitions between the two images
- ONLY blend the edges where the two images meet
- Preserve 100% of the original content and quality of both images

Layout Instructions:
- Place the story image in the top 3/4 of the composition
- Place the selfie image in the bottom 1/4 of the composition
- Create a natural transition zone between the two images
- Fill any empty spaces with appropriate background extension from the story image
- Maintain the original aspect ratios and proportions of both images
- Output in 2:3 aspect ratio (portrait format)

The goal is to create a seamless composite where both original images remain completely intact, with only the transition area and background gaps being filled."""
        }
        
        response = requests.post(
            "https://api.openai.com/v1/images/edits",
            headers=headers,
            data=data,
            files=files,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            # gpt-image-1 base64 formatında döner
            if "data" in result and len(result["data"]) > 0:
                image_base64 = result["data"][0]["b64_json"]
                image_data = base64.b64decode(image_base64)
                print("✓ Successfully remixed story and selfie images")
                return image_data
            else:
                print("No image data in response")
                return story_image_data
        else:
            print(f"OpenAI Images API edit error: {response.status_code} - {response.text}")
            return story_image_data

    except Exception as e:
        print(f"GPT-Image Vision remix error: {e}")
        return story_image_data

def generate_group_futuristic_selfie_with_image_edit(participants, story):
    """
    OpenAI Images API edit endpoint kullanarak 2-4 katılımcının fotoğraflarından 
    futuristik grup selfie görseli oluşturur.
    gpt-image-1 modeli kullanarak birden fazla görseli array olarak gönderir.
    """
    try:
        if not OPENAI_API_KEY:
            print("OpenAI API key not configured")
            return None
        
        # 2-4 katılımcı fotoğrafı gerekli
        available_participants = [p for p in participants if p.photo_path]
        if len(available_participants) < 2:
            print("At least 2 participant photos required for group selfie")
            return None
        elif len(available_participants) > 4:
            print("Maximum 4 participants supported, using first 4")
            available_participants = available_participants[:4]
        
        print(f"Processing {len(available_participants)} participants for group selfie")
        
        # Tüm katılımcı fotoğraflarını indir ve işle
        processed_images = []
        participant_names = []
        
        for participant in available_participants:
            image_file_path = None
            try:
                # Fotoğrafı indir
                image_file_path = download_from_gcs(participant.photo_path)
                if not image_file_path:
                    print(f"Failed to download photo for {participant.name}")
                    continue
                
                # Fotoğrafı 1024x1024 boyutuna getir
                from PIL import Image
                import io
                
                # Dosyayı oku
                with open(image_file_path, 'rb') as f:
                    image_data = f.read()
                
                img = Image.open(io.BytesIO(image_data))
                
                # Eğer görsel zaten 1024x1024 ise olduğu gibi kullan, değilse resize et
                if img.size == (1024, 1024):
                    print(f"✓ Photo for {participant.name} is already 1024x1024, using as is")
                else:
                    print(f"✓ Resizing photo for {participant.name} from {img.size} to 1024x1024")
                    img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
                
                # PNG formatında kaydet
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                processed_images.append(img_buffer.getvalue())
                participant_names.append(participant.name)
                
                print(f"✓ Processed photo for {participant.name} (1024x1024)")
                
            except Exception as e:
                print(f"Error processing photo for {participant.name}: {e}")
                continue
            finally:
                # Geçici dosyayı temizle
                if image_file_path and os.path.exists(image_file_path):
                    try:
                        os.remove(image_file_path)
                    except:
                        pass
        
        if len(processed_images) < 2:
            print("Insufficient processed images for group selfie")
            return None
        
        # Katılımcı isimlerini birleştir
        names_text = " and ".join(participant_names)
        
        # OpenAI Images API edit endpoint'ini kullan (gpt-image-1)
        # multipart/form-data formatında gönder
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        # Form data hazırla
        files = []
        for i, img_data in enumerate(processed_images):
            files.append(('image[]', (f'participant_{i+1}.png', img_data, 'image/png')))
        
        data = {
            'model': 'gpt-image-1',
            'quality': 'high',
            'prompt': f"""Create a realistic group selfie showing these {len(participant_names)} people together in 2040.

Participants: {names_text}

Requirements:
- Create a natural group selfie showing all participants together
- Set the scene in 2040 (subtle future indication only)
- Apply subtle anti-aging effects: reduce fine lines and wrinkles by 20-30%, smooth skin texture slightly, maintain natural skin tone and features
- Keep everyone looking naturally themselves - don't over-process or make them look artificial
- No futuristic accessories, glasses, or tech jewelry
- Use plain, clean background
- Maintain highly realistic appearance of all people
- Professional but approachable atmosphere
- High-quality, detailed image with realistic skin textures and facial features
- Everyone should look confident and successful but natural
- Group composition should be natural and engaging
- Ensure all participants are clearly visible and well-integrated
- Focus on realistic human appearance
- Keep the background simple and clean
- Output in 16:9 aspect ratio

Story context: {story}

Create a photorealistic group selfie that shows these professionals together, with only subtle indication they are in the future, maintaining their natural appearance with gentle anti-aging effects."""
        }
        
        response = requests.post(
            "https://api.openai.com/v1/images/edits",
            headers=headers,
            data=data,
            files=files,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            # gpt-image-1 base64 formatında döner
            if "data" in result and len(result["data"]) > 0:
                image_base64 = result["data"][0]["b64_json"]
                image_data = base64.b64decode(image_base64)
                print(f"✓ Successfully generated group selfie for {len(participant_names)} participants")
                return image_data
            else:
                print("No image data in response")
                return None
        else:
            print(f"OpenAI Images API edit error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Group futuristic selfie generation with image edit error: {e}")
        return None

def generate_collaborative_story(participants, image_provider="dalle"):
    """
    Ana fonksiyon: Tüm adımları sırasıyla uygulayarak hikaye, görsel prompt ve görsel üretir.
    
    Args:
        participants: Katılımcı listesi
        image_provider (str): Görsel üretim provider'ı ("dalle", "imagen")
    
    Returns: (story, visual_prompt, final_image_data)
    """
    try:
        print("Adım 1: Bireysel vizyon hikayeleri oluşturuluyor...")
        individual_stories = []
        for participant in participants:
            story = generate_individual_vision_story(participant)
            individual_stories.append((participant.name, story))
            print(f"- {participant.name} için hikaye oluşturuldu")
        
        print("Adım 2: Ortak gelecek vizyonu hikayesi oluşturuluyor...")
        collaborative_story = create_collaborative_future_story(individual_stories)
        print("Ortak hikaye oluşturuldu")
        
        print("Adım 3: Hikaye görsel prompt'u oluşturuluyor...")
        story_visual_prompt = create_story_visual_prompt(collaborative_story)
        print("Hikaye görsel prompt'u oluşturuldu")
        
        print(f"Adım 4: Hikaye görseli üretiliyor ({image_provider.upper()})...")
        story_image_data = generate_image_unified(story_visual_prompt, "1:1", image_provider)
        if story_image_data:
            print("Hikaye görseli üretildi")
            
            # Hikaye görselini local klasöre kaydet
            from datetime import datetime
            
            # Local klasörleri oluştur
            local_generated_dir = "local_generated"
            story_images_dir = os.path.join(local_generated_dir, "story_images")
            selfie_images_dir = os.path.join(local_generated_dir, "selfie_images")
            
            os.makedirs(story_images_dir, exist_ok=True)
            os.makedirs(selfie_images_dir, exist_ok=True)
            
            # Timestamp oluştur
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            participant_names = "_".join([p.name.replace(" ", "_") for p in participants[:3]])  # İlk 3 katılımcı
            
            # Hikaye görselini kaydet
            story_filename = f"story_{timestamp}_{participant_names}_{image_provider}.png"
            story_filepath = os.path.join(story_images_dir, story_filename)
            
            with open(story_filepath, 'wb') as f:
                f.write(story_image_data)
            print(f"📁 Hikaye görseli kaydedildi: {story_filepath}")
            
        else:
            print("❌ Hikaye görseli üretimi başarısız")
        
        print("Adım 5: OpenAI Images API ile futuristik grup selfie üretiliyor...")
        # Sadece grup selfie destekleniyor (2-4 katılımcı)
        available_participants = [p for p in participants if p.photo_path]
        if len(available_participants) < 2:
            print("⚠️  At least 2 participants with photos required for group selfie")
            print("Skipping selfie generation due to insufficient participants")
            selfie_image_data = None
        else:
            selfie_image_data = generate_group_futuristic_selfie_with_image_edit(participants, collaborative_story)
            if selfie_image_data:
                print("✓ Futuristik grup selfie görseli üretildi")
                
                # Selfie görselini local klasöre kaydet
                selfie_filename = f"selfie_{timestamp}_{participant_names}.png"
                selfie_filepath = os.path.join(selfie_images_dir, selfie_filename)
                
                with open(selfie_filepath, 'wb') as f:
                    f.write(selfie_image_data)
                print(f"📁 Selfie görseli kaydedildi: {selfie_filepath}")
                
            else:
                print("⚠️  Group selfie generation failed")
        
        if story_image_data and selfie_image_data:
            print("Adım 6: GPT-Image-1 ile görseller remix ediliyor...")
            final_image_data = remix_images_with_image_edit(story_image_data, selfie_image_data)
            
            # Final görseli de kaydet
            final_filename = f"final_{timestamp}_{participant_names}_{image_provider}.png"
            final_filepath = os.path.join(local_generated_dir, final_filename)
            
            with open(final_filepath, 'wb') as f:
                f.write(final_image_data)
            print(f"📁 Final görsel kaydedildi: {final_filepath}")
            
            # Şablonu uygula
            final_image_data = apply_template_to_image_data(final_image_data)
            
            print("Tüm işlemler tamamlandı!")
            return collaborative_story, story_visual_prompt, final_image_data
        elif story_image_data:
            print("⚠️  Selfie generation failed, using only story image")
            # Sadece hikaye görselini kullan
            final_image_data = apply_template_to_image_data(story_image_data)
            return collaborative_story, story_visual_prompt, final_image_data
        else:
            print("❌ Görsel üretimi başarısız")
            return collaborative_story, story_visual_prompt, None
            
    except Exception as e:
        print(f"Collaborative story generation error: {e}")
        return "Katılımcılar birlikte geleceği şekillendiren bir teknoloji projesi geliştirdi.", "Photorealistic futuristic technology workspace in 2040", None

def regenerate_image_from_story(story_text, visual_prompt, participants=None, image_provider="dalle"):
    """
    Mevcut hikaye ve görsel prompt'undan tekrar görsel üretir.
    Hem yeni hikayeler hem de mevcut görselleri yeniden üretmek için kullanılabilir.
    
    Args:
        story_text (str): Hikaye metni
        visual_prompt (str): Görsel üretim promptu
        participants (list): Katılımcı listesi (opsiyonel, selfie için kullanılır)
        image_provider (str): Görsel üretim provider'ı ("dalle", "imagen")
    
    Returns:
        tuple: (story_text, visual_prompt, final_image_data)
    """
    try:
        print("🔄 Görsel yeniden üretimi başlatılıyor...")
        
        # Local klasörleri oluştur
        import os
        from datetime import datetime
        
        local_generated_dir = "local_generated"
        story_images_dir = os.path.join(local_generated_dir, "story_images")
        selfie_images_dir = os.path.join(local_generated_dir, "selfie_images")
        
        os.makedirs(story_images_dir, exist_ok=True)
        os.makedirs(selfie_images_dir, exist_ok=True)
        
        # Timestamp oluştur
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        participant_names = ""
        if participants:
            participant_names = "_".join([p.name.replace(" ", "_") for p in participants[:3]])
        
        print(f"Adım 1: Hikaye görseli üretiliyor ({image_provider.upper()})...")
        story_image_data = generate_image_unified(visual_prompt, "1:1", image_provider)
        if not story_image_data:
            print("❌ Hikaye görseli üretimi başarısız")
            return story_text, visual_prompt, None
        print("✓ Hikaye görseli üretildi")
        
        # Hikaye görselini kaydet
        story_filename = f"story_regenerated_{timestamp}_{participant_names}_{image_provider}.png"
        story_filepath = os.path.join(story_images_dir, story_filename)
        
        with open(story_filepath, 'wb') as f:
            f.write(story_image_data)
        print(f"📁 Hikaye görseli kaydedildi: {story_filepath}")
        
        # Eğer katılımcılar varsa ve fotoğrafları mevcutsa selfie de üret
        selfie_image_data = None
        if participants:
            print("Adım 2: Grup selfie üretiliyor...")
            available_participants = [p for p in participants if p.photo_path]
            if len(available_participants) >= 2:
                selfie_image_data = generate_group_futuristic_selfie_with_image_edit(participants, story_text)
                if selfie_image_data:
                    print("✓ Grup selfie üretildi")
                    
                    # Selfie görselini kaydet
                    selfie_filename = f"selfie_regenerated_{timestamp}_{participant_names}.png"
                    selfie_filepath = os.path.join(selfie_images_dir, selfie_filename)
                    
                    with open(selfie_filepath, 'wb') as f:
                        f.write(selfie_image_data)
                    print(f"📁 Selfie görseli kaydedildi: {selfie_filepath}")
                    
                else:
                    print("⚠️  Grup selfie üretimi başarısız")
            else:
                print("⚠️  Yetersiz katılımcı fotoğrafı, selfie üretilmiyor")
        
        # Görselleri birleştir
        if story_image_data and selfie_image_data:
            print("Adım 3: Görseller remix ediliyor...")
            final_image_data = remix_images_with_image_edit(story_image_data, selfie_image_data)
            
            # Final görseli kaydet
            final_filename = f"final_regenerated_{timestamp}_{participant_names}_{image_provider}.png"
            final_filepath = os.path.join(local_generated_dir, final_filename)
            
            with open(final_filepath, 'wb') as f:
                f.write(final_image_data)
            print(f"📁 Final görsel kaydedildi: {final_filepath}")
            
            # Şablonu uygula
            final_image_data = apply_template_to_image_data(final_image_data)
            
            print("✓ Görsel yeniden üretimi tamamlandı!")
            return story_text, visual_prompt, final_image_data
        elif story_image_data:
            print("⚠️  Selfie yok, sadece hikaye görseli kullanılıyor")
            # Sadece hikaye görselini kullan
            final_image_data = apply_template_to_image_data(story_image_data)
            return story_text, visual_prompt, final_image_data
        else:
            print("❌ Görsel üretimi başarısız")
            return story_text, visual_prompt, None
            
    except Exception as e:
        print(f"Görsel yeniden üretimi hatası: {e}")
        return story_text, visual_prompt, None