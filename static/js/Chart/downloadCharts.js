function downloadApexChart(chartInstance, chartTitle, filterDesc, filename) {
  if (!chartInstance) {
    console.error("Chart instance not found for:", chartTitle);
    return;
  }
  
  // Get the base64 image from ApexCharts
  chartInstance.dataURI().then(({ imgURI }) => {
    const img = new window.Image();
    img.src = imgURI;
    
    img.onload = function() {
      // Create a canvas to draw the title, filter text, and chart
      const padding = 20;
      const fontSize = 22;
      const filterFontSize = 16;
      const fontFamily = "Inter, Arial, sans-serif";
      
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      // Add extra height for the title and filter text
      canvas.height = img.height + fontSize + filterFontSize + padding;
      
      const ctx = canvas.getContext('2d');

      // 1. Fill background with white
      ctx.fillStyle = "#fff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // 2. Draw Title
      ctx.font = `bold ${fontSize}px ${fontFamily}`;
      ctx.fillStyle = "#22223b";
      ctx.textAlign = "center";
      ctx.fillText(chartTitle, canvas.width / 2, fontSize + 10);

      // 3. Draw Filter Description (e.g., "Last 7 Days")
      ctx.font = `${filterFontSize}px ${fontFamily}`;
      ctx.fillStyle = "#64748b";
      ctx.fillText(filterDesc, canvas.width / 2, fontSize + filterFontSize + 15);

      // 4. Draw the Chart Image
      ctx.drawImage(img, 0, fontSize + filterFontSize + padding);

      // 5. Trigger Download
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
  // Helper to get text content safely
  function getFilterDesc(id) {
    const el = document.getElementById(id);
    return el ? el.textContent : "";
  }

  // 1. Download Visitor Trend
  const trendBtn = document.getElementById("download-timeline-chart");
  if (trendBtn) {
    trendBtn.addEventListener("click", function(e) {
      e.preventDefault();
      downloadApexChart(
        window.visitorTrendChart, 
        "Visitor Trend Over Time",
        getFilterDesc("trend-filter-desc"),
        "visitor_trend_chart.png"
      );
    });
  }

  // 2. Download Top Visitors
  const topVisitorBtn = document.getElementById("download-top-visitor-chart");
  if (topVisitorBtn) {
    topVisitorBtn.addEventListener("click", function(e) {
      e.preventDefault();
      downloadApexChart(
        window.topVisitorChartInstance,
        "Top Visitors",
        getFilterDesc("top-visitor-filter-desc"),
        "top_visitors_chart.png"
      );
    });
  }

  // 3. Download Duration
  const durationBtn = document.getElementById("download-duration-chart");
  if (durationBtn) {
    durationBtn.addEventListener("click", function(e) {
      e.preventDefault();
      downloadApexChart(
        window.durationChartInstance,
        "Visitor Duration",
        getFilterDesc("duration-filter-desc"),
        "visitor_duration_chart.png"
      );
    });
  }

  // 4. 👇 UPDATED: Download Destination Distribution (Replaces Purpose)
  const destBtn = document.getElementById("download-destination-chart");
  if (destBtn) {
    destBtn.addEventListener("click", function(e) {
      e.preventDefault();
      downloadApexChart(
        window.destinationChartInstance, // Uses the new instance name
        "Destination Distribution",
        getFilterDesc("destination-filter-desc"),
        "destination_distribution_chart.png"
      );
    });
  }
});