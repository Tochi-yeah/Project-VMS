document.addEventListener('DOMContentLoaded', function () {
    // Sidebar Toggle
    const sidebar = document.getElementById('sidebar');
    const toggleButton = document.querySelector('.sidebar-toggle');

    if (toggleButton) {
        toggleButton.addEventListener('click', function () {
            sidebar.classList.toggle('collapsed');
            const toggleIcon = document.getElementById('toggle-icon');
            if (toggleIcon) {
                toggleIcon.classList.toggle('fa-chevron-left');
                toggleIcon.classList.toggle('fa-chevron-right');
            }
        });
    }

    // Dropdown Toggle
    window.toggleDropdown = function() {
        const dropdown = document.getElementById('dropdown');
        if (dropdown) dropdown.classList.toggle('show');
    }

    // Mobile Sidebar Toggle
    window.toggleMobileSidebar = function() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.classList.toggle('mobile-open');
    }

    // Click Outside Handler
    window.addEventListener('click', function(e) {
        const dropdown = document.getElementById('dropdown');
        const userAvatar = document.querySelector('.user-avatar');
        const sidebar = document.getElementById('sidebar');
        const mobileMenuBtn = document.querySelector('.mobile-menu-btn');

        if (dropdown && userAvatar && !userAvatar.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.remove('show');
        }

        if (window.innerWidth <= 1024 && sidebar && !sidebar.contains(e.target) && !mobileMenuBtn?.contains(e.target)) {
            sidebar.classList.remove('mobile-open');
        }
    });

    // Resize Handler
    window.addEventListener('resize', function() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar && window.innerWidth > 1024) {
            sidebar.classList.remove('mobile-open');
        }
    });

    // Escape Key Handler
    window.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const dropdown = document.getElementById('dropdown');
            if (dropdown) dropdown.classList.remove('show');
        }
    });

    // Mobile Menu Button (if on Dashboard or similar page)
    if (window.innerWidth <= 1024) {
        const header = document.querySelector('.header');
        if (header && !document.querySelector('.mobile-menu-btn')) {
            const mobileMenuBtn = document.createElement('button');
            mobileMenuBtn.innerHTML = '<i class="fas fa-bars"></i>';
            mobileMenuBtn.className = 'mobile-menu-btn';
            mobileMenuBtn.style.padding = '8px 12px';
            mobileMenuBtn.style.border = 'none';
            mobileMenuBtn.style.background = 'var(--primary-color)';
            mobileMenuBtn.style.color = 'white';
            mobileMenuBtn.style.borderRadius = '8px';
            mobileMenuBtn.style.cursor = 'pointer';
            mobileMenuBtn.style.marginRight = '12px';
            mobileMenuBtn.onclick = window.toggleMobileSidebar;
            header.insertBefore(mobileMenuBtn, header.firstChild);
        }
    }
});