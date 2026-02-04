/**
 * AI-Digest Frontend JavaScript Utilities
 */

// Toast notifications
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 show`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1100';
    document.body.appendChild(container);
    return container;
}

// API helper functions
async function apiCall(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
    };

    const response = await fetch(url, { ...defaultOptions, ...options });

    if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
}

// Form validation helpers
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validatePassword(password) {
    return password.length >= 8;
}

// Loading state management
function showLoading(element) {
    element.disabled = true;
    element.dataset.originalText = element.innerHTML;
    element.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
}

function hideLoading(element) {
    element.disabled = false;
    element.innerHTML = element.dataset.originalText || element.innerHTML;
}

// Confirmation dialogs
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Persona card toggle (used in personas.html)
function togglePersona(card, personaName) {
    const checkbox = card.querySelector('input[type="checkbox"]');
    checkbox.checked = !checkbox.checked;
    card.classList.toggle('selected', checkbox.checked);
}

// OTP input auto-focus and format
function initOtpInput(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;

    input.focus();

    input.addEventListener('input', function(e) {
        this.value = this.value.replace(/\D/g, '');
        if (this.value.length === 6) {
            this.form.submit();
        }
    });
}

// Password confirmation validation
function initPasswordConfirmation(passwordId, confirmId) {
    const confirmInput = document.getElementById(confirmId);
    const passwordInput = document.getElementById(passwordId);

    if (!confirmInput || !passwordInput) return;

    confirmInput.addEventListener('input', function() {
        if (passwordInput.value !== this.value) {
            this.setCustomValidity('Passwords do not match');
        } else {
            this.setCustomValidity('');
        }
    });
}

// Color picker sync (used in admin config)
function syncColorPicker(pickerId, inputId) {
    const picker = document.getElementById(pickerId);
    const input = document.getElementById(inputId);

    if (!picker || !input) return;

    picker.addEventListener('change', () => input.value = picker.value);
    input.addEventListener('change', () => picker.value = input.value);
}

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const closeBtn = alert.querySelector('.btn-close');
            if (closeBtn) closeBtn.click();
        }, 5000);
    });
});

// Enable Bootstrap tooltips
document.addEventListener('DOMContentLoaded', function() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
