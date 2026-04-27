const slotType = document.querySelector('#id_slot_type');
const timeFields = document.querySelectorAll('[data-time-field]');
const eventFields = document.querySelectorAll('[data-event-field]');
const timeInputs = [
    document.querySelector('#id_start_time_minutes'),
    document.querySelector('#id_end_time_minutes'),
].filter(Boolean);
const eventInput = document.querySelector('#id_event_type');

function syncTimeFields() {
    const isUnavailable = slotType && slotType.value === 'unavailable';

    timeFields.forEach((field) => {
        field.classList.toggle('is-hidden', isUnavailable);
    });

    eventFields.forEach((field) => {
        field.classList.toggle('is-hidden', isUnavailable);
    });

    timeInputs.forEach((input) => {
        input.disabled = isUnavailable;
    });

    if (eventInput) {
        eventInput.disabled = isUnavailable;
    }
}

if (slotType) {
    slotType.addEventListener('change', syncTimeFields);
    syncTimeFields();
}
