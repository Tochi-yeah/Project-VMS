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