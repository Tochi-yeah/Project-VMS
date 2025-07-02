let currentPurposeFilter = "Last 7 Days";

function formatDateStr(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function setPurposeFilterDesc(desc) {
  document.getElementById("purpose-filter-desc").textContent = desc;
  currentPurposeFilter = desc;
}

function fetchPurposeChartData(params = {}) {
  let url = "/api/purpose_distribution";
  const query = new URLSearchParams(params).toString();
  if (query) url += "?" + query;

  // Determine filter description (same as others)
  let filterDesc = "All Time";
  if (params.days) {
    filterDesc = params.days === "7" ? "Last 7 Days" : `Last ${params.days} Days`;
  } else if (params.start_date && params.end_date) {
    filterDesc = `${formatDateStr(params.start_date)} - ${formatDateStr(params.end_date)}`;
  }
  setPurposeFilterDesc(filterDesc);

  fetch(url)
    .then(response => response.json())
    .then(data => {
      const purposes = data.map(entry => entry.purpose);
      const values = data.map(entry => entry.count);

      const options = {
        chart: {
          type: 'pie',
          height: 300,
          animations: { enabled: true, easing: 'easeinout', speed: 800 }
        },
        series: values,
        labels: purposes,
        colors: [
          '#2563eb', '#10b981', '#f59e0b', '#ef4444', '#a855f7', '#f43f5e',
          '#14b8a6', '#8b5cf6', '#f87171', '#22d3ee', '#eab308', '#4ade80',
          '#fb923c', '#7c3aed', '#ec4899', '#0ea5e9'
        ],
        legend: {
          position: 'bottom',
          fontSize: '12px',
          labels: { colors: '#1e293b' }
        },
        responsive: [{
          breakpoint: 768,
          options: {
            chart: { height: 280 },
            legend: { fontSize: '11px' }
          }
        }]
      };

      if (window.purposeChartInstance) {
        window.purposeChartInstance.destroy();
      }
      window.purposeChartInstance = new ApexCharts(document.querySelector('#purpose-chart'), options);
      window.purposeChartInstance.render();
    });
}

// Listen for global filter event ONLY
window.addEventListener("dateFilterChanged", (e) => {
  fetchPurposeChartData(e.detail);
});
