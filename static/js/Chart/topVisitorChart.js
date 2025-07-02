let currentTopVisitorFilter = "Last 7 Days";

function formatDateStr(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function setTopVisitorFilterDesc(desc) {
  document.getElementById("top-visitor-filter-desc").textContent = desc;
  currentTopVisitorFilter = desc;
}

function fetchTopVisitorChartData(params = {}) {
  let url = "/api/top_visitors";
  const query = new URLSearchParams(params).toString();
  if (query) url += "?" + query;

  // Determine filter description (unified logic)
  let filterDesc = "All Time";
  if (params.days) {
    filterDesc = params.days === "7" ? "Last 7 Days" : `Last ${params.days} Days`;
  } else if (params.start_date && params.end_date) {
    filterDesc = `${formatDateStr(params.start_date)} - ${formatDateStr(params.end_date)}`;
  }
  setTopVisitorFilterDesc(filterDesc);

  fetch(url)
    .then(response => response.json())
    .then(data => {
      const names = data.map(entry => entry.name);
      const counts = data.map(entry => entry.count);

      const options = {
        chart: {
          type: 'bar',
          height: 300,
          toolbar: { show: false },
          animations: { enabled: true, easing: 'easeinout', speed: 800 }
        },
        series: [{ name: 'Check-Ins', data: counts }],
        xaxis: {
          categories: names,
          labels: { rotate: -45, style: { fontSize: '12px', colors: '#64748b' } }
        },
        yaxis: {
          title: { text: 'Number of Check-Ins', style: { fontSize: '14px' } },
          labels: { style: { fontSize: '12px' } }
        },
        plotOptions: {
          bar: { columnWidth: '50%', borderRadius: 4 }
        },
        colors: ['#2563eb'],
        grid: { borderColor: '#e5e7eb', strokeDashArray: 4 },
        tooltip: { theme: 'light' }
      };

      if (window.topVisitorChartInstance) {
        window.topVisitorChartInstance.destroy();
      }
      window.topVisitorChartInstance = new ApexCharts(document.querySelector('#visitor-chart'), options);
      window.topVisitorChartInstance.render();
    });
}

// Listen for global date filter event ONLY
window.addEventListener("dateFilterChanged", (e) => {
  fetchTopVisitorChartData(e.detail);
});


