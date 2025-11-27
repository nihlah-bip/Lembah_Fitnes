from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func

app = Flask(__name__)

# ==========================================
# WAJIB DITAMBAHKAN AGAR LOGIN BISA JALAN
# ==========================================
app.secret_key = 'kunci_rahasia_lembah_fitness_123' 

# Konfigurasi Database (yang sudah ada)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lembah_fitness.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# 2. DEFINISI MODEL (TABEL DATABASE)
# ==========================================

# Tabel User (Login)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'manager', 'admin', 'pt'


# Tabel Member (Data Pelanggan Lengkap)
class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_lengkap = db.Column(db.String(100), nullable=False)
    program = db.Column(db.String(50), nullable=False)  # Insidental / Reguler / Personal Trainer

    # Data Umum (Untuk Reguler & PT)
    no_wa = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    alamat = db.Column(db.Text, nullable=True)
    ttl = db.Column(db.Date, nullable=True)  # Tanggal Lahir

    # Data Fisik (Khusus PT)
    tinggi_badan = db.Column(db.Integer, nullable=True)
    berat_badan = db.Column(db.Integer, nullable=True)
    goals = db.Column(db.String(50), nullable=True)  # Muscle Gain / Bulking / Cutting

    # Personal trainer yang dipilih (khusus program Personal Trainer)
    trainer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Status Membership
    status = db.Column(db.String(20), default='Aktif')
    tgl_daftar = db.Column(db.Date, default=datetime.utcnow)
    tgl_habis = db.Column(db.Date, nullable=False)

    # Relasi
    pembayaran = db.relationship('Pembayaran', backref='member', lazy=True)
    latihan = db.relationship('Latihan', backref='member', lazy=True)


# Tabel Latihan (Progres)
class Latihan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    tanggal = db.Column(db.Date, default=datetime.utcnow)
    berat_badan = db.Column(db.Float, nullable=True)
    bmi = db.Column(db.Float, nullable=True)
    jadwal_teks = db.Column(db.String(200), nullable=True)


# Tabel Pembayaran
class Pembayaran(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    tanggal_bayar = db.Column(db.Date, default=datetime.utcnow)
    nominal = db.Column(db.Integer, nullable=False)
    keterangan = db.Column(db.String(100), nullable=True)


# ==========================================
# 3. ROUTE (JALUR HALAMAN)
# ==========================================

# --- BAGIAN PUBLIC (MEMBER/PENGUNJUNG) ---
@app.route('/')
def index():
    return render_template('public/home.html')


@app.route('/about')
def about():
    return render_template('public/about.html')


@app.route('/courses')
def courses():
    return render_template('public/courses.html')


@app.route('/pricing')
def pricing():
    return render_template('public/pricing.html')


@app.route('/gallery')
def gallery():
    return render_template('public/gallery.html')


@app.route('/blog')
def blog():
    return render_template('public/blog.html')


@app.route('/blog/details')
def blog_details():
    return render_template('public/blog_details.html')


@app.route('/contact')
def contact():
    return render_template('public/contact.html')

# @app.route('/login')
# def login():
#     return render_template('login/login.html')


@app.route('/services')
def services():
    return render_template('public/services.html')


@app.route('/elements')
def elements():
    return render_template('public/elements.html')

# --- ROUTE LOGIN (PINTU MASUK) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Cek database
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session.clear() # Bersihkan sesi lama
            # Simpan data login baru
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Username atau Password Salah!', 'danger')
            
    return render_template('admin/login.html')

# --- ROUTE LOGOUT ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- BAGIAN ADMIN (DASHBOARD & SISTEM) ---
@app.route('/admin')
def admin_dashboard():
    """
    Dashboard admin dengan data:
    - pemasukan bulanan (tabel Pembayaran) tahun ini
    - jumlah pendaftaran per program per bulan tahun ini
    - pemasukan bulan ini & total setahun (untuk kartu kecil)
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    today = datetime.utcnow().date()
    year = today.year
    year_str = str(year)

    # Label bulan untuk chart
    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
                    'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

    # ===== 1. Pemasukan bulanan (Pembayaran) =====
    income_per_month = [0] * 12  # index 0 = Jan

    income_rows = (
        db.session.query(
            func.strftime('%m', Pembayaran.tanggal_bayar).label('month'),
            func.sum(Pembayaran.nominal)
        )
        .filter(func.strftime('%Y', Pembayaran.tanggal_bayar) == year_str)
        .group_by('month')
        .all()
    )

    for month_str, total in income_rows:
        idx = int(month_str) - 1
        income_per_month[idx] = int(total or 0)

    current_month_index = today.month - 1
    month_income_value = income_per_month[current_month_index]
    year_income_value = sum(income_per_month)

    # ===== 2. Pendaftaran member per program per bulan =====
    programs = ['Insidental', 'Reguler', 'Personal Trainer']
    registrations_per_program = {p: [0] * 12 for p in programs}

    reg_rows = (
        db.session.query(
            func.strftime('%m', Member.tgl_daftar).label('month'),
            Member.program,
            func.count(Member.id)
        )
        .filter(func.strftime('%Y', Member.tgl_daftar) == year_str)
        .group_by('month', Member.program)
        .all()
    )

    for month_str, program, count in reg_rows:
        idx = int(month_str) - 1
        if program in registrations_per_program:
            registrations_per_program[program][idx] = int(count or 0)

    return render_template(
        'admin/dashboard.html',
        labels=month_labels,
        income_data=income_per_month,
        registrations_data=registrations_per_program,
        month_income=month_income_value,
        year_income=year_income_value,
        year=year
    )


# --- HALAMAN MANAJEMEN MEMBER ---
@app.route('/admin/members')
def manage_members():
    # Ambil semua data member, urutkan dari yang paling baru daftar
    all_members = Member.query.order_by(Member.id.desc()).all()

    # Kirim tanggal hari ini agar HTML bisa menghitung sisa hari aktif
    today = datetime.utcnow().date()

    return render_template(
        'admin/manage_members.html',
        members=all_members,
        today_date=today
    )


# HAPUS MEMBER
@app.route('/admin/members/delete/<int:member_id>', methods=['POST'])
def delete_member(member_id):
    member = Member.query.get_or_404(member_id)

    # Hapus dulu data yang berelasi (Latihan & Pembayaran)
    Latihan.query.filter_by(member_id=member.id).delete()
    Pembayaran.query.filter_by(member_id=member.id).delete()

    # Hapus member-nya
    db.session.delete(member)
    db.session.commit()

    return redirect(url_for('manage_members'))


# --- HALAMAN INPUT PEMBAYARAN (KASIR) ---
@app.route('/admin/payments', methods=['GET', 'POST'])
def payments():
    if request.method == 'POST':
        member_id = request.form['member_id']
        nominal = int(request.form['nominal'])
        bulan_tambah = int(request.form['bulan_tambah'])  # 1, 3, 6, atau 12
        keterangan = request.form['keterangan']

        # Simpan ke Tabel Pembayaran (Log Transaksi)
        bayar_baru = Pembayaran(
            member_id=member_id,
            nominal=nominal,
            keterangan=keterangan,
            tanggal_bayar=datetime.utcnow()
        )
        db.session.add(bayar_baru)

        # Update tanggal habis member
        member = Member.query.get(member_id)
        today = datetime.utcnow().date()

        if member.tgl_habis < today:
            base_date = today
        else:
            base_date = member.tgl_habis

        new_expired_date = base_date + timedelta(days=30 * bulan_tambah)

        member.tgl_habis = new_expired_date
        member.status = 'Aktif'

        db.session.commit()

        return redirect(url_for('payments'))

    # GET: tampilkan halaman pembayaran
    all_members = Member.query.order_by(Member.nama_lengkap.asc()).all()
    history = Pembayaran.query.order_by(Pembayaran.id.desc()).limit(10).all()

    return render_template(
        'admin/payments.html',
        members=all_members,
        history_pembayaran=history
    )


@app.route('/admin/training')
def training():
    return render_template('admin/dashboard.html')  # Placeholder


# --- FITUR MANAGER: KELOLA STAFF (READ & CREATE) ---
@app.route('/admin/staff', methods=['GET', 'POST'])
def manage_staff():
    # Cek Login & Cek Role (Hanya Manager yang boleh akses)
    if 'user_id' not in session: return redirect(url_for('login'))
    if session.get('role') != 'manager': return "Akses Ditolak! Hanya Manager.", 403

    # LOGIKA TAMBAH STAFF BARU (CREATE)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        # Cek apakah username sudah ada?
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username sudah dipakai! Ganti yang lain.', 'danger')
        else:
            # Hash password biar aman
            hashed_pw = generate_password_hash(password)
            new_user = User(username=username, password=hashed_pw, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('Akun berhasil dibuat!', 'success')
        
        return redirect(url_for('manage_staff'))

    # TAMPILKAN TABEL STAFF (READ)
    all_users = User.query.order_by(User.role.asc()).all()
    return render_template('admin/manage_staff.html', users=all_users)

# --- FITUR HAPUS STAFF (DELETE) ---
@app.route('/admin/staff/delete/<int:id>', methods=['POST'])
def delete_staff(id):
    if 'user_id' not in session or session.get('role') != 'manager':
        return redirect(url_for('login'))
    
    user_to_delete = User.query.get_or_404(id)
    
    # Mencegah manager menghapus dirinya sendiri
    if user_to_delete.username == session['username'] or user_to_delete.username == 'manager':
        flash('Tidak bisa menghapus akun utama!', 'warning')
    else:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('Akun berhasil dihapus.', 'success')
        
    return redirect(url_for('manage_staff'))

# ==========================================
# 4. INISIALISASI DATABASE
# ==========================================
with app.app_context():
    db.create_all()



# --- HALAMAN REGISTRASI & TRANSAKSI (ALL IN ONE) ---
@app.route('/admin/registrasi', methods=['GET', 'POST'])
def registrasi():
    if request.method == 'POST':
        # 1. Ambil Data Dasar
        program = request.form['program']
        nama = request.form['nama']
        no_wa = request.form['no_wa']
        nominal = int(request.form['nominal'])  # Harga otomatis dari form

        # 2. Siapkan Variabel Opsional
        gender = None
        alamat = None
        ttl_date = None
        tb = None
        bb = None
        goals = None
        personal_trainer = None  # <-- untuk program Personal Trainer

        # Tanggal habis default
        tgl_habis = datetime.utcnow().date()

        # 3. Logika Berdasarkan Program
        if program == 'Insidental':
            # Insidental cuma aktif 1 hari (hari ini)
            tgl_habis = datetime.utcnow().date()

        elif program == 'Reguler' or program == 'Personal Trainer':
            # Data tambahan
            gender = request.form['gender']
            alamat = request.form['alamat']
            ttl_input = request.form['ttl']

            if ttl_input:
                ttl_date = datetime.strptime(ttl_input, '%Y-%m-%d').date()

            # aktif 1 bulan (30 hari)
            tgl_habis = datetime.utcnow().date() + timedelta(days=30)

            if program == 'Personal Trainer':
                # Data fisik & goals
                tb = request.form['tinggi_badan']
                bb = request.form['berat_badan']
                goals = request.form['goals']
                personal_trainer = request.form.get('personal_trainer')  # <-- ambil dari form

        # 4. Simpan Data Member Baru
            member_baru = Member(
                nama_lengkap=nama, 
                program=program, 
                no_wa=no_wa, 
                gender=gender,
                alamat=alamat, 
                ttl=ttl_date, 
                tinggi_badan=tb, 
                berat_badan=bb,
                goals=goals, 
                tgl_habis=tgl_habis, 
                status='Aktif'
                # Hapus koma di baris atasnya juga biar rapi
            )
        db.session.add(member_baru)
        db.session.commit()  # supaya dapat ID

        # 5. Otomatis Catat Pembayaran
        bayar_baru = Pembayaran(
            member_id=member_baru.id,
            nominal=nominal,
            keterangan=f"Pendaftaran {program}",
            tanggal_bayar=datetime.utcnow()
        )
        db.session.add(bayar_baru)
        db.session.commit()

        return redirect(url_for('registrasi'))

    # GET -> tampilkan form registrasi
    return render_template('admin/registrasi.html')

# --- ROUTE DARURAT: PAKSA BUAT AKUN ---
@app.route('/buat_akun_darurat')
def buat_akun_darurat():
    # 1. Hash Password
    password_aman = generate_password_hash('admin123')
    
    # 2. Cek apakah user manager sudah ada?
    cek_user = User.query.filter_by(username='manager').first()
    
    if cek_user:
        # Kalau ada, kita update passwordnya saja biar yakin
        cek_user.password = password_aman
        db.session.commit()
        return "Akun 'manager' SUDAH ADA. Password telah di-reset jadi: admin123. Silakan Login."
    else:
        # Kalau belum ada, kita buat baru
        manager_baru = User(username='manager', password=password_aman, role='manager')
        db.session.add(manager_baru)
        db.session.commit()
        return "BERHASIL! Akun 'manager' baru saja dibuat. Password: admin123. Silakan Login."

# ==========================================
# ROUTE KHUSUS DASHBOARD PT (TRAINER)
# ==========================================
@app.route('/pt/dashboard')
def pt_dashboard():
    # Cek login dulu (Opsional, bisa diaktifkan nanti)
    # if 'user_id' not in session: return redirect(url_for('login'))
    
    # SEMENTARA: Kita set ID Trainer manual = 1 (Nanti diganti session['user_id'])
    trainer_id = 1 
    
    # Ambil member yang di-assign ke trainer ini
    my_clients = Member.query.filter_by(trainer_id=trainer_id).all()
    count = len(my_clients)
    
    return render_template('admin/dashboard_pt.html', my_members=my_clients, my_members_count=count)


# ==========================================
# ROUTE KHUSUS PORTAL MEMBER (PELANGGAN)
# ==========================================
# Akses lewat browser: /member/dashboard/1 (angka 1 adalah ID member)
@app.route('/member/dashboard/<int:id>')
def member_dashboard(id):
    # Ambil data member
    member = Member.query.get_or_404(id)
    
    # Ambil riwayat latihan
    logs = Latihan.query.filter_by(member_id=id).order_by(Latihan.tanggal.asc()).all()
    
    today = datetime.utcnow().date()
    
    # Arahkan ke folder templates/member/dashboard.html
    return render_template('member/dashboard.html', member=member, logs=logs, today=today)

# -----------------------------------------------------------
# PASTIKAN KODE INI TETAP PALING BAWAH
# -----------------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # ... (kode buat akun admin default) ...
    app.run(debug=True)

