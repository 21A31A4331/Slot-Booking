import uuid
from datetime import date, datetime, timedelta, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from app.models import db, Service, Slot, Booking
from app.forms import BookingForm

booking_bp = Blueprint('booking', __name__)

def generate_booking_reference():
    """Generates a clean, unique booking reference code e.g. BK-20260921-A1B2."""
    today_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    random_hex = uuid.uuid4().hex[:4].upper()
    return f"BK-{today_str}-{random_hex}"


@booking_bp.route('/services')
def services_list():
    category = request.args.get('category')
    search = request.args.get('q', '').strip()

    query = Service.query.filter_by(is_active=True)

    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(
            (Service.name.ilike(f"%{search}%")) | (Service.description.ilike(f"%{search}%"))
        )

    services = query.order_by(Service.name).all()
    categories = [
        c[0] for c in db.session.query(Service.category).filter(Service.is_active == True).distinct().all() if c[0]
    ]

    return render_template('booking/services.html', services=services, categories=categories, current_category=category, search=search)


@booking_bp.route('/service/<int:service_id>/book')
@login_required
def select_slot(service_id):
    service = Service.query.get_or_404(service_id)
    if not service.is_active:
        flash('This service is currently unavailable for booking.', 'warning')
        return redirect(url_for('booking.services_list'))

    # Default to selected date or today
    selected_date_str = request.args.get('date')
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()

    form = BookingForm()

    # Get available slots for the selected date
    slots = Slot.query.filter(
        Slot.service_id == service.id,
        Slot.date == selected_date
    ).order_by(Slot.start_time).all()

    # Pre-fetch upcoming dates that have available slots (next 30 days)
    available_dates_query = db.session.query(Slot.date).filter(
        Slot.service_id == service.id,
        Slot.date >= date.today(),
        Slot.date <= date.today() + timedelta(days=30),
        Slot.is_available == True
    ).distinct().all()
    available_dates = [d[0].strftime('%Y-%m-%d') for d in available_dates_query]

    return render_template(
        'booking/select_slot.html',
        service=service,
        selected_date=selected_date,
        slots=slots,
        available_dates=available_dates,
        form=form
    )


@booking_bp.route('/api/slots/<int:service_id>')
def api_slots(service_id):
    """JSON API endpoint returning slots for a service and date."""
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Missing date parameter'}), 400

    try:
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400

    slots = Slot.query.filter(
        Slot.service_id == service_id,
        Slot.date == query_date
    ).order_by(Slot.start_time).all()

    slots_data = []
    for slot in slots:
        slots_data.append({
            'id': slot.id,
            'start_time': slot.start_time.strftime('%I:%M %p'),
            'end_time': slot.end_time.strftime('%I:%M %p'),
            'formatted_time': slot.formatted_time_range,
            'is_available': slot.is_available and not slot.is_past,
            'is_past': slot.is_past,
            'capacity': slot.capacity
        })

    return jsonify({'slots': slots_data, 'date': date_str})


@booking_bp.route('/reserve', methods=['POST'])
@login_required
def reserve_slot():
    form = BookingForm()
    if form.validate_on_submit():
        slot_id = form.slot_id.data
        notes = form.notes.data

        # Concurrency safety: check and update slot within a database transaction
        slot = db.session.query(Slot).with_for_update().filter_by(id=slot_id).first()

        if not slot:
            flash('Selected slot was not found.', 'danger')
            return redirect(url_for('booking.services_list'))

        if not slot.is_available or slot.is_past:
            flash('Sorry, this slot has just been booked or has passed. Please choose another slot.', 'warning')
            return redirect(url_for('booking.select_slot', service_id=slot.service_id, date=slot.date.strftime('%Y-%m-%d')))

        # Check if user already has an active booking for this exact slot
        existing_user_booking = Booking.query.filter_by(
            user_id=current_user.id,
            slot_id=slot.id,
            status='CONFIRMED'
        ).first()

        if existing_user_booking:
            flash('You have already booked this slot.', 'info')
            return redirect(url_for('booking.confirmation', reference=existing_user_booking.booking_reference))

        # Create booking and mark slot unavailable
        reference = generate_booking_reference()
        # Guarantee reference uniqueness
        while Booking.query.filter_by(booking_reference=reference).first():
            reference = generate_booking_reference()

        booking = Booking(
            booking_reference=reference,
            user_id=current_user.id,
            slot_id=slot.id,
            status='CONFIRMED',
            notes=notes
        )

        slot.is_available = False

        db.session.add(booking)
        db.session.commit()

        flash('Your slot has been successfully reserved!', 'success')
        return redirect(url_for('booking.confirmation', reference=reference))

    flash('Failed to reserve slot. Invalid submission.', 'danger')
    return redirect(url_for('booking.services_list'))


@booking_bp.route('/confirmation/<reference>')
@login_required
def confirmation(reference):
    booking = Booking.query.filter_by(booking_reference=reference).first_or_404()
    # Check permissions: only the booking owner or an admin can view confirmation
    if booking.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    return render_template('booking/confirmation.html', booking=booking)


@booking_bp.route('/my-bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    today = date.today()
    return render_template('booking/my_bookings.html', bookings=bookings, today=today)


@booking_bp.route('/cancel/<reference>', methods=['POST'])
@login_required
def cancel_booking(reference):
    booking = Booking.query.filter_by(booking_reference=reference).first_or_404()
    if booking.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    if booking.status == 'CANCELLED':
        flash('This booking is already cancelled.', 'info')
        return redirect(url_for('booking.my_bookings'))

    # Update booking status
    booking.status = 'CANCELLED'

    # Release the slot if slot is in the future
    slot = db.session.get(Slot, booking.slot_id)
    if slot and not slot.is_past:
        slot.is_available = True

    db.session.commit()
    flash(f'Booking #{booking.booking_reference} has been successfully cancelled.', 'success')

    if current_user.is_admin and request.referrer and 'admin' in request.referrer:
        return redirect(url_for('admin.bookings_list'))
    return redirect(url_for('booking.my_bookings'))
