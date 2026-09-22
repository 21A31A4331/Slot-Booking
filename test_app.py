import unittest
from datetime import date, time, timedelta, datetime
from app import create_app
from app.models import db, User, Service, Slot, Booking
from config import TestConfig

class SlotBookingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create Admin
        self.admin = User(
            username='admin_test',
            email='admin@test.local',
            full_name='Admin Tester',
            role='admin'
        )
        self.admin.set_password('AdminPass123')

        # Create Regular User
        self.user = User(
            username='client_test',
            email='client@test.local',
            full_name='Client Tester',
            role='client'
        )
        self.user.set_password('ClientPass123')

        # Create Sample Service
        self.service = Service(
            name='Dental Checkup',
            category='Dental',
            duration_minutes=30,
            price=50.00,
            description='Test dental examination',
            is_active=True
        )

        db.session.add_all([self.admin, self.user, self.service])
        db.session.commit()

        # Create Sample Slot (tomorrow at 10:00 AM)
        self.tomorrow = date.today() + timedelta(days=1)
        self.slot = Slot(
            service_id=self.service.id,
            date=self.tomorrow,
            start_time=time(10, 0),
            end_time=time(10, 30),
            capacity=1,
            is_available=True
        )
        db.session.add(self.slot)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_user(self, username='client_test', password='ClientPass123'):
        return self.client.post('/auth/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def logout_user(self):
        return self.client.get('/auth/logout', follow_redirects=True)

    def test_user_authentication(self):
        # Successful login
        res = self.login_user('client_test', 'ClientPass123')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Welcome back', res.data)

        # Logout
        res = self.logout_user()
        self.assertIn(b'You have been logged out', res.data)

        # Invalid password
        res = self.login_user('client_test', 'WrongPassword')
        self.assertIn(b'Invalid username/email or password', res.data)

    def test_homepage_and_services(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Dental Checkup', res.data)

        res = self.client.get('/booking/services')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Dental Checkup', res.data)

    def test_slot_api(self):
        date_str = self.tomorrow.strftime('%Y-%m-%d')
        res = self.client.get(f'/booking/api/slots/{self.service.id}?date={date_str}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('slots', data)
        self.assertEqual(len(data['slots']), 1)
        self.assertTrue(data['slots'][0]['is_available'])

    def test_slot_booking_flow(self):
        self.login_user('client_test', 'ClientPass123')

        # Reserve slot
        res = self.client.post('/booking/reserve', data={
            'slot_id': self.slot.id,
            'notes': 'First time visit'
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Appointment Receipt', res.data)
        self.assertIn(b'First time visit', res.data)

        # Verify slot is no longer available in DB
        slot_in_db = db.session.get(Slot, self.slot.id)
        self.assertFalse(slot_in_db.is_available)

        # Verify booking created in DB
        booking = Booking.query.filter_by(slot_id=self.slot.id).first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.status, 'CONFIRMED')
        self.assertTrue(booking.booking_reference.startswith('BK-'))

    def test_double_booking_prevention(self):
        # Manually mark slot as booked
        self.slot.is_available = False
        db.session.commit()

        self.login_user('client_test', 'ClientPass123')
        res = self.client.post('/booking/reserve', data={
            'slot_id': self.slot.id,
            'notes': 'Trying to double book'
        }, follow_redirects=True)

        self.assertIn(b'slot has just been booked or has passed', res.data)

    def test_booking_cancellation_releases_slot(self):
        self.login_user('client_test', 'ClientPass123')

        # Create a booking
        booking = Booking(
            booking_reference='BK-TEST-1234',
            user_id=self.user.id,
            slot_id=self.slot.id,
            status='CONFIRMED'
        )
        self.slot.is_available = False
        db.session.add(booking)
        db.session.commit()

        # Cancel the booking
        res = self.client.post(f'/booking/cancel/{booking.booking_reference}', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'has been successfully cancelled', res.data)

        # Verify slot is released back to available
        slot_in_db = db.session.get(Slot, self.slot.id)
        self.assertTrue(slot_in_db.is_available)

        # Verify booking status is updated
        booking_in_db = Booking.query.filter_by(booking_reference='BK-TEST-1234').first()
        self.assertEqual(booking_in_db.status, 'CANCELLED')

    def test_admin_access_control(self):
        # Regular client should receive 403 Forbidden on admin pages
        self.login_user('client_test', 'ClientPass123')
        res = self.client.get('/admin/')
        self.assertEqual(res.status_code, 403)

        self.logout_user()

        # Admin user should access admin dashboard
        self.login_user('admin_test', 'AdminPass123')
        res = self.client.get('/admin/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'System Overview', res.data)

if __name__ == '__main__':
    unittest.main()
