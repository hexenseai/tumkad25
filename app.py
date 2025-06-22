from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
import json
from PIL import Image
import io
from gcs import upload_to_gcs, get_gcs_file_url, delete_from_gcs, download_from_gcs
import tempfile

from utils import normalize_phone, apply_template_to_image_data
from generation import generate_collaborative_story, regenerate_image_from_story


# OpenAI API konfigürasyonu
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'your-openai-api-key-here')

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
    email = db.Column(db.String(100), nullable=False)  # Email adresi
    profession = db.Column(db.String(100), nullable=False)  # Mesleğiniz / Temel Uzmanlık Alanı
    sector = db.Column(db.String(100), nullable=False)  # Çalıştığınız Sektör
    technical_interest = db.Column(db.Text, nullable=False)  # Sizi En Çok Heyecanlandıran Teknik Alan
    future_impact = db.Column(db.Text, nullable=False)  # 2040 Yılında Yaratmak İstediğiniz En Büyük Etki
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
    status = db.Column(db.String(20), default='processing')  # processing, completed, failed
    whatsapp_notification_sent = db.Column(db.Boolean, default=False)  # WhatsApp bildirimi gönderildi mi
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
        email = request.form.get('email')
        profession = request.form.get('profession')
        sector = request.form.get('sector')
        technical_interest = request.form.get('technical_interest')
        future_impact = request.form.get('future_impact')
        
        # Validate required fields
        if not all([name, phone, email, profession, sector, technical_interest, future_impact]):
            flash('Lütfen tüm zorunlu alanları doldurunuz.', 'danger')
            return render_template('register.html')
        
        # Check if participant with this phone number already exists
        existing_participant = Participant.query.filter_by(phone=phone).first()
        if existing_participant:
            # Update existing participant
            existing_participant.name = name
            existing_participant.email = email
            existing_participant.profession = profession
            existing_participant.sector = sector
            existing_participant.technical_interest = technical_interest
            existing_participant.future_impact = future_impact
            existing_participant.kvkk_consent = kvkk_consent
            participant = existing_participant
        else:
            # Create new participant
            participant = Participant(
                name=name,
                phone=phone,
                email=email,
                profession=profession,
                sector=sector,
                technical_interest=technical_interest,
                future_impact=future_impact,
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
            
            # GCS'e yükle (bu aslında yerel dosya sistemine kaydediyor)
            gcs_url = upload_to_gcs(img_data, filename, 'uploads')
            
            if not gcs_url:
                flash('Fotoğraf yüklenirken bir hata oluştu.', 'danger')
                return render_template('register.html')
            
            # Veritabanına GCS URL'sini kaydet
            participant.photo_path = gcs_url
            
            print(f"Fotoğraf başarıyla kaydedildi: {filename}")
            print(f"Yerel URL: {gcs_url}")
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
    # Get all completed stories from GenerationProcess
    processes = GenerationProcess.query.filter(
        GenerationProcess.generated_image_url.isnot(None),
        GenerationProcess.status == 'completed'
    ).all()
    
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
    
    # Filename'i çıkar ve generated_file route'unu kullan
    filename = process.generated_image_url.split('/')[-1] if '/' in process.generated_image_url else process.generated_image_url
    return redirect(url_for('generated_file', filename=filename))

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
            # Filename'i çıkar ve generated_file route'unu kullan
            filename = process.generated_image_url.split('/')[-1] if '/' in process.generated_image_url else process.generated_image_url
            return redirect(url_for('generated_file', filename=filename))
    
    return "Görsel bulunamadı", 404

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """
    Uploaded dosyaları serve eder. Yerel dosya sisteminden doğrudan gösterir.
    """
    try:
        # Yerel dosyayı kontrol et
        local_path = os.path.join('local_uploads', filename)
        if os.path.exists(local_path):
            return send_file(
                local_path,
                mimetype='image/png',
                as_attachment=False,
                download_name=filename
            )
        else:
            print(f"Local file not found: {local_path}")
            return "Dosya bulunamadı", 404
            
    except Exception as e:
        print(f"Uploaded file serving error: {e}")
        return "Dosya servis hatası", 500

@app.route('/generated/<filename>')
def generated_file(filename):
    """
    Generated dosyaları serve eder. Yerel dosya sisteminden doğrudan gösterir.
    """
    try:
        # Yerel dosyayı kontrol et
        local_path = os.path.join('local_generated', filename)
        if os.path.exists(local_path):
            return send_file(
                local_path,
                mimetype='image/png',
                as_attachment=False,
                download_name=filename
            )
        else:
            print(f"Local file not found: {local_path}")
            return "Dosya bulunamadı", 404
            
    except Exception as e:
        print(f"Generated file serving error: {e}")
        return "Dosya servis hatası", 500

@app.route('/api/participants')
def api_participants():
    participants = Participant.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'phone': p.phone,
        'email': p.email,
        'profession': p.profession,
        'sector': p.sector,
        'technical_interest': p.technical_interest,
        'future_impact': p.future_impact,
        'is_processed': p.is_processed,
        'share_token': p.share_token,
        'created_at': p.created_at.isoformat() if p.created_at else None
    } for p in participants])

@app.route('/api/participant/<int:participant_id>')
def get_participant_details(participant_id):
    """
    Belirli bir katılımcının tüm detaylarını getirir.
    """
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Yetkisiz erişim'}), 401
    
    participant = Participant.query.get(participant_id)
    if not participant:
        return jsonify({'error': 'Katılımcı bulunamadı'}), 404
    
    return jsonify({
        'id': participant.id,
        'name': participant.name,
        'phone': participant.phone,
        'email': participant.email,
        'profession': participant.profession,
        'sector': participant.sector,
        'technical_interest': participant.technical_interest,
        'future_impact': participant.future_impact,
        'photo_path': participant.photo_path,
        'generated_image_path': participant.generated_image_path,
        'share_token': participant.share_token,
        'kvkk_consent': participant.kvkk_consent,
        'is_processed': participant.is_processed,
        'created_at': participant.created_at.isoformat() if participant.created_at else None
    })

@app.route('/api/participant/<int:participant_id>/update_photo', methods=['POST'])
def update_participant_photo(participant_id):
    """
    Katılımcının fotoğrafını günceller.
    """
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Yetkisiz erişim'}), 401
    
    participant = Participant.query.get(participant_id)
    if not participant:
        return jsonify({'error': 'Katılımcı bulunamadı'}), 404
    
    # Fotoğraf dosyasını kontrol et
    if 'photo' not in request.files:
        return jsonify({'error': 'Fotoğraf dosyası bulunamadı'}), 400
    
    photo = request.files['photo']
    if photo.filename == '':
        return jsonify({'error': 'Fotoğraf seçilmedi'}), 400
    
    try:
        # Eski fotoğrafı sil (eğer varsa)
        if participant.photo_path:
            try:
                delete_from_gcs(participant.photo_path)
            except Exception as e:
                print(f"Eski fotoğraf silinirken hata: {e}")
        
        # Yeni fotoğrafı işle ve yükle
        filename = secure_filename(f"{uuid.uuid4()}_square_photo.png")
        
        # Fotoğrafı Pillow ile açıp PNG olarak hazırla
        img = Image.open(photo.stream)
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_data = img_buffer.getvalue()
        
        # GCS'e yükle
        gcs_url = upload_to_gcs(img_data, filename, 'uploads')
        
        if not gcs_url:
            return jsonify({'error': 'Fotoğraf yüklenirken bir hata oluştu'}), 500
        
        # Veritabanını güncelle
        participant.photo_path = gcs_url
        participant.is_processed = False  # Yeni fotoğraf için işlem durumunu sıfırla
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Fotoğraf başarıyla güncellendi',
            'photo_path': gcs_url
        })
        
    except Exception as e:
        print(f"Fotoğraf güncelleme hatası: {e}")
        return jsonify({'error': f'Fotoğraf güncellenirken hata oluştu: {str(e)}'}), 500

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
        
        # Yeni hikaye oluşturma süreci - 6 adımlı süreç
        if OPENAI_API_KEY == 'your-openai-api-key-here':
            flash('OpenAI API anahtarı eksik. Lütfen .env dosyasında OPENAI_API_KEY değişkenini ayarlayın.', 'danger')
            return render_template('generate_story.html', participants=[], process=None)
        
        try:
            # Yeni generate_collaborative_story fonksiyonu hem hikaye hem görsel üretir
            story_text, story_visual_prompt, final_image_data = generate_collaborative_story(participants)
            
            if not story_text:
                flash('Hikaye oluşturulurken bir hata oluştu.', 'danger')
                return render_template('generate_story.html', participants=[], process=None)
            
            generated_image_url = None
            if final_image_data:
                # Görseli GCS'e yükle
                generated_filename = f"generated_story_{'_'.join([str(p.id) for p in participants])}_{uuid.uuid4()}.png"
                gcs_url = upload_to_gcs(final_image_data, generated_filename, 'generated')
                if gcs_url:
                    generated_image_url = gcs_url
                else:
                    flash('Görsel GCS\'e yüklenemedi.', 'danger')
            else:
                flash('Görsel üretimi başarısız oldu.', 'warning')
            
            # DB kaydı - hikaye, görsel prompt ve görsel URL'si kaydedilecek
            process = GenerationProcess(
                participant_ids=json.dumps([p.id for p in participants]),
                story_text=story_text,
                image_prompt=story_visual_prompt,  # Artık gerçek prompt kaydediliyor
                generated_image_url=generated_image_url,
                share_token=str(uuid.uuid4()),
                status='completed' if generated_image_url else 'failed'
            )
            db.session.add(process)
            db.session.commit()
            
            if generated_image_url:
                flash('Hikaye ve görsel başarıyla oluşturuldu!', 'success')
            else:
                flash('Hikaye oluşturuldu ancak görsel üretimi başarısız oldu.', 'warning')
            
            return render_template('generate_story.html', participants=participants, process=process)
            
        except Exception as e:
            print(f"Story generation error: {e}")
            flash(f'Hikaye oluşturulurken bir hata oluştu: {str(e)}', 'danger')
            return render_template('generate_story.html', participants=[], process=None)
    
    return render_template('generate_story.html', participants=[], process=None)

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
            'photo_exists': p.photo_path is not None and p.photo_path.startswith('/local_files/')
        }
        
        # Yerel dosya URL'si varsa dosya bilgilerini kontrol et
        if p.photo_path and p.photo_path.startswith('/local_files/'):
            try:
                # Yerel dosya bilgilerini al
                local_path = p.photo_path.replace('/local_files/', '')
                if local_path.startswith('uploads/'):
                    full_path = os.path.join('local_uploads', local_path.replace('uploads/', ''))
                elif local_path.startswith('generated/'):
                    full_path = os.path.join('local_generated', local_path.replace('generated/', ''))
                else:
                    full_path = local_path
                
                if os.path.exists(full_path):
                    info['file_size'] = os.path.getsize(full_path)
                    info['file_path'] = p.photo_path
                else:
                    info['file_exists'] = False
            except Exception as e:
                info['local_error'] = str(e)
        
        debug_info.append(info)
    
    return jsonify(debug_info)

@app.route('/debug_story_generation/<int:participant_id>')
def debug_story_generation(participant_id):
    """
    Tek bir katılımcı için hikaye oluşturma sürecini test eder.
    Yeni 6 adımlı süreci gösterir.
    """
    if not session.get('admin_logged_in'):
        return "Yetkisiz erişim", 401
    
    try:
        participant = db.session.get(Participant, participant_id)
        if not participant:
            return "Katılımcı bulunamadı", 404
        
        # Yeni süreç ile test
        participants = [participant]
        
        # Yeni generate_collaborative_story fonksiyonunu test et
        story_text, story_visual_prompt, final_image_data = generate_collaborative_story(participants)
        
        debug_info = {
            'participant': {
                'id': participant.id,
                'name': participant.name,
                'profession': participant.profession,
                'sector': participant.sector,
                'technical_interest': participant.technical_interest,
                'future_impact': participant.future_impact
            },
            'new_process': {
                'story_text': story_text,
                'story_visual_prompt': story_visual_prompt,
                'image_generated': final_image_data is not None,
                'image_size': len(final_image_data) if final_image_data else 0
            },
            'process_info': {
                'method': 'New 6-step OpenAI process',
                'steps': [
                    '1. Individual vision story generation',
                    '2. Collaborative future story creation',
                    '3. Story visual prompt creation',
                    '4. Group selfie generation with gpt-image-1',
                    '5. Image generation with DALL-E',
                    '6. AI remix of story and selfie images'
                ]
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

@app.route('/local_files/<folder>/<filename>')
def local_file(folder, filename):
    """
    Yerel dosyaları servis eder.
    """
    try:
        if folder == 'uploads':
            file_path = os.path.join('local_uploads', filename)
        elif folder == 'generated':
            file_path = os.path.join('local_generated', filename)
        else:
            return "Geçersiz klasör", 404
        
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='image/png')
        else:
            return "Dosya bulunamadı", 404
    except Exception as e:
        print(f"Local file serving error: {e}")
        return "Dosya servis hatası", 500

@app.route('/generate_image/<int:process_id>', methods=['POST'])
def generate_image(process_id):
    """
    Generate image for a specific story process
    """
    try:
        # Find the generation process
        process = GenerationProcess.query.get(process_id)
        if not process:
            return jsonify({'success': False, 'error': 'Process not found'}), 404
        
        # Get participant IDs from the process
        participant_ids = json.loads(process.participant_ids)
        
        # Get participants
        participants = Participant.query.filter(Participant.id.in_(participant_ids)).all()
        if not participants:
            return jsonify({'success': False, 'error': 'No participants found for this process'}), 400
        
        # Generate collaborative story and image
        story, story_visual_prompt, image_data = generate_collaborative_story(participants)
        
        if not image_data:
            # Set status to failed if image generation fails
            process.status = 'failed'
            db.session.commit()
            return jsonify({'success': False, 'error': 'Failed to generate image'}), 500
        
        # Save image to GCS
        filename = f"generated_story_{process_id}_{uuid.uuid4()}.png"
        gcs_url = upload_to_gcs(image_data, filename, 'generated')
        
        if not gcs_url:
            return jsonify({'success': False, 'error': 'Failed to upload image to storage'}), 500
        
        # Update process with generated image URL and prompt
        process.generated_image_url = gcs_url
        process.status = 'completed'  # Set status to completed
        if story and not process.story_text:
            process.story_text = story
        if story_visual_prompt and not process.image_prompt:
            process.image_prompt = story_visual_prompt
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Image generated successfully',
            'image_url': gcs_url,
            'method': 'DALL-E 3 with Character Reference'
        })
        
    except Exception as e:
        print(f"Error generating image for process {process_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/regenerate_image/<int:process_id>', methods=['POST'])
def regenerate_image(process_id):
    """
    Mevcut hikaye ve görsel prompt'undan görseli yeniden üretir.
    """
    try:
        # Find the generation process
        process = GenerationProcess.query.get(process_id)
        if not process:
            return jsonify({'success': False, 'error': 'Process not found'}), 404
        
        # Check if we have story and prompt data
        if not process.story_text or not process.image_prompt:
            return jsonify({'success': False, 'error': 'Story or visual prompt data missing'}), 400
        
        # Get participant IDs from the process
        participant_ids = json.loads(process.participant_ids)
        
        # Get participants
        participants = Participant.query.filter(Participant.id.in_(participant_ids)).all()
        if not participants:
            return jsonify({'success': False, 'error': 'No participants found for this process'}), 400
        
        # Regenerate image from existing story and prompt
        story, visual_prompt, image_data = regenerate_image_from_story(
            process.story_text, 
            process.image_prompt, 
            participants
        )
        
        if not image_data:
            # Set status to failed if image regeneration fails
            process.status = 'failed'
            db.session.commit()
            return jsonify({'success': False, 'error': 'Failed to regenerate image'}), 500
        
        # Save image to GCS
        filename = f"regenerated_story_{process_id}_{uuid.uuid4()}.png"
        gcs_url = upload_to_gcs(image_data, filename, 'generated')
        
        if not gcs_url:
            return jsonify({'success': False, 'error': 'Failed to upload image to storage'}), 500
        
        # Update process with new generated image URL
        process.generated_image_url = gcs_url
        process.status = 'completed'  # Set status to completed
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Image regenerated successfully',
            'image_url': gcs_url,
            'method': 'Regenerated from existing story and prompt'
        })
        
    except Exception as e:
        print(f"Error regenerating image for process {process_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/debug_local_files')
def debug_local_files():
    """
    Yerel dosya sisteminin durumunu kontrol eder.
    """
    if not session.get('admin_logged_in'):
        return "Yetkisiz erişim", 401
    
    debug_info = {
        'local_uploads_exists': os.path.exists('local_uploads'),
        'local_generated_exists': os.path.exists('local_generated'),
        'local_uploads_files': [],
        'local_generated_files': [],
        'participants_with_photos': []
    }
    
    # local_uploads klasöründeki dosyaları listele
    if os.path.exists('local_uploads'):
        debug_info['local_uploads_files'] = os.listdir('local_uploads')
    
    # local_generated klasöründeki dosyaları listele
    if os.path.exists('local_generated'):
        debug_info['local_generated_files'] = os.listdir('local_generated')
    
    # Katılımcıların fotoğraf yollarını kontrol et
    participants = Participant.query.all()
    for participant in participants:
        if participant.photo_path:
            debug_info['participants_with_photos'].append({
                'id': participant.id,
                'name': participant.name,
                'photo_path': participant.photo_path,
                'is_local': participant.photo_path.startswith('/local_files/')
            })
    
    return jsonify(debug_info)

@app.route('/debug_image_urls')
def debug_image_urls():
    """
    Veritabanındaki görsel URL'lerini kontrol eder.
    """
    if not session.get('admin_logged_in'):
        return "Yetkisiz erişim", 401
    
    processes = GenerationProcess.query.all()
    debug_info = []
    
    for process in processes:
        info = {
            'process_id': process.id,
            'generated_image_url': process.generated_image_url,
            'url_type': 'Local' if process.generated_image_url and process.generated_image_url.startswith('/local_files/') else 'None',
            'created_at': process.created_at.isoformat() if process.created_at else None
        }
        
        # URL varsa dosya varlığını kontrol et
        if process.generated_image_url:
            if process.generated_image_url.startswith('/local_files/'):
                # Yerel dosyayı kontrol et
                local_path = process.generated_image_url.replace('/local_files/', '')
                if local_path.startswith('uploads/'):
                    full_path = os.path.join('local_uploads', local_path.replace('uploads/', ''))
                elif local_path.startswith('generated/'):
                    full_path = os.path.join('local_generated', local_path.replace('generated/', ''))
                else:
                    full_path = local_path
                
                info['file_exists'] = os.path.exists(full_path)
                if os.path.exists(full_path):
                    info['file_size'] = os.path.getsize(full_path)
        
        debug_info.append(info)
    
    return jsonify(debug_info)

@app.route('/send_whatsapp_notification/<int:process_id>', methods=['POST'])
def send_whatsapp_notification(process_id):
    """
    Katılımcılara WhatsApp bildirimi gönderir.
    """
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Yetkisiz erişim'}), 401
    
    try:
        # Find the generation process
        process = GenerationProcess.query.get(process_id)
        if not process:
            return jsonify({'success': False, 'error': 'Process not found'}), 404
        
        # Check if story is completed
        if not process.generated_image_url:
            return jsonify({'success': False, 'error': 'Story is not completed yet'}), 400
        
        # Get participant IDs from the process
        participant_ids = json.loads(process.participant_ids)
        
        # Get participants
        participants = Participant.query.filter(Participant.id.in_(participant_ids)).all()
        if not participants:
            return jsonify({'success': False, 'error': 'No participants found for this process'}), 400
        
        # Create share story URL
        share_url = request.host_url.rstrip('/') + url_for('share_story', token=process.share_token)
        
        # Create WhatsApp message
        participant_names = ', '.join([p.name for p in participants])
        message = f"""🎉 TUMKAD 2040 Hikayeniz Hazır!

Merhaba {participant_names},

Birlikte oluşturduğumuz 2040 vizyon hikayeniz hazır! Hikayenizi görüntülemek için aşağıdaki linke tıklayabilirsiniz:

{share_url}

Bu hikaye, sizin vizyonlarınızın birleşiminden oluşturulmuş özel bir AI görseli içermektedir.

TUMKAD Ekibi"""

        # Create WhatsApp links for each participant
        whatsapp_links = []
        for participant in participants:
            # Remove any non-numeric characters from phone number
            clean_phone = ''.join(filter(str.isdigit, participant.phone))
            # Add country code if not present (assuming Turkey +90)
            if not clean_phone.startswith('90'):
                clean_phone = '90' + clean_phone
            # Create WhatsApp link
            encoded_message = message.replace(' ', '%20').replace('\n', '%0A')
            whatsapp_url = f"https://wa.me/{clean_phone}?text={encoded_message}"
            whatsapp_links.append({
                'name': participant.name,
                'phone': participant.phone,
                'whatsapp_url': whatsapp_url
            })
        
        # Mark as notification sent
        process.whatsapp_notification_sent = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'WhatsApp notification prepared successfully',
            'whatsapp_links': whatsapp_links,
            'share_url': share_url
        })
        
    except Exception as e:
        print(f"Error sending WhatsApp notification for process {process_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Mevcut hikayelere share_token ekle
        processes_without_token = GenerationProcess.query.filter_by(share_token=None).all()
        for process in processes_without_token:
            process.share_token = str(uuid.uuid4())
        
        # Mevcut hikayelere status ve whatsapp_notification_sent alanlarını ekle
        processes_without_status = GenerationProcess.query.filter_by(status=None).all()
        for process in processes_without_status:
            # Eğer görsel varsa tamamlandı, yoksa başarısız olarak işaretle
            if process.generated_image_url:
                process.status = 'completed'
            else:
                process.status = 'failed'
            # WhatsApp bildirimi henüz gönderilmemiş
            if not hasattr(process, 'whatsapp_notification_sent') or process.whatsapp_notification_sent is None:
                process.whatsapp_notification_sent = False
        
        db.session.commit()
        
    app.run(debug=True, host='0.0.0.0', port=5000) 