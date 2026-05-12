# 🔨 HandsToHope - Informal Worker Platform for Rural India

A Django platform connecting informal workers with hirers across rural India, with community-based verification, fair admin-set wages, and a blockchain-inspired review system.

---

## ✨ Features

### For Workers (Informal Labour)
- Register with email + OTP verification
- Complete profile: Full name, Aadhar, address, skill, intro, references
- Upload portfolio photos of past work
- **Community Verification**: 3 verified workers in same area review your profile
- Toggle availability (available/unavailable)
- Accept or reject job offers
- View star ratings and reviews

### For Hirers (Employers)
- Register with email + phone + OTP verification
- Search workers by skill, date, and time
- Only see workers in **same district** (location-restricted)
- Wages **fixed by admin** per region and skill
- Send job offers with date/time/description
- Mark jobs as completed
- Write detailed star reviews

### Blockchain-Inspired Verification
- 3 high-rated verified workers auto-assigned per area to verify new workers
- **Consensus rule**: 2 agree, 1 disagrees → disagree gets -0.5 rating score; agreers get +0.25
- Unanimous agreement → everyone gets +0.25
- Incentivizes honest, accurate verification (like crypto miners)

### Admin Panel
- Set wages per state/district/skill
- View and manage all workers, hirers, verifications
- Approve/reject reviews
- Direct worker verification actions

---

## 🚀 Quick Setup

### 1. Install Requirements
```bash
cd kaamwala
pip install -r requirements.txt
```

### 2. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Create Superuser (Admin)
```bash
python manage.py createsuperuser
```

### 4. Run Development Server
```bash
python manage.py runserver
```

Open: http://127.0.0.1:8000/

---

## 📧 Email Setup (for OTP)

**Development**: OTPs are printed to the terminal console.

**Production** (Gmail SMTP example):
```python
# In kaamwala/settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'  # Use Google App Password
```

---

## 🏛️ Admin Panel

Go to: http://127.0.0.1:8000/admin/

Login with superuser credentials.

### Setting Wages
1. Go to Admin → Jobs → Wage Rates
2. Add rates for each state/district/skill combination
3. Example: `Agriculture` in `Muzaffarpur, Bihar` → `₹350/day`

---

## 📁 Project Structure

```
kaamwala/
├── manage.py
├── requirements.txt
├── kaamwala/          # Settings, URLs, WSGI
│   ├── settings.py
│   └── urls.py
├── accounts/          # Custom User model, OTP, Login/Signup
├── workers/           # Worker profiles, verification, portfolio
├── hirers/            # Hirer profiles, search, offers, reviews
├── jobs/              # JobOffer, Review, WageRate models
└── templates/         # All HTML templates
    ├── base.html
    ├── home.html
    ├── accounts/
    ├── workers/
    └── hirers/
```

---

## 🔄 User Flows

### Worker Flow
1. Sign up (email + password)
2. Verify email with OTP
3. Fill complete profile (Aadhar, address, skill, references, photo)
4. Wait for 3 nearby verified workers to verify your profile
5. Once verified → appear in search results for hirers
6. Accept/reject job offers
7. Build rating through reviews

### Hirer Flow
1. Sign up (email + phone + password)
2. Verify email with OTP
3. Complete hirer profile (name, location)
4. Search workers by skill/date/time in your area
5. Send job offer with details
6. Worker accepts/rejects
7. Mark job complete when done
8. Write review with star rating

### Verification Flow (Blockchain-style)
1. New worker submits profile
2. System auto-selects 3 highest-rated verified workers from same district
3. Each verifier gets notification in their dashboard
4. They review and vote Approve/Reject with comments
5. 2+ Approve → Worker gets Verified; minority gets score penalty
6. 2+ Reject → Worker rejected; minority gets score penalty
7. Unanimous → all verifiers earn +0.25 score

---

## 🛠️ Production Checklist

- [ ] Change `SECRET_KEY` in settings.py
- [ ] Set `DEBUG = False`
- [ ] Configure SMTP email for real OTP delivery
- [ ] Set up PostgreSQL instead of SQLite
- [ ] Configure media file storage (AWS S3, etc.)
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Add SSL certificate

---

## 💡 Technology Stack

- **Backend**: Django 4.2
- **Database**: SQLite (dev), PostgreSQL (production recommended)
- **Image handling**: Pillow
- **Frontend**: Bootstrap 5, Font Awesome 6
- **Authentication**: Custom User model with email-based auth
- **OTP**: Database-stored OTPs with console backend for dev

---

## 🌍 Built for Rural India

- All 28 Indian states + Delhi in location dropdowns
- Hindi tagline on homepage
- Skill categories relevant to Indian informal labor market
- Aadhar-based identity verification
- District-level location matching

---

*Made with ❤️ for the 400+ million informal workers of India*
