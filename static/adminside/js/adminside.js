document.addEventListener('DOMContentLoaded', function() {
    // Sidebar Toggle Functionality
    const sidebarCollapseBtn = document.getElementById('sidebarCollapseBtn');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const body = document.body;
    
    // Function to detect screen size
    function isSmallScreen() {
      return window.innerWidth < 768;
    }
    
    // Toggle sidebar for larger screens (collapse/expand)
    if (sidebarCollapseBtn) {
      sidebarCollapseBtn.addEventListener('click', function() {
        body.classList.toggle('sidebar-collapsed');
        
        // Save state to localStorage
        localStorage.setItem('sidebar-collapsed', body.classList.contains('sidebar-collapsed'));
      });
    }
    
    // Toggle sidebar for mobile (show/hide)
    if (sidebarToggle) {
      sidebarToggle.addEventListener('click', function() {
        body.classList.remove('sidebar-open');
      });
    }
    
    // Show sidebar on mobile when hamburger is clicked
    document.querySelector('.sidebar-toggle.d-md-none')?.addEventListener('click', function() {
      body.classList.add('sidebar-open');
    });
    
    // Load saved sidebar state
    const savedState = localStorage.getItem('sidebar-collapsed');
    if (savedState === 'true' && !isSmallScreen()) {
      body.classList.add('sidebar-collapsed');
    }
    
    // Handle window resize
    window.addEventListener('resize', function() {
      if (isSmallScreen()) {
        body.classList.remove('sidebar-collapsed');
        body.classList.remove('sidebar-open');
      } else {
        // Reapply saved state for larger screens
        const savedState = localStorage.getItem('sidebar-collapsed');
        if (savedState === 'true') {
          body.classList.add('sidebar-collapsed');
        } else if (savedState === 'false') {
          body.classList.remove('sidebar-collapsed');
        }
      }
    });
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
      const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
      tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
      });
    }
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
      if (!e.target.closest('.dropdown-menu') && !e.target.closest('.dropdown-toggle')) {
        document.querySelectorAll('.dropdown-menu.show').forEach(function(dropdown) {
          bootstrap.Dropdown.getInstance(dropdown.previousElementSibling).hide();
        });
      }
    });
    
    // Active link highlighting based on current page
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(function(link) {
      if (link.getAttribute('href') && currentPath.includes(link.getAttribute('href'))) {
        link.classList.add('active');
      }
    });
    
    // Form validation styles for Bootstrap
    document.querySelectorAll('form.needs-validation').forEach(function(form) {
      form.addEventListener('submit', function(event) {
        if (!form.checkValidity()) {
          event.preventDefault();
          event.stopPropagation();
        }
        
        form.classList.add('was-validated');
      }, false);
    });
    
    // Auto-hide alerts after 5 seconds
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(function(alert) {
      setTimeout(function() {
        if (alert && bootstrap.Alert) {
          const bsAlert = new bootstrap.Alert(alert);
          bsAlert.close();
        }
      }, 5000);
    });
  });