const codeForm = document.getElementById("code-form");
const codeInput = document.getElementById("code-input");
const resultDisplay = document.getElementById("result-display");

let cooldown = false;

codeForm.addEventListener("submit", (e) => {
  e.preventDefault();

  if (cooldown) return;
  cooldown = true;

  const code = codeInput.value.trim();
  if (!code) {
    cooldown = false;
    return;
  }

  fetch("/scan-checkin", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin", 
    body: JSON.stringify({ qr_data: code })
  })
  .then(res => res.json())
  .then(data => {
    resultDisplay.textContent = data.message;
    resultDisplay.className = "result-display success";
    showNotification(data.message);
  })
  .catch(err => {
    console.error("Error:", err);
    resultDisplay.textContent = "An error occurred.";
    resultDisplay.className = "result-display error";
    showNotification("An error occurred.", 'error');
  })
  .finally(() => {
    codeInput.value = "";
    codeInput.focus();
    setTimeout(() => { cooldown = false; }, 2000);
  });
});

// Autofocus on load
window.addEventListener("DOMContentLoaded", () => {
  codeInput.focus();
});

// Notification function
function showNotification(message, type = 'success') {
  const notification = document.getElementById("notification");
  notification.textContent = message;
  notification.style.backgroundColor = type === 'error' ? 'var(--danger-color)' : 'var(--success-color)';
  notification.style.display = "block";

  setTimeout(() => {
    notification.style.display = "none";
  }, 3000);
}
