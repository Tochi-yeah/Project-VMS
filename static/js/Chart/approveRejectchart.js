let currentApproveRejectFilter = "Last 7 Days";

function formatDateStr(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function setApproveRejectFilterDesc(desc) {
  document.getElementById("request-filter-desc").textContent = desc;
  currentApproveRejectFilter = desc;
}

function fetchApproveRejectChartData(params = {}) {
  let url = "/api/request_status_distribution";
  const query = new URLSearchParams(params).toString();
  if (query) url += "?" + query;

  // Determine filter description (same as others)
  let filterDesc = "All Time";
  if (params.days) {
    filterDesc = params.days === "7" ? "Last 7 Days" : `Last ${params.days} Days`;
  } else if (params.start_date && params.end_date) {
    filterDesc = `${formatDateStr(params.start_date)} - ${formatDateStr(params.end_date)}`;
  }
  setApproveRejectFilterDesc(filterDesc);

  fetch(url)
    .then(response => response.json())
    .then(data => {
      const labels = data.map(item => item.status);
      const series = data.map(item => item.count);

      const options = {
        chart: {
          type: 'pie',
          height: 300,
          animations: { enabled: true, easing: 'easeinout', speed: 800 }
        },
        series: series,
        labels: labels,
        colors: ['#10b981', '#ef4444', '#3b82f6', '#f59e0b'],
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

      if (window.approveRejectChartInstance) {
        window.approveRejectChartInstance.destroy();
      }
      window.approveRejectChartInstance = new ApexCharts(document.querySelector('#request-chart'), options);
      window.approveRejectChartInstance.render();
    })
    .catch(error => {
      console.error("Failed to fetch request status distribution:", error);
    });
}

// Listen for global filter event ONLY
window.addEventListener("dateFilterChanged", (e) => {
  fetchApproveRejectChartData(e.detail);
});
