// requests.js - JavaScript for the requests page in DevERP

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips and popovers if using Bootstrap components
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Add data-label attributes for responsive tables
    const table = document.getElementById('requestsTable');
    if (table) {
        const headerCells = table.querySelectorAll('thead th');
        const headerTexts = Array.from(headerCells).map(cell => cell.textContent.trim());
        
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                if (index < headerTexts.length) {
                    cell.setAttribute('data-label', headerTexts[index]);
                }
            });
        });
    }

    // Handle filter form submission
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            applyFilters();
        });
    }

    // Clear filters button
    const clearFiltersBtn = document.getElementById('clearFilters');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            // Reset all filter inputs
            document.getElementById('statusFilter').value = '';
            document.getElementById('dateRangeFilter').value = '';
            document.getElementById('searchInput').value = '';
            
            // Apply the cleared filters
            applyFilters();
        });
    }

    // View request details
    const viewRequestBtns = document.querySelectorAll('.view-request');
    viewRequestBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const requestId = this.getAttribute('data-request-id');
            viewRequestDetails(requestId);
        });
    });

    // Create Request form handling
    const createRequestForm = document.getElementById('createRequestForm');
    if (createRequestForm) {
        // Update quantity unit when item is selected
        const itemSelect = document.getElementById('item');
        const quantityUnit = document.getElementById('quantityUnit');
        const itemAvailability = document.getElementById('itemAvailability');
        
        itemSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const unit = selectedOption.getAttribute('data-unit') || 'units';
            const available = selectedOption.getAttribute('data-available') || '0';
            
            quantityUnit.textContent = unit;
            itemAvailability.textContent = `Available: ${available} ${unit}`;
            
            // Optionally, set max attribute on quantity input
            const quantityInput = document.getElementById('quantity');
            quantityInput.setAttribute('max', available);
        });
        
        // Form validation
        createRequestForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Validate inputs
            const itemId = itemSelect.value;
            const quantity = document.getElementById('quantity').value;
            
            if (!itemId) {
                showAlert('Please select an item', 'danger');
                return;
            }
            
            if (!quantity || quantity <= 0) {
                showAlert('Please enter a valid quantity', 'danger');
                return;
            }
            
            // Submit form using fetch API
            const formData = new FormData(this);
            
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Close modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('createRequestModal'));
                    modal.hide();
                    
                    // Show success message
                    showAlert(data.message || 'Request submitted successfully', 'success');
                    
                    // Reload page to show the new request
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    showAlert(data.message || 'Error submitting request', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('An error occurred while submitting the request', 'danger');
            });
        });
    }

    // Action buttons event listeners
    setupActionButtons();

    // Setup search debounce
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let debounceTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimeout);
            debounceTimeout = setTimeout(() => {
                if (this.value.length >= 2 || this.value.length === 0) {
                    applyFilters();
                }
            }, 500);
        });
    }
});

/**
 * Apply filters and update request list
 */
function applyFilters() {
    const status = document.getElementById('statusFilter').value;
    const dateRange = document.getElementById('dateRangeFilter').value;
    const search = document.getElementById('searchInput').value;
    
    // Build query string
    let queryParams = new URLSearchParams();
    if (status) queryParams.append('status', status);
    if (dateRange) queryParams.append('date_range', dateRange);
    if (search) queryParams.append('search', search);
    
    // Redirect to filtered URL
    window.location.href = `${window.location.pathname}?${queryParams.toString()}`;
}

/**
 * View request details in modal
 * @param {string} requestId - The ID of the request to view
 */
function viewRequestDetails(requestId) {
    // Show loading state
    const modal = new bootstrap.Modal(document.getElementById('viewRequestModal'));
    modal.show();
    
    // Fetch request details
    fetch(`/inventory/api/requests/${requestId}/`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const request = data.request;
            
            // Populate request details
            document.getElementById('requestId').textContent = request.id;
            document.getElementById('requestRequester').textContent = request.requester_name;
            document.getElementById('requestDepartment').textContent = request.department || 'N/A';
            document.getElementById('requestItem').textContent = request.item_name;
            document.getElementById('requestQuantity').textContent = `${request.quantity} ${request.unit}`;
            document.getElementById('requestDate').textContent = request.created_at;
            
            // Status with badge
            const statusEl = document.getElementById('requestStatus');
            statusEl.innerHTML = `<span class="badge rounded-pill bg-${request.status.toLowerCase()}-subtle text-${request.status.toLowerCase()}">${request.status}</span>`;
            
            // Priority with indicator
            const priorityEl = document.getElementById('requestPriority');
            priorityEl.innerHTML = `<span class="priority-indicator priority-${request.priority.toLowerCase()}">${request.priority}</span>`;
            
            // Reason
            document.getElementById('requestReason').textContent = request.reason || 'No reason provided';
            
            // Request history
            populateRequestHistory(request.history);
            
            // Action buttons based on status and permissions
            populateActionButtons(request);
            
        } else {
            showAlert(data.message || 'Error loading request details', 'danger');
            modal.hide();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('An error occurred while loading request details', 'danger');
        modal.hide();
    });
}

/**
 * Populate request history timeline
 * @param {Array} history - Array of history items
 */
function populateRequestHistory(history) {
    const historyContainer = document.getElementById('requestHistory');
    historyContainer.innerHTML = '';
    
    if (!history || history.length === 0) {
        historyContainer.innerHTML = '<p class="text-muted">No history available</p>';
        return;
    }
    
    history.forEach(item => {
        const iconClass = getHistoryIconClass(item.action);
        const badgeClass = `timeline-badge-${item.action.toLowerCase()}`;
        const contentClass = `timeline-content-${item.action.toLowerCase()}`;
        
        const historyItem = document.createElement('div');
        historyItem.className = 'timeline-item';
        historyItem.innerHTML = `
            <div class="timeline-badge ${badgeClass}">
                <i class="${iconClass}"></i>
            </div>
            <div class="timeline-content ${contentClass}">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="fw-semibold">${item.action}</span>
                    <span class="timeline-time">${item.timestamp}</span>
                </div>
                <div>
                    <span>${item.user}</span>
                    ${item.comment ? `<p class="mt-1 mb-0 text-muted">${item.comment}</p>` : ''}
                </div>
            </div>
        `;
        
        historyContainer.appendChild(historyItem);
    });
}

/**
 * Get appropriate icon class for history timeline
 * @param {string} action - The action type
 * @returns {string} - CSS class for the icon
 */
function getHistoryIconClass(action) {
    switch (action.toLowerCase()) {
        case 'created':
            return 'fas fa-plus';
        case 'approved':
            return 'fas fa-check';
        case 'rejected':
            return 'fas fa-times';
        case 'fulfilled':
            return 'fas fa-box-check';
        case 'updated':
            return 'fas fa-edit';
        default:
            return 'fas fa-circle';
    }
}

/**
 * Populate action buttons based on request status and user permissions
 * @param {Object} request - The request data
 */
function populateActionButtons(request) {
    const actionButtons = document.getElementById('requestActionButtons');
    actionButtons.innerHTML = '';
    
    if (request.status === 'pending' && request.can_approve) {
        const approveBtn = createActionButton('approve', 'success', 'check', 'Approve');
        const rejectBtn = createActionButton('reject', 'danger', 'times', 'Reject');
        
        actionButtons.appendChild(approveBtn);
        actionButtons.appendChild(rejectBtn);
    }
    
    if (request.status === 'approved' && request.can_fulfill) {
        const fulfillBtn = createActionButton('fulfill', 'primary', 'box-check', 'Mark Fulfilled');
        actionButtons.appendChild(fulfillBtn);
    }
    
    if (request.can_delete) {
        const deleteBtn = createActionButton('delete', 'danger', 'trash-alt', 'Delete');
        actionButtons.appendChild(deleteBtn);
    }
}

/**
 * Create an action button element
 * @param {string} action - The action type
 * @param {string} colorClass - Bootstrap color class
 * @param {string} iconName - FontAwesome icon name
 * @param {string} text - Button text
 * @returns {HTMLElement} - The button element
 */
function createActionButton(action, colorClass, iconName, text) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `btn btn-${colorClass} me-2`;
    btn.dataset.action = action;
    btn.innerHTML = `<i class="fas fa-${iconName} me-1"></i> ${text}`;
    
    btn.addEventListener('click', function() {
        handleRequestAction(action);
    });
    
    return btn;
}

/**
 * Setup action buttons for all requests in the table
 */
function setupActionButtons() {
    // Approve request buttons
    document.querySelectorAll('.approve-request').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const requestId = this.getAttribute('data-request-id');
            showConfirmationModal('approve', requestId, 'Are you sure you want to approve this request?');
        });
    });
    
    // Reject request buttons
    document.querySelectorAll('.reject-request').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const requestId = this.getAttribute('data-request-id');
            showConfirmationModal('reject', requestId, 'Are you sure you want to reject this request?', true);
        });
    });
    
    // Fulfill request buttons
    document.querySelectorAll('.fulfill-request').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const requestId = this.getAttribute('data-request-id');
            showConfirmationModal('fulfill', requestId, 'Are you sure you want to mark this request as fulfilled?');
        });
    });
    
    // Delete request buttons
    document.querySelectorAll('.delete-request').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const requestId = this.getAttribute('data-request-id');
            showConfirmationModal('delete', requestId, 'Are you sure you want to delete this request? This action cannot be undone.');
        });
    });
}

/**
 * Show confirmation modal for an action
 * @param {string} action - The action type
 * @param {string} requestId - The request ID
 * @param {string} message - Confirmation message
 * @param {boolean} showComment - Whether to show comment field
 */
function showConfirmationModal(action, requestId, message, showComment = false) {
    const modal = new bootstrap.Modal(document.getElementById('confirmationModal'));
    const confirmBtn = document.getElementById('confirmAction');
    const commentSection = document.getElementById('commentSection');
    
    document.getElementById('confirmationMessage').textContent = message;
    
    // Show/hide comment section
    if (showComment) {
        commentSection.classList.remove('d-none');
        document.getElementById('actionComment').value = '';
    } else {
        commentSection.classList.add('d-none');
    }
    
    // Update button color based on action
    confirmBtn.className = 'btn btn-primary';
    if (action === 'approve') confirmBtn.className = 'btn btn-success';
    if (action === 'reject') confirmBtn.className = 'btn btn-danger';
    if (action === 'delete') confirmBtn.className = 'btn btn-danger';
    
    // Set onclick for the confirm button
    confirmBtn.onclick = function() {
        const comment = showComment ? document.getElementById('actionComment').value : '';
        performRequestAction(action, requestId, comment);
        modal.hide();
    };
    
    modal.show();
}

/**
 * Handle request action from the details modal
 * @param {string} action - The action type
 */
function handleRequestAction(action) {
    const requestId = document.getElementById('requestId').textContent;
    showConfirmationModal(action, requestId, `Are you sure you want to ${action} this request?`, action === 'reject');
}

/**
 * Perform the request action via API call
 * @param {string} action - The action type
 * @param {string} requestId - The request ID
 * @param {string} comment - Optional comment
 */
function performRequestAction(action, requestId, comment = '') {
    // Create request body
    const requestBody = {
        action: action,
        comment: comment
    };
    
    // Determine endpoint
    let endpoint = `/inventory/api/requests/${requestId}/`;
    let method = 'PATCH';
    
    if (action === 'delete') {
        method = 'DELETE';
    }
    
    // Make API call
    fetch(endpoint, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: method === 'DELETE' ? null : JSON.stringify(requestBody)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert(data.message || 'Action completed successfully', 'success');
            
            // Reload page after a brief delay
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showAlert(data.message || 'Error performing action', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('An error occurred while performing the action', 'danger');
    });
}

/**
 * Show alert message
 * @param {string} message - The message to display
 * @param {string} type - Alert type (success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    // Check if alert container exists, create if not
    let alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'alertContainer';
        alertContainer.className = 'position-fixed top-0 start-50 translate-middle-x mt-3 z-index-1050';
        document.body.appendChild(alertContainer);
    }
    
    // Create alert element
    const alertId = 'alert-' + Date.now();
    const alertEl = document.createElement('div');
    alertEl.className = `alert alert-${type} alert-dismissible fade show`;
    alertEl.role = 'alert';
    alertEl.id = alertId;
    alertEl.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to container
    alertContainer.appendChild(alertEl);
    
    // Initialize Bootstrap alert
    const bsAlert = new bootstrap.Alert(alertEl);
    
    // Auto close after 5 seconds
    setTimeout(() => {
        bsAlert.close();
    }, 5000);
    
    // Remove from DOM after closed
    alertEl.addEventListener('closed.bs.alert', function() {
        alertEl.remove();
        if (alertContainer.children.length === 0) {
            alertContainer.remove();
        }
    });
}

/**
 * Get CSRF token from cookies
 * @returns {string} - CSRF token
 */
function getCsrfToken() {
    let csrfToken = '';
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith('csrftoken=')) {
            csrfToken = cookie.substring('csrftoken='.length);
            break;
        }
    }
    return csrfToken;
}