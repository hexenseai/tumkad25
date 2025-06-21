import requests
import os
import base64
import time
from utils import apply_template_to_image_data
from vertexai.preview.generative_models import GenerativeModel

LUMALABS_API_KEY = os.environ.get('LUMALABS_API_KEY')
LUMALABS_API_URL = "https://api.lumalabs.ai/dream-machine/v1/generations/image"


def generate_image_with_lumalabs(prompt, reference_images):
    """
    Lumalabs.ai API kullanarak Character Reference ile görsel üretir.
    Katılımcıların fotoğraflarını GCS URL'leri olarak kullanır.
    Asenkron işlem - polling ile sonucu bekler.
    
    Args:
        prompt: Görsel üretim prompt'u
        reference_images: Referans görseller listesi
        callback_url: Opsiyonel webhook URL'si
    """
    try:
        if not LUMALABS_API_KEY or LUMALABS_API_KEY == 'your-lumalabs-api-key-here':
            print("Lumalabs.ai API key not configured")
            return None
        
        # Character Reference için payload hazırla
        character_ref = {}
        
        # Her katılımcı için ayrı identity oluştur
        for i, ref_img in enumerate(reference_images):
            if isinstance(ref_img, dict) and 'image_url' in ref_img:
                # Signed URL'yi kullan (Lumalabs.ai için)
                image_url = ref_img['image_url']
                print(f"Using signed URL for identity{i}: {image_url[:50]}...")
                character_ref[f"identity{i}"] = {
                    "images": [image_url]
                }
            elif isinstance(ref_img, str) and os.path.exists(ref_img):
                # Eski format için dosyayı base64'e çevir
                with open(ref_img, 'rb') as f:
                    img_base64 = base64.b64encode(f.read()).decode('utf-8')
                    data_url = f"data:image/png;base64,{img_base64}"
                    character_ref[f"identity{i}"] = {
                        "images": [data_url]
                    }
        
        if not character_ref:
            print("No valid reference images found")
            return None
        
        # API isteği için payload hazırla
        payload = {
            "prompt": prompt,
            "model": "photon-1",
            "aspect_ratio": "1:1",
            "format": "png"
        }
        
        # Character Reference varsa ekle
        if character_ref:
            payload["character_ref"] = character_ref
        
        
        headers = {
            "Authorization": f"Bearer {LUMALABS_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        print(f"Starting Lumalabs.ai generation with prompt: {prompt[:100]}...")
        
        # API isteği gönder
        response = requests.post(LUMALABS_API_URL, json=payload, headers=headers)
        
        if response.status_code == 201:
            result = response.json()
            print(f"Generation started: {result}")
            
            # Generation ID'sini al
            if 'id' in result:
                generation_id = result['id']
                print(f"Generation ID: {generation_id}")
                
            
                # Polling ile sonucu bekle
                max_attempts = 60  # 5 dakika (5 saniye aralıklarla)
                for attempt in range(max_attempts):
                    print(f"Checking generation status... (attempt {attempt + 1}/{max_attempts})")
                    
                    # Status kontrol et
                    status_response = requests.get(
                        f"https://api.lumalabs.ai/dream-machine/v1/generations/{generation_id}",
                        headers=headers
                    )
                    
                    if status_response.status_code == 200:
                        status_result = status_response.json()
                        print(status_result)
                        status = status_result.get('state', 'unknown')
                        print(f"Status: {status}")
                        
                        if status == 'completed':
                            print(status_result)
                            # Görsel hazır, URL'yi al
                            if 'assets' in status_result and status_result['assets'] and status_result['assets'].get('image'):
                                image_url = status_result['assets']['image']
                                print(f"Image ready: {image_url}")
                                
                                # Görseli indir
                                img_response = requests.get(image_url)
                                if img_response.status_code == 200:
                                    # Görseli bytes olarak al
                                    image_data = img_response.content
                                    
                                    # Şablonu uygula
                                    final_image_data = apply_template_to_image_data(image_data)
                                    return final_image_data
                                else:
                                    print(f"Failed to download image: {img_response.status_code}")
                                    return None
                            else:
                                print("No image data in completed response")
                                print(f"Assets: {status_result.get('assets')}")
                                return None
                                
                        elif status == 'failed':
                            print(f"Generation failed: {status_result}")
                            failure_reason = status_result.get('failure_reason', 'Unknown error')
                            print(f"Failure reason: {failure_reason}")
                            return None
                            
                        elif status in ['queued', 'processing', 'dreaming']:
                            # Devam et, bekle
                            time.sleep(5)  # 5 saniye bekle
                            continue
                            
                        else:
                            print(f"Unknown status: {status}")
                            print(f"Full response: {status_result}")
                            return None
                    else:
                        print(f"Status check failed: {status_response.status_code}")
                        return None
                
                print("Generation timeout - max attempts reached")
                return None
            else:
                print("No generation ID in response")
                return None
                    
        else:
            print(f"Lumalabs.ai API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Lumalabs.ai generation error: {e}")
        return None



def extract_keywords_and_themes(text):
    """
    Metinden anahtar kelimeleri ve temaları çıkarır.
    """
    try:
        # Google Cloud credentials kontrol et
        if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            return []
        
        # Vertex AI'yi başlat
        import vertexai
        vertexai.init(
            project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
            location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
        )
        
        # Gemini 2.0 Flash modelini kullan
        model = GenerativeModel(model_name="gemini-2.0-flash-001")
        
        prompt = f"""
        Bu metinden teknoloji ve inovasyon ile ilgili anahtar kelimeleri ve temaları çıkar:
        
        Metin: {text}
        
        Çıkarılacak kategoriler:
        1. Teknoloji alanları (AI, blockchain, IoT, vb.)
        2. İnovasyon türleri (disruptive, incremental, vb.)
        3. Sektörler (healthcare, finance, education, vb.)
        4. Gelecek vizyonu temaları (sustainability, efficiency, vb.)
        5. Çalışma stilleri (collaborative, analytical, creative, vb.)
        
        Her kategori için en önemli 3-5 kelimeyi virgülle ayırarak listele.
        Sadece kelimeleri ver, açıklama yapma.
        """
        
        response = model.generate_content(prompt)
        keywords = [kw.strip() for kw in response.text.split(',') if kw.strip()]
        return keywords
        
    except Exception as e:
        print(f"Keyword extraction error: {e}")
        return []

def analyze_participant_personality(participant):
    """
    Katılımcının kişilik profilini ve anahtar kelimelerini analiz eder.
    """
    try:
        # Google Cloud credentials kontrol et
        if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            print("Google Cloud credentials not set")
            return None, []
        
        # Vertex AI'yi başlat
        import vertexai
        vertexai.init(
            project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
            location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
        )
        
        # Gemini 2.0 Flash modelini kullan
        model = GenerativeModel(model_name="gemini-2.0-flash-001")
        
        # Katılımcı bilgilerini analiz et
        participant_info = f"""
        İsim: {participant.name}
        Meslek/Uzmanlık: {participant.profession}
        Sektör: {participant.sector}
        Teknik İlgi Alanı: {participant.technical_interest}
        Gelecek Hedefi (2040): {participant.future_impact}
        İdeal Çalışma Ortamı: {participant.work_environment}
        """
        
        # Anahtar kelimeleri çıkar
        all_text = f"{participant.profession} {participant.sector} {participant.technical_interest} {participant.future_impact} {participant.work_environment}"
        keywords = extract_keywords_and_themes(all_text)
        
        # Kişilik analizi prompt'u
        prompt = f"""
        Bu kişinin bilgilerini analiz ederek, 2040 yılında teknoloji dünyasında nasıl bir rol oynayabileceğini tahmin et.
        
        Kişi Bilgileri:
        {participant_info}
        
        Analiz etmen gereken noktalar:
        1. Bu kişinin güçlü yanları neler olabilir?
        2. Hangi teknoloji alanlarında uzmanlaşmış olabilir?
        3. Liderlik tarzı nasıl olabilir? (vizyoner, analitik, yaratıcı, vs.)
        4. Takım içindeki rolü ne olabilir? (lider, uzman, koordinatör, vs.)
        5. 2040'te hangi teknoloji trendlerine odaklanmış olabilir?
        6. İnovasyon yaklaşımı nasıl olabilir? (disruptive, incremental, vb.)
        
        Analizi Türkçe olarak, 2-3 cümle halinde özetle.
        """
        
        response = model.generate_content(prompt)
        personality = response.text
        
        return personality, keywords
        
    except Exception as e:
        print(f"Personality analysis error: {e}")
        return f"{participant.name} teknoloji alanında uzmanlaşmış bir profesyonel.", []

def find_common_themes(participants_keywords):
    """
    Katılımcıların anahtar kelimelerinden ortak temaları ve gelecek vizyonlarını bulur.
    """
    try:
        # Google Cloud credentials kontrol et
        if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            return [], ""
        
        # Vertex AI'yi başlat
        import vertexai
        vertexai.init(
            project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
            location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
        )
        
        # Gemini 2.0 Flash modelini kullan
        model = GenerativeModel(model_name="gemini-2.0-flash-001")
        
        # Tüm anahtar kelimeleri birleştir
        all_keywords = []
        for name, keywords in participants_keywords:
            all_keywords.extend(keywords)
        
        keywords_text = ", ".join(all_keywords)
        
        prompt = f"""
        Bu anahtar kelimelerden ortak temaları ve gelecek vizyonlarını bul:
        
        Anahtar kelimeler: {keywords_text}
        
        Katılımcıların ortak ilgi alanları:
        {chr(10).join([f"- {name}: {', '.join(keywords)}" for name, keywords in participants_keywords])}
        
        Ortak temaları ve bu temaların 2040 yılında nasıl bir inovasyon projesine dönüşebileceğini analiz et.
        Özellikle katılımcıların gelecek vizyonlarının nasıl birleşebileceğine odaklan.
        
        Çıktı formatı:
        TEMALAR: [ortak temalar virgülle ayrılmış]
        PROJE FİKRİ: [bu temalardan ve gelecek vizyonlarından yola çıkarak 2040'te geliştirilebilecek proje fikri - katılımcıların vizyonlarının birleşmesini vurgula]
        """
        
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Yanıtı parçala
        themes = []
        project_idea = ""
        
        if "TEMALAR:" in response_text and "PROJE FİKRİ:" in response_text:
            parts = response_text.split("PROJE FİKRİ:")
            themes_part = parts[0].replace("TEMALAR:", "").strip()
            themes = [t.strip() for t in themes_part.split(',') if t.strip()]
            project_idea = parts[1].strip()
        
        return themes, project_idea
        
    except Exception as e:
        print(f"Theme analysis error: {e}")
        return [], ""

def generate_collaborative_story(participants):
    """
    Katılımcıların gelecek vizyonlarını birleştirerek 2040'te birlikte gerçekleştirecekleri proje hikayesini oluşturur.
    Hikayenin içeriği ve vizyonu öncelikli, kişilerin yüzleri ikincil önemde.
    """
    try:
        # Google Cloud credentials kontrol et
        if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            print("Google Cloud credentials not set")
            return None, None
        
        # Vertex AI'yi başlat
        import vertexai
        vertexai.init(
            project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
            location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
        )
        
        # Gemini 2.0 Flash modelini kullan
        model = GenerativeModel(model_name="gemini-2.0-flash-001")
        
        # Katılımcıların gelecek vizyonlarını analiz et
        future_visions = []
        participants_info = []
        participants_keywords = []
        
        for p in participants:
            personality, keywords = analyze_participant_personality(p)
            participants_keywords.append((p.name, keywords))
            
            # Gelecek vizyonunu detaylandır
            future_visions.append(f"""
            {p.name} - Gelecek Vizyonu:
            - 2040 Hedefi: {p.future_impact}
            - Teknik İlgi: {p.technical_interest}
            - Sektör: {p.sector}
            - Meslek: {p.profession}
            - İdeal Çalışma Ortamı: {p.work_environment}
            - Kişilik Analizi: {personality}
            - Anahtar Kelimeler: {', '.join(keywords)}
            """)
            
            participants_info.append(f"""
            {p.name}:
            - Meslek: {p.profession}
            - Sektör: {p.sector}
            - Teknik İlgi: {p.technical_interest}
            - 2040 Hedefi: {p.future_impact}
            - Kişilik Analizi: {personality}
            - Anahtar Kelimeler: {', '.join(keywords)}
            """)
        
        # Ortak temaları bul
        common_themes, project_idea = find_common_themes(participants_keywords)
        
        # Görsel referansları oluştur
        visual_references = generate_visual_references(common_themes, project_idea)
        
        future_visions_text = "\n".join(future_visions)
        participants_text = "\n".join(participants_info)
        names = ', '.join([p.name for p in participants])
        themes_text = ', '.join(common_themes) if common_themes else "teknoloji, inovasyon, gelecek"
        
        # Hikaye oluşturma prompt'u - gelecek vizyonlarını birleştirmeye odaklı
        prompt = f"""
        Bu {len(participants)} kişinin gelecek vizyonlarını birleştirerek 2040 yılında birlikte gerçekleştirecekleri çığır açan bir teknoloji projesi hikayesi yaz.
        
        Katılımcıların Gelecek Vizyonları:
        {future_visions_text}
        
        Ortak Temalar: {themes_text}
        Proje Fikri: {project_idea}
        Görsel Referanslar: {', '.join(visual_references) if visual_references else 'futuristik ortam'}
        
        Hikaye gereksinimleri:
        1. 2040 yılında geçmeli
        2. Her katılımcının gelecek vizyonunu ve hedefini birleştiren bir proje olmalı
        3. Dünyayı değiştiren, çığır açan bir teknoloji olmalı
        4. Her kişinin vizyonunun projeye nasıl katkı sağladığı net olmalı
        5. Gerçekçi ama vizyoner olmalı
        6. İnovatif düşünce ve görsel referansları destekleyecek içerik barındırmalı
        7. 4-5 paragraf uzunluğunda olmalı
        8. Türkçe yazılmalı
        9. Hikaye şu yapıda olmalı:
           - Giriş: Vizyonların birleşmesi ve ekip oluşumu
           - Gelişme: Teknolojik zorluklar ve vizyonların çözüme katkısı
           - Doruk: Başarı anı ve dünya üzerindeki etki
           - Sonuç: Gelecek vizyonu ve sürdürülebilir etki
        
        Hikayeyi yazdıktan sonra, bu hikayeden yola çıkarak AI görsel üretimi için İngilizce bir prompt da oluştur.
        Görsel, hikayenin içeriğini ve projenin vizyonunu illustre etmeli, kişilerin yüzleri ikincil önemde olmalı.
        
        Görsel prompt gereksinimleri:
        - 1080x1080 kare format
        - Fotogerçekçi, yüksek kaliteli
        - 2040 yılı futuristik teknoloji ortamı
        - Hikayenin içeriğini ve projenin vizyonunu illustre eden görsel elementler
        - Teknolojik ilerleme ve yenilik teması
        - Ortak temaları görsel olarak yansıtmalı
        - Projenin dünya üzerindeki etkisini gösteren görsel ipuçları
        - Kişilerin yüzleri net olmayabilir, odak projenin kendisi olmalı
        - Dramatik aydınlatma ve kompozisyon
        - İnovatif ve çığır açan teknoloji atmosferi
        
        Yanıtı şu formatta ver:
        HİKAYE:
        [hikaye metni]
        
        GÖRSEL PROMPT:
        [İngilizce görsel prompt - hikayenin içeriğini illustre eden, 1080x1080, fotogerçekçi, futuristik]
        """
        
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Yanıtı parçala
        if "HİKAYE:" in response_text and "GÖRSEL PROMPT:" in response_text:
            parts = response_text.split("GÖRSEL PROMPT:")
            story_text = parts[0].replace("HİKAYE:", "").strip()
            image_prompt = parts[1].strip()
        else:
            # Fallback
            story_text = f"2040 yılında {names} birlikte yenilikçi bir teknoloji projesi geliştirdi. Bu ekip, farklı gelecek vizyonlarını birleştirerek geleceği şekillendiren bir çözüm üretti."
            image_prompt = f"Photorealistic 1080x1080 futuristic workspace in 2040, innovative technology project visualization, holographic displays, advanced equipment, professional lighting, {themes_text}, collaborative innovation environment, visionary technology impact"
        
        # Hikayeyi inovasyon elementleriyle zenginleştir
        enhanced_story = enhance_story_with_innovation_elements(story_text, common_themes, visual_references)
        
        # İnovatif görsel prompt oluştur - hikayenin içeriğini illustre eden
        innovative_image_prompt = create_vision_focused_image_prompt(enhanced_story, common_themes, visual_references, participants)
        
        return enhanced_story, innovative_image_prompt
        
    except Exception as e:
        print(f"Story generation error: {e}")
        names = ', '.join([p.name for p in participants])
        fallback_story = f"2040 yılında {names} birlikte yenilikçi bir teknoloji projesi geliştirdi. Bu ekip, farklı gelecek vizyonlarını birleştirerek geleceği şekillendiren bir çözüm üretti."
        fallback_prompt = f"Photorealistic 1080x1080 futuristic workspace in 2040, {names} (all women) collaborating on an innovative technology project, holographic displays, advanced equipment, professional lighting, all female professionals"
        return fallback_story, fallback_prompt

def generate_visual_references(themes, project_idea):
    """
    Temalar ve proje fikrinden yola çıkarak görsel referansları oluşturur.
    """
    try:
        # Google Cloud credentials kontrol et
        if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            return []
        
        # Vertex AI'yi başlat
        import vertexai
        vertexai.init(
            project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
            location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
        )
        
        # Gemini 2.0 Flash modelini kullan
        model = GenerativeModel(model_name="gemini-2.0-flash-001")
        
        themes_text = ', '.join(themes) if themes else "teknoloji, inovasyon"
        
        prompt = f"""
        Bu temalar ve proje fikrinden yola çıkarak 2040 yılında görsel olarak nasıl temsil edilebileceğini analiz et:
        
        Temalar: {themes_text}
        Proje Fikri: {project_idea}
        
        Görsel referansları şu kategorilerde oluştur:
        1. Teknoloji ekipmanları (holografik ekranlar, AI arayüzleri, vb.)
        2. Çalışma ortamı özellikleri (futuristik ofis, laboratuvar, vb.)
        3. Renk paleti ve aydınlatma
        4. Kompozisyon ve düzen
        5. Detaylar ve aksesuarlar
        
        Her kategori için 3-5 görsel özellik öner.
        Sadece görsel özellikleri listele, açıklama yapma.
        """
        
        response = model.generate_content(prompt)
        references = [ref.strip() for ref in response.text.split('\n') if ref.strip()]
        return references
        
    except Exception as e:
        print(f"Visual reference generation error: {e}")
        return []

def enhance_story_with_innovation_elements(story_text, themes, visual_references):
    """
    Hikayeyi inovasyon elementleri ve görsel referanslarla zenginleştirir.
    Gelecek vizyonlarının birleşmesini ve projenin etkisini vurgular.
    """
    try:
        # Google Cloud credentials kontrol et
        if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            return story_text
        
        # Vertex AI'yi başlat
        import vertexai
        vertexai.init(
            project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
            location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
        )
        
        # Gemini 2.0 Flash modelini kullan
        model = GenerativeModel(model_name="gemini-2.0-flash-001")
        
        themes_text = ', '.join(themes) if themes else "teknoloji"
        visual_refs_text = ', '.join(visual_references) if visual_references else "futuristik ortam"
        
        prompt = f"""
        Bu hikayeyi inovasyon elementleri ve görsel referanslarla zenginleştir:
        
        Orijinal Hikaye:
        {story_text}
        
        Temalar: {themes_text}
        Görsel Referanslar: {visual_refs_text}
        
        Hikayeyi şu şekilde geliştir:
        1. Katılımcıların gelecek vizyonlarının nasıl birleştiğini daha net göster
        2. Projenin dünya üzerindeki etkisini daha detaylı anlat
        3. Teknolojik detayları ve inovasyon sürecini zenginleştir
        4. 2040 yılının teknolojik atmosferini daha canlı yansıt
        5. Vizyonların çözüme nasıl katkı sağladığını vurgula
        6. Projenin sürdürülebilir etkisini ve gelecek vizyonunu güçlendir
        7. Görsel betimlemeleri hikayenin içeriğini illustre edecek şekilde zenginleştir
        
        Hikayeyi aynı uzunlukta tut ama gelecek vizyonlarının birleşmesini ve projenin etkisini daha güçlü vurgula.
        """
        
        response = model.generate_content(prompt)
        enhanced_story = response.text
        
        return enhanced_story if enhanced_story else story_text
        
    except Exception as e:
        print(f"Story enhancement error: {e}")
        return story_text

def create_vision_focused_image_prompt(story_text, themes, visual_references, participants):
    """
    Hikaye, temalar ve görsel referanslardan yola çıkarak hikayenin içeriğini illustre eden görsel prompt oluşturur.
    Lumalabs.ai Character Reference için optimize edilmiş - katılımcıların gerçek görünümlerini korur.
    """
    try:
        # Google Cloud credentials kontrol et
        if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            return ""
        
        # Vertex AI'yi başlat
        import vertexai
        vertexai.init(
            project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
            location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
        )
        
        # Gemini 2.0 Flash modelini kullan
        model = GenerativeModel(model_name="gemini-2.0-flash-001")
        
        # Katılımcıların gelecek vizyonlarını hazırla
        future_visions = []
        for p in participants:
            future_visions.append(f"{p.name}: {p.future_impact}")
        
        future_visions_text = ", ".join(future_visions)
        themes_text = ', '.join(themes) if themes else "teknoloji, inovasyon"
        visual_refs_text = ', '.join(visual_references) if visual_references else "futuristik ortam"
        names = ', '.join([p.name for p in participants])
        
        prompt = f"""
        Bu bilgilerden yola çıkarak 2040 yılında geçen, hikayenin içeriğini ve projenin vizyonunu illustre eden bir görsel prompt oluştur:
        
        Hikaye: {story_text}
        Katılımcıların Gelecek Vizyonları: {future_visions_text}
        Temalar: {themes_text}
        Görsel Referanslar: {visual_refs_text}
        
        Prompt gereksinimleri (Lumalabs.ai Character Reference için optimize edilmiş):
        - 2040 yılı futuristik teknoloji ortamı
        - Hikayenin içeriğini ve projenin vizyonunu illustre eden görsel elementler
        - Projenin dünya üzerindeki etkisini gösteren görsel ipuçları
        - Teknolojik ilerleme ve yenilik teması
        - Ortak temaları görsel olarak yansıtmalı
        - İnovatif ve çığır açan teknoloji atmosferi
        - Dramatik aydınlatma ve kompozisyon
        - Profesyonel iş ortamı atmosferi
        - Holografik ekranlar, gelişmiş ekipmanlar
        - Katılımcıların gerçek görünümlerini koruyacak şekilde tasarlanmalı
        - Projenin vizyonunu ve gelecek etkisini gösteren sembolik elementler
        - Hikayede bahsedilen teknolojik çözümün görsel temsili
        
        ÖNEMLİ: Lumalabs.ai Character Reference kullanılacak, bu yüzden:
        - Katılımcıların yüz detaylarını prompt'ta belirtmeye gerek yok
        - Character Reference otomatik olarak gerçek görünümleri koruyacak
        - Odak hikayenin içeriği ve projenin vizyonu olmalı
        - Ortam ve teknoloji detaylarını vurgula
        
        Prompt'u İngilizce olarak, Character Reference'ın otomatik olarak karakterleri yöneteceğini göz önünde bulundurarak oluştur.
        """
        
        response = model.generate_content(prompt)
        image_prompt = response.text.strip()
        
        return image_prompt if image_prompt else f"2040 futuristic technology workspace, {names} collaborating on innovative project, holographic displays, advanced equipment, professional lighting, {themes_text}, visionary technology environment, collaborative innovation workspace, {future_visions_text}"
        
    except Exception as e:
        print(f"Vision-focused image prompt creation error: {e}")
        names = ', '.join([p.name for p in participants])
        themes_text = ', '.join(themes) if themes else "teknoloji, inovasyon"
        future_visions = [f"{p.name}: {p.future_impact}" for p in participants]
        future_visions_text = ", ".join(future_visions)
        return f"2040 futuristic technology workspace, {names} collaborating on innovative project, holographic displays, advanced equipment, professional lighting, {themes_text}, visionary technology environment, collaborative innovation workspace, {future_visions_text}"
