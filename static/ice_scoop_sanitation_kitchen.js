/**
 * Ice Scoop Sanitation Monitor (Kitchen)
 */

let units = [];
let currentUnitId = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadUnits();
    setDefaultDate();
});

function initializeEventListeners() {
    const loadBtn = document.getElementById('load-entry-btn');
    if (loadBtn) loadBtn.addEventListener('click', loadChecklistEntry);

    const saveBtn = document.getElementById('save-entry-btn');
    if (saveBtn) saveBtn.addEventListener('click', saveChecklistEntry);

    const userRole = (window.userRole || '').trim();
    if (userRole === 'Manager') {
        const addUnitBtn = document.getElementById('add-unit-btn');
        if (addUnitBtn) addUnitBtn.addEventListener('click', () => openUnitModal());

        const unitForm = document.getElementById('unit-form');
        if (unitForm) unitForm.addEventListener('submit', handleUnitFormSubmit);

        const unitModalClose = document.getElementById('unit-modal-close');
        const unitFormCancel = document.getElementById('unit-form-cancel');
        if (unitModalClose) unitModalClose.addEventListener('click', closeUnitModal);
        if (unitFormCancel) unitFormCancel.addEventListener('click', closeUnitModal);
    }
}

function setDefaultDate() {
    const dateInput = document.getElementById('entry-date');
    if (dateInput && !dateInput.value) {
        dateInput.value = new Date().toISOString().split('T')[0];
    }
}

function getSlots() {
    const slotsEl = document.getElementById('ice-scoop-slots');
    if (!slotsEl) return [];
    try {
        return JSON.parse(slotsEl.getAttribute('data-slots') || '[]');
    } catch (e) {
        return [];
    }
}

function loadUnits() {
    fetch('/checklist/kitchen/ice-scoop/units')
        .then(res => res.json())
        .then(data => {
            units = data;
            renderUnits();
            updateUnitSelect();
        })
        .catch(err => {
            console.error('Error loading units:', err);
            showError('Failed to load units');
        });
}

function renderUnits() {
    const userRole = (window.userRole || '').trim();
    if (userRole !== 'Manager') return;
    const unitsList = document.getElementById('units-list');
    if (!unitsList) return;
    if (units.length === 0) {
        unitsList.innerHTML = '<p style="color: #666;">No units found. Create one to get started.</p>';
        return;
    }
    unitsList.innerHTML = units.map(unit => `
        <div style="padding: 10px; background: white; border-radius: 4px; border: 1px solid #ddd;">
            <div style="font-weight: bold; margin-bottom: 5px;">${unit.unit_name}</div>
            ${unit.description ? `<div style="font-size: 0.9em; color: #666;">${unit.description}</div>` : ''}
            <div style="margin-top: 8px; display: flex; gap: 5px;">
                <button onclick="editUnit(${unit.id})" class="btn-secondary" style="font-size: 0.85em; padding: 4px 8px;">Edit</button>
                <button onclick="deleteUnit(${unit.id})" class="btn-secondary" style="font-size: 0.85em; padding: 4px 8px; color: #d32f2f;">Delete</button>
            </div>
        </div>
    `).join('');
}

function updateUnitSelect() {
    const unitSelect = document.getElementById('unit-select');
    if (!unitSelect) return;
    unitSelect.innerHTML = '<option value="">-- Select Unit --</option>' +
        units.map(unit => `<option value="${unit.id}">${unit.unit_name}</option>`).join('');
}

function loadChecklistEntry() {
    const unitId = document.getElementById('unit-select')?.value;
    const entryDate = document.getElementById('entry-date')?.value;
    if (!unitId || !entryDate) {
        showError('Please select a unit and date');
        return;
    }
    currentUnitId = parseInt(unitId);
    fetch(`/checklist/kitchen/ice-scoop/entries?unit_id=${unitId}&entry_date=${entryDate}`)
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                showError(data.error || 'Failed to load checklist');
                return;
            }
            renderChecklistItems(data.slots || []);
            document.getElementById('checklist-items-container').style.display = 'block';
        })
        .catch(err => {
            console.error('Error loading entry:', err);
            showError('Failed to load checklist entry');
        });
}

function renderChecklistItems(slots) {
    const slotsConfig = getSlots();
    const slotMap = {};
    slots.forEach(slot => {
        slotMap[slot.slot_index] = slot;
    });
    const itemsContainer = document.getElementById('checklist-items');
    if (!itemsContainer) return;

    itemsContainer.innerHTML = slotsConfig.map(slot => {
        const entry = slotMap[slot.index] || {};
        const checked = entry.is_completed ? 'checked' : '';
        const initials = entry.staff_initials || '';
        return `
            <div style="display: grid; grid-template-columns: 160px 1fr 120px; gap: 10px; align-items: center; margin-bottom: 10px;">
                <div style="font-weight: 600;">${slot.label}</div>
                <label style="display: flex; align-items: center; gap: 8px;">
                    <input type="checkbox" class="slot-checkbox" data-slot-index="${slot.index}" ${checked}>
                    <span>Sanitised</span>
                </label>
                <input type="text" class="slot-initials" data-slot-index="${slot.index}" maxlength="10" placeholder="Initials" value="${initials}">
            </div>
        `;
    }).join('');

    itemsContainer.querySelectorAll('.slot-checkbox').forEach(cb => {
        cb.addEventListener('change', function() {
            const slotIndex = this.getAttribute('data-slot-index');
            const initialsInput = itemsContainer.querySelector(`.slot-initials[data-slot-index="${slotIndex}"]`);
            if (this.checked && initialsInput && !initialsInput.value) {
                initialsInput.value = window.userInitials || '';
            }
        });
    });
}

function saveChecklistEntry() {
    const entryDate = document.getElementById('entry-date')?.value;
    if (!currentUnitId || !entryDate) {
        showError('Please select a unit and date');
        return;
    }
    const slotsConfig = getSlots();
    const slotsPayload = slotsConfig.map(slot => {
        const checkbox = document.querySelector(`.slot-checkbox[data-slot-index="${slot.index}"]`);
        const initials = document.querySelector(`.slot-initials[data-slot-index="${slot.index}"]`);
        return {
            slot_index: slot.index,
            is_completed: checkbox ? checkbox.checked : false,
            staff_initials: initials ? initials.value.trim() : ''
        };
    });
    fetch('/checklist/kitchen/ice-scoop/entries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            unit_id: currentUnitId,
            entry_date: entryDate,
            slots: slotsPayload
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showSuccess('Checklist saved!');
            } else {
                showError(data.error || 'Failed to save checklist');
            }
        })
        .catch(err => {
            console.error('Error saving entry:', err);
            showError('Failed to save checklist');
        });
}

// Unit management
let editingUnitId = null;

function openUnitModal(unit = null) {
    const modal = document.getElementById('unit-modal');
    if (!modal) return;
    editingUnitId = unit ? unit.id : null;
    document.getElementById('unit-modal-title').textContent = unit ? 'Edit Unit' : 'Add Unit';
    document.getElementById('unit-id').value = unit ? unit.id : '';
    document.getElementById('unit-name').value = unit ? unit.unit_name : '';
    document.getElementById('unit-description').value = unit ? (unit.description || '') : '';
    modal.style.display = 'block';
    modal.classList.remove('hidden');
}

function closeUnitModal() {
    const modal = document.getElementById('unit-modal');
    if (!modal) return;
    modal.style.display = 'none';
    modal.classList.add('hidden');
    editingUnitId = null;
}

function handleUnitFormSubmit(e) {
    e.preventDefault();
    const unitName = document.getElementById('unit-name').value.trim();
    const description = document.getElementById('unit-description').value.trim();
    if (!unitName) {
        showError('Unit name is required');
        return;
    }
    const payload = {
        action: editingUnitId ? 'update' : 'create',
        id: editingUnitId || undefined,
        unit_name: unitName,
        description: description
    };
    fetch('/checklist/kitchen/ice-scoop/units', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                closeUnitModal();
                loadUnits();
                showSuccess(editingUnitId ? 'Unit updated successfully' : 'Unit created successfully');
            } else {
                showError(data.error || 'Failed to save unit');
            }
        })
        .catch(err => {
            console.error('Error saving unit:', err);
            showError('Failed to save unit');
        });
}

function editUnit(unitId) {
    const unit = units.find(u => u.id === unitId);
    if (unit) openUnitModal(unit);
}

function deleteUnit(unitId) {
    if (!confirm('Are you sure you want to delete this unit?')) return;
    fetch('/checklist/kitchen/ice-scoop/units', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'delete', id: unitId })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                loadUnits();
                showSuccess('Unit deleted successfully');
            } else {
                showError(data.error || 'Failed to delete unit');
            }
        })
        .catch(err => {
            console.error('Error deleting unit:', err);
            showError('Failed to delete unit');
        });
}

function showError(message) {
    alert('Error: ' + message);
}

function showSuccess(message) {
    alert('Success: ' + message);
}

