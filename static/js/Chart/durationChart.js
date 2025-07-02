let currentDurationFilter = "Last 7 Days";

function formatDateStr(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function setDurationFilterDesc(desc) {
  document.getElementById("duration-filter-desc").textContent = desc;
  currentDurationFilter = desc;
}

function fetchDurationChartData(params = {}) {
  let url = "/api/visit_durations";
  const query = new URLSearchParams(params).toString();
  if (query) url += "?" + query;

  // Determine filter description (like Top Visitors)
  let filterDesc = "All Time";
  if (params.days) {
    filterDesc = params.days === "7" ? "Last 7 Days" : `Last ${params.days} Days`;
  } else if (params.start_date && params.end_date) {
    filterDesc = `${formatDateStr(params.start_date)} - ${formatDateStr(params.end_date)}`;
  }
  setDurationFilterDesc(filterDesc);

  fetch(url)
    .then(response => response.json())
    .then(data => {
      const durations = data.durations.map(d => Math.round(d.duration_minutes));
      if (durations.length === 0) {
        document.querySelector("#duration-chart").innerHTML = "<div style='text-align:center;color:#888;'>No data for selected range.</div>";
        return;
      }

      const maxDuration = Math.max(...durations);
      const binSize = 5;
      const bins = [];
      for (let i = 0; i <= maxDuration; i += binSize) {
        bins.push(i);
      }

      const histogramData = bins.map((start, index) => {
        const end = start + binSize;
        const count = durations.filter(d => d >= start && d < end).length;
        return { x: `${start}-${end} min`, y: count };
      }).filter(d => d.y > 0);

      const options = {
        chart: { 
          type: 'bar', 
          height: 300, 
          toolbar: { show: false }, 
          animations: { enabled: true, easing: 'easeinout', speed: 800 },
          background: '#ffffff'
        },
        series: [{ name: 'Visitor Count', data: histogramData }],
        xaxis: {
          type: 'category',
          labels: { rotate: -45, style: { fontSize: '12px', colors: '#334155', fontWeight: 500 } },
          axisBorder: { show: true, color: '#cbd5e1' },
          axisTicks: { show: true, color: '#cbd5e1' }
        },
        yaxis: {
          title: { text: 'Number of Visitors', style: { color: '#1e293b', fontSize: '14px', fontWeight: 600 }},
          labels: { 
            style: { colors: '#334155', fontSize: '12px', fontWeight: 500 },
            formatter: val => Math.round(val)
          },
          min: 0,
          forceNiceScale: true
        },
        plotOptions: { 
          bar: { columnWidth: '80%', borderRadius: 4, dataLabels: { position: 'top' } } 
        },
        dataLabels: {
          enabled: true,
          formatter: val => `${val}`,
          offsetY: -20,
          style: { fontSize: '12px', colors: ['#1e293b'], fontWeight: 600 },
          background: { enabled: true, foreColor: '#ffffff', padding: 4, borderRadius: 2, borderWidth: 1, borderColor: '#e5e7eb' }
        },
        colors: ['#2563eb'],
        grid: { borderColor: '#e5e7eb', strokeDashArray: 4, yaxis: { lines: { show: true }} },
        tooltip: { 
          theme: 'light', 
          style: { fontSize: '12px' },
          y: { 
            formatter: (val, { dataPointIndex, w }) => {
              const total = histogramData.reduce((sum, d) => sum + d.y, 0);
              const percentage = ((val / total) * 100).toFixed(1);
              return `${val} visitors (${percentage}%)`;
            },
            title: { formatter: () => 'Visitors:' }
          },
          x: { formatter: val => `Duration: ${val}` }
        },
        fill: { opacity: 0.9 }
      };

      if (window.durationChartInstance) {
        window.durationChartInstance.destroy();
      }
      window.durationChartInstance = new ApexCharts(document.querySelector("#duration-chart"), options);
      window.durationChartInstance.render();
    })
    .catch(error => {
      document.querySelector("#duration-chart").innerHTML = "<div style='text-align:center;color:#e53e3e;'>Failed to load durations.</div>";
      console.error("Failed to load durations:", error);
    });
}

// Listen for global filter event ONLY
window.addEventListener("dateFilterChanged", (e) => {
  fetchDurationChartData(e.detail);
});
