from flask import Blueprint, render_template
from app.models import Service, Slot, Booking
from datetime import date

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    featured_services = Service.query.filter_by(is_active=True).limit(6).all()
    total_services = Service.query.filter_by(is_active=True).count()
    available_slots_count = Slot.query.filter(
        Slot.date >= date.today(),
        Slot.is_available == True
    ).count()

    return render_template(
        'index.html',
        services=featured_services,
        total_services=total_services,
        available_slots_count=available_slots_count
    )

@main_bp.route('/about')
def about():
    return render_template('about.html')
