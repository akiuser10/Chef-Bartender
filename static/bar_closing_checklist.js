/**
 * BAR Closing Checklist - Frontend JavaScript
 * Daily checklist management for bar closing shift
 */

// Global state
let units = [];
let checklistPoints = [];
let currentEntry = null;
let currentUnitId = null;
let editingUnitId = null;
let editingPointId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadUnits();
    
    // Auto-fill current date if not set
    const dateInput = document.getElementById('entry-date');
    if (dateInput && !dateInput.value) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.value = today;
    }
});

// Event Listeners
function initializeEventListeners() {
    // Load entry button
    const loadBtn = document.getElementById('load-entry-btn');
    if (loadBtn) {
        loadBtn.addEventListener('click', loadChecklistEntry);
    }
    
    // Save entry button
    const saveBtn = document.getElementById('save-entry-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveChecklistEntry);
    }
    
    // Unit management (Manager only)
    // Normalize role check - strip whitespace
    const userRole = (window.userRole || '').trim();
    if (userRole === 'Manager') {
        const addUnitBtn = document.getElementById('add-unit-btn');
        if (addUnitBtn) {
            addUnitBtn.addEventListener('click', () => {
                console.log('Add unit button clicked');
                openUnitModal();
            });
        } else {
            console.error('Add unit button not found');
        }
        
        const unitForm = document.getElementById('unit-form');
        if (unitForm) {
            unitForm.addEventListener('submit', handleUnitFormSubmit);
        }
        
        const unitModalClose = document.getElementById('unit-modal-close');
        const unitFormCancel = document.getElementById('unit-form-cancel');
        if (unitModalClose) unitModalClose.addEventListener('click', closeUnitModal);
        if (unitFormCancel) unitFormCancel.addEventListener('click', closeUnitModal);
        
        // Checklist points management
        const addPointBtn = document.getElementById('add-point-btn');
        if (addPointBtn) {
            addPointBtn.addEventListener('click', () => openPointModal());
        }
        
        const pointForm = document.getElementById('point-form');
        if (pointForm) {
            pointForm.addEventListener('submit', handlePointFormSubmit);
        }
        
        const pointModalClose = document.getElementById('point-modal-close');
        const pointFormCancel = document.getElementById('point-form-cancel');
        if (pointModalClose) pointModalClose.addEventListener('click', closePointModal);
        if (pointFormCancel) pointFormCancel.addEventListener('click', closePointModal);
    }
    
    // PDF generation (available to both Manager and Bartender)
    const generatePdfBtn = document.getElementById('generate-pdf-btn');
    if (generatePdfBtn) {
        generatePdfBtn.addEventListener('click', generatePDF);
    }
    
    const pdfMonth = document.getElementById('pdf-month');
    const pdfYear = document.getElementById('pdf-year');
    if (pdfMonth) pdfMonth.addEventListener('change', updatePdfButton);
    if (pdfYear) pdfYear.addEventListener('input', updatePdfButton);
}

// Load Units
function loadUnits() {
    fetch('/checklist/bar/shift-closing/units')
        .then(response => response.json())
        .then(data => {
            units = data;
            renderUnits();
            updateUnitSelect();
        })
        .catch(error => {
            console.error('Error loading units:', error);
            showError('Failed to load units');
        });
}

// Render Units (Manager only)
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

// Update Unit Select
function updateUnitSelect() {
    const unitSelect = document.getElementById('unit-select');
    if (!unitSelect) return;
    
    unitSelect.innerHTML = '<option value="">-- Select Unit --</option>' +
        units.map(unit => `<option value="${unit.id}">${unit.unit_name}</option>`).join('');
}

// Load Checklist Entry
function loadChecklistEntry() {
    const unitId = document.getElementById('unit-select')?.value;
    const entryDate = document.getElementById('entry-date')?.value;
    
    if (!unitId || !entryDate) {
        showError('Please select a unit and date');
        return;
    }
    
    currentUnitId = parseInt(unitId);
    
    fetch(`/checklist/bar/shift-closing/entries?unit_id=${unitId}&entry_date=${entryDate}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentEntry = data;
                renderChecklistItems(data.points);
                document.getElementById('checklist-items-container').style.display = 'block';
                
                // Load checklist points for manager
                const userRole = (window.userRole || '').trim();
                if (userRole === 'Manager') {
                    loadChecklistPoints(unitId);
                }
            } else {
                showError(data.error || 'Failed to load checklist entry');
            }
        })
        .catch(error => {
            console.error('Error loading entry:', error);
            showError('Failed to load checklist entry');
        });
}

// Load Checklist Points (Manager only)
function loadChecklistPoints(unitId) {
    fetch(`/checklist/bar/shift-closing/points?unit_id=${unitId}`)
        .then(response => response.json())
        .then(data => {
            checklistPoints = data;
            renderChecklistPoints();
        })
        .catch(error => {
            console.error('Error loading checklist points:', error);
        });
}

// Render Checklist Points (Manager only)
function renderChecklistPoints() {
    const userRole = (window.userRole || '').trim();
    if (userRole !== 'Manager') return;
    
    const pointsList = document.getElementById('points-list');
    const addPointBtn = document.getElementById('add-point-btn');
    
    if (!pointsList || !addPointBtn) return;
    
    if (checklistPoints.length === 0) {
        pointsList.innerHTML = '<p style="color: #666;">No checklist points found. Create them to set up the checklist.</p>';
        pointsList.style.display = 'block';
        addPointBtn.style.display = 'block';
        return;
    }
    
    // Group points by group_name
    const grouped = {};
    checklistPoints.forEach(point => {
        if (!grouped[point.group_name]) {
            grouped[point.group_name] = [];
        }
        grouped[point.group_name].push(point);
    });
    
    pointsList.innerHTML = Object.keys(grouped).map(groupName => `
        <div style="margin-bottom: 15px; padding: 10px; background: white; border-radius: 4px; border: 1px solid #ddd;">
            <div style="font-weight: bold; margin-bottom: 8px; color: #333;">${groupName}</div>
            ${grouped[groupName].map(point => `
                <div style="margin-left: 15px; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center;">
                    <span>${point.point_text}</span>
                    <div style="display: flex; gap: 5px;">
                        <button onclick="editPoint(${point.id})" class="btn-secondary" style="font-size: 0.85em; padding: 4px 8px;">Edit</button>
                        <button onclick="deletePoint(${point.id})" class="btn-secondary" style="font-size: 0.85em; padding: 4px 8px; color: #d32f2f;">Delete</button>
                    </div>
                </div>
            `).join('')}
        </div>
    `).join('');
    
    pointsList.style.display = 'block';
    addPointBtn.style.display = 'block';
}

// Render Checklist Items
function renderChecklistItems(points) {
    const container = document.getElementById('checklist-items');
    if (!container) return;
    
    // Group points by group_name
    const grouped = {};
    points.forEach(point => {
        if (!grouped[point.group_name]) {
            grouped[point.group_name] = [];
        }
        grouped[point.group_name].push(point);
    });
    
    container.innerHTML = Object.keys(grouped).map(groupName => `
        <div style="margin-bottom: 20px; padding: 15px; background: #f9f9f9; border-radius: 8px; border: 1px solid #e0e0e0;">
            <h4 style="margin: 0 0 15px 0; color: #333; font-size: 1.1em; font-weight: bold;">${groupName}</h4>
            ${grouped[groupName].map(point => {
                const itemId = `item-${point.point_id}`;
                const checkboxId = `checkbox-${point.point_id}`;
                const initialsId = `initials-${point.point_id}`;
                const isCompleted = point.is_completed || false;
                const initials = point.staff_initials || '';
                
                return `
                    <div style="margin-bottom: 10px; padding: 10px; background: white; border-radius: 4px; display: flex; align-items: center; gap: 10px;">
                        <input type="checkbox" 
                               id="${checkboxId}" 
                               data-point-id="${point.point_id}"
                               ${isCompleted ? 'checked' : ''}
                               style="width: 20px; height: 20px; cursor: pointer;">
                        <label for="${checkboxId}" style="flex: 1; cursor: pointer; margin: 0;">
                            ${point.point_text}
                        </label>
                        <input type="text" 
                               id="${initialsId}"
                               data-point-id="${point.point_id}"
                               placeholder="Initials" 
                               maxlength="10"
                               value="${initials}"
                               style="width: 80px; padding: 5px; text-align: center; text-transform: uppercase;">
                    </div>
                `;
            }).join('')}
        </div>
    `).join('');
    
    // Add event listeners to checkboxes and initials
    points.forEach(point => {
        const checkbox = document.getElementById(`checkbox-${point.point_id}`);
        const initialsInput = document.getElementById(`initials-${point.point_id}`);
        
        if (checkbox) {
            checkbox.addEventListener('change', () => updateChecklistItem(point.point_id));
        }
        
        if (initialsInput) {
            initialsInput.addEventListener('blur', () => updateChecklistItem(point.point_id));
            // Auto-uppercase
            initialsInput.addEventListener('input', function() {
                this.value = this.value.toUpperCase();
            });
        }
    });
}

// Update Checklist Item
function updateChecklistItem(pointId) {
    if (!currentEntry) return;
    
    const checkbox = document.getElementById(`checkbox-${pointId}`);
    const initialsInput = document.getElementById(`initials-${pointId}`);
    
    if (!checkbox || !initialsInput) return;
    
    const isCompleted = checkbox.checked;
    const initials = initialsInput.value.trim();
    
    fetch('/checklist/bar/shift-closing/entries', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: 'update_item',
            entry_id: currentEntry.entry_id,
            checklist_point_id: pointId,
            is_completed: isCompleted,
            staff_initials: initials || (window.userInitials || '')
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update local state
            const point = currentEntry.points.find(p => p.point_id === pointId);
            if (point) {
                point.is_completed = isCompleted;
                point.staff_initials = data.item.staff_initials;
            }
        } else {
            showError(data.error || 'Failed to update checklist item');
            // Revert checkbox
            checkbox.checked = !isCompleted;
        }
    })
    .catch(error => {
        console.error('Error updating item:', error);
        showError('Failed to update checklist item');
        checkbox.checked = !isCompleted;
    });
}

// Save Checklist Entry (for explicit save button)
function saveChecklistEntry() {
    showSuccess('Checklist saved!');
}

// Unit Management (Manager only)
function openUnitModal(unitId = null) {
    editingUnitId = unitId;
    const modal = document.getElementById('unit-modal');
    const form = document.getElementById('unit-form');
    const title = document.getElementById('unit-modal-title');
    
    if (!modal || !form || !title) {
        console.error('Modal elements not found');
        return;
    }
    
    if (unitId) {
        const unit = units.find(u => u.id === unitId);
        if (unit) {
            document.getElementById('unit-id').value = unit.id;
            document.getElementById('unit-name').value = unit.unit_name;
            document.getElementById('unit-description').value = unit.description || '';
            title.textContent = 'Edit Unit';
        }
    } else {
        form.reset();
        document.getElementById('unit-id').value = '';
        title.textContent = 'Add Unit';
    }
    
    // Remove hidden class to show modal (CSS uses !important on .modal.hidden)
    modal.classList.remove('hidden');
}

function closeUnitModal() {
    const modal = document.getElementById('unit-modal');
    if (modal) {
        // Add hidden class to hide modal
        modal.classList.add('hidden');
    }
}

function handleUnitFormSubmit(e) {
    e.preventDefault();
    
    const formData = {
        action: editingUnitId ? 'update' : 'create',
        id: editingUnitId,
        unit_name: document.getElementById('unit-name').value.trim(),
        description: document.getElementById('unit-description').value.trim()
    };
    
    fetch('/checklist/bar/shift-closing/units', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(editingUnitId ? 'Unit updated successfully' : 'Unit created successfully');
            closeUnitModal();
            loadUnits();
        } else {
            showError(data.error || 'Failed to save unit');
        }
    })
    .catch(error => {
        console.error('Error saving unit:', error);
        showError('Failed to save unit');
    });
}

function editUnit(unitId) {
    openUnitModal(unitId);
}

function deleteUnit(unitId) {
    if (!confirm('Are you sure you want to delete this unit? This action cannot be undone.')) {
        return;
    }
    
    fetch('/checklist/bar/shift-closing/units', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: 'delete',
            id: unitId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess('Unit deleted successfully');
            loadUnits();
        } else {
            showError(data.error || 'Failed to delete unit');
        }
    })
    .catch(error => {
        console.error('Error deleting unit:', error);
        showError('Failed to delete unit');
    });
}

// Checklist Point Management (Manager only)
function openPointModal(pointId = null) {
    if (!currentUnitId) {
        showError('Please select a unit first');
        return;
    }
    
    editingPointId = pointId;
    const modal = document.getElementById('point-modal');
    const form = document.getElementById('point-form');
    const title = document.getElementById('point-modal-title');
    
    if (!modal || !form || !title) {
        console.error('Point modal elements not found');
        return;
    }
    
    document.getElementById('point-unit-id').value = currentUnitId;
    
    if (pointId) {
        const point = checklistPoints.find(p => p.id === pointId);
        if (point) {
            document.getElementById('point-id').value = point.id;
            document.getElementById('point-group-name').value = point.group_name;
            document.getElementById('point-text').value = point.point_text;
            document.getElementById('point-display-order').value = point.display_order;
            title.textContent = 'Edit Checklist Point';
        }
    } else {
        form.reset();
        document.getElementById('point-id').value = '';
        document.getElementById('point-unit-id').value = currentUnitId;
        // Set next display order
        const maxOrder = checklistPoints.length > 0 
            ? Math.max(...checklistPoints.map(p => p.display_order)) 
            : 0;
        document.getElementById('point-display-order').value = maxOrder + 1;
        title.textContent = 'Add Checklist Point';
    }
    
    // Remove hidden class to show modal (CSS uses !important on .modal.hidden)
    modal.classList.remove('hidden');
}

function closePointModal() {
    const modal = document.getElementById('point-modal');
    if (modal) {
        // Add hidden class to hide modal
        modal.classList.add('hidden');
    }
}

function handlePointFormSubmit(e) {
    e.preventDefault();
    
    const formData = {
        action: editingPointId ? 'update' : 'create',
        id: editingPointId,
        unit_id: parseInt(document.getElementById('point-unit-id').value),
        group_name: document.getElementById('point-group-name').value.trim(),
        point_text: document.getElementById('point-text').value.trim(),
        display_order: parseInt(document.getElementById('point-display-order').value)
    };
    
    fetch('/checklist/bar/shift-closing/points', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(editingPointId ? 'Checklist point updated successfully' : 'Checklist point created successfully');
            closePointModal();
            loadChecklistPoints(currentUnitId);
            // Reload entry if it's loaded
            if (currentEntry) {
                loadChecklistEntry();
            }
        } else {
            showError(data.error || 'Failed to save checklist point');
        }
    })
    .catch(error => {
        console.error('Error saving point:', error);
        showError('Failed to save checklist point');
    });
}

function editPoint(pointId) {
    openPointModal(pointId);
}

function deletePoint(pointId) {
    if (!confirm('Are you sure you want to delete this checklist point? This action cannot be undone.')) {
        return;
    }
    
    fetch('/checklist/bar/shift-closing/points', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: 'delete',
            id: pointId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess('Checklist point deleted successfully');
            loadChecklistPoints(currentUnitId);
            // Reload entry if it's loaded
            if (currentEntry) {
                loadChecklistEntry();
            }
        } else {
            showError(data.error || 'Failed to delete checklist point');
        }
    })
    .catch(error => {
        console.error('Error deleting point:', error);
        showError('Failed to delete checklist point');
    });
}

// PDF Generation (Manager and Bartender)
function updatePdfButton() {
    const pdfMonth = document.getElementById('pdf-month')?.value;
    const pdfYear = document.getElementById('pdf-year')?.value;
    const generateBtn = document.getElementById('generate-pdf-btn');
    
    if (generateBtn) {
        generateBtn.style.display = (pdfMonth && pdfYear) ? 'block' : 'none';
    }
}

function generatePDF() {
    const pdfMonth = document.getElementById('pdf-month')?.value;
    const pdfYear = document.getElementById('pdf-year')?.value;
    const unitId = document.getElementById('unit-select')?.value;
    
    if (!pdfMonth || !pdfYear || !unitId) {
        showError('Please select month, year, and unit');
        return;
    }
    
    const monthYear = `${pdfYear}-${pdfMonth}`;
    
    fetch('/checklist/bar/shift-closing/pdf', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            unit_id: parseInt(unitId),
            month: monthYear
        })
    })
    .then(response => {
        if (response.ok) {
            return response.blob();
        } else {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to generate PDF');
            });
        }
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `BAR_Closing_Checklist_${pdfMonth}_${pdfYear}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showSuccess('PDF generated successfully');
    })
    .catch(error => {
        console.error('Error generating PDF:', error);
        showError(error.message || 'Failed to generate PDF');
    });
}

// Utility Functions
function showError(message) {
    // Simple alert for now - can be replaced with a toast notification
    alert('Error: ' + message);
}

function showSuccess(message) {
    // Simple alert for now - can be replaced with a toast notification
    alert('Success: ' + message);
}

