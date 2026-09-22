import os
from datetime import date, time, datetime, timedelta
import pymysql
from config import Config
from app import create_app
from app.models import db, User, Service, Slot, Booking

def ensure_mysql_database():
    """Attempts to connect to MySQL server and ensure the target database exists."""
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=int(Config.DB_PORT),
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            connect_timeout=3
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.commit()
        conn.close()
        print(f"[OK] MySQL database '{Config.DB_NAME}' verified/created.")
        return True
    except Exception as e:
        print(f"[WARNING] MySQL database connection/creation skipped: {e}")
        return False

def seed_database(app):
    with app.app_context():
        # Create all tables according to SQLAlchemy models
        db.create_all()
        print("[OK] Database tables created successfully.")

        # 1. Seed Admin User
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@slotbooker.local',
                full_name='System Administrator',
                phone='+1 800-555-0100',
                role='admin'
            )
            admin_user.set_password('Admin@123')
            db.session.add(admin_user)
            print("[SEED] Admin account created: admin / Admin@123")

        # 2. Seed Demo Client User
        client_user = User.query.filter_by(username='john_client').first()
        if not client_user:
            client_user = User(
                username='john_client',
                email='john@example.com',
                full_name='John Doe',
                phone='+1 800-555-0199',
                role='client'
            )
            client_user.set_password('Client@123')
            db.session.add(client_user)
            print("[SEED] Client account created: john_client / Client@123")

        db.session.commit()

        # 3. Seed Services
        if Service.query.count() == 0:
            sample_services = [
                Service(
                    name="General Health Consultation",
                    category="Medical",
                    duration_minutes=30,
                    price=45.00,
                    description="Comprehensive 1-on-1 health assessment with a certified physician.",
                    is_active=True
                ),
                Service(
                    name="Dental Cleaning & Exam",
                    category="Dental",
                    duration_minutes=45,
                    price=80.00,
                    description="Routine dental cleaning, plaque removal, and oral hygiene assessment.",
                    is_active=True
                ),
                Service(
                    name="Executive Conference Room Booking",
                    category="Workspace",
                    duration_minutes=60,
                    price=35.00,
                    description="Equipped with 4K display, video conference camera, and high-speed Wi-Fi.",
                    is_active=True
                ),
                Service(
                    name="Personal Fitness Consultation",
                    category="Wellness",
                    duration_minutes=45,
                    price=40.00,
                    description="Custom fitness roadmap, body composition assessment, and workout plan.",
                    is_active=True
                )
            ]
            db.session.add_all(sample_services)
            db.session.commit()
            print(f"[SEED] Created {len(sample_services)} default services.")

        # 4. Seed Slots for the next 7 days
        services = Service.query.filter_by(is_active=True).all()
        total_slots_created = 0

        for service in services:
            # Check if this service already has slots scheduled for upcoming days
            existing_slots = Slot.query.filter(
                Slot.service_id == service.id,
                Slot.date >= date.today()
            ).count()

            if existing_slots == 0:
                # Generate slots for next 7 days
                for day_offset in range(1, 8):
                    slot_date = date.today() + timedelta(days=day_offset)
                    # Skip weekends
                    if slot_date.weekday() in (5, 6):
                        continue

                    # Slots from 09:00 to 16:00
                    start_dt = datetime.combine(slot_date, time(9, 0))
                    day_end_dt = datetime.combine(slot_date, time(16, 0))

                    while start_dt + timedelta(minutes=service.duration_minutes) <= day_end_dt:
                        slot_start = start_dt.time()
                        slot_end = (start_dt + timedelta(minutes=service.duration_minutes)).time()

                        slot = Slot(
                            service_id=service.id,
                            date=slot_date,
                            start_time=slot_start,
                            end_time=slot_end,
                            capacity=1,
                            is_available=True
                        )
                        db.session.add(slot)
                        total_slots_created += 1

                        start_dt += timedelta(minutes=service.duration_minutes)

        db.session.commit()
        if total_slots_created > 0:
            print(f"[SEED] Created {total_slots_created} initial time slots across services.")

        print("\n=======================================================")
        print("  Slot Booking Database Initialization Complete!")
        print("=======================================================")
        print("Admin Credentials:")
        print("  Username: admin")
        print("  Password: Admin@123")
        print("\nDemo Client Credentials:")
        print("  Username: john_client")
        print("  Password: Client@123")
        print("=======================================================\n")

if __name__ == '__main__':
    # Step 1: Ensure MySQL database exists if MySQL is running
    ensure_mysql_database()

    # Step 2: Initialize application and tables
    app = create_app()
    seed_database(app)
