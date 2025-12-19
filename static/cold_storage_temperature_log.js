/**
 * Cold Storage Temperature Log - Frontend JavaScript
 * Date/Time-based entry: Select date and time, then enter temperature for all units
 */

// Global state
let allUnits = [];
let currentDate = new Date();
let currentTime = '10:00 AM';
let scheduledTimes = ['10:00 AM', '02:00 PM', '06:00 PM', '10:00 PM'];

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    setupNotifications();
    updateDateDisplay();
    loadUnits();
});

// Event Listeners
function initializeEventListeners() {
    // Date and time selection
    document.getElementById('log-date')?.addEventListener('change', handleDateChange);
    document.getElementById('log-time')?.addEventListener('change', handleTimeChange);
    
    // Unit management
    document.getElementById('add-unit-btn')?.addEventListener('click', openAddUnitForm);
    document.getElementById('manage-add-unit-btn')?.addEventListener('click', openAddUnitForm);
    document.getElementById('unit-form-close')?.addEventListener('click', closeUnitForm);
    document.getElementById('cancel-unit-form')?.addEventListener('click', closeUnitForm);
    document.getElementById('unit-form')?.addEventListener('submit', handleUnitFormSubmit);
    
    // Unit type change - show/hide wine chiller temps
    document.getElementById('unit-type')?.addEventListener('change', function() {
        const wineChillerTemps = document.getElementById('wine-chiller-temps');
        if (this.value === 'Wine Chiller') {
            wineChillerTemps.classList.remove('hidden');
        } else {
            wineChillerTemps.classList.add('hidden');
        }
    });
    
    // PDF generation
    document.getElementById('generate-pdf-btn')?.addEventListener('click', openPDFModal);
    document.getElementById('pdf-modal-close')?.addEventListener('click', closePDFModal);
    document.getElementById('cancel-pdf')?.addEventListener('click', closePDFModal);
    document.getElementById('pdf-form')?.addEventListener('submit', handlePDFGeneration);
    
    // Report type change
    document.querySelectorAll('input[name="report_type"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const endDateGroup = document.getElementById('pdf-end-date-group');
            if (this.value === 'weekly') {
                endDateGroup.classList.remove('hidden');
                document.getElementById('pdf-end-date').required = true;
            } else {
                endDateGroup.classList.add('hidden');
                document.getElementById('pdf-end-date').required = false;
            }
        });
    });
}

// Date and Time Management
function updateDateDisplay() {
    const dateInput = document.getElementById('log-date');
    if (dateInput) {
        dateInput.value = formatDateForInput(currentDate);
    }
    
    const displayDate = document.getElementById('display-date');
    if (displayDate) {
        displayDate.textContent = formatDateDisplay(currentDate);
    }
    
    const displayTime = document.getElementById('display-time');
    if (displayTime) {
        displayTime.textContent = currentTime;
    }
}

function formatDateForInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function formatDateDisplay(date) {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 
                    'July', 'August', 'September', 'October', 'November', 'December'];
    
    const dayName = days[date.getDay()];
    const monthName = months[date.getMonth()];
    const day = date.getDate();
    const year = date.getFullYear();
    
    return `${dayName}, ${monthName} ${day}, ${year}`;
}

function handleDateChange() {
    const dateInput = document.getElementById('log-date');
    if (dateInput && dateInput.value) {
        currentDate = new Date(dateInput.value);
        updateDateDisplay();
        loadTemperatureEntries();
    }
}

function handleTimeChange() {
    const timeSelect = document.getElementById('log-time');
    if (timeSelect) {
        currentTime = timeSelect.value;
        updateDateDisplay();
        loadTemperatureEntries();
    }
}

// Load Units
async function loadUnits() {
    try {
        const response = await fetch('/checklist/bar/cold-storage/units');
        allUnits = await response.json();
        
        renderTemperatureTable();
        
        // Hide empty state if units exist
        const emptyState = document.getElementById('empty-state');
        const logSection = document.getElementById('temperature-log-section');
        
        if (allUnits.length > 0) {
            if (emptyState) emptyState.classList.add('hidden');
            if (logSection) logSection.style.display = 'block';
        } else {
            if (emptyState) emptyState.classList.remove('hidden');
            if (logSection) logSection.style.display = 'none';
        }
    } catch (error) {
        console.error('Error loading units:', error);
        showNotification('Error loading units', 'error');
    }
}

// Render Temperature Table
function renderTemperatureTable() {
    const tbody = document.getElementById('temperature-log-tbody');
    tbody.innerHTML = '';
    
    if (allUnits.length === 0) {
        return;
    }
    
    allUnits.forEach(unit => {
        const row = createUnitRow(unit);
        tbody.appendChild(row);
    });
    
    // Load existing entries for current date/time
    loadTemperatureEntries();
}

// Create Unit Row
function createUnitRow(unit) {
    const row = document.createElement('tr');
    row.className = 'temperature-row';
    row.setAttribute('data-unit-id', unit.id);
    
    // Unit Number cell
    const unitCell = document.createElement('td');
    unitCell.className = 'unit-cell';
    unitCell.textContent = unit.unit_number;
    row.appendChild(unitCell);
    
    // Location cell
    const locationCell = document.createElement('td');
    locationCell.className = 'location-cell';
    locationCell.textContent = unit.location;
    row.appendChild(locationCell);
    
    // Type cell
    const typeCell = document.createElement('td');
    typeCell.className = 'type-cell';
    typeCell.textContent = unit.unit_type;
    row.appendChild(typeCell);
    
    // Temperature cell
    const tempCell = document.createElement('td');
    tempCell.className = 'temperature-cell';
    const tempInputWrapper = document.createElement('div');
    tempInputWrapper.className = 'temp-input-wrapper';
    
    const tempInput = document.createElement('input');
    tempInput.type = 'number';
    tempInput.step = '0.1';
    tempInput.className = 'temperature-input';
    tempInput.setAttribute('data-unit-id', unit.id);
    tempInput.placeholder = 'Enter temperature';
    
    const tempUnit = document.createElement('span');
    tempUnit.className = 'temp-unit';
    tempUnit.textContent = '°C';
    
    tempInputWrapper.appendChild(tempInput);
    tempInputWrapper.appendChild(tempUnit);
    tempCell.appendChild(tempInputWrapper);
    tempInput.addEventListener('blur', () => validateAndSaveEntry(unit.id));
    tempInput.addEventListener('input', () => validateTemperatureInput(unit.id));
    
    row.appendChild(tempCell);
    
    // Corrective action cell
    const actionCell = document.createElement('td');
    actionCell.className = 'corrective-action-cell';
    const actionTextarea = document.createElement('textarea');
    actionTextarea.className = 'corrective-action-input';
    actionTextarea.setAttribute('data-unit-id', unit.id);
    actionTextarea.placeholder = 'Enter corrective action if needed';
    actionTextarea.addEventListener('blur', () => saveEntry(unit.id));
    actionCell.appendChild(actionTextarea);
    row.appendChild(actionCell);
    
    // Initial cell
    const initialCell = document.createElement('td');
    initialCell.className = 'initial-cell';
    const initialInput = document.createElement('input');
    initialInput.type = 'text';
    initialInput.className = 'initial-input';
    initialInput.setAttribute('data-unit-id', unit.id);
    initialInput.placeholder = 'Initials';
    initialInput.maxLength = 10;
    initialInput.required = true;
    initialInput.addEventListener('blur', () => saveEntry(unit.id));
    initialCell.appendChild(initialInput);
    row.appendChild(initialCell);
    
    return row;
}

// Load Temperature Entries
async function loadTemperatureEntries() {
    if (allUnits.length === 0) return;
    
    const dateStr = formatDateForInput(currentDate);
    
    // Load entries for all units in parallel
    const promises = allUnits.map(unit => 
        fetch(`/checklist/bar/cold-storage/log/${unit.id}/${dateStr}`)
            .then(response => response.json())
            .then(data => ({ unitId: unit.id, data }))
            .catch(error => {
                console.error(`Error loading entry for unit ${unit.id}:`, error);
                return { unitId: unit.id, data: null };
            })
    );
    
    const results = await Promise.all(promises);
    
    results.forEach(({ unitId, data }) => {
        if (data && data.success) {
            const entry = data.log.entries[currentTime] || null;
            populateUnitRow(unitId, entry);
        }
    });
}

// Populate Unit Row with Entry Data
function populateUnitRow(unitId, entry) {
    const row = document.querySelector(`.temperature-row[data-unit-id="${unitId}"]`);
    if (!row) return;
    
    // Set temperature
    const tempInput = row.querySelector('.temperature-input');
    if (tempInput) {
        tempInput.value = entry?.temperature ?? '';
        if (entry?.temperature !== null && entry?.temperature !== undefined) {
            validateTemperatureInput(unitId);
        }
    }
    
    // Set corrective action
    const actionTextarea = row.querySelector('.corrective-action-input');
    if (actionTextarea) {
        actionTextarea.value = entry?.corrective_action ?? '';
    }
    
    // Set initial
    const initialInput = row.querySelector('.initial-input');
    if (initialInput) {
        initialInput.value = entry?.initial ?? '';
    }
}

// Temperature Validation
function getTemperatureLimits(unitId) {
    const unit = allUnits.find(u => u.id === unitId);
    if (!unit) return { min: null, max: null };
    
    if (unit.unit_type === 'Refrigerator') {
        return { min: 0, max: 4 };
    } else if (unit.unit_type === 'Freezer') {
        return { min: -22, max: -12 };
    } else if (unit.unit_type === 'Wine Chiller') {
        return { 
            min: parseFloat(unit.min_temp) || 0, 
            max: parseFloat(unit.max_temp) || 20 
        };
    }
    return { min: null, max: null };
}

function checkTemperatureRange(unitId, temperature) {
    const limits = getTemperatureLimits(unitId);
    if (limits.min === null || limits.max === null) return false;
    
    return temperature < limits.min || temperature > limits.max;
}

function validateTemperatureInput(unitId) {
    const row = document.querySelector(`.temperature-row[data-unit-id="${unitId}"]`);
    if (!row) return;
    
    const input = row.querySelector('.temperature-input');
    if (!input) return;
    
    const tempCell = input.closest('.temperature-cell');
    
    if (input.value === '') {
        tempCell.classList.remove('out-of-range');
        input.classList.remove('out-of-range');
        return;
    }
    
    const temperature = parseFloat(input.value);
    if (isNaN(temperature)) return;
    
    const isOutOfRange = checkTemperatureRange(unitId, temperature);
    if (isOutOfRange) {
        tempCell.classList.add('out-of-range');
        input.classList.add('out-of-range');
        
        const actionTextarea = row.querySelector('.corrective-action-input');
        if (actionTextarea) {
            actionTextarea.required = true;
        }
        
        const unit = allUnits.find(u => u.id === unitId);
        showNotification(`Temperature ${temperature}°C is OUT OF RANGE for ${unit.unit_type}! Corrective action required.`, 'error');
    } else {
        tempCell.classList.remove('out-of-range');
        input.classList.remove('out-of-range');
    }
}

async function validateAndSaveEntry(unitId) {
    const row = document.querySelector(`.temperature-row[data-unit-id="${unitId}"]`);
    if (!row) return;
    
    const input = row.querySelector('.temperature-input');
    const temperature = input.value ? parseFloat(input.value) : null;
    
    if (temperature !== null) {
        validateTemperatureInput(unitId);
    }
    
    await saveEntry(unitId);
}

// Save Entry
async function saveEntry(unitId) {
    const row = document.querySelector(`.temperature-row[data-unit-id="${unitId}"]`);
    if (!row) return;
    
    const tempInput = row.querySelector('.temperature-input');
    const actionTextarea = row.querySelector('.corrective-action-input');
    const initialInput = row.querySelector('.initial-input');
    
    if (!tempInput || !actionTextarea || !initialInput) return;
    
    const temperature = tempInput.value ? parseFloat(tempInput.value) : null;
    const correctiveAction = actionTextarea.value.trim();
    const initial = initialInput.value.trim();
    
    // Validate initials
    if (!initial) {
        showNotification('Initials are required for each entry', 'error');
        initialInput.focus();
        return;
    }
    
    // Check if corrective action is required
    const isOutOfRange = temperature !== null && checkTemperatureRange(unitId, temperature);
    if (isOutOfRange && !correctiveAction) {
        showNotification('Corrective action is required when temperature is out of range', 'error');
        actionTextarea.focus();
        return;
    }
    
    // Check if entry is late
    const scheduledTime = getScheduledTimeForSlot(currentDate, currentTime);
    const now = new Date();
    const isLateEntry = now > scheduledTime;
    
    const dateStr = formatDateForInput(currentDate);
    
    try {
        const response = await fetch(`/checklist/bar/cold-storage/log/${unitId}/${dateStr}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'save_entry',
                scheduled_time: currentTime,
                temperature: temperature,
                corrective_action: correctiveAction,
                action_time: isOutOfRange && correctiveAction ? new Date().toISOString() : null,
                recheck_temperature: null,
                initial: initial,
                is_late_entry: isLateEntry
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (isLateEntry) {
                showNotification(`Entry for ${currentTime} marked as Late Entry`, 'warning');
            } else {
                showNotification('Entry saved successfully', 'success');
            }
        } else {
            showNotification('Error saving entry: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error saving entry:', error);
        showNotification('Error saving entry', 'error');
    }
}

function getScheduledTimeForSlot(date, timeSlot) {
    const [time, period] = timeSlot.split(' ');
    const [hours, minutes] = time.split(':').map(Number);
    
    const scheduledDate = new Date(date);
    let hour24 = hours;
    
    if (period === 'PM' && hours !== 12) {
        hour24 = hours + 12;
    } else if (period === 'AM' && hours === 12) {
        hour24 = 0;
    }
    
    scheduledDate.setHours(hour24, minutes, 0, 0);
    return scheduledDate;
}

// Unit Management
function openAddUnitForm() {
    document.getElementById('unit-form-title').textContent = 'Add Unit';
    document.getElementById('unit-id').value = '';
    document.getElementById('unit-form').reset();
    document.getElementById('wine-chiller-temps').classList.add('hidden');
    document.getElementById('unit-form-modal').classList.remove('hidden');
}

function closeUnitForm() {
    document.getElementById('unit-form-modal').classList.add('hidden');
}

async function handleUnitFormSubmit(event) {
    event.preventDefault();
    
    const formData = {
        action: document.getElementById('unit-id').value ? 'update' : 'create',
        unit_number: document.getElementById('unit-number').value,
        location: document.getElementById('unit-location').value,
        unit_type: document.getElementById('unit-type').value,
        min_temp: document.getElementById('min-temp').value || null,
        max_temp: document.getElementById('max-temp').value || null
    };
    
    if (formData.action === 'update') {
        formData.id = parseInt(document.getElementById('unit-id').value);
    }
    
    try {
        const response = await fetch('/checklist/bar/cold-storage/units', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(formData.action === 'create' ? 'Unit created successfully' : 'Unit updated successfully', 'success');
            await loadUnits();
            closeUnitForm();
        } else {
            showNotification('Error saving unit: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error saving unit:', error);
        showNotification('Error saving unit', 'error');
    }
}

// PDF Generation
async function openPDFModal() {
    const modal = document.getElementById('pdf-modal');
    
    try {
        const response = await fetch('/checklist/bar/cold-storage/units');
        const units = await response.json();
        
        const checkboxesContainer = document.getElementById('pdf-unit-checkboxes');
        checkboxesContainer.innerHTML = '';
        
        units.forEach(unit => {
            const label = document.createElement('label');
            label.className = 'checkbox-label';
            label.innerHTML = `
                <input type="checkbox" name="units" value="${unit.id}" checked>
                ${unit.unit_number} - ${unit.location} (${unit.unit_type})
            `;
            checkboxesContainer.appendChild(label);
        });
        
        const today = new Date();
        document.getElementById('pdf-start-date').value = formatDateForInput(today);
        document.getElementById('pdf-end-date').value = formatDateForInput(today);
        
        modal.classList.remove('hidden');
    } catch (error) {
        console.error('Error loading units:', error);
        showNotification('Error loading units', 'error');
    }
}

function closePDFModal() {
    document.getElementById('pdf-modal').classList.add('hidden');
}

async function handlePDFGeneration(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const reportType = formData.get('report_type');
    const startDate = formData.get('start_date');
    const endDate = reportType === 'weekly' ? formData.get('end_date') : startDate;
    
    const selectedUnits = Array.from(document.querySelectorAll('input[name="units"]:checked')).map(cb => parseInt(cb.value));
    
    if (selectedUnits.length === 0) {
        showNotification('Please select at least one unit', 'error');
        return;
    }
    
    try {
        const response = await fetch('/checklist/bar/cold-storage/pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                unit_ids: selectedUnits,
                start_date: startDate,
                end_date: endDate
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `temperature_log_${startDate}_${endDate}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showNotification('PDF generated successfully', 'success');
            closePDFModal();
        } else {
            const data = await response.json();
            showNotification('Error generating PDF: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error generating PDF:', error);
        showNotification('Error generating PDF', 'error');
    }
}

// Notifications
function setupNotifications() {
    // Notification setup if needed
}

// UI Notifications
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}
