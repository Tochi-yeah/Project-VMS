// In static/js/modal/global.js

// ADD THIS CODE AT THE TOP OF THE FILE
document.addEventListener('DOMContentLoaded', () => {
    // Look for any flashed messages rendered by the server
    const flashMessage = document.querySelector('.flash-message');
    
    if (flashMessage) {
        const message = flashMessage.dataset.message;
        const category = flashMessage.dataset.category;

        // Use the category to determine the notification type ('success' or 'error')
        const notificationType = (category === 'danger' || category === 'error') ? 'error' : 'success';

        // Display the message using our global notification function
        showNotification(message, notificationType);
    }
});

function showNotification(message, type = 'success') {
  const notification = document.getElementById("notification");
  notification.textContent = message;
  notification.style.backgroundColor = type === 'error' ? 'var(--danger-color)' : 'var(--success-color)';
  notification.style.display = "block";

  setTimeout(() => {
    notification.style.display = "none";
  }, 3000);
}

// --- ADD THIS CODE TO THE END OF static/js/global.js ---

(function() {
    let scanBuffer = '';
    let scanTimeout = null;
    const SCAN_TIMEOUT_MS = 100; // Time (ms) between keystrokes

    document.addEventListener('keydown', function(e) {
        
        // 1. First, check if the user is busy typing in a form.
        // If they are, we must NOT intercept their typing.
        const activeEl = document.activeElement;
        const isTyping = activeEl && (
            activeEl.tagName === 'INPUT' || 
            activeEl.tagName === 'SELECT' || 
            activeEl.tagName === 'TEXTAREA' ||
            activeEl.isContentEditable
        );

        if (isTyping) {
            // User is typing in a field, so this is NOT a global scan.
            return;
        }

        // 2. If 'Enter' is pressed, it's the end of the scan.
        if (e.key === 'Enter') {
            if (scanBuffer.length > 3) { // A good minimum length for a code
                e.preventDefault(); // Stop 'Enter' from doing anything else

                // Check if our global function from Check-in-modal.js exists
                if (typeof handleCodeSubmit === 'function') {
                    console.log('Global scan detected:', scanBuffer);
                    handleCodeSubmit(scanBuffer);
                }
                scanBuffer = ''; // Clear buffer
            }
        } 
        // 3. If a normal character is pressed, add it to our buffer
        else if (e.key.length === 1 && e.key.match(/[a-zA-Z0-9]/)) {
            e.preventDefault(); // Stop the key from scrolling, etc.
            scanBuffer += e.key;
        } 
        // Any other key (like Tab, Shift, etc.) is ignored or resets buffer
        else if (e.key !== 'Shift' && e.key !== 'Control' && e.key !== 'Alt') {
             scanBuffer = '';
        }

        // 4. Set a timeout to clear the buffer.
        // A real scanner is fast. If keys are typed slowly,
        // this timeout will clear the buffer, ignoring stray key presses.
        if (scanTimeout) {
            clearTimeout(scanTimeout);
        }
        scanTimeout = setTimeout(() => {
            scanBuffer = '';
        }, SCAN_TIMEOUT_MS);
    });
})();