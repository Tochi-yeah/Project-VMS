// Get all the elements we need to work with
const modal = document.getElementById('checkinModal');
const codeForm = document.getElementById('code-form');
const codeInput = document.getElementById('code-input');
const resultDisplay = document.getElementById('result-display'); // This will be null on pages other than Request.html

const modalCheckinForm = document.getElementById('modalCheckinForm');
const modalVisitorName = document.getElementById('modalVisitorName');
const modalUniqueCodeInput = document.getElementById('modalUniqueCode');
const csrfToken = document.getElementById('csrf_token').value;

const modalPurposeSelect = document.getElementById('modalPurposeSelect');
const modalOtherPurposeContainer = document.getElementById('modalOtherPurposeContainer');
const modalOtherPurposeInput = document.getElementById('modalOtherPurposeInput');

// ✅ NEW: Get the Destination Dropdown
const modalDestinationSelect = document.getElementById('modalDestinationSelect');

// --- Main function to handle ANY code submission ---
async function handleCodeSubmit(code, purpose = null, destination = null) {
    
    // Only update resultDisplay if it exists on the page
    if (resultDisplay) {
        resultDisplay.textContent = 'Processing...';
        resultDisplay.className = 'result-display';
    }

    try {
        const response = await fetch('/scan-checkin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                qr_data: code,
                purpose: purpose,
                destination: destination // ✅ Send destination to backend
            })
        });

        const data = await response.json();

        if (response.ok) {
            if (data.action === 'show_modal') {
                // Modal elements are global, so these are safe
                modalVisitorName.textContent = data.name;
                modalUniqueCodeInput.value = code;

                // 1. Handle Purpose Pre-fill
                const options = Array.from(modalPurposeSelect.options).map(opt => opt.value);
                if (data.purpose && options.includes(data.purpose)) {
                    modalPurposeSelect.value = data.purpose;
                    modalOtherPurposeContainer.style.display = 'none';
                    modalOtherPurposeInput.value = '';
                } else if (data.purpose) {
                    modalPurposeSelect.value = 'Other';
                    modalOtherPurposeContainer.style.display = 'block';
                    modalOtherPurposeInput.value = data.purpose;
                } else {
                    modalPurposeSelect.value = '';
                    modalOtherPurposeContainer.style.display = 'none';
                    modalOtherPurposeInput.value = '';
                }

                // ✅ 2. Handle Destination Pre-fill
                if (data.destination) {
                    modalDestinationSelect.value = data.destination;
                } else {
                    modalDestinationSelect.value = ""; // Reset to default
                }

                openModal();
                
                if (resultDisplay) {
                    resultDisplay.textContent = `Please confirm details for ${data.name}.`;
                }
            } else {
                // Success message
                if (resultDisplay) {
                    resultDisplay.textContent = data.message;
                    resultDisplay.classList.add('success');
                }
                if (codeInput) {
                    codeInput.value = '';
                }
                showNotification(data.message); 
            }
        } else {
            // Error handling
            if (resultDisplay) {
                resultDisplay.textContent = data.message || 'An error occurred.';
                resultDisplay.classList.add('error');
            }
            showNotification(data.message || 'An error occurred.', 'error');
        }

    } catch (error) {
        console.error('Error during submission:', error);
        
        if (resultDisplay) {
            resultDisplay.textContent = 'A network error occurred.';
            resultDisplay.classList.add('error');
        }
        showNotification('A network error occurred.', 'error');
    }
}


// --- Event Listeners ---

// Only add this listener if the manual code-form exists on the page
if (codeForm) {
    codeForm.addEventListener('submit', (event) => {
        event.preventDefault();
        const code = codeInput.value.trim();
        if (code) {
            handleCodeSubmit(code);
        }
    });
}

// This listener is safe because the modal form is global (in base.html)
modalCheckinForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const code = modalUniqueCodeInput.value;
    
    // Get Purpose
    let purpose = modalPurposeSelect.value;
    if (purpose === 'Other') {
        purpose = modalOtherPurposeInput.value.trim();
    }

    // ✅ Get Destination
    const destination = modalDestinationSelect.value;

    // Validate both
    if (code && purpose && destination) {
        closeModal();
        handleCodeSubmit(code, purpose, destination);
    } else {
        alert("Please fill in all fields.");
    }
});


// --- Helper Functions (Unchanged) ---
modalPurposeSelect.addEventListener('change', () => {
    if (modalPurposeSelect.value === 'Other') {
        modalOtherPurposeContainer.style.display = 'block';
        modalOtherPurposeInput.required = true;
    } else {
        modalOtherPurposeContainer.style.display = 'none';
        modalOtherPurposeInput.required = false;
        modalOtherPurposeInput.value = '';
    }
});

function openModal() {
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('show'), 10);
}

function closeModal() {
    modal.classList.remove('show');
    setTimeout(() => modal.style.display = 'none', 300);
}