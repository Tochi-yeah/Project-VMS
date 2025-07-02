document.addEventListener('DOMContentLoaded', function() {
  // Find all tab links and all settings sections
  const tabLinks = document.querySelectorAll('.tab-link');
  const sections = document.querySelectorAll('.settings-section');

  if (!tabLinks.length || !sections.length) return;

  tabLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      // Remove active from all links
      tabLinks.forEach(l => l.classList.remove('active'));
      this.classList.add('active');
      // Hide all sections
      sections.forEach(sec => sec.classList.remove('active'));
      // Show selected section
      const tab = this.getAttribute('data-tab');
      const section = document.getElementById(tab + '-section');
      if (section) section.classList.add('active');
    });
  });

  // Show the first section by default
  sections.forEach((sec, idx) => {
    if (idx === 0) sec.classList.add('active');
    else sec.classList.remove('active');
  });
});