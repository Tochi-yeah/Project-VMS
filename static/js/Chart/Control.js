function getFilterParams() {
  const startDate = document.getElementById("start-date").value;
  const endDate = document.getElementById("end-date").value;
  return { start_date: startDate, end_date: endDate };
}

function setDateInputs(start, end) {
  document.getElementById("start-date").value = start;
  document.getElementById("end-date").value = end;
}

// Set default to last 7 days on DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 6); // last 7 days including today

  const pad = n => n.toString().padStart(2, '0');
  const format = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

  setDateInputs(format(start), format(end));

  // Set the first time-range button as active
  const firstBtn = document.querySelector(".time-range-btn[data-range='7']");
  if (firstBtn) {
    document.querySelectorAll(".time-range-btn").forEach(b => b.classList.remove("active"));
    firstBtn.classList.add("active");
  }

  // Emit global event for default filter
  const filters = { start_date: format(start), end_date: format(end) };
  const event = new CustomEvent("dateFilterChanged", { detail: filters });
  window.dispatchEvent(event);
});

document.querySelector(".apply-btn").addEventListener("click", () => {
  const filters = getFilterParams();
  const event = new CustomEvent("dateFilterChanged", { detail: filters });
  window.dispatchEvent(event);
});

// Add event listeners for time range buttons
document.querySelectorAll(".time-range-btn").forEach(btn => {
  btn.addEventListener("click", function() {
    // Remove active class from all buttons
    document.querySelectorAll(".time-range-btn").forEach(b => b.classList.remove("active"));
    this.classList.add("active");

    const days = parseInt(this.dataset.range, 10);
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - days + 1);

    // Format as yyyy-mm-dd
    const pad = n => n.toString().padStart(2, '0');
    const format = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

    setDateInputs(format(start), format(end));

    // Emit global event
    const filters = { start_date: format(start), end_date: format(end) };
    const event = new CustomEvent("dateFilterChanged", { detail: filters });
    window.dispatchEvent(event);
  });
});