/**
 * Bar Glass Washer Checklist - Frontend JavaScript
 * HACCP-compliant checklist with unit management and validation
 */

// Global state
let units = [];
let entries = [];
let editingUnitId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadUnits();
    loadEntries();
    
    // Automatically set staff initials from logged-in user
    const staffInitialsField = document.getElementById('staff-initials');
    if (staffInitialsField && window.userInitials) {
        staffInitialsField.value = window.userInitials;
        // Make it readonly or keep it editable? User requirement says it should be auto-filled
        // But since they want it automatic, let's make it readonly or auto-populated but still editable if needed
    }
});

// Event Listeners
function initializeEventListeners() {
    // Time input conversion to 12-hour format
    const timeInput = document.getElementById('entry-time-input');
    const timePeriod = document.getElementById('time-period');
    const hiddenTime = document.getElementById('entry-time');
    
    if (timeInput && timePeriod && hiddenTime) {
        function updateTimeValue() {
            const time24 = timeInput.value; // HH:MM format (24-hour)
            if (time24) {
                const [hours, minutes] = time24.split(':');
                const hour24 = parseInt(hours, 10);
                
                // Determine AM/PM from 24-hour format
                let period = 'AM';
                let hour12 = hour24;
                
                if (hour24 === 0) {
                    hour12 = 12;
                    period = 'AM';
                } else if (hour24 < 12) {
                    hour12 = hour24;
                    period = 'AM';
                } else if (hour24 === 12) {
                    hour12 = 12;
                    period = 'PM';
                } else {
                    hour12 = hour24 - 12;
                    period = 'PM';
                }
                
                // Update the period selector
                timePeriod.value = period;
                
                // Create 12-hour format string
                const time12Hour = `${hour12}:${minutes.padStart(2, '0')} ${period}`;
                hiddenTime.value = time12Hour;
                
                // Trigger validation
                validateHACCP();
            }
        }
        
        timeInput.addEventListener('change', updateTimeValue);
        timeInput.addEventListener('input', updateTimeValue);
        
        // Also handle period change (allows manual override)
        timePeriod.addEventListener('change', function() {
            const time24 = timeInput.value;
            if (time24) {
                updateTimeValue();
            }
        });
    }
    
    // Form submission
    const form = document.getElementById('checklist-form');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
    
    // Reset button
    const resetBtn = document.getElementById('reset-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetForm);
    }
    
    // Temperature inputs - validate on change
    const washTemp = document.getElementById('wash-temperature');
    const rinseTemp = document.getElementById('rinse-sanitising-temperature');
    const sanitisingMethod = document.getElementById('sanitising-method');
    
    if (washTemp) washTemp.addEventListener('input', validateHACCP);
    if (rinseTemp) rinseTemp.addEventListener('input', validateHACCP);
    if (sanitisingMethod) sanitisingMethod.addEventListener('change', validateHACCP);
    
    // Unit management (Manager only)
    if (window.userRole === 'Manager') {
        const addUnitBtn = document.getElementById('add-unit-btn');
        if (addUnitBtn) {
            addUnitBtn.addEventListener('click', openAddUnitModal);
        }
        
        const unitForm = document.getElementById('unit-form');
        if (unitForm) {
            unitForm.addEventListener('submit', handleUnitFormSubmit);
        }
        
        const unitModalClose = document.getElementById('unit-modal-close');
        const unitFormCancel = document.getElementById('unit-form-cancel');
        if (unitModalClose) unitModalClose.addEventListener('click', closeUnitModal);
        if (unitFormCancel) unitFormCancel.addEventListener('click', closeUnitModal);
        
        // Manager verification
        const verifyForm = document.getElementById('verify-form');
        if (verifyForm) {
            verifyForm.addEventListener('submit', handleVerifySubmit);
        }
        
        const verifyModalClose = document.getElementById('verify-modal-close');
        const verifyFormCancel = document.getElementById('verify-form-cancel');
        if (verifyModalClose) verifyModalClose.addEventListener('click', closeVerifyModal);
        if (verifyFormCancel) verifyFormCancel.addEventListener('click', closeVerifyModal);
    }
}

// HACCP Validation
function validateHACCP() {
    const washTemp = parseFloat(document.getElementById('wash-temperature').value);
    const rinseTempInput = document.getElementById('rinse-sanitising-temperature');
    const rinseTemp = rinseTempInput.value ? parseFloat(rinseTempInput.value) : null;
    const sanitisingMethod = document.getElementById('sanitising-method').value;
    
    const passFailDisplay = document.getElementById('pass-fail-display');
    const passFailText = document.getElementById('pass-fail-text');
    const correctiveActionGroup = document.getElementById('corrective-action-group');
    const correctiveAction = document.getElementById('corrective-action');
    
    if (!washTemp || !sanitisingMethod) {
        passFailDisplay.style.display = 'none';
        correctiveActionGroup.style.display = 'none';
        return;
    }
    
    // HACCP Rules:
    // 1. Wash temperature ≥ 55°C
    // 2. If Thermal: Rinse/Sanitising temperature ≥ 82°C
    // 3. If Chemical: Rinse temperature optional (compliance per chemical spec)
    
    let pass = true;
    let reasons = [];
    
    if (washTemp < 55) {
        pass = false;
        reasons.push('Wash temperature must be ≥ 55°C');
    }
    
    if (sanitisingMethod === 'Thermal') {
        if (!rinseTemp || rinseTemp < 82) {
            pass = false;
            reasons.push('Rinse/Sanitising temperature must be ≥ 82°C for Thermal sanitising');
        }
    }
    
    passFailDisplay.style.display = 'block';
    if (pass) {
        passFailDisplay.style.backgroundColor = '#d4edda';
        passFailDisplay.style.borderColor = '#c3e6cb';
        passFailDisplay.style.color = '#155724';
        passFailText.textContent = 'PASS';
        passFailText.style.color = '#155724';
        passFailText.style.fontWeight = 'bold';
        correctiveActionGroup.style.display = 'none';
        correctiveAction.required = false;
    } else {
        passFailDisplay.style.backgroundColor = '#f8d7da';
        passFailDisplay.style.borderColor = '#f5c6cb';
        passFailDisplay.style.color = '#721c24';
        passFailText.textContent = 'FAIL - ' + reasons.join(', ');
        passFailText.style.color = '#721c24';
        passFailText.style.fontWeight = 'bold';
        correctiveActionGroup.style.display = 'block';
        correctiveAction.required = true;
    }
}

// Load Units
async function loadUnits() {
    try {
        const response = await fetch('/checklist/bar/glass-washer/units');
        if (response.ok) {
            units = await response.json();
            populateUnitSelect();
            if (window.userRole === 'Manager') {
                populateUnitsList();
            }
        } else {
            console.error('Failed to load units:', response.statusText);
        }
    } catch (error) {
        console.error('Error loading units:', error);
    }
}

// Populate Unit Select
function populateUnitSelect() {
    const select = document.getElementById('unit-select');
    if (!select) return;
    
    // Clear existing options except the first one
    while (select.options.length > 1) {
        select.remove(1);
    }
    
    units.forEach(unit => {
        const option = document.createElement('option');
        option.value = unit.id;
        option.textContent = unit.unit_name;
        select.appendChild(option);
    });
}

// Populate Units List (Manager only)
function populateUnitsList() {
    const unitsList = document.getElementById('units-list');
    if (!unitsList) return;
    
    unitsList.innerHTML = '';
    
    units.forEach(unit => {
        const unitCard = document.createElement('div');
        unitCard.style.cssText = 'padding: 10px; background: white; border-radius: 4px; border: 1px solid #ddd;';
        unitCard.innerHTML = `
            <strong>${unit.unit_name}</strong>
            ${unit.description ? `<div style="font-size: 0.9em; color: #666; margin-top: 5px;">${unit.description}</div>` : ''}
            <div style="margin-top: 10px; display: flex; gap: 5px;">
                <button class="btn-secondary" style="flex: 1; padding: 5px;" onclick="editUnit(${unit.id})">Edit</button>
                <button class="btn-secondary" style="flex: 1; padding: 5px;" onclick="deleteUnit(${unit.id})">Delete</button>
            </div>
        `;
        unitsList.appendChild(unitCard);
    });
}

// Handle Form Submit
async function handleFormSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    
    // Validate required fields
    const unitId = formData.get('unit_id');
    const entryDate = formData.get('entry_date');
    const entryTime = document.getElementById('entry-time').value;
    const washTemp = formData.get('wash_temperature');
    const sanitisingMethod = formData.get('sanitising_method');
    const staffInitials = formData.get('staff_initials');
    
    if (!unitId || !entryDate || !entryTime || !washTemp || !sanitisingMethod || !staffInitials) {
        alert('Please fill in all required fields.');
        return;
    }
    
    // Get rinse temp (optional for chemical)
    const rinseTemp = formData.get('rinse_sanitising_temperature') || null;
    
    // Validate HACCP before submission
    const washTempNum = parseFloat(washTemp);
    const rinseTempNum = rinseTemp ? parseFloat(rinseTemp) : null;
    
    let pass = true;
    if (washTempNum < 55) pass = false;
    if (sanitisingMethod === 'Thermal' && (!rinseTempNum || rinseTempNum < 82)) pass = false;
    
    const correctiveAction = formData.get('corrective_action');
    if (!pass && !correctiveAction) {
        alert('Corrective action is required when result is Fail.');
        document.getElementById('corrective-action').focus();
        return;
    }
    
    // Prepare data
    const data = {
        action: 'create',
        unit_id: parseInt(unitId),
        entry_date: entryDate,
        entry_time: entryTime,
        wash_temperature: washTempNum,
        rinse_sanitising_temperature: rinseTempNum,
        sanitising_method: sanitisingMethod,
        staff_initials: staffInitials,
        corrective_action: correctiveAction || null
    };
    
    try {
        const response = await fetch('/checklist/bar/glass-washer/entries', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Entry submitted successfully!');
            resetForm();
            loadEntries();
        } else {
            alert('Error: ' + (result.error || 'Failed to submit entry'));
        }
    } catch (error) {
        console.error('Error submitting entry:', error);
        alert('Error submitting entry. Please try again.');
    }
}

// Reset Form
function resetForm() {
    document.getElementById('checklist-form').reset();
    document.getElementById('entry-date').value = new Date().toISOString().split('T')[0];
    document.getElementById('staff-name').value = window.userDisplayName || '';
    // Always restore staff initials from logged-in user
    const staffInitialsField = document.getElementById('staff-initials');
    if (staffInitialsField && window.userInitials) {
        staffInitialsField.value = window.userInitials;
    }
    document.getElementById('pass-fail-display').style.display = 'none';
    document.getElementById('corrective-action-group').style.display = 'none';
    document.getElementById('corrective-action').required = false;
}

// Load Entries
async function loadEntries() {
    try {
        const response = await fetch('/checklist/bar/glass-washer/entries');
        if (response.ok) {
            entries = await response.json();
            displayEntries();
        } else {
            console.error('Failed to load entries:', response.statusText);
        }
    } catch (error) {
        console.error('Error loading entries:', error);
    }
}

// Display Entries
function displayEntries() {
    const entriesList = document.getElementById('entries-list');
    if (!entriesList) return;
    
    if (entries.length === 0) {
        entriesList.innerHTML = '<p>No entries yet.</p>';
        return;
    }
    
    // Show last 20 entries
    const recentEntries = entries.slice(0, 20);
    
    const table = document.createElement('table');
    table.className = 'data-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>Date</th>
                <th>Time</th>
                <th>Unit</th>
                <th>Staff</th>
                <th>Wash Temp (°C)</th>
                <th>Rinse/Sanitise Temp (°C)</th>
                <th>Method</th>
                <th>Status</th>
                <th>Staff Initials</th>
                <th>Manager Verified</th>
                ${window.userRole === 'Manager' ? '<th>Actions</th>' : ''}
            </tr>
        </thead>
        <tbody>
            ${recentEntries.map(entry => `
                <tr>
                    <td>${entry.entry_date}</td>
                    <td>${entry.entry_time}</td>
                    <td>${entry.unit_name}</td>
                    <td>${entry.staff_name}</td>
                    <td>${entry.wash_temperature}</td>
                    <td>${entry.rinse_sanitising_temperature || 'N/A'}</td>
                    <td>${entry.sanitising_method}</td>
                    <td><span style="color: ${entry.pass_fail === 'Pass' ? 'green' : 'red'}; font-weight: bold;">${entry.pass_fail}</span></td>
                    <td>${entry.staff_initials}</td>
                    <td>${entry.manager_verified ? '✓ ' + entry.manager_verification_initials : 'Pending'}</td>
                    ${window.userRole === 'Manager' && !entry.manager_verified ? `
                        <td><button class="btn-primary" onclick="openVerifyModal(${entry.id})">Verify</button></td>
                    ` : '<td></td>'}
                </tr>
            `).join('')}
        </tbody>
    `;
    
    entriesList.innerHTML = '';
    entriesList.appendChild(table);
}

// Unit Management (Manager only)
function openAddUnitModal() {
    editingUnitId = null;
    document.getElementById('unit-modal-title').textContent = 'Add Unit';
    document.getElementById('unit-form').reset();
    document.getElementById('unit-id').value = '';
    document.getElementById('unit-modal').classList.remove('hidden');
    document.getElementById('unit-modal').style.display = 'block';
}

function closeUnitModal() {
    document.getElementById('unit-modal').classList.add('hidden');
    document.getElementById('unit-modal').style.display = 'none';
}

async function handleUnitFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const unitId = formData.get('unit_id');
    
    const data = {
        action: unitId ? 'update' : 'create',
        id: unitId ? parseInt(unitId) : undefined,
        unit_name: formData.get('unit_name'),
        description: formData.get('description')
    };
    
    try {
        const response = await fetch('/checklist/bar/glass-washer/units', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Unit saved successfully!');
            closeUnitModal();
            loadUnits();
        } else {
            alert('Error: ' + (result.error || 'Failed to save unit'));
        }
    } catch (error) {
        console.error('Error saving unit:', error);
        alert('Error saving unit. Please try again.');
    }
}

function editUnit(unitId) {
    const unit = units.find(u => u.id === unitId);
    if (!unit) return;
    
    editingUnitId = unitId;
    document.getElementById('unit-modal-title').textContent = 'Edit Unit';
    document.getElementById('unit-id').value = unitId;
    document.getElementById('unit-name').value = unit.unit_name;
    document.getElementById('unit-description').value = unit.description || '';
    document.getElementById('unit-modal').classList.remove('hidden');
    document.getElementById('unit-modal').style.display = 'block';
}

async function deleteUnit(unitId) {
    if (!confirm('Are you sure you want to delete this unit? Historical records will be preserved.')) {
        return;
    }
    
    try {
        const response = await fetch('/checklist/bar/glass-washer/units', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'delete',
                id: unitId
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Unit deleted successfully!');
            loadUnits();
        } else {
            alert('Error: ' + (result.error || 'Failed to delete unit'));
        }
    } catch (error) {
        console.error('Error deleting unit:', error);
        alert('Error deleting unit. Please try again.');
    }
}

// Manager Verification
function openVerifyModal(entryId) {
    document.getElementById('verify-entry-id').value = entryId;
    document.getElementById('manager-initials').value = window.userInitials || '';
    document.getElementById('verify-modal').classList.remove('hidden');
    document.getElementById('verify-modal').style.display = 'block';
}

function closeVerifyModal() {
    document.getElementById('verify-modal').classList.add('hidden');
    document.getElementById('verify-modal').style.display = 'none';
}

async function handleVerifySubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    
    const data = {
        action: 'verify',
        entry_id: parseInt(formData.get('entry_id')),
        manager_initials: formData.get('manager_initials')
    };
    
    try {
        const response = await fetch('/checklist/bar/glass-washer/entries', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Entry verified successfully!');
            closeVerifyModal();
            loadEntries();
        } else {
            alert('Error: ' + (result.error || 'Failed to verify entry'));
        }
    } catch (error) {
        console.error('Error verifying entry:', error);
        alert('Error verifying entry. Please try again.');
    }
}

// Make functions available globally
window.editUnit = editUnit;
window.deleteUnit = deleteUnit;
window.openVerifyModal = openVerifyModal;

