let visitorTrendChart;
let currentTrendFilter = "Last 7 Days";

function formatDateStr(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function setTrendFilterDesc(desc) {
  document.getElementById("trend-filter-desc").textContent = desc;
  currentTrendFilter = desc;
}

function fetchVisitorTrendChartData(params = {}) {
  let url = "/api/visitor_trend";
  const query = new URLSearchParams(params).toString();
  if (query) url += "?" + query;

  // Determine filter description 
  let filterDesc = "All Time";
  if (params.days) {
    filterDesc = params.days === "7" ? "Last 7 Days" : `Last ${params.days} Days`;
  } else if (params.start_date && params.end_date) {
    filterDesc = `${formatDateStr(params.start_date)} - ${formatDateStr(params.end_date)}`;
  }
  setTrendFilterDesc(filterDesc);

  fetch(url)
    .then(response => response.json())
    .then(data => {
      const dates = data.map(entry => entry.date);
      const counts = data.map(entry => entry.count);

      const formattedLabels = dates.map(date => {
        const d = new Date(date);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      });

      const options = {
        chart: {
          type: 'line',
          height: 300,
          toolbar: { show: false }
        },
        series: [{ name: 'Check-Ins', data: counts }],
        xaxis: {
          categories: formattedLabels,
          labels: { rotate: -45, style: { fontSize: '12px', colors: '#64748b' } }
        },
        yaxis: {
          title: { text: 'Check-Ins', style: { fontSize: '14px' } },
          labels: { style: { fontSize: '12px' } }
        },
        stroke: { curve: 'smooth', width: 3 },
        colors: ['#2563eb'],
        tooltip: { theme: 'light' }
      };

      if (window.visitorTrendChart) {
        window.visitorTrendChart.updateOptions(options);
      } else {
        window.visitorTrendChart = new ApexCharts(document.querySelector('#timeline-chart'), options);
        window.visitorTrendChart.render();
      }
    });
}

// Listen for global filter event ONLY (no local buttons here)
window.addEventListener("dateFilterChanged", (e) => {
  fetchVisitorTrendChartData(e.detail);
});