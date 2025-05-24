/**
 * Enhanced Responsive JavaScript for DevERP Inventory
 * Adds device-aware behavior and better responsive handling
 */

// Execute when DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
  // Global variables
  const isMobile = window.innerWidth < 768;
  const isTablet = window.innerWidth >= 768 && window.innerWidth < 992;
  const isLandscape = window.innerHeight < window.innerWidth;
  
  // ===== Device-specific optimizations =====
  function applyDeviceOptimizations() {
    // Set appropriate view based on device
    if (isMobile && !isLandscape) {
      // Small phones in portrait: Always start with card view
      setViewMode('card');
    }
    
    // Optimize modal behavior on mobile
    if (isMobile) {
      optimizeModalsForMobile();
    }
    
    // Handle orientation changes
    handleOrientationChange();
    
    // Set touch-friendly spacing
    if ('ontouchstart' in window) {
      document.body.classList.add('touch-device');
    }
  }
  
  // ===== View Mode Management =====
  function setViewMode(mode) {
    const cardView = document.getElementById('card-view');
    const tableView = document.getElementById('table-view');
    const toggleBtn = document.getElementById('toggleViewBtn');
    const toggleBtnText = document.getElementById('toggleBtnText');
    
    if (!cardView || !tableView || !toggleBtn || !toggleBtnText) return;
    
    if (mode === 'card') {
      // Switch to card view
      cardView.classList.remove('d-none');
      tableView.classList.add('d-none');
      toggleBtnText.textContent = 'Table View';
      toggleBtn.querySelector('i').classList.remove('bi-grid');
      toggleBtn.querySelector('i').classList.add('bi-table');
      
      // Store preference
      localStorage.setItem('preferredViewMode', 'card');
    } else {
      // Switch to table view
      cardView.classList.add('d-none');
      tableView.classList.remove('d-none');
      toggleBtnText.textContent = 'Card View';
      toggleBtn.querySelector('i').classList.remove('bi-table');
      toggleBtn.querySelector('i').classList.add('bi-grid');
      
      // Store preference
      localStorage.setItem('preferredViewMode', 'table');
    }
  }
  
  // ===== Mobile-Optimized Modals =====
  function optimizeModalsForMobile() {
    // Make modals more mobile-friendly
    const allModals = document.querySelectorAll('.modal');
    
    allModals.forEach(modal => {
      // Ensure modals are vertically centered
      const modalDialog = modal.querySelector('.modal-dialog');
      if (modalDialog && !modalDialog.classList.contains('modal-dialog-centered')) {
        modalDialog.classList.add('modal-dialog-centered');
      }
      
      // Add bottom sheet style on very small screens
      if (window.innerHeight < 600) {
        modalDialog.classList.add('modal-dialog-bottom');
      }
    });
    
    // Add swipe-to-close functionality for modals
    addSwipeToCloseModals();
  }
  
  // ===== Add swipe down to close modals on touch devices =====
  function addSwipeToCloseModals() {
    if (!('ontouchstart' in window)) return;
    
    const modals = document.querySelectorAll('.modal');
    
    modals.forEach(modal => {
      let startY = 0;
      let currentY = 0;
      
      modal.addEventListener('touchstart', function(e) {
        const modalHeader = modal.querySelector('.modal-header');
        // Only allow swiping from the header
        if (e.target.closest('.modal-header')) {
          startY = e.touches[0].clientY;
          modalHeader.style.transition = 'none';
        }
      }, { passive: true });
      
      modal.addEventListener('touchmove', function(e) {
        const modalHeader = modal.querySelector('.modal-header');
        const modalContent = modal.querySelector('.modal-content');
        
        if (e.target.closest('.modal-header') && startY > 0) {
          currentY = e.touches[0].clientY;
          const diffY = currentY - startY;
          
          if (diffY > 0) { // Only allow downward swipe
            modalContent.style.transform = `translateY(${diffY}px)`;
            modalContent.style.opacity = 1 - (diffY / 400);
          }
        }
      }, { passive: true });
      
      modal.addEventListener('touchend', function(e) {
        const modalContent = modal.querySelector('.modal-content');
        
        if (startY > 0) {
          const diffY = currentY - startY;
          
          modalContent.style.transition = 'transform 0.3s, opacity 0.3s';
          
          if (diffY > 100) { // Threshold to close the modal
            modalContent.style.transform = 'translateY(100%)';
            modalContent.style.opacity = '0';
            
            // Close the modal after animation
            setTimeout(() => {
              const modalInstance = bootstrap.Modal.getInstance(modal);
              if (modalInstance) {
                modalInstance.hide();
              }
              
              // Reset styles
              modalContent.style.transform = '';
              modalContent.style.opacity = '';
              modalContent.style.transition = '';
            }, 300);
          } else {
            // Reset position if not enough to close
            modalContent.style.transform = '';
            modalContent.style.opacity = '';
            
            setTimeout(() => {
              modalContent.style.transition = '';
            }, 300);
          }
          
          startY = 0;
          currentY = 0;
        }
      }, { passive: true });
    });
  }
  
  // ===== Handle Orientation Changes =====
  function handleOrientationChange() {
    window.addEventListener('orientationchange', function() {
      // Wait for orientation to complete
      setTimeout(() => {
        const isNewLandscape = window.innerHeight < window.innerWidth;
        
        // Adjust UI based on new orientation
        if (isNewLandscape) {
          // Optimize for landscape mode
          optimizeForLandscape();
        } else {
          // Reset to portrait optimizations
          optimizeForPortrait();
        }
        
        // Re-apply lazy loading for newly visible elements
        initLazyLoading();
      }, 300);
    });
  }
  
  // Landscape optimizations
  function optimizeForLandscape() {
    // For small screens in landscape, use a more compact layout
    if (window.innerWidth < 992) {
      document.body.classList.add('landscape-mode');
      
      // Close any open modals when rotating to landscape on small screens
      if (window.innerHeight < 500) {
        const openModals = document.querySelectorAll('.modal.show');
        openModals.forEach(modal => {
          const modalInstance = bootstrap.Modal.getInstance(modal);
          if (modalInstance) {
            modalInstance.hide();
          }
        });
      }
    }
  }
  
  // Portrait optimizations
  function optimizeForPortrait() {
    document.body.classList.remove('landscape-mode');
  }
  
  // ===== Improve Card Grid Responsiveness =====
  function updateCardGrid() {
    const cardView = document.getElementById('card-view');
    if (!cardView) return;
    
    const width = window.innerWidth;
    const isLandscape = window.innerHeight < window.innerWidth;
    
    // Adjust card columns based on screen size and orientation
    if (width < 576) {
      // Extra small screens
      if (isLandscape) {
        // 3 cards per row in landscape on phones
        adjustCardColumns(cardView, 'col-4', ['col-6', 'col-md-4', 'col-lg-3']);
      } else {
        // 2 cards per row in portrait on phones (default)
      }
    } else if (width >= 1600) {
      // Extra large screens - show 6 cards per row
      adjustCardColumns(cardView, 'col-2', ['col-6', 'col-md-4', 'col-lg-3', 'col-4']);
    }
  }
  
  function adjustCardColumns(container, newClass, oldClasses) {
    const cards = container.querySelectorAll('.col-6, .col-md-4, .col-lg-3, .col-4, .col-2');
    
    cards.forEach(card => {
      // Remove old classes
      oldClasses.forEach(cls => {
        card.classList.remove(cls);
      });
      
      // Add new class
      card.classList.add(newClass);
    });
  }
  
  // ===== Improve Table Responsiveness =====
  function enhanceTableResponsiveness() {
    const tables = document.querySelectorAll('.table-responsive table');
    
    tables.forEach(table => {
      // Add data attributes to cells for mobile display
      const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
      
      table.querySelectorAll('tbody tr').forEach(row => {
        row.querySelectorAll('td').forEach((cell, index) => {
          if (headers[index]) {
            cell.setAttribute('data-label', headers[index]);
          }
        });
      });
    });
  }
  
  // ===== Improved Lazy Loading with Intersection Observer =====
  function initLazyLoading() {
    const lazyImages = document.querySelectorAll("img.lazy:not([data-loaded='true'])");
    
    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            if (img.dataset.src && !img.dataset.loaded) {
              // Preload image
              const preloadImg = new Image();
              preloadImg.onload = function() {
                img.src = img.dataset.src;
                img.classList.add('loaded');
                img.dataset.loaded = "true";
                img.classList.remove("lazy");
              };
              preloadImg.onerror = function() {
                // If image fails to load, use placeholder
                img.src = "{% static 'inventory/placeholder.jpg' %}";
                img.dataset.loaded = "true";
                img.classList.remove("lazy");
              };
              preloadImg.src = img.dataset.src;
              
              observer.unobserve(img);
            }
          }
        });
      }, {
        rootMargin: '50px 0px',
        threshold: 0.01
      });
      
      lazyImages.forEach(img => imageObserver.observe(img));
    } else {
      // Fallback for browsers without IntersectionObserver
      lazyImages.forEach(img => {
        if (img.dataset.src) {
          img.src = img.dataset.src;
          img.dataset.loaded = "true";
          img.classList.remove("lazy");
        }
      });
    }
  }
  
  // ===== Restore user's view preference =====
  function restoreUserPreferences() {
    // Restore view mode preference
    const preferredViewMode = localStorage.getItem('preferredViewMode');
    if (preferredViewMode && !isMobile) {
      setViewMode(preferredViewMode);
    }
  }
  
  // ===== Initialization =====
  function init() {
    // Apply device-specific optimizations
    applyDeviceOptimizations();
    
    // Update card grid for current screen size
    updateCardGrid();
    
    // Enhance table responsiveness
    enhanceTableResponsiveness();
    
    // Initialize lazy loading
    initLazyLoading();
    
    // Restore user preferences
    restoreUserPreferences();
    
    // Listen for window resize events
    window.addEventListener('resize', debounce(function() {
      updateCardGrid();
    }, 250));
  }
  
  // Debounce function for resize event
  function debounce(func, wait) {
    let timeout;
    return function(...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }
  
  // Start initialization
  init();
});

/**
 * Adjusts modal image carousel for device and orientation
 * @param {string} designNo - Product design number
 * @param {string} color - Selected color (White, Yellow, Rose)
 * @param {string} modalId - Modal identifier
 */
function optimizeImageCarousel(designNo, color, modalId) {
  const carouselInner = document.getElementById(`carousel-inner-${modalId}`);
  if (!carouselInner) return;
  
  // Base URL for images
  const baseUrl = `https://dev-jewels.s3.us-east-2.amazonaws.com/products/${designNo}/${color}/`;
  
  // Determine if we're on a mobile device
  const isMobile = window.innerWidth < 768;
  
  // Image file patterns to try - limit number of images on mobile to improve performance
  const patterns = isMobile ? 
    [{ prefix: 'D_', suffix: '-1.jpg' }, { prefix: 'H_', suffix: '-2.jpg' }] : 
    [
      { prefix: 'D_', suffix: '-1.jpg' },
      { prefix: 'H_', suffix: '-2.jpg' },
      { prefix: '', suffix: '-3.jpg' },
      { prefix: '', suffix: '-4.jpg' }
    ];
  
  // Generate carousel items HTML
  let html = '';
  patterns.forEach((pattern, idx) => {
    html += `
      <div class="carousel-item ${idx === 0 ? 'active' : ''}">
        <img src="${baseUrl}${pattern.prefix}${designNo}${pattern.suffix}" 
          class="modal-carousel-img d-inline-block" 
          alt="${designNo} ${color} ${idx + 1}"
          onerror="this.onerror=null;this.src='{% static 'inventory/placeholder.jpg' %}';">
      </div>
    `;
  });
  
  carouselInner.innerHTML = html;
  
  // Add swipe support for mobile
  if (isMobile && 'ontouchstart' in window) {
    addSwipeSupport(`carousel-${modalId}`);
  }
}

/**
 * Adds swipe support for carousels on mobile
 * @param {string} carouselId - Carousel identifier
 */
function addSwipeSupport(carouselId) {
  const carousel = document.getElementById(carouselId);
  if (!carousel) return;
  
  let startX = 0;
  let startTime = 0;
  
  carousel.addEventListener('touchstart', function(e) {
    startX = e.touches[0].clientX;
    startTime = new Date().getTime();
  }, { passive: true });
  
  carousel.addEventListener('touchend', function(e) {
    const endX = e.changedTouches[0].clientX;
    const endTime = new Date().getTime();
    const diffX = endX - startX;
    const diffTime = endTime - startTime;
    
    // Only trigger if swipe was fast enough and long enough
    if (diffTime < 300 && Math.abs(diffX) > 50) {
      const carouselInstance = bootstrap.Carousel.getInstance(carousel);
      
      if (diffX > 0) {
        // Swipe right, go to previous
        carouselInstance.prev();
      } else {
        // Swipe left, go to next
        carouselInstance.next();
      }
    }
  }, { passive: true });
}

// Override the original color button click handler
document.addEventListener('click', function(e) {
  const colorBtn = e.target.closest('.color-btn');
  if (colorBtn) {
    // Remove active class from all siblings
    const buttons = colorBtn.parentNode.querySelectorAll('.color-btn');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    // Add active class to clicked button
    colorBtn.classList.add('active');
    
    const designNo = colorBtn.getAttribute('data-design');
    const color = colorBtn.getAttribute('data-color');
    const modalId = colorBtn.getAttribute('data-modal');
    
    // Use the optimized carousel function
    optimizeImageCarousel(designNo, color, modalId);
  }
});