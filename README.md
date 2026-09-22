# SlotBooker - Slot Booking Web Application

A full-featured, modern **Slot Booking & Appointment Scheduling Web Application** built by **Deepika.V** with **Python (Flask)** and **MySQL**.

---

## 🌟 Key Features

### 👤 Customer / Client Experience
- **Interactive Service Catalog**: Browse services with pricing, duration, categories, and keyword search.
- **Dynamic Slot Picker**: Interactive calendar and real-time visual slot grid with instant availability status.
- **Conflict-Free Reservation**: Atomic database locking prevents race conditions and double-bookings.
- **Booking Confirmation & Receipts**: Instant human-readable booking reference (`BK-YYYYMMDD-XXXX`) with printable appointment receipts.
- **Self-Service Dashboard ("My Bookings")**: Track upcoming and past appointments, view receipts, and cancel bookings with automatic slot release.

### 🛡️ Administrator Control Center
- **Executive KPI Dashboard**: Live stats for total bookings, today's appointments, available future slots, and registered users.
- **Service CRUD**: Add, edit, deactivate, or delete services with custom duration and pricing.
- **Bulk Slot Generator**: Automatically generate time slots across date ranges, customizable business hours (e.g. 09:00 - 17:00), intervals (e.g. 30 or 60 mins), and weekend exclusion options.
- **Manual Slot Manager**: Add one-off slots or delete individual scheduled slots with filtering by date, service, and availability.
- **Bookings Oversight**: Master control table to search, filter by status (`CONFIRMED`, `COMPLETED`, `CANCELLED`), and update booking states.
- **Users Directory**: View registered clients and roles.

---

## 🏗️ Tech Stack

- **Backend**: Python 3.10+ / 3.13 (Flask 3.x)
- **Database**: MySQL 8.0+ / MariaDB via pure-Python `PyMySQL` driver
- **ORM & Data Layer**: Flask-SQLAlchemy (SQLAlchemy 2.0)
- **Authentication**: Flask-Login + Werkzeug salted password hashing (`pbkdf2`/`scrypt`)
- **Forms & Validation**: Flask-WTF / WTForms with CSRF tokens
- **Frontend**: Bootstrap 5, Bootstrap Icons, custom responsive CSS, and Vanilla JavaScript for asynchronous slot lookups

---

## 🚀 Quick Start (Zero Setup)

The application comes ready to run out-of-the-box. If a local MySQL server is not currently running, it seamlessly defaults to a local SQLite database for instant development and testing.

### 1. Activate the Virtual Environment
On Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Initialize and Seed the Database
```powershell
python init_db.py
```
This seeds the initial administrator account, sample client, default services (Medical, Dental, Workspace, Fitness), and over 190 upcoming time slots.

### 3. Launch the Web Application
```powershell
python run.py
```
Open your browser and navigate to: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🔑 Default Credentials

| Role | Username | Email | Password |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin@slotbooker.local` | `Admin@123` |
| **Demo Client** | `john_client` | `john@example.com` | `Client@123` |

*(You can also register a new client account anytime via the "Get Started" button on the navbar.)*

---

## 🗄️ MySQL Database Setup & Configuration

To connect the application to your native MySQL server:

### Step 1: Configure `.env`
Edit the `.env` file in the project root:
```env
# Secret Key
SECRET_KEY=your-secure-production-secret-key

# MySQL Configuration
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=slot_booking_db

# Set to False to strictly enforce MySQL without fallback
USE_SQLITE_FALLBACK=False
```

### Step 2: Initialize MySQL Database
You can initialize your MySQL database in either of two ways:

#### Option A: Using Python (`init_db.py`)
```powershell
python init_db.py
```
*(Automatically creates `slot_booking_db` if permissions allow, runs table migrations, and seeds initial data.)*

#### Option B: Direct SQL Import (`schema.sql`)
Run the provided `schema.sql` in MySQL Command Line, MySQL Workbench, or phpMyAdmin:
```powershell
mysql -u root -p < schema.sql
```

---

## 📁 Project Directory Structure

```
slot-booking/
├── .env                  # Environment variables & DB configuration
├── .env.example          # Environment template
├── .gitignore            # Git exclusion rules
├── config.py             # App configuration & intelligent DB connection resolver
├── init_db.py            # DB schema creation & seed script
├── requirements.txt      # Python dependencies
├── run.py                # Server execution entrypoint
├── schema.sql            # Native MySQL DDL schema script
├── app/
│   ├── __init__.py       # Application factory & blueprint registration
│   ├── forms.py          # WTForms input validation & CSRF
│   ├── models.py         # SQLAlchemy models (User, Service, Slot, Booking)
│   ├── routes/
│   │   ├── admin.py      # Admin dashboard, service CRUD, slot generator
│   │   ├── auth.py       # Authentication (register, login, logout, profile)
│   │   ├── booking.py    # Slot booking flow, API, cancellation
│   │   └── main.py       # Homepage, landing info, about page
│   ├── static/
│   │   ├── css/style.css # Modern styling, slot grid, receipt styling
│   │   └── js/booking.js # Dynamic slot fetching & AJAX date selection
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── about.html
│       ├── auth/         # login, register, profile
│       ├── booking/      # services, select_slot, confirmation, my_bookings
│       └── admin/        # dashboard, services, service_form, slots, generate_slots, bookings, users
└── tests/
    ├── test_app.py       # Automated unit tests for auth, conflicts, and admin rules
    └── test_live_db.py   # Live database integration tests
```

---

## 🧪 Running Automated Tests

Run the complete test suite with `unittest`:
```powershell
python -m unittest discover -s tests
```
All 10 tests will execute, validating authentication, double-booking prevention, atomic slot release, and role protection.
