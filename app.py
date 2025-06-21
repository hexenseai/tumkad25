from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
import json
from PIL import Image
import io
from gcs import upload_to_gcs, get_gcs_file_url, delete_from_gcs, bucket

from utils import normalize_phone, get_participant_reference_images, apply_template_to_image_data
from generation import analyze_participant_personality, find_common_themes, generate_collaborative_story, generate_image_with_lumalabs, generate_visual_references

# Google Cloud credentials ayarla
credentials_path = os.path.join(os.getcwd(), 'api-project-974861835731-14fb4124b1b2.json')
if os.path.exists(credentials_path):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    print(f"Google Cloud credentials loaded from: {credentials_path}")
else:
    print(f"Warning: Google Cloud credentials file not found at: {credentials_path}")

# Lumalabs.ai API konfigürasyonu
LUMALABS_API_KEY = os.environ.get('LUMALABS_API_KEY', 'your-lumalabs-api-key-here')

# Google Cloud Storage konfigürasyonu
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'tumkad25-storage')
GCS_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', 'api-project-974861835731')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tumkad-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tumkad.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['GENERATED_FOLDER'] = 'generated'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size


db = SQLAlchemy(app)

# Database Models
class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    profession = db.Column(db.String(100), nullable=False)  # Mesleğiniz / Temel Uzmanlık Alanı
    sector = db.Column(db.String(100), nullable=False)  # Çalıştığınız Sektör
    technical_interest = db.Column(db.Text, nullable=False)  # Sizi En Çok Heyecanlandıran Teknik Alan
    future_impact = db.Column(db.Text, nullable=False)  # 2040 Yılında Yaratmak İstediğiniz En Büyük Etki
    work_environment = db.Column(db.String(200), nullable=False)  # Çalışma Ortamı Hayali
    photo_path = db.Column(db.String(255))
    generated_image_path = db.Column(db.String(255))
    share_token = db.Column(db.String(100), unique=True)
    kvkk_consent = db.Column(db.Boolean, default=False)  # KVKK Onayı
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_processed = db.Column(db.Boolean, default=False)

class GeneratedSlide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slide_path = db.Column(db.String(255), nullable=False)
    participants = db.Column(db.Text)  # JSON string of participant IDs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GenerationProcess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_ids = db.Column(db.Text, nullable=False)  # JSON list of participant IDs
    story_text = db.Column(db.Text)
    image_prompt = db.Column(db.Text)
    generated_image_url = db.Column(db.String(255))
    share_token = db.Column(db.String(100), unique=True)  # Hikaye paylaşım token'ı
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check KVKK consent
        kvkk_consent = request.form.get('kvkk_consent') == 'on'
        if not kvkk_consent:
            flash('KVKK onayı gereklidir. Lütfen onay veriniz.', 'danger')
            return render_template('register.html')
        
        name = request.form.get('name')
        phone = request.form.get('phone')
        phone = normalize_phone(phone)
        profession = request.form.get('profession')
        sector = request.form.get('sector')
        technical_interest = request.form.get('technical_interest')
        future_impact = request.form.get('future_impact')
        work_environment = request.form.get('work_environment')
        
        # Validate required fields
        if not all([name, phone, profession, sector, technical_interest, future_impact, work_environment]):
            flash('Lütfen tüm zorunlu alanları doldurunuz.', 'danger')
            return render_template('register.html')
        
        # Check if participant with this phone number already exists
        existing_participant = Participant.query.filter_by(phone=phone).first()
        if existing_participant:
            # Update existing participant
            existing_participant.name = name
            existing_participant.profession = profession
            existing_participant.sector = sector
            existing_participant.technical_interest = technical_interest
            existing_participant.future_impact = future_impact
            existing_participant.work_environment = work_environment
            existing_participant.kvkk_consent = kvkk_consent
            participant = existing_participant
        else:
            # Create new participant
            participant = Participant(
                name=name,
                phone=phone,
                profession=profession,
                sector=sector,
                technical_interest=technical_interest,
                future_impact=future_impact,
                work_environment=work_environment,
                kvkk_consent=kvkk_consent,
                share_token=str(uuid.uuid4())
            )
            db.session.add(participant)
        
        # Handle photo upload
        photo = request.files.get('photo')
        if photo and photo.filename:
            # Her zaman .png olarak kaydet
            filename = secure_filename(f"{uuid.uuid4()}_{os.path.splitext(photo.filename)[0]}.png")
            
            # Fotoğrafı Pillow ile açıp PNG olarak hazırla
            img = Image.open(photo.stream)
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()
            
            # GCS'e yükle
            gcs_url = upload_to_gcs(img_data, filename, 'uploads')
            
            if not gcs_url:
                flash('Fotoğraf yüklenirken bir hata oluştu.', 'danger')
                return render_template('register.html')
            
            # Veritabanına GCS URL'sini kaydet
            participant.photo_path = gcs_url
        else:
            flash('Lütfen bir fotoğraf yükleyiniz.', 'danger')
            return render_template('register.html')
        
        db.session.commit()
        flash('Kayıt başarıyla tamamlandı!', 'success')
        return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'tumkad25':
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Hatalı şifre!', 'danger')
    return render_template('admin_login.html')

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    participants = Participant.query.order_by(Participant.created_at.desc()).all()
    return render_template('admin.html', participants=participants)

@app.route('/slides')
def slides():
    # Get all generated stories from GenerationProcess
    processes = GenerationProcess.query.filter(GenerationProcess.generated_image_url.isnot(None)).all()
    
    # Create a flat list of all story data
    all_stories = []
    for process in processes:
        # Get participant IDs from the process
        participant_ids = json.loads(process.participant_ids)
        # Get all participants for this story
        participants = Participant.query.filter(Participant.id.in_(participant_ids)).all()
        
        if participants:
            # Create participant info list
            participant_info = []
            for p in participants:
                participant_info.append({
                    'name': p.name,
                    'sector': p.sector
                })
            
            # Create story data with all participants
            story_data = {
                'participants': participant_info,
                'generated_image_path': process.generated_image_url
            }
            all_stories.append(story_data)
    
    # Group stories into sets of 3 for slides
    slide_groups = [all_stories[i:i+3] for i in range(0, len(all_stories), 3)]
    
    return render_template('slides.html', slide_groups=slide_groups)

@app.route('/share/<token>')
def share(token):
    participant = Participant.query.filter_by(share_token=token).first()
    if not participant:
        return "Görsel bulunamadı", 404
    
    return render_template('share.html', participant=participant)

@app.route('/story/<token>')
def share_story(token):
    process = GenerationProcess.query.filter_by(share_token=token).first()
    if not process:
        return "Hikaye bulunamadı", 404
    
    # Katılımcı bilgilerini getir
    try:
        participant_ids = json.loads(process.participant_ids)
        participants = Participant.query.filter(Participant.id.in_(participant_ids)).all()
    except:
        participants = []
    
    return render_template('share_story.html', process=process, participants=participants)

@app.route('/story_image/<token>')
def get_story_image(token):
    process = GenerationProcess.query.filter_by(share_token=token).first()
    if not process or not process.generated_image_url:
        return "Görsel bulunamadı", 404
    
    # GCS URL'sini doğrudan döndür
    return redirect(process.generated_image_url)

@app.route('/image/<token>')
def get_image(token):
    participant = Participant.query.filter_by(share_token=token).first()
    if not participant:
        return "Görsel bulunamadı", 404
    
    # Find the GenerationProcess that contains this participant
    processes = GenerationProcess.query.filter(GenerationProcess.generated_image_url.isnot(None)).all()
    
    for process in processes:
        participant_ids = json.loads(process.participant_ids)
        if participant.id in participant_ids and process.generated_image_url:
            # GCS URL'sini doğrudan döndür
            return redirect(process.generated_image_url)
    
    return "Görsel bulunamadı", 404

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # GCS URL'sini oluştur ve yönlendir
    gcs_url = get_gcs_file_url(filename, 'uploads')
    return redirect(gcs_url)

@app.route('/generated/<filename>')
def generated_file(filename):
    # GCS URL'sini oluştur ve yönlendir
    gcs_url = get_gcs_file_url(filename, 'generated')
    return redirect(gcs_url)

@app.route('/api/participants')
def api_participants():
    participants = Participant.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'phone': p.phone,
        'profession': p.profession,
        'sector': p.sector,
        'technical_interest': p.technical_interest,
        'future_impact': p.future_impact,
        'work_environment': p.work_environment,
        'is_processed': p.is_processed,
        'share_token': p.share_token,
        'created_at': p.created_at.isoformat() if p.created_at else None
    } for p in participants])


@app.route('/generate_story', methods=['GET', 'POST'])
def generate_story():
    participants = []
    process = None
    if request.method == 'POST':
        numbers = request.form.getlist('whatsapp_numbers')
        numbers = [normalize_phone(n.strip()) for n in numbers if n.strip()]
        if len(numbers) < 2 or len(numbers) > 4:
            flash('En az 2, en fazla 4 numara girmelisiniz.', 'danger')
            return render_template('generate_story.html', participants=[], process=None)
        if len(set(numbers)) != len(numbers):
            flash('Aynı WhatsApp numarasını birden fazla kez girdiniz. Lütfen her numarayı yalnızca bir kez girin.', 'danger')
            return render_template('generate_story.html', participants=[], process=None)
        # Katılımcıları bul
        participants = Participant.query.filter(Participant.phone.in_(numbers)).all()
        if len(participants) != len(numbers):
            flash('Bazı numaralara ait katılımcı bulunamadı.', 'danger')
            return render_template('generate_story.html', participants=[], process=None)
        
        # Hikaye oluştur
        story_text, image_prompt = generate_collaborative_story(participants)
        
        if not story_text or not image_prompt:
            flash('Hikaye oluşturulurken bir hata oluştu.', 'danger')
            return render_template('generate_story.html', participants=[], process=None)
        
        # Katılımcıların fotoğraflarını referans olarak al
        reference_images = get_participant_reference_images(participants)
        generated_image_url = None
        if reference_images and LUMALABS_API_KEY != 'your-lumalabs-api-key-here':
            generated_image_data = generate_image_with_lumalabs(image_prompt, reference_images)
            if generated_image_data:
                generated_filename = f"generated_story_{'_'.join([str(p.id) for p in participants])}_{uuid.uuid4()}.png"
                gcs_url = upload_to_gcs(generated_image_data, generated_filename, 'generated')
                if gcs_url:
                    generated_image_url = gcs_url
                else:
                    flash('Görsel GCS\'e yüklenemedi.', 'danger')
            else:
                # Asenkron işlem başlatıldı, callback ile sonucu alacağız
                flash('Görsel üretimi başlatıldı. Tamamlandığında bildirim alacaksınız.', 'info')
        else:
            flash('Lumalabs.ai API anahtarı eksik veya referans görsel yok.', 'danger')
        
        # DB kaydı - hikaye, prompt ve görsel URL'si kaydedilecek
        process = GenerationProcess(
            participant_ids=json.dumps([p.id for p in participants]),
            story_text=story_text,
            image_prompt=image_prompt,
            generated_image_url=generated_image_url,
            share_token=str(uuid.uuid4())
        )
        db.session.add(process)
        db.session.commit()
        
        flash('Hikaye ve görsel başarıyla oluşturuldu!', 'success')
        return render_template('generate_story.html', participants=participants, process=process)
    return render_template('generate_story.html', participants=[], process=None)

@app.route('/generate_image/<int:process_id>', methods=['POST'])
def generate_image(process_id):
    """
    Mevcut bir hikaye için görsel üretir.
    Lumalabs.ai API kullanarak katılımcıların fotoğraflarını referans alır.
    """
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Yetkisiz erişim'}), 401
    
    try:
        process = db.session.get(GenerationProcess, process_id)
        if not process:
            return jsonify({'success': False, 'error': 'Hikaye bulunamadı'}), 404
        
        if not process.image_prompt:
            return jsonify({'success': False, 'error': 'Görsel prompt bulunamadı'}), 404
        
        # Katılımcıları getir
        participant_ids = json.loads(process.participant_ids)
        participants = Participant.query.filter(Participant.id.in_(participant_ids)).all()
        
        if not participants:
            return jsonify({'success': False, 'error': 'Katılımcılar bulunamadı'}), 404
        
        # Katılımcıların fotoğraflarını referans olarak al
        reference_images = get_participant_reference_images(participants)
        
        # Görsel üret
        generated_filename = f"generated_story_{process_id}_{uuid.uuid4()}.png"
        
        # Lumalabs.ai ile görsel üret (referans görsellerle)
        if reference_images and LUMALABS_API_KEY != 'your-lumalabs-api-key-here':
            generated_image_data = generate_image_with_lumalabs(process.image_prompt, reference_images)
        else:
            return jsonify({'success': False, 'error': 'Lumalabs.ai API anahtarı eksik veya referans görsel yok'}), 500
        
        if not generated_image_data:
            return jsonify({'success': False, 'error': 'Görsel üretilemedi'}), 500
        
        # GCS'e yükle
        gcs_url = upload_to_gcs(generated_image_data, generated_filename, 'generated')
        
        if not gcs_url:
            return jsonify({'success': False, 'error': 'Görsel GCS\'e yüklenemedi'}), 500
        
        # Veritabanını güncelle
        process.generated_image_url = gcs_url
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'image_url': gcs_url,
            'message': 'Görsel başarıyla üretildi!',
            'method': 'Lumalabs.ai'
        })
        
    except Exception as e:
        print(f"Image generation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/debug_descriptions')
def debug_descriptions():
    if not session.get('admin_logged_in'):
        return "Yetkisiz erişim", 401
    
    participants = Participant.query.all()
    debug_info = []
    
    for p in participants:
        info = {
            'id': p.id,
            'name': p.name,
            'photo_path': p.photo_path,
            'photo_exists': p.photo_path is not None and p.photo_path.startswith('https://storage.googleapis.com/')
        }
        
        # GCS URL'si varsa dosya bilgilerini kontrol et
        if p.photo_path and p.photo_path.startswith('https://storage.googleapis.com/'):
            try:
                # GCS'den dosya bilgilerini al
                if p.photo_path.startswith(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/"):
                    blob_path = p.photo_path.replace(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/", "")
                else:
                    blob_path = p.photo_path
                
                blob = bucket.blob(blob_path)
                if blob.exists():
                    info['file_size'] = blob.size
                    info['file_path'] = p.photo_path
                else:
                    info['file_exists'] = False
            except Exception as e:
                info['gcs_error'] = str(e)
        
        debug_info.append(info)
    
    return jsonify(debug_info)

@app.route('/debug_story_generation/<int:participant_id>')
def debug_story_generation(participant_id):
    """
    Tek bir katılımcı için hikaye oluşturma sürecini test eder.
    Gelecek vizyonlarının birleşmesini gösterir.
    """
    if not session.get('admin_logged_in'):
        return "Yetkisiz erişim", 401
    
    try:
        participant = db.session.get(Participant, participant_id)
        if not participant:
            return "Katılımcı bulunamadı", 404
        
        # Kişilik analizi ve anahtar kelimeleri çıkar
        personality, keywords = analyze_participant_personality(participant)
        
        # Tek katılımcı ile hikaye oluştur (test için)
        participants = [participant]
        participants_keywords = [(participant.name, keywords)]
        
        # Ortak temaları bul
        common_themes, project_idea = find_common_themes(participants_keywords)
        
        # Görsel referansları oluştur
        visual_references = generate_visual_references(common_themes, project_idea)
        
        # Hikaye oluştur
        story_text, image_prompt = generate_collaborative_story(participants)
        
        debug_info = {
            'participant': {
                'id': participant.id,
                'name': participant.name,
                'profession': participant.profession,
                'sector': participant.sector,
                'technical_interest': participant.technical_interest,
                'future_impact': participant.future_impact,
                'work_environment': participant.work_environment
            },
            'analysis': {
                'personality': personality,
                'keywords': keywords
            },
            'themes': {
                'common_themes': common_themes,
                'project_idea': project_idea,
                'visual_references': visual_references
            },
            'story': {
                'text': story_text,
                'image_prompt': image_prompt
            },
            'vision_analysis': {
                'future_vision': participant.future_impact,
                'vision_keywords': [kw for kw in keywords if any(word in kw.lower() for word in ['future', 'vision', 'impact', 'change', 'innovation', 'technology', 'sustainable', 'collaborative'])]
            }
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        print(f"Debug story generation error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin_stories')
def admin_stories():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Tüm hikaye süreçlerini getir
    processes = GenerationProcess.query.order_by(GenerationProcess.created_at.desc()).all()
    
    # Her süreç için katılımcı bilgilerini de getir
    for process in processes:
        try:
            participant_ids = json.loads(process.participant_ids)
            process.participants = Participant.query.filter(Participant.id.in_(participant_ids)).all()
        except:
            process.participants = []
    
    return render_template('admin_stories.html', processes=processes)

@app.route('/admin/normalize_phones')
def admin_normalize_phones():
    if not session.get('admin_logged_in'):
        return "Yetkisiz erişim", 401

    participants = Participant.query.all()
    updated = 0
    for p in participants:
        normalized = normalize_phone(p.phone)
        if p.phone != normalized:
            p.phone = normalized
            updated += 1
    db.session.commit()
    return f"Tüm telefonlar normalize edildi. Güncellenen kayıt sayısı: {updated}"

@app.route('/delete_story/<int:process_id>', methods=['POST'])
def delete_story(process_id):
    """
    Hikaye ve ilişkili görseli siler.
    """
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Yetkisiz erişim'}), 401
    
    try:
        process = db.session.get(GenerationProcess, process_id)
        if not process:
            return jsonify({'success': False, 'error': 'Hikaye bulunamadı'}), 404
        
        # Eğer üretilmiş görsel varsa, GCS'den sil
        if process.generated_image_url:
            delete_from_gcs(process.generated_image_url)
        
        # Veritabanından sil
        db.session.delete(process)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Hikaye başarıyla silindi'
        })
        
    except Exception as e:
        print(f"Story deletion error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Mevcut hikayelere share_token ekle
        processes_without_token = GenerationProcess.query.filter_by(share_token=None).all()
        for process in processes_without_token:
            process.share_token = str(uuid.uuid4())
        db.session.commit()
        
    app.run(debug=True, host='0.0.0.0', port=5000) 