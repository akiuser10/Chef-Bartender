/**
 * Cold Storage Temperature Log - Frontend JavaScript
 * Handles temperature entry for multiple units with weekly view
 */

// Global state
let allUnits = [];
let unitLogs = {}; // Cache for unit logs: { unitId: { dateStr: logData } }
let scheduledTimes = ['10:00 AM', '02:00 PM', '06:00 PM', '10:00 PM'];
let startOfWeek = getStartOfWeek(new Date());

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    setupNotifications();
    loadUnits();
});

// Helper: Get start of week (Monday)
function getStartOfWeek(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust when day is Sunday
    return new Date(d.setDate(diff));
}

// Helper: Format date for display
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

// Helper: Format date for input
function formatDateForInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Helper: Get date for day of week (0 = Monday, 6 = Sunday)
function getDateForDay(dayIndex) {
    const date = new Date(startOfWeek);
    date.setDate(startOfWeek.getDate() + dayIndex);
    return date;
}

// Event Listeners
function initializeEventListeners() {
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

// Load Units
async function loadUnits() {
    try {
        const response = await fetch('/checklist/bar/cold-storage/units');
        allUnits = await response.json();
        
        renderUnitsGrid();
        renderWeekView();
        
        // Hide empty state if units exist
        if (allUnits.length > 0) {
            document.getElementById('empty-state').classList.add('hidden');
        } else {
            document.getElementById('empty-state').classList.remove('hidden');
        }
    } catch (error) {
        console.error('Error loading units:', error);
        showNotification('Error loading units', 'error');
    }
}

// Render Units Grid
function renderUnitsGrid() {
    const grid = document.getElementById('units-grid');
    grid.innerHTML = '';
    
    allUnits.forEach(unit => {
        const unitCard = document.createElement('div');
        unitCard.className = 'unit-card';
        unitCard.innerHTML = `
            <div class="unit-card-header">
                <strong>${unit.unit_number}</strong>
            </div>
            <div class="unit-card-body">
                <div>Location: ${unit.location}</div>
                <div>Type: ${unit.unit_type}</div>
            </div>
        `;
        grid.appendChild(unitCard);
    });
}

// Render Week View for All Units
function renderWeekView() {
    const container = document.getElementById('units-week-view');
    container.innerHTML = '';
    
    allUnits.forEach(unit => {
        const unitWeekSection = document.createElement('div');
        unitWeekSection.className = 'unit-week-section';
        unitWeekSection.setAttribute('data-unit-id', unit.id);
        
        // Unit header
        const unitHeader = document.createElement('div');
        unitHeader.className = 'unit-week-header';
        unitHeader.innerHTML = `
            <div class="unit-week-info">
                <strong>UNIT NO: ${unit.unit_number}</strong>
                <span>Location: <input type="text" class="unit-location-input" value="${unit.location}" readonly></span>
            </div>
        `;
        unitWeekSection.appendChild(unitHeader);
        
        // 7 tables for the week
        const tablesContainer = document.createElement('div');
        tablesContainer.className = 'week-tables-container';
        
        for (let dayIndex = 0; dayIndex < 7; dayIndex++) {
            const date = getDateForDay(dayIndex);
            const table = createDayTable(unit, date, dayIndex);
            tablesContainer.appendChild(table);
        }
        
        unitWeekSection.appendChild(tablesContainer);
        container.appendChild(unitWeekSection);
        
        // Load data for this unit's week
        loadUnitWeekData(unit.id);
    });
}

// Create Day Table
function createDayTable(unit, date, dayIndex) {
    const tableWrapper = document.createElement('div');
    tableWrapper.className = 'day-table-wrapper';
    
    // Date header with date picker
    const dateHeader = document.createElement('div');
    dateHeader.className = 'day-table-header';
    const dateInput = document.createElement('input');
    dateInput.type = 'date';
    dateInput.className = 'day-date-input';
    dateInput.value = formatDateForInput(date);
    dateInput.setAttribute('data-unit-id', unit.id);
    dateInput.setAttribute('data-day-index', dayIndex);
    dateInput.addEventListener('change', handleDayDateChange);
    
    const dateLabel = document.createElement('div');
    dateLabel.className = 'day-date-label';
    dateLabel.textContent = formatDateDisplay(date);
    dateLabel.setAttribute('data-date-input', formatDateForInput(date));
    
    dateHeader.appendChild(dateInput);
    dateHeader.appendChild(dateLabel);
    
    // Table
    const table = document.createElement('table');
    table.className = 'temperature-log-table day-table';
    table.setAttribute('data-unit-id', unit.id);
    table.setAttribute('data-date', formatDateForInput(date));
    
    // Table header
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th>TIME</th>
            <th>TEMPERATURE (°C)</th>
            <th>CORRECTIVE ACTION</th>
            <th>INITIAL</th>
        </tr>
    `;
    table.appendChild(thead);
    
    // Table body
    const tbody = document.createElement('tbody');
    scheduledTimes.forEach(timeSlot => {
        const row = createTemperatureRow(unit.id, formatDateForInput(date), timeSlot);
        tbody.appendChild(row);
    });
    table.appendChild(tbody);
    
    tableWrapper.appendChild(dateHeader);
    tableWrapper.appendChild(table);
    
    return tableWrapper;
}

// Create Temperature Row
function createTemperatureRow(unitId, dateStr, timeSlot) {
    const row = document.createElement('tr');
    row.className = 'temperature-row';
    row.setAttribute('data-unit-id', unitId);
    row.setAttribute('data-date', dateStr);
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
    tempInput.setAttribute('data-unit-id', unitId);
    tempInput.setAttribute('data-date', dateStr);
    tempInput.setAttribute('data-time', timeSlot);
    tempInput.placeholder = 'Enter temperature';
    
    const tempUnit = document.createElement('span');
    tempUnit.className = 'temp-unit';
    tempUnit.textContent = '°C';
    
    tempInputWrapper.appendChild(tempInput);
    tempInputWrapper.appendChild(tempUnit);
    tempCell.appendChild(tempInputWrapper);
    tempInput.addEventListener('blur', () => validateAndSaveEntry(unitId, dateStr, timeSlot));
    tempInput.addEventListener('input', () => validateTemperatureInput(unitId, dateStr, timeSlot));
    
    row.appendChild(tempCell);
    
    // Corrective action cell
    const actionCell = document.createElement('td');
    actionCell.className = 'corrective-action-cell';
    const actionTextarea = document.createElement('textarea');
    actionTextarea.className = 'corrective-action-input';
    actionTextarea.setAttribute('data-unit-id', unitId);
    actionTextarea.setAttribute('data-date', dateStr);
    actionTextarea.setAttribute('data-time', timeSlot);
    actionTextarea.placeholder = 'Enter corrective action if needed';
    actionTextarea.addEventListener('blur', () => saveEntry(unitId, dateStr, timeSlot));
    actionCell.appendChild(actionTextarea);
    row.appendChild(actionCell);
    
    // Initial cell
    const initialCell = document.createElement('td');
    initialCell.className = 'initial-cell';
    const initialInput = document.createElement('input');
    initialInput.type = 'text';
    initialInput.className = 'initial-input';
    initialInput.setAttribute('data-unit-id', unitId);
    initialInput.setAttribute('data-date', dateStr);
    initialInput.setAttribute('data-time', timeSlot);
    initialInput.placeholder = 'Initials';
    initialInput.maxLength = 10;
    initialInput.required = true;
    initialInput.addEventListener('blur', () => saveEntry(unitId, dateStr, timeSlot));
    initialCell.appendChild(initialInput);
    row.appendChild(initialCell);
    
    return row;
}

// Handle Day Date Change
function handleDayDateChange(event) {
    const dateInput = event.target;
    const unitId = parseInt(dateInput.getAttribute('data-unit-id'));
    const dayIndex = parseInt(dateInput.getAttribute('data-day-index'));
    const newDate = new Date(dateInput.value);
    
    // Update the date label
    const dateLabel = dateInput.nextElementSibling;
    dateLabel.textContent = formatDateDisplay(newDate);
    dateLabel.setAttribute('data-date-input', formatDateForInput(newDate));
    
    // Update the table's date attribute
    const table = dateInput.closest('.day-table-wrapper').querySelector('.day-table');
    const newDateStr = formatDateForInput(newDate);
    table.setAttribute('data-date', newDateStr);
    
    // Update all rows in this table
    const rows = table.querySelectorAll('.temperature-row');
    rows.forEach(row => {
        row.setAttribute('data-date', newDateStr);
        const inputs = row.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            input.setAttribute('data-date', newDateStr);
        });
    });
    
    // Load data for new date
    loadDayData(unitId, newDateStr);
}

// Load Unit Week Data
async function loadUnitWeekData(unitId) {
    const dates = [];
    for (let i = 0; i < 7; i++) {
        dates.push(formatDateForInput(getDateForDay(i)));
    }
    
    // Load all dates in parallel
    await Promise.all(dates.map(dateStr => loadDayData(unitId, dateStr)));
}

// Load Day Data
async function loadDayData(unitId, dateStr) {
    try {
        const response = await fetch(`/checklist/bar/cold-storage/log/${unitId}/${dateStr}`);
        const data = await response.json();
        
        if (data.success) {
            // Cache the log
            if (!unitLogs[unitId]) {
                unitLogs[unitId] = {};
            }
            unitLogs[unitId][dateStr] = data.log;
            
            // Populate the table
            const table = document.querySelector(`.day-table[data-unit-id="${unitId}"][data-date="${dateStr}"]`);
            if (table) {
                populateTable(table, data.log.entries);
            }
        }
    } catch (error) {
        console.error(`Error loading data for unit ${unitId}, date ${dateStr}:`, error);
    }
}

// Populate Table with Entries
function populateTable(table, entries) {
    const rows = table.querySelectorAll('.temperature-row');
    rows.forEach(row => {
        const timeSlot = row.getAttribute('data-time');
        const entry = entries[timeSlot] || null;
        
        // Set temperature
        const tempInput = row.querySelector('.temperature-input');
        if (tempInput) {
            tempInput.value = entry?.temperature ?? '';
            if (entry?.temperature !== null && entry?.temperature !== undefined) {
                validateTemperatureInput(
                    parseInt(row.getAttribute('data-unit-id')),
                    row.getAttribute('data-date'),
                    timeSlot
                );
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
    });
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

function validateTemperatureInput(unitId, dateStr, timeSlot) {
    const input = document.querySelector(
        `.temperature-input[data-unit-id="${unitId}"][data-date="${dateStr}"][data-time="${timeSlot}"]`
    );
    if (!input) return;
    
    const row = input.closest('.temperature-row');
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

async function validateAndSaveEntry(unitId, dateStr, timeSlot) {
    const input = document.querySelector(
        `.temperature-input[data-unit-id="${unitId}"][data-date="${dateStr}"][data-time="${timeSlot}"]`
    );
    const temperature = input.value ? parseFloat(input.value) : null;
    
    if (temperature !== null) {
        validateTemperatureInput(unitId, dateStr, timeSlot);
    }
    
    await saveEntry(unitId, dateStr, timeSlot);
}

// Save Entry
async function saveEntry(unitId, dateStr, timeSlot) {
    const tempInput = document.querySelector(
        `.temperature-input[data-unit-id="${unitId}"][data-date="${dateStr}"][data-time="${timeSlot}"]`
    );
    const actionTextarea = document.querySelector(
        `.corrective-action-input[data-unit-id="${unitId}"][data-date="${dateStr}"][data-time="${timeSlot}"]`
    );
    const initialInput = document.querySelector(
        `.initial-input[data-unit-id="${unitId}"][data-date="${dateStr}"][data-time="${timeSlot}"]`
    );
    
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
    const scheduledTime = getScheduledTimeForSlot(dateStr, timeSlot);
    const now = new Date();
    const isLateEntry = now > scheduledTime;
    
    try {
        const response = await fetch(`/checklist/bar/cold-storage/log/${unitId}/${dateStr}`, {
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
                recheck_temperature: null,
                initial: initial,
                is_late_entry: isLateEntry
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update cache
            if (!unitLogs[unitId]) {
                unitLogs[unitId] = {};
            }
            if (!unitLogs[unitId][dateStr]) {
                unitLogs[unitId][dateStr] = { entries: {} };
            }
            unitLogs[unitId][dateStr].entries[timeSlot] = data.entry;
            
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

function getScheduledTimeForSlot(dateStr, timeSlot) {
    const [time, period] = timeSlot.split(' ');
    const [hours, minutes] = time.split(':').map(Number);
    
    const scheduledDate = new Date(dateStr);
    let hour24 = hours;
    
    if (period === 'PM' && hours !== 12) {
        hour24 = hours + 12;
    } else if (period === 'AM' && hours === 12) {
        hour24 = 0;
    }
    
    scheduledDate.setHours(hour24, minutes, 0, 0);
    return scheduledDate;
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
        
        modal.classList.remove('hidden');
    } catch (error) {
        console.error('Error loading units:', error);
        showNotification('Error loading units', 'error');
    }
}

function closeUnitManagement() {
    document.getElementById('unit-modal').classList.add('hidden');
}

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
            document.getElementById('wine-chiller-temps').classList.remove('hidden');
            document.getElementById('min-temp').value = unit.min_temp || '';
            document.getElementById('max-temp').value = unit.max_temp || '';
        } else {
            document.getElementById('wine-chiller-temps').classList.add('hidden');
        }
        
        document.getElementById('unit-form-modal').classList.remove('hidden');
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
