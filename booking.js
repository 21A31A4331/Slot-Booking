// Dynamic slot selection and reservation handling
document.addEventListener('DOMContentLoaded', () => {
    const datePicker = document.getElementById('slot-date-picker');
    const slotGrid = document.getElementById('slot-grid-container');
    const hiddenSlotInput = document.getElementById('slot_id');
    const submitBookingBtn = document.getElementById('btn-submit-booking');
    const selectedSlotText = document.getElementById('selected-slot-summary');
    const serviceIdElem = document.getElementById('current-service-id');

    if (datePicker && slotGrid && serviceIdElem) {
        const serviceId = serviceIdElem.value;

        // Fetch slots when date input changes
        datePicker.addEventListener('change', async (e) => {
            const selectedDate = e.target.value;
            if (!selectedDate) return;

            // Show loading state
            slotGrid.innerHTML = `
                <div class="col-12 text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading slots...</span>
                    </div>
                    <p class="mt-2 text-muted">Checking available time slots...</p>
                </div>
            `;
            
            // Reset selection
            if (hiddenSlotInput) hiddenSlotInput.value = '';
            if (submitBookingBtn) submitBookingBtn.disabled = true;
            if (selectedSlotText) selectedSlotText.textContent = 'No slot selected';

            try {
                const response = await fetch(`/booking/api/slots/${serviceId}?date=${selectedDate}`);
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || 'Failed to fetch slots');
                }

                renderSlots(data.slots);
            } catch (err) {
                slotGrid.innerHTML = `
                    <div class="col-12 text-center py-4 text-danger">
                        <i class="bi bi-exclamation-triangle fs-3"></i>
                        <p class="mt-2">Error loading slots. Please try refreshing or choosing another date.</p>
                    </div>
                `;
            }
        });

        // Function to render slot cards
        function renderSlots(slots) {
            if (!slots || slots.length === 0) {
                slotGrid.innerHTML = `
                    <div class="col-12 text-center py-5">
                        <i class="bi bi-calendar-x text-muted fs-1"></i>
                        <h5 class="mt-3 text-secondary">No slots scheduled for this date</h5>
                        <p class="text-muted small">Please select another date from the calendar.</p>
                    </div>
                `;
                return;
            }

            let html = '<div class="slot-grid w-100">';
            slots.forEach(slot => {
                if (slot.is_available) {
                    html += `
                        <div class="slot-card available" data-slot-id="${slot.id}" data-time="${slot.formatted_time}">
                            <div class="slot-time">${slot.start_time}</div>
                            <div class="slot-status-label text-success small">Available</div>
                        </div>
                    `;
                } else if (slot.is_past) {
                    html += `
                        <div class="slot-card unavailable" title="Time has passed">
                            <div class="slot-time">${slot.start_time}</div>
                            <div class="slot-status-label text-muted small">Passed</div>
                        </div>
                    `;
                } else {
                    html += `
                        <div class="slot-card unavailable" title="Already booked">
                            <div class="slot-time">${slot.start_time}</div>
                            <div class="slot-status-label text-danger small">Booked</div>
                        </div>
                    `;
                }
            });
            html += '</div>';

            slotGrid.innerHTML = html;
            attachSlotClickHandlers();
        }

        function attachSlotClickHandlers() {
            const availableCards = slotGrid.querySelectorAll('.slot-card.available');
            availableCards.forEach(card => {
                card.addEventListener('click', () => {
                    // Deselect previous
                    slotGrid.querySelectorAll('.slot-card').forEach(c => c.classList.remove('selected'));
                    
                    // Select clicked
                    card.classList.add('selected');
                    const slotId = card.getAttribute('data-slot-id');
                    const slotTime = card.getAttribute('data-time');

                    if (hiddenSlotInput) hiddenSlotInput.value = slotId;
                    if (submitBookingBtn) submitBookingBtn.disabled = false;
                    if (selectedSlotText) {
                        selectedSlotText.innerHTML = `<strong>Selected Slot:</strong> ${datePicker.value} (${slotTime})`;
                    }
                });
            });
        }

        // Attach handlers to initially rendered slots
        attachSlotClickHandlers();
    }
});
