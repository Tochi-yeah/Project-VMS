// Get all the elements we need to work with
const modal = document.getElementById('checkinModal');
const codeForm = document.getElementById('code-form');
const codeInput = document.getElementById('code-input');
const resultDisplay = document.getElementById('result-display');

const modalCheckinForm = document.getElementById('modalCheckinForm');
const modalVisitorName = document.getElementById('modalVisitorName');
const modalUniqueCodeInput = document.getElementById('modalUniqueCode');
const csrfToken = document.getElementById('csrf_token').value;

const modalPurposeSelect = document.getElementById('modalPurposeSelect');
const modalOtherPurposeContainer = document.getElementById('modalOtherPurposeContainer');
const modalOtherPurposeInput = document.getElementById('modalOtherPurposeInput');

// --- Main function to handle ANY code submission ---
async function handleCodeSubmit(code, purpose = null) {
    resultDisplay.textContent = 'Processing...';
    resultDisplay.className = 'result-display';

    try {
        const response = await fetch('/scan-checkin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                qr_data: code,
                purpose: purpose
            })
        });

        const data = await response.json();

        if (response.ok) {
            if (data.action === 'show_modal') {
                modalVisitorName.textContent = data.name;
                modalUniqueCodeInput.value = code;
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
                openModal();
                resultDisplay.textContent = `Please confirm purpose for ${data.name}.`;
            } else {
                resultDisplay.textContent = data.message;
                resultDisplay.classList.add('success');
                codeInput.value = '';
                // ADD THIS LINE
                showNotification(data.message);
            }
        } else {
            resultDisplay.textContent = data.message || 'An error occurred.';
            resultDisplay.classList.add('error');
            // ADD THIS LINE
            showNotification(data.message || 'An error occurred.', 'error');
        }

    } catch (error) {
        console.error('Error during submission:', error);
        resultDisplay.textContent = 'A network error occurred.';
        resultDisplay.classList.add('error');
        // ADD THIS LINE
        showNotification('A network error occurred.', 'error');
    }
}


// --- Event Listeners ---
codeForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const code = codeInput.value.trim();
    if (code) {
        handleCodeSubmit(code);
    }
});

modalCheckinForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const code = modalUniqueCodeInput.value;
    let purpose = modalPurposeSelect.value;
    if (purpose === 'Other') {
        purpose = modalOtherPurposeInput.value.trim();
    }
    if (code && purpose) {
        closeModal();
        handleCodeSubmit(code, purpose);
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
    modal.style.display = 'none';
    setTimeout(() => modal.classList.remove('show'), 300);
}