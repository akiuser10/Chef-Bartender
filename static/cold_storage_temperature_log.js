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
    
    // Unit management (only for Managers)
    const addUnitBtn = document.getElementById('add-unit-btn');
    if (addUnitBtn) {
        addUnitBtn.addEventListener('click', openAddUnitForm);
    }
    const manageAddUnitBtn = document.getElementById('manage-add-unit-btn');
    if (manageAddUnitBtn) {
        manageAddUnitBtn.addEventListener('click', openAddUnitForm);
    }
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
    
    // Update Temperature button
    document.getElementById('update-temperature-btn')?.addEventListener('click', handleUpdateTemperature);
    
    // Checklist Download
    document.getElementById('checklist-download-btn')?.addEventListener('click', openChecklistDownloadModal);
    document.getElementById('checklist-modal-close')?.addEventListener('click', closeChecklistDownloadModal);
    document.getElementById('cancel-checklist')?.addEventListener('click', closeChecklistDownloadModal);
    document.getElementById('checklist-form')?.addEventListener('submit', handleChecklistDownload);
    
    // PDF generation (legacy)
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
        // Hide checklist download button when date changes (new data needs to be saved)
        document.getElementById('checklist-download-btn').classList.add('hidden');
        loadTemperatureEntries();
    }
}

function handleTimeChange() {
    const timeSelect = document.getElementById('log-time');
    if (timeSelect) {
        currentTime = timeSelect.value;
        updateDateDisplay();
        // Hide checklist download button when time changes (new data needs to be saved)
        document.getElementById('checklist-download-btn').classList.add('hidden');
        // Update which fields are editable based on new time selection
        updateEditableFields();
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

// Render Temperature Tables (one table per unit)
function renderTemperatureTable() {
    const container = document.getElementById('units-tables-container');
    container.innerHTML = '';
    
    if (allUnits.length === 0) {
        return;
    }
    
    allUnits.forEach(unit => {
        const unitTable = createUnitTable(unit);
        container.appendChild(unitTable);
    });
    
    // Load existing entries for current date
    loadTemperatureEntries();
}

// Create Unit Table (one table per unit with time slots as rows)
function createUnitTable(unit) {
    // Create table wrapper
    const tableWrapper = document.createElement('div');
    tableWrapper.className = 'unit-table-wrapper';
    tableWrapper.setAttribute('data-unit-id', unit.id);
    
    // Create table
    const table = document.createElement('table');
    table.className = 'temperature-log-table unit-table';
    
    // Create header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    
    // Unit info header
    const unitHeader = document.createElement('th');
    unitHeader.colSpan = 4;
    unitHeader.className = 'unit-header';
    unitHeader.innerHTML = `
        <div class="unit-header-content">
            <span class="unit-number">UNIT NO: ${unit.unit_number}</span>
            <span class="unit-location">Location: ${unit.location || '—'}</span>
            <span class="unit-type">Type: ${unit.unit_type}</span>
        </div>
    `;
    headerRow.appendChild(unitHeader);
    thead.appendChild(headerRow);
    
    // Column headers
    const columnHeaderRow = document.createElement('tr');
    const timeHeader = document.createElement('th');
    timeHeader.textContent = 'TIME';
    columnHeaderRow.appendChild(timeHeader);
    
    const tempHeader = document.createElement('th');
    tempHeader.textContent = 'TEMPERATURE (°C)';
    columnHeaderRow.appendChild(tempHeader);
    
    const actionHeader = document.createElement('th');
    actionHeader.textContent = 'CORRECTIVE ACTION';
    columnHeaderRow.appendChild(actionHeader);
    
    const initialHeader = document.createElement('th');
    initialHeader.textContent = 'INITIAL';
    columnHeaderRow.appendChild(initialHeader);
    
    thead.appendChild(columnHeaderRow);
    table.appendChild(thead);
    
    // Create tbody
    const tbody = document.createElement('tbody');
    tbody.className = 'unit-tbody';
    tbody.setAttribute('data-unit-id', unit.id);
    
    // Create rows for each time slot
    scheduledTimes.forEach(time => {
        const row = createTimeRow(unit.id, time);
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    tableWrapper.appendChild(table);
    
    return tableWrapper;
}

// Create Time Row (one row per time slot)
function createTimeRow(unitId, time) {
    const row = document.createElement('tr');
    row.className = 'time-row';
    row.setAttribute('data-unit-id', unitId);
    row.setAttribute('data-time', time);
    
    // Time cell
    const timeCell = document.createElement('td');
    timeCell.className = 'time-cell';
    timeCell.textContent = time;
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
    tempInput.setAttribute('data-time', time);
    tempInput.placeholder = '—';
    tempInput.readOnly = true; // Will be editable only for current time
    
    const tempUnit = document.createElement('span');
    tempUnit.className = 'temp-unit';
    tempUnit.textContent = '°C';
    
    tempInputWrapper.appendChild(tempInput);
    tempInputWrapper.appendChild(tempUnit);
    tempCell.appendChild(tempInputWrapper);
    row.appendChild(tempCell);
    
    // Corrective action cell
    const actionCell = document.createElement('td');
    actionCell.className = 'corrective-action-cell';
    const actionTextarea = document.createElement('textarea');
    actionTextarea.className = 'corrective-action-input';
    actionTextarea.setAttribute('data-unit-id', unitId);
    actionTextarea.setAttribute('data-time', time);
    actionTextarea.placeholder = '—';
    actionTextarea.readOnly = true; // Will be editable only for current time
    actionTextarea.rows = 2;
    actionCell.appendChild(actionTextarea);
    row.appendChild(actionCell);
    
    // Initial cell
    const initialCell = document.createElement('td');
    initialCell.className = 'initial-cell';
    const initialInput = document.createElement('input');
    initialInput.type = 'text';
    initialInput.className = 'initial-input';
    initialInput.setAttribute('data-unit-id', unitId);
    initialInput.setAttribute('data-time', time);
    initialInput.placeholder = '—';
    initialInput.maxLength = 10;
    initialInput.readOnly = true; // Will be editable only for current time
    initialCell.appendChild(initialInput);
    row.appendChild(initialCell);
    
    return row;
}

// Load Temperature Entries for all time slots
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
    
    // Populate all time slots for each unit
    results.forEach(({ unitId, data }) => {
        if (data && data.success) {
            const entries = data.log.entries || {};
            populateUnitTable(unitId, entries);
        } else {
            // No data, populate with empty entries
            populateUnitTable(unitId, {});
        }
    });
    
    // Make inputs editable for current time only
    updateEditableFields();
}

// Populate Unit Table with Entry Data for all time slots
function populateUnitTable(unitId, entries) {
    // Populate each time slot row
    scheduledTimes.forEach(time => {
        const row = document.querySelector(`.time-row[data-unit-id="${unitId}"][data-time="${time}"]`);
        if (!row) return;
        
        const entry = entries[time] || null;
        
        // Set temperature
        const tempInput = row.querySelector('.temperature-input');
        if (tempInput) {
            if (entry?.temperature !== null && entry?.temperature !== undefined) {
                tempInput.value = entry.temperature;
            } else {
                tempInput.value = '';
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

// Update editable fields based on current time selection
function updateEditableFields() {
    // Update all time rows across all units
    scheduledTimes.forEach(time => {
        const isCurrentTime = time === currentTime;
        const rows = document.querySelectorAll(`.time-row[data-time="${time}"]`);
        
        rows.forEach(row => {
            // Temperature input
            const tempInput = row.querySelector('.temperature-input');
            if (tempInput) {
                tempInput.readOnly = !isCurrentTime;
                tempInput.placeholder = isCurrentTime ? 'Enter temperature' : '—';
            }
            
            // Corrective action textarea
            const actionTextarea = row.querySelector('.corrective-action-input');
            if (actionTextarea) {
                actionTextarea.readOnly = !isCurrentTime;
                actionTextarea.placeholder = isCurrentTime ? 'Enter corrective action if needed' : '—';
            }
            
            // Initial input
            const initialInput = row.querySelector('.initial-input');
            if (initialInput) {
                initialInput.readOnly = !isCurrentTime;
                initialInput.placeholder = isCurrentTime ? 'Initials' : '—';
                initialInput.required = isCurrentTime;
            }
            
            // Add visual indicator for current time row
            if (isCurrentTime) {
                row.classList.add('current-time-row');
            } else {
                row.classList.remove('current-time-row');
            }
        });
    });
}

// Add event delegation for temperature input validation
document.addEventListener('input', function(e) {
    if (e.target.classList.contains('temperature-input') && !e.target.readOnly) {
        const unitId = parseInt(e.target.getAttribute('data-unit-id'));
        const time = e.target.getAttribute('data-time');
        if (unitId && time && time === currentTime) {
            validateTemperatureInput(unitId, time);
        }
    }
});

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

function validateTemperatureInput(unitId, time) {
    const row = document.querySelector(`.time-row[data-unit-id="${unitId}"][data-time="${time}"]`);
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
        
        const actionTextarea = row.querySelector(`.corrective-action-input[data-time="${time}"]`);
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

// Update All Temperatures for Current Time Slot
async function handleUpdateTemperature() {
    const updateBtn = document.getElementById('update-temperature-btn');
    const originalText = updateBtn.textContent;
    
    // Disable button and show loading
    updateBtn.disabled = true;
    updateBtn.textContent = 'Updating...';
    
    let successCount = 0;
    let errorCount = 0;
    const errors = [];
    
    // Save all entries for the current time slot only
    for (const unit of allUnits) {
        try {
            // Get row for current time
            const row = document.querySelector(`.time-row[data-unit-id="${unit.id}"][data-time="${currentTime}"]`);
            if (!row) continue;
            
            // Get inputs for current time
            const tempInput = row.querySelector('.temperature-input');
            const actionTextarea = row.querySelector('.corrective-action-input');
            const initialInput = row.querySelector('.initial-input');
            
            if (!tempInput || !actionTextarea || !initialInput) continue;
            
            const temperature = tempInput.value ? parseFloat(tempInput.value) : null;
            const correctiveAction = actionTextarea.value.trim();
            const initial = initialInput.value.trim();
            
            // Skip if no data entered
            if (temperature === null && !correctiveAction && !initial) continue;
            
            // Validate initials
            if (!initial) {
                errors.push(`${unit.unit_number}: Initials are required`);
                errorCount++;
                continue;
            }
            
            // Check if corrective action is required
            const isOutOfRange = temperature !== null && checkTemperatureRange(unit.id, temperature);
            if (isOutOfRange && !correctiveAction) {
                errors.push(`${unit.unit_number}: Corrective action required for out-of-range temperature`);
                errorCount++;
                continue;
            }
            
            // Save entry
            const dateStr = formatDateForInput(currentDate);
            const scheduledTime = getScheduledTimeForSlot(currentDate, currentTime);
            const now = new Date();
            const isLateEntry = now > scheduledTime;
            
            const response = await fetch(`/checklist/bar/cold-storage/log/${unit.id}/${dateStr}`, {
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
                successCount++;
            } else {
                errors.push(`${unit.unit_number}: ${data.error || 'Unknown error'}`);
                errorCount++;
            }
        } catch (error) {
            console.error(`Error saving entry for unit ${unit.id}:`, error);
            errors.push(`${unit.unit_number}: Error saving entry`);
            errorCount++;
        }
    }
    
    // Re-enable button
    updateBtn.disabled = false;
    updateBtn.textContent = originalText;
    
    // Reload entries to show updated data for all time slots
    if (successCount > 0) {
        await loadTemperatureEntries();
    }
    
    // Show results
    if (errorCount === 0 && successCount > 0) {
        showNotification(`Successfully updated ${successCount} unit(s) for ${currentTime}`, 'success');
        // Show Checklist Download button
        document.getElementById('checklist-download-btn').classList.remove('hidden');
    } else if (successCount > 0) {
        showNotification(`Updated ${successCount} unit(s), ${errorCount} error(s)`, 'warning');
        if (errors.length > 0) {
            console.error('Errors:', errors);
        }
    } else {
        showNotification(`Failed to update: ${errors.join('; ')}`, 'error');
    }
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
    console.log('Opening Add Unit form...');
    const modal = document.getElementById('unit-form-modal');
    if (!modal) {
        console.error('Unit form modal not found!');
        showNotification('Error: Unit form modal not found', 'error');
        return;
    }
    
    document.getElementById('unit-form-title').textContent = 'Add Unit';
    document.getElementById('unit-id').value = '';
    document.getElementById('unit-form').reset();
    document.getElementById('wine-chiller-temps').classList.add('hidden');
    modal.classList.remove('hidden');
    console.log('Unit form modal opened');
}

function closeUnitForm() {
    document.getElementById('unit-form-modal').classList.add('hidden');
}

async function handleUnitFormSubmit(event) {
    event.preventDefault();
    
    console.log('Unit form submitted');
    
    const unitId = document.getElementById('unit-id').value;
    const unitNumber = document.getElementById('unit-number').value;
    const location = document.getElementById('unit-location').value;
    const unitType = document.getElementById('unit-type').value;
    
    // Validate required fields
    if (!unitNumber || !location || !unitType) {
        showNotification('Please fill in all required fields (Unit Number, Location, and Unit Type)', 'error');
        return;
    }
    
    const formData = {
        action: unitId ? 'update' : 'create',
        unit_number: unitNumber,
        location: location,
        unit_type: unitType,
        min_temp: document.getElementById('min-temp').value || null,
        max_temp: document.getElementById('max-temp').value || null
    };
    
    if (formData.action === 'update') {
        formData.id = parseInt(unitId);
    }
    
    console.log('Submitting unit data:', formData);
    
    try {
        const response = await fetch('/checklist/bar/cold-storage/units', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        // Check if response is ok
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}: ${response.statusText}` }));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(formData.action === 'create' ? 'Unit created successfully' : 'Unit updated successfully', 'success');
            await loadUnits();
            closeUnitForm();
        } else {
            const errorMsg = data.error || 'Unknown error';
            console.error('Error saving unit:', errorMsg);
            showNotification('Error saving unit: ' + errorMsg, 'error');
        }
    } catch (error) {
        console.error('Error saving unit:', error);
        const errorMsg = error.message || 'Failed to save unit. Please check console for details.';
        showNotification('Error saving unit: ' + errorMsg, 'error');
    }
}

// Checklist Download
function openChecklistDownloadModal() {
    const modal = document.getElementById('checklist-download-modal');
    
    // Populate unit checkboxes
    const checkboxesContainer = document.getElementById('checklist-unit-checkboxes');
    checkboxesContainer.innerHTML = '';
    
    allUnits.forEach(unit => {
        const label = document.createElement('label');
        label.className = 'checkbox-label';
        label.innerHTML = `
            <input type="checkbox" name="units" value="${unit.id}" checked>
            ${unit.unit_number} - ${unit.location} (${unit.unit_type})
        `;
        checkboxesContainer.appendChild(label);
    });
    
    // Set default dates (current date)
    const today = new Date();
    document.getElementById('checklist-start-date').value = formatDateForInput(today);
    document.getElementById('checklist-end-date').value = formatDateForInput(today);
    
    modal.classList.remove('hidden');
}

function closeChecklistDownloadModal() {
    document.getElementById('checklist-download-modal').classList.add('hidden');
}

async function handleChecklistDownload(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const startDate = formData.get('start_date');
    const endDate = formData.get('end_date');
    const selectedTimes = Array.from(document.querySelectorAll('#checklist-time-checkboxes input[name="times"]:checked')).map(cb => cb.value);
    const selectedUnits = Array.from(document.querySelectorAll('#checklist-unit-checkboxes input[name="units"]:checked')).map(cb => parseInt(cb.value));
    
    if (selectedUnits.length === 0) {
        showNotification('Please select at least one unit', 'error');
        return;
    }
    
    if (selectedTimes.length === 0) {
        showNotification('Please select at least one time', 'error');
        return;
    }
    
    if (!startDate || !endDate) {
        showNotification('Please select start and end dates', 'error');
        return;
    }
    
    try {
        const response = await fetch('/checklist/bar/cold-storage/checklist-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                unit_ids: selectedUnits,
                start_date: startDate,
                end_date: endDate,
                times: selectedTimes
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `temperature_checklist_${startDate}_${endDate}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showNotification('Checklist PDF generated successfully', 'success');
            closeChecklistDownloadModal();
        } else {
            const data = await response.json();
            showNotification('Error generating PDF: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error generating checklist PDF:', error);
        showNotification('Error generating checklist PDF', 'error');
    }
}

// PDF Generation (Legacy)
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
