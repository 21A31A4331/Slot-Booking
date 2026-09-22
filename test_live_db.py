import unittest
from datetime import date, time, timedelta
from app import create_app
from app.models import db, User, Service, Slot, Booking
from config import Config

class LiveDatabaseIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(Config)
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Dedicated test slot in the future to ensure pure isolation
        self.test_service = Service.query.first()
        self.future_date = date.today() + timedelta(days=20)
        
        # Clean up any leftover test slot from previous runs
        existing_test_slot = Slot.query.filter_by(
            service_id=self.test_service.id,
            date=self.future_date,
            start_time=time(11, 0)
        ).first()
        if existing_test_slot:
            db.session.delete(existing_test_slot)
            db.session.commit()

        self.test_slot = Slot(
            service_id=self.test_service.id,
            date=self.future_date,
            start_time=time(11, 0),
            end_time=time(11, 30),
            capacity=1,
            is_available=True
        )
        db.session.add(self.test_slot)
        db.session.commit()

    def tearDown(self):
        # Clean up test artifacts
        if hasattr(self, 'test_slot') and self.test_slot.id:
            slot = db.session.get(Slot, self.test_slot.id)
            if slot:
                db.session.delete(slot)
                db.session.commit()
        self.app_context.pop()

    def test_seeded_data_exists(self):
        admin = User.query.filter_by(username='admin').first()
        self.assertIsNotNone(admin)
        self.assertTrue(admin.is_admin)

        client = User.query.filter_by(username='john_client').first()
        self.assertIsNotNone(client)
        self.assertEqual(client.role, 'client')

        services_count = Service.query.count()
        self.assertGreaterEqual(services_count, 4)

        slots_count = Slot.query.count()
        self.assertGreaterEqual(slots_count, 100)

    def test_client_booking_workflow(self):
        # 1. Login
        res = self.client.post('/auth/login', data={
            'username': 'john_client',
            'password': 'Client@123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'John', res.data)

        # 2. Book the dedicated test slot
        res = self.client.post('/booking/reserve', data={
            'slot_id': self.test_slot.id,
            'notes': 'Automated test booking'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Appointment Receipt', res.data)
        self.assertIn(b'Reservation Confirmed', res.data)

        # 3. Check slot is marked booked
        updated_slot = db.session.get(Slot, self.test_slot.id)
        self.assertFalse(updated_slot.is_available)

        # 4. Check booking appears in My Bookings
        res = self.client.get('/booking/my-bookings')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Automated test booking', res.data)

        # 5. Cancel booking using latest booking reference for this slot
        booking = Booking.query.filter_by(slot_id=self.test_slot.id).order_by(Booking.id.desc()).first()
        self.assertIsNotNone(booking)
        res = self.client.post(f'/booking/cancel/{booking.booking_reference}', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'cancelled', res.data)

        # 6. Verify slot is released back to available
        released_slot = db.session.get(Slot, self.test_slot.id)
        self.assertTrue(released_slot.is_available)

    def test_admin_dashboard_and_slot_generation(self):
        # 1. Login as admin
        res = self.client.post('/auth/login', data={
            'username': 'admin',
            'password': 'Admin@123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Administrator Control Center', res.data)

        # 2. View dashboard
        res = self.client.get('/admin/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'System Overview', res.data)

        # 3. View bookings oversight
        res = self.client.get('/admin/bookings')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Bookings Oversight', res.data)

        # 4. View users list
        res = self.client.get('/admin/users')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'john_client', res.data)

if __name__ == '__main__':
    unittest.main()
