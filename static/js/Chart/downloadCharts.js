function downloadApexChart(chartInstance, chartTitle, filterDesc, filename) {
  if (!chartInstance) return;
  chartInstance.dataURI().then(({ imgURI }) => {
    const img = new window.Image();
    img.src = imgURI;
    img.onload = function() {
      const padding = 20;
      const fontSize = 22;
      const filterFontSize = 16;
      const fontFamily = "Inter, Arial, sans-serif";
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height + fontSize + filterFontSize + padding;
      const ctx = canvas.getContext('2d');

      ctx.fillStyle = "#fff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.font = `bold ${fontSize}px ${fontFamily}`;
      ctx.fillStyle = "#22223b";
      ctx.textAlign = "center";
      ctx.fillText(chartTitle, canvas.width / 2, fontSize + 2);

      ctx.font = `${filterFontSize}px ${fontFamily}`;
      ctx.fillStyle = "#64748b";
      ctx.fillText(filterDesc, canvas.width / 2, fontSize + filterFontSize + 6);

      ctx.drawImage(img, 0, fontSize + filterFontSize + padding / 2);

      const link = document.createElement('a');
      link.href = canvas.toDataURL("image/png");
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    };
  });
}

document.addEventListener("DOMContentLoaded", () => {
  // Helper to get filter description by id
  function getFilterDesc(id) {
    const el = document.getElementById(id);
    return el ? el.textContent : "";
  }

  // Download Visitor Trend
  document.getElementById("download-timeline-chart").addEventListener("click", function(e) {
    e.preventDefault();
    downloadApexChart(
      window.visitorTrendChart, // Make sure this is set in your chart script!
      "Visitor Trend Over Time",
      getFilterDesc("trend-filter-desc"),
      "visitor_trend_chart.png"
    );
  });

  // Download Top Visitors
  document.getElementById("download-top-visitor-chart").addEventListener("click", function(e) {
    e.preventDefault();
    downloadApexChart(
      window.topVisitorChartInstance,
      "Top Visitors",
      getFilterDesc("top-visitor-filter-desc"),
      "top_visitors_chart.png"
    );
  });

  // Download Duration
  document.getElementById("download-duration-chart").addEventListener("click", function(e) {
    e.preventDefault();
    downloadApexChart(
      window.durationChartInstance,
      "Visitor Duration",
      getFilterDesc("duration-filter-desc"),
      "visitor_duration_chart.png"
    );
  });

  // Download Purpose
  document.getElementById("download-purpose-chart").addEventListener("click", function(e) {
    e.preventDefault();
    downloadApexChart(
      window.purposeChartInstance,
      "Purpose Distribution",
      getFilterDesc("purpose-filter-desc"),
      "purpose_distribution_chart.png"
    );
  });

  // Download Approve/Reject
  document.getElementById("download-request-chart").addEventListener("click", function(e) {
    e.preventDefault();
    downloadApexChart(
      window.approveRejectChartInstance,
      "Approved and Rejected Requests",
      getFilterDesc("request-filter-desc"),
      "request_status_chart.png"
    );
  });
});