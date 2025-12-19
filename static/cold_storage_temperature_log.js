/**
 * Cold Storage Temperature Log - Frontend JavaScript
 * Handles temperature entry, validation, notifications, and UI interactions
 */

// Global state
let currentUnitId = null;
let currentUnit = null;
let currentDate = new Date();
let currentLog = null;
let scheduledTimes = ['10:00 AM', '02:00 PM', '06:00 PM', '10:00 PM'];

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    setupNotifications();
    updateDateDisplay();
    
    // Load units if any exist
    loadUnits();
});

// Event Listeners
function initializeEventListeners() {
    // Unit selection
    const unitSelect = document.getElementById('unit-select');
    if (unitSelect) {
        unitSelect.addEventListener('change', handleUnitSelection);
    }
    
    // Date navigation
    const logDate = document.getElementById('log-date');
    if (logDate) {
        logDate.addEventListener('change', handleDateChange);
    }
    
    document.getElementById('prev-date-btn')?.addEventListener('click', () => navigateDate(-1));
    document.getElementById('next-date-btn')?.addEventListener('click', () => navigateDate(1));
    document.getElementById('today-btn')?.addEventListener('click', goToToday);
    
    // Unit management
    document.getElementById('manage-units-btn')?.addEventListener('click', openUnitManagement);
    document.getElementById('modal-close')?.addEventListener('click', closeUnitManagement);
    document.getElementById('add-unit-btn')?.addEventListener('click', openAddUnitForm);
    document.getElementById('unit-form-close')?.addEventListener('click', closeUnitForm);
    document.getElementById('cancel-unit-form')?.addEventListener('click', closeUnitForm);
    document.getElementById('unit-form')?.addEventListener('submit', handleUnitFormSubmit);
    
    // Unit type change - show/hide wine chiller temps
    document.getElementById('unit-type')?.addEventListener('change', function() {
        const wineChillerTemps = document.getElementById('wine-chiller-temps');
        if (this.value === 'Wine Chiller') {
            wineChillerTemps.style.display = 'block';
        } else {
            wineChillerTemps.style.display = 'none';
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
                endDateGroup.style.display = 'block';
                document.getElementById('pdf-end-date').required = true;
            } else {
                endDateGroup.style.display = 'none';
                document.getElementById('pdf-end-date').required = false;
            }
        });
    });
    
    // Supervisor verification
    document.getElementById('verify-log-btn')?.addEventListener('click', handleSupervisorVerification);
}

// Unit Management
async function loadUnits() {
    try {
        const response = await fetch('/checklist/bar/cold-storage/units');
        const units = await response.json();
        
        const unitSelect = document.getElementById('unit-select');
        if (unitSelect) {
            // Clear existing options except the first one
            while (unitSelect.options.length > 1) {
                unitSelect.remove(1);
            }
            
            units.forEach(unit => {
                const option = document.createElement('option');
                option.value = unit.id;
                option.textContent = `${unit.unit_number} - ${unit.location} (${unit.unit_type})`;
                option.setAttribute('data-unit-number', unit.unit_number);
                option.setAttribute('data-location', unit.location);
                option.setAttribute('data-unit-type', unit.unit_type);
                option.setAttribute('data-min-temp', unit.min_temp || '');
                option.setAttribute('data-max-temp', unit.max_temp || '');
                unitSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading units:', error);
        showNotification('Error loading units', 'error');
    }
}

async function handleUnitSelection(event) {
    const unitId = event.target.value;
    if (!unitId) {
        hideUnitLog();
        return;
    }
    
    const selectedOption = event.target.options[event.target.selectedIndex];
    currentUnit = {
        id: parseInt(unitId),
        unit_number: selectedOption.getAttribute('data-unit-number'),
        location: selectedOption.getAttribute('data-location'),
        unit_type: selectedOption.getAttribute('data-unit-type'),
        min_temp: selectedOption.getAttribute('data-min-temp'),
        max_temp: selectedOption.getAttribute('data-max-temp')
    };
    
    currentUnitId = parseInt(unitId);
    await loadTemperatureLog();
    showUnitLog();
}

function showUnitLog() {
    document.getElementById('unit-log-section').style.display = 'block';
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('generate-pdf-btn').style.display = 'inline-block';
    
    // Update unit header
    document.getElementById('display-unit-number').textContent = currentUnit.unit_number;
    document.getElementById('display-location').textContent = currentUnit.location;
    document.getElementById('display-unit-type').textContent = currentUnit.unit_type;
}

function hideUnitLog() {
    document.getElementById('unit-log-section').style.display = 'none';
    document.getElementById('empty-state').style.display = 'block';
    document.getElementById('generate-pdf-btn').style.display = 'none';
}

// Date Management
function updateDateDisplay() {
    const dateInput = document.getElementById('log-date');
    if (dateInput) {
        dateInput.value = formatDateForInput(currentDate);
    }
    
    const displayDate = document.getElementById('display-date');
    if (displayDate) {
        displayDate.textContent = formatDateDisplay(currentDate);
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

function navigateDate(days) {
    currentDate = new Date(currentDate);
    currentDate.setDate(currentDate.getDate() + days);
    updateDateDisplay();
    handleDateChange();
}

function goToToday() {
    currentDate = new Date();
    updateDateDisplay();
    handleDateChange();
}

async function handleDateChange() {
    const dateInput = document.getElementById('log-date');
    if (dateInput && dateInput.value) {
        currentDate = new Date(dateInput.value);
        updateDateDisplay();
    }
    
    if (currentUnitId) {
        await loadTemperatureLog();
    }
}

// Temperature Log Loading
async function loadTemperatureLog() {
    if (!currentUnitId) return;
    
    const dateStr = formatDateForInput(currentDate);
    
    try {
        const response = await fetch(`/checklist/bar/cold-storage/log/${currentUnitId}/${dateStr}`);
        const data = await response.json();
        
        if (data.success) {
            currentLog = data.log;
            currentUnit = data.unit;
            renderTemperatureTable(data.log.entries);
            
            // Show supervisor verification if verified
            if (data.log.supervisor_verified) {
                showSupervisorVerification(data.log.supervisor_name, data.log.supervisor_verified_at);
            } else {
                hideSupervisorVerification();
                // Show verify button for managers
                const userRole = document.body.getAttribute('data-user-role') || '';
                if (userRole === 'Manager') {
                    document.getElementById('verify-log-btn').style.display = 'inline-block';
                }
            }
        }
    } catch (error) {
        console.error('Error loading temperature log:', error);
        showNotification('Error loading temperature log', 'error');
    }
}

function renderTemperatureTable(entries) {
    const tbody = document.getElementById('temperature-log-tbody');
    tbody.innerHTML = '';
    
    scheduledTimes.forEach(timeSlot => {
        const entry = entries[timeSlot] || null;
        const row = createTemperatureRow(timeSlot, entry);
        tbody.appendChild(row);
    });
}

function createTemperatureRow(timeSlot, entry) {
    const row = document.createElement('tr');
    row.className = 'temperature-row';
    row.setAttribute('data-time', timeSlot);
    
    // Time cell
    const timeCell = document.createElement('td');
    timeCell.className = 'time-cell';
    timeCell.textContent = timeSlot;
    row.appendChild(timeCell);
    
    // Temperature cell
    const tempCell = document.createElement('td');
    tempCell.className = 'temperature-cell';
    const tempInputWrapper = document.createElement('div');
    tempInputWrapper.className = 'temp-input-wrapper';
    
    const tempInput = document.createElement('input');
    tempInput.type = 'number';
    tempInput.step = '0.1';
    tempInput.className = 'temperature-input';
    tempInput.setAttribute('data-time', timeSlot);
    tempInput.placeholder = 'Enter temperature';
    tempInput.value = entry?.temperature ?? '';
    
    // Add °C display
    const tempUnit = document.createElement('span');
    tempUnit.className = 'temp-unit';
    tempUnit.textContent = '°C';
    
    tempInputWrapper.appendChild(tempInput);
    tempInputWrapper.appendChild(tempUnit);
    tempCell.appendChild(tempInputWrapper);
    
    // Add event listeners for validation
    tempInput.addEventListener('blur', () => validateAndSaveTemperature(timeSlot));
    tempInput.addEventListener('input', () => validateTemperatureInput(timeSlot));
    
    row.appendChild(tempCell);
    
    // Corrective action cell
    const actionCell = document.createElement('td');
    actionCell.className = 'corrective-action-cell';
    const actionTextarea = document.createElement('textarea');
    actionTextarea.className = 'corrective-action-input';
    actionTextarea.setAttribute('data-time', timeSlot);
    actionTextarea.placeholder = 'Enter corrective action if needed';
    actionTextarea.value = entry?.corrective_action ?? '';
    actionTextarea.addEventListener('blur', () => saveEntry(timeSlot));
    actionCell.appendChild(actionTextarea);
    row.appendChild(actionCell);
    
    // Initial cell
    const initialCell = document.createElement('td');
    initialCell.className = 'initial-cell';
    const initialInput = document.createElement('input');
    initialInput.type = 'text';
    initialInput.className = 'initial-input';
    initialInput.setAttribute('data-time', timeSlot);
    initialInput.placeholder = 'Initials';
    initialInput.maxLength = 10;
    initialInput.value = entry?.initial ?? '';
    initialInput.required = true;
    initialInput.addEventListener('blur', () => saveEntry(timeSlot));
    initialCell.appendChild(initialInput);
    row.appendChild(initialCell);
    
    // Check if out of range and highlight
    if (entry && entry.temperature !== null && entry.temperature !== undefined) {
        const isOutOfRange = checkTemperatureRange(entry.temperature);
        if (isOutOfRange) {
            tempCell.classList.add('out-of-range');
            tempInput.classList.add('out-of-range');
            actionTextarea.required = true;
        }
    }
    
    return row;
}

// Temperature Validation
function getTemperatureLimits() {
    if (!currentUnit) return { min: null, max: null };
    
    if (currentUnit.unit_type === 'Refrigerator') {
        return { min: 0, max: 4 };
    } else if (currentUnit.unit_type === 'Freezer') {
        return { min: -22, max: -12 };
    } else if (currentUnit.unit_type === 'Wine Chiller') {
        return { 
            min: parseFloat(currentUnit.min_temp) || 0, 
            max: parseFloat(currentUnit.max_temp) || 20 
        };
    }
    return { min: null, max: null };
}

function checkTemperatureRange(temperature) {
    const limits = getTemperatureLimits();
    if (limits.min === null || limits.max === null) return false;
    
    return temperature < limits.min || temperature > limits.max;
}

function validateTemperatureInput(timeSlot) {
    const input = document.querySelector(`.temperature-input[data-time="${timeSlot}"]`);
    const tempCell = input.closest('.temperature-cell');
    
    if (input.value === '') {
        tempCell.classList.remove('out-of-range');
        input.classList.remove('out-of-range');
        return;
    }
    
    const temperature = parseFloat(input.value);
    if (isNaN(temperature)) return;
    
    const isOutOfRange = checkTemperatureRange(temperature);
    if (isOutOfRange) {
        tempCell.classList.add('out-of-range');
        input.classList.add('out-of-range');
        
        // Require corrective action
        const actionTextarea = document.querySelector(`.corrective-action-input[data-time="${timeSlot}"]`);
        if (actionTextarea) {
            actionTextarea.required = true;
        }
        
        // Show immediate notification
        showNotification(`Temperature ${temperature}°C is OUT OF RANGE for ${currentUnit.unit_type}! Corrective action required.`, 'error');
    } else {
        tempCell.classList.remove('out-of-range');
        input.classList.remove('out-of-range');
    }
}

async function validateAndSaveTemperature(timeSlot) {
    const input = document.querySelector(`.temperature-input[data-time="${timeSlot}"]`);
    const temperature = input.value ? parseFloat(input.value) : null;
    
    if (temperature !== null) {
        validateTemperatureInput(timeSlot);
    }
    
    await saveEntry(timeSlot);
}

// Save Entry
async function saveEntry(timeSlot) {
    if (!currentUnitId) return;
    
    const tempInput = document.querySelector(`.temperature-input[data-time="${timeSlot}"]`);
    const actionTextarea = document.querySelector(`.corrective-action-input[data-time="${timeSlot}"]`);
    const initialInput = document.querySelector(`.initial-input[data-time="${timeSlot}"]`);
    
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
    const isOutOfRange = temperature !== null && checkTemperatureRange(temperature);
    if (isOutOfRange && !correctiveAction) {
        showNotification('Corrective action is required when temperature is out of range', 'error');
        actionTextarea.focus();
        return;
    }
    
    // Check if entry is late
    const scheduledTime = getScheduledTimeForSlot(timeSlot);
    const now = new Date();
    const isLateEntry = now > scheduledTime;
    
    const dateStr = formatDateForInput(currentDate);
    
    try {
        const response = await fetch(`/checklist/bar/cold-storage/log/${currentUnitId}/${dateStr}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'save_entry',
                scheduled_time: timeSlot,
                temperature: temperature,
                corrective_action: correctiveAction,
                action_time: isOutOfRange && correctiveAction ? new Date().toISOString() : null,
                recheck_temperature: null, // Can be added later
                initial: initial,
                is_late_entry: isLateEntry
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update entry in current log
            if (!currentLog.entries) {
                currentLog.entries = {};
            }
            currentLog.entries[timeSlot] = data.entry;
            
            // Show late entry indicator if applicable
            if (isLateEntry) {
                showNotification(`Entry for ${timeSlot} marked as Late Entry`, 'warning');
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

function getScheduledTimeForSlot(timeSlot) {
    const [time, period] = timeSlot.split(' ');
    const [hours, minutes] = time.split(':').map(Number);
    
    const scheduledDate = new Date(currentDate);
    let hour24 = hours;
    
    if (period === 'PM' && hours !== 12) {
        hour24 = hours + 12;
    } else if (period === 'AM' && hours === 12) {
        hour24 = 0;
    }
    
    scheduledDate.setHours(hour24, minutes, 0, 0);
    return scheduledDate;
}

// Supervisor Verification
async function handleSupervisorVerification() {
    if (!currentUnitId) return;
    
    const supervisorName = prompt('Enter supervisor name:');
    if (!supervisorName) return;
    
    const dateStr = formatDateForInput(currentDate);
    
    try {
        const response = await fetch(`/checklist/bar/cold-storage/log/${currentUnitId}/${dateStr}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'verify',
                supervisor_name: supervisorName
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSupervisorVerification(supervisorName, new Date().toISOString());
            document.getElementById('verify-log-btn').style.display = 'none';
            showNotification('Log verified successfully', 'success');
        } else {
            showNotification('Error verifying log: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error verifying log:', error);
        showNotification('Error verifying log', 'error');
    }
}

function showSupervisorVerification(name, dateStr) {
    const section = document.getElementById('supervisor-verification-section');
    document.getElementById('supervisor-name').textContent = name;
    document.getElementById('verification-date').textContent = new Date(dateStr).toLocaleString();
    section.style.display = 'block';
}

function hideSupervisorVerification() {
    document.getElementById('supervisor-verification-section').style.display = 'none';
    document.getElementById('verify-log-btn').style.display = 'none';
}

// Unit Management Modal
async function openUnitManagement() {
    const modal = document.getElementById('unit-modal');
    const container = document.getElementById('unit-list-container');
    
    try {
        const response = await fetch('/checklist/bar/cold-storage/units');
        const units = await response.json();
        
        container.innerHTML = '';
        
        if (units.length === 0) {
            container.innerHTML = '<p>No units found. Add your first unit to get started.</p>';
        } else {
            units.forEach(unit => {
                const unitDiv = document.createElement('div');
                unitDiv.className = 'unit-item';
                unitDiv.innerHTML = `
                    <div class="unit-item-info">
                        <strong>${unit.unit_number}</strong> - ${unit.location} (${unit.unit_type})
                    </div>
                    <div class="unit-item-actions">
                        <button class="btn-small edit-unit" data-id="${unit.id}">Edit</button>
                        <button class="btn-small delete-unit" data-id="${unit.id}">Delete</button>
                    </div>
                `;
                container.appendChild(unitDiv);
            });
            
            // Add event listeners
            container.querySelectorAll('.edit-unit').forEach(btn => {
                btn.addEventListener('click', () => editUnit(parseInt(btn.getAttribute('data-id'))));
            });
            
            container.querySelectorAll('.delete-unit').forEach(btn => {
                btn.addEventListener('click', () => deleteUnit(parseInt(btn.getAttribute('data-id'))));
            });
        }
        
        modal.style.display = 'block';
    } catch (error) {
        console.error('Error loading units:', error);
        showNotification('Error loading units', 'error');
    }
}

function closeUnitManagement() {
    document.getElementById('unit-modal').style.display = 'none';
}

function openAddUnitForm() {
    document.getElementById('unit-form-title').textContent = 'Add Unit';
    document.getElementById('unit-id').value = '';
    document.getElementById('unit-form').reset();
    document.getElementById('wine-chiller-temps').style.display = 'none';
    document.getElementById('unit-form-modal').style.display = 'block';
}

function closeUnitForm() {
    document.getElementById('unit-form-modal').style.display = 'none';
}

async function editUnit(unitId) {
    try {
        const response = await fetch('/checklist/bar/cold-storage/units');
        const units = await response.json();
        const unit = units.find(u => u.id === unitId);
        
        if (!unit) {
            showNotification('Unit not found', 'error');
            return;
        }
        
        document.getElementById('unit-form-title').textContent = 'Edit Unit';
        document.getElementById('unit-id').value = unit.id;
        document.getElementById('unit-number').value = unit.unit_number;
        document.getElementById('unit-location').value = unit.location;
        document.getElementById('unit-type').value = unit.unit_type;
        
        if (unit.unit_type === 'Wine Chiller') {
            document.getElementById('wine-chiller-temps').style.display = 'block';
            document.getElementById('min-temp').value = unit.min_temp || '';
            document.getElementById('max-temp').value = unit.max_temp || '';
        } else {
            document.getElementById('wine-chiller-temps').style.display = 'none';
        }
        
        document.getElementById('unit-form-modal').style.display = 'block';
    } catch (error) {
        console.error('Error loading unit:', error);
        showNotification('Error loading unit', 'error');
    }
}

async function deleteUnit(unitId) {
    if (!confirm('Are you sure you want to delete this unit? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch('/checklist/bar/cold-storage/units', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'delete',
                id: unitId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Unit deleted successfully', 'success');
            await loadUnits();
            closeUnitManagement();
            
            // If deleted unit was selected, clear selection
            if (currentUnitId === unitId) {
                document.getElementById('unit-select').value = '';
                hideUnitLog();
                currentUnitId = null;
                currentUnit = null;
            }
        } else {
            showNotification('Error deleting unit: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error deleting unit:', error);
        showNotification('Error deleting unit', 'error');
    }
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
            closeUnitManagement();
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
    
    // Load units for selection
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
        
        // Set default dates
        const today = new Date();
        document.getElementById('pdf-start-date').value = formatDateForInput(today);
        document.getElementById('pdf-end-date').value = formatDateForInput(today);
        
        modal.style.display = 'block';
    } catch (error) {
        console.error('Error loading units:', error);
        showNotification('Error loading units', 'error');
    }
}

function closePDFModal() {
    document.getElementById('pdf-modal').style.display = 'none';
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
    // Check for scheduled notification times
    checkScheduledNotifications();
    
    // Set up interval to check every minute
    setInterval(checkScheduledNotifications, 60000);
}

function checkScheduledNotifications() {
    const now = new Date();
    const currentHour = now.getHours();
    const currentMinute = now.getMinutes();
    
    // Check each scheduled time
    scheduledTimes.forEach(timeSlot => {
        const [time, period] = timeSlot.split(' ');
        const [hours, minutes] = time.split(':').map(Number);
        
        let hour24 = hours;
        if (period === 'PM' && hours !== 12) {
            hour24 = hours + 12;
        } else if (period === 'AM' && hours === 12) {
            hour24 = 0;
        }
        
        // Check if it's time for notification (within 5 minutes of scheduled time)
        if (currentHour === hour24 && Math.abs(currentMinute - minutes) <= 5) {
            checkAndNotify(timeSlot);
        }
    });
}

async function checkAndNotify(timeSlot) {
    if (!currentUnitId) return;
    
    const dateStr = formatDateForInput(currentDate);
    
    try {
        const response = await fetch(`/checklist/bar/cold-storage/log/${currentUnitId}/${dateStr}`);
        const data = await response.json();
        
        if (data.success) {
            const entry = data.log.entries[timeSlot];
            
            // If no entry exists, send notification
            if (!entry || entry.temperature === null || entry.temperature === undefined) {
                requestNotificationPermission();
                showBrowserNotification(`Temperature entry required for ${timeSlot}`, `Please enter temperature for ${currentUnit.unit_number}`);
            }
        }
    } catch (error) {
        console.error('Error checking entry:', error);
    }
}

function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

function showBrowserNotification(title, body) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, {
            body: body,
            icon: '/static/C&B.png'
        });
    }
}

// UI Notifications
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Hide and remove after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}
