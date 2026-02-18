// Rename to destinationChart.js

let currentDestinationFilter = "Last 7 Days";

function formatDateStr(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function setDestinationFilterDesc(desc) {
  // ⚠️ Make sure your HTML has id="destination-filter-desc"
  const el = document.getElementById("destination-filter-desc");
  if(el) {
      el.textContent = desc;
      currentDestinationFilter = desc;
  }
}

function fetchDestinationChartData(params = {}) {
  // 1. Update URL to new route
  let url = "/api/destination_distribution";
  const query = new URLSearchParams(params).toString();
  if (query) url += "?" + query;

  let filterDesc = "All Time";
  if (params.days) {
    filterDesc = params.days === "7" ? "Last 7 Days" : `Last ${params.days} Days`;
  } else if (params.start_date && params.end_date) {
    filterDesc = `${formatDateStr(params.start_date)} - ${formatDateStr(params.end_date)}`;
  }
  setDestinationFilterDesc(filterDesc);

  fetch(url)
    .then(response => response.json())
    .then(data => {
      // 2. Map 'destination' from JSON
      const destinations = data.map(entry => entry.destination);
      const values = data.map(entry => entry.count);

      const options = {
        chart: {
          type: 'pie',
          height: 300,
          animations: { enabled: true, easing: 'easeinout', speed: 800 }
        },
        series: values,
        labels: destinations, // 3. Use destinations as labels
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

      if (window.destinationChartInstance) {
        window.destinationChartInstance.destroy();
      }
      
      // ⚠️ Make sure your HTML has a div with id="destination-chart"
      const chartEl = document.querySelector('#destination-chart');
      if(chartEl) {
        window.destinationChartInstance = new ApexCharts(chartEl, options);
        window.destinationChartInstance.render();
      }
    });
}

// Listen for global filter event
window.addEventListener("dateFilterChanged", (e) => {
  fetchDestinationChartData(e.detail);
});
