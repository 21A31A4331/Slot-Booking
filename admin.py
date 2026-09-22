from functools import wraps
from datetime import datetime, date, time, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.models import db, User, Service, Slot, Booking
from app.forms import ServiceForm, SlotGeneratorForm, ManualSlotForm

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.before_request
@login_required
@admin_required
def require_admin():
    """Ensure all admin blueprint routes require admin role."""
    pass


@admin_bp.route('/')
def dashboard():
    today = date.today()
    total_bookings = Booking.query.count()
    today_bookings = Booking.query.join(Slot).filter(Slot.date == today).count()
    total_services = Service.query.count()
    total_users = User.query.filter_by(role='client').count()
    upcoming_available_slots = Slot.query.filter(Slot.date >= today, Slot.is_available == True).count()

    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(8).all()

    return render_template(
        'admin/dashboard.html',
        total_bookings=total_bookings,
        today_bookings=today_bookings,
        total_services=total_services,
        total_users=total_users,
        upcoming_available_slots=upcoming_available_slots,
        recent_bookings=recent_bookings,
        today=today
    )


# ---------------- Services Management ----------------
@admin_bp.route('/services')
def services_list():
    services = Service.query.order_by(Service.id.desc()).all()
    return render_template('admin/services.html', services=services)


@admin_bp.route('/services/new', methods=['GET', 'POST'])
def add_service():
    form = ServiceForm()
    if form.validate_on_submit():
        service = Service(
            name=form.name.data.strip(),
            category=form.category.data.strip(),
            duration_minutes=form.duration_minutes.data,
            price=form.price.data,
            description=form.description.data.strip() if form.description.data else None,
            is_active=form.is_active.data
        )
        db.session.add(service)
        db.session.commit()
        flash(f'Service "{service.name}" created successfully!', 'success')
        return redirect(url_for('admin.services_list'))

    return render_template('admin/service_form.html', form=form, title='Add New Service')


@admin_bp.route('/services/<int:service_id>/edit', methods=['GET', 'POST'])
def edit_service(service_id):
    service = db.get_or_404(Service, service_id)
    form = ServiceForm(obj=service)

    if form.validate_on_submit():
        service.name = form.name.data.strip()
        service.category = form.category.data.strip()
        service.duration_minutes = form.duration_minutes.data
        service.price = form.price.data
        service.description = form.description.data.strip() if form.description.data else None
        service.is_active = form.is_active.data
        db.session.commit()
        flash(f'Service "{service.name}" updated successfully!', 'success')
        return redirect(url_for('admin.services_list'))

    return render_template('admin/service_form.html', form=form, title=f'Edit: {service.name}', service=service)


@admin_bp.route('/services/<int:service_id>/toggle', methods=['POST'])
def toggle_service(service_id):
    service = db.get_or_404(Service, service_id)
    service.is_active = not service.is_active
    db.session.commit()
    status_text = 'activated' if service.is_active else 'deactivated'
    flash(f'Service "{service.name}" has been {status_text}.', 'info')
    return redirect(url_for('admin.services_list'))


@admin_bp.route('/services/<int:service_id>/delete', methods=['POST'])
def delete_service(service_id):
    service = db.get_or_404(Service, service_id)
    name = service.name
    db.session.delete(service)
    db.session.commit()
    flash(f'Service "{name}" deleted successfully.', 'success')
    return redirect(url_for('admin.services_list'))


# ---------------- Slots Management & Generator ----------------
@admin_bp.route('/slots')
def slots_list():
    service_id = request.args.get('service_id', type=int)
    date_filter = request.args.get('date')
    status_filter = request.args.get('status')

    query = Slot.query

    if service_id:
        query = query.filter(Slot.service_id == service_id)

    if date_filter:
        try:
            d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Slot.date == d)
        except ValueError:
            pass
    else:
        # Default show today and future
        query = query.filter(Slot.date >= date.today())

    if status_filter == 'available':
        query = query.filter(Slot.is_available == True)
    elif status_filter == 'booked':
        query = query.filter(Slot.is_available == False)

    slots = query.order_by(Slot.date.asc(), Slot.start_time.asc()).limit(200).all()
    services = Service.query.order_by(Service.name).all()

    return render_template(
        'admin/slots.html',
        slots=slots,
        services=services,
        selected_service=service_id,
        selected_date=date_filter,
        selected_status=status_filter
    )


@admin_bp.route('/slots/generate', methods=['GET', 'POST'])
def generate_slots():
    form = SlotGeneratorForm()
    services = Service.query.filter_by(is_active=True).order_by(Service.name).all()
    form.service_id.choices = [(s.id, s.name) for s in services]

    if form.validate_on_submit():
        service_id = form.service_id.data
        start_date = form.start_date.data
        end_date = form.end_date.data
        start_time = form.start_time.data
        end_time = form.end_time.data
        duration_minutes = form.slot_duration.data
        capacity = form.capacity.data
        skip_weekends = form.skip_weekends.data

        created_count = 0
        skipped_count = 0

        current_curr_date = start_date
        while current_curr_date <= end_date:
            # Check weekend skip
            if skip_weekends and current_curr_date.weekday() in (5, 6):
                current_curr_date += timedelta(days=1)
                continue

            # Generate slots within the day window
            curr_slot_dt = datetime.combine(current_curr_date, start_time)
            day_end_dt = datetime.combine(current_curr_date, end_time)

            while curr_slot_dt + timedelta(minutes=duration_minutes) <= day_end_dt:
                slot_start = curr_slot_dt.time()
                slot_end = (curr_slot_dt + timedelta(minutes=duration_minutes)).time()

                # Check if slot already exists
                existing = Slot.query.filter_by(
                    service_id=service_id,
                    date=current_curr_date,
                    start_time=slot_start
                ).first()

                if not existing:
                    new_slot = Slot(
                        service_id=service_id,
                        date=current_curr_date,
                        start_time=slot_start,
                        end_time=slot_end,
                        capacity=capacity,
                        is_available=True
                    )
                    db.session.add(new_slot)
                    created_count += 1
                else:
                    skipped_count += 1

                curr_slot_dt += timedelta(minutes=duration_minutes)

            current_curr_date += timedelta(days=1)

        db.session.commit()
        flash(f'Slot generation complete! {created_count} slots created ({skipped_count} skipped duplicates).', 'success')
        return redirect(url_for('admin.slots_list', service_id=service_id))

    return render_template('admin/generate_slots.html', form=form)


@admin_bp.route('/slots/new', methods=['GET', 'POST'])
def add_slot():
    form = ManualSlotForm()
    services = Service.query.filter_by(is_active=True).order_by(Service.name).all()
    form.service_id.choices = [(s.id, s.name) for s in services]

    if form.validate_on_submit():
        existing = Slot.query.filter_by(
            service_id=form.service_id.data,
            date=form.date.data,
            start_time=form.start_time.data
        ).first()

        if existing:
            flash('A slot for this service at the chosen date and start time already exists.', 'warning')
        else:
            slot = Slot(
                service_id=form.service_id.data,
                date=form.date.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data,
                capacity=form.capacity.data,
                is_available=True
            )
            db.session.add(slot)
            db.session.commit()
            flash('Slot added successfully.', 'success')
            return redirect(url_for('admin.slots_list', service_id=form.service_id.data))

    return render_template('admin/add_slot.html', form=form)


@admin_bp.route('/slots/<int:slot_id>/delete', methods=['POST'])
def delete_slot(slot_id):
    slot = db.get_or_404(Slot, slot_id)
    service_id = slot.service_id
    db.session.delete(slot)
    db.session.commit()
    flash('Slot deleted successfully.', 'success')
    return redirect(url_for('admin.slots_list', service_id=service_id))


# ---------------- Bookings Oversight ----------------
@admin_bp.route('/bookings')
def bookings_list():
    status = request.args.get('status')
    search = request.args.get('search', '').strip()
    date_filter = request.args.get('date')

    query = Booking.query.join(User).join(Slot).join(Service)

    if status:
        query = query.filter(Booking.status == status)

    if date_filter:
        try:
            d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Slot.date == d)
        except ValueError:
            pass

    if search:
        query = query.filter(
            (Booking.booking_reference.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (Service.name.ilike(f"%{search}%"))
        )

    bookings = query.order_by(Booking.created_at.desc()).all()

    return render_template('admin/bookings.html', bookings=bookings, current_status=status, search=search, date_filter=date_filter)


@admin_bp.route('/bookings/<int:booking_id>/status', methods=['POST'])
def update_booking_status(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    new_status = request.form.get('status')

    if new_status in ('CONFIRMED', 'COMPLETED', 'CANCELLED'):
        old_status = booking.status
        booking.status = new_status

        # If transitioning to CANCELLED, release the slot
        if new_status == 'CANCELLED' and old_status != 'CANCELLED':
            slot = db.session.get(Slot, booking.slot_id)
            if slot and not slot.is_past:
                slot.is_available = True
        # If transitioning back to CONFIRMED from CANCELLED, re-occupy the slot if available
        elif new_status == 'CONFIRMED' and old_status == 'CANCELLED':
            slot = db.session.get(Slot, booking.slot_id)
            if slot:
                slot.is_available = False

        db.session.commit()
        flash(f'Booking #{booking.booking_reference} status changed to {new_status}.', 'success')
    else:
        flash('Invalid status specified.', 'danger')

    return redirect(request.referrer or url_for('admin.bookings_list'))


# ---------------- Users Management ----------------
@admin_bp.route('/users')
def users_list():
    users = User.query.order_by(User.role.asc(), User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)
