document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    const icon = themeToggle.querySelector('i');

    // Check saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        body.classList.add('dark-mode');
        icon.classList.replace('fa-moon', 'fa-sun');
    }

    themeToggle.addEventListener('click', () => {
        body.classList.toggle('dark-mode');
        const isDark = body.classList.contains('dark-mode');

        if (isDark) {
            icon.classList.replace('fa-moon', 'fa-sun');
            localStorage.setItem('theme', 'dark');
        } else {
            icon.classList.replace('fa-sun', 'fa-moon');
            localStorage.setItem('theme', 'light');
        }
    });

    // Flash message auto-hide
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // Hamburger Menu Logic
    const hamburger = document.getElementById('hamburger');
    const navLinks = document.getElementById('nav-links');

    if (hamburger) {
        hamburger.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }

    // Budget Alert Modal Logic
    const budgetModal = document.getElementById('budget-modal');
    if (budgetModal) {
        const messageText = budgetModal.getAttribute('data-message');
        if (messageText && sessionStorage.getItem('dismissed_alert_' + messageText) !== 'true') {
            budgetModal.style.display = 'flex';
            // Trigger reflow to ensure CSS transitions apply smoothly
            void budgetModal.offsetWidth;
            budgetModal.classList.add('active');
        }
    }
});

// Modal Close Function
window.closeBudgetModal = function () {
    const modal = document.getElementById('budget-modal');
    if (modal) {
        const messageText = modal.getAttribute('data-message');
        if (messageText) {
            sessionStorage.setItem('dismissed_alert_' + messageText, 'true');
        }
        modal.classList.remove('active');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300); // Wait for fade out
    }
};
