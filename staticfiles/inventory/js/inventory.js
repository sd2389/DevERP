/**
 * DevERP Inventory Management JavaScript
 * Optimized for performance with DevJewels API integration
 */

document.addEventListener("DOMContentLoaded", function () {
  // Cache DOM elements for better performance
  const elements = {
    tableView: document.getElementById('table-view'),
    cardView: document.getElementById('card-view'),
    toggleViewBtn: document.getElementById('toggleViewBtn'),
    searchInput: document.getElementById('searchInput'),
    categoryFilter: document.getElementById('categoryFilter'),
    genderFilter: document.getElementById('genderFilter'),
    collectionFilter: document.getElementById('collectionFilter'),
    subcategoryFilter: document.getElementById('subcategoryFilter'),
    producttypeFilter: document.getElementById('producttypeFilter'),
    btnAll: document.getElementById('btn-all'),
    btnInStock: document.getElementById('btn-instock'),
    btnNotInStock: document.getElementById('btn-notinstock'),
    clearFiltersBtn: document.getElementById('clearFiltersBtn'),
    refreshInventoryBtn: document.getElementById('refreshInventoryBtn'),
    loadingOverlay: document.getElementById('loading-overlay'),
    visibleCount: document.getElementById('visibleCount'),
    totalCount: document.getElementById('totalCount'),
    loadingTime: document.getElementById('loadingTime')
  };
  
  // State management
  const state = {
    loading: false,
    currentPage: 1,
    hasMore: true,
    lastScrollPosition: 0,
    scrollDirection: 'down',
    inventory: [],
    filterTimeout: null
  };

  // ===== VIEW TOGGLE FUNCTIONALITY =====
  elements.toggleViewBtn.addEventListener('click', function () {
    const isTableView = !elements.tableView.classList.contains('d-none');

    if (isTableView) {
      elements.tableView.classList.add('d-none');
      elements.cardView.classList.remove('d-none');
      this.innerHTML = '<i class="bi bi-table"></i> Table View';
    } else {
      elements.tableView.classList.remove('d-none');
      elements.cardView.classList.add('d-none');
      this.innerHTML = '<i class="bi bi-grid"></i> Card View';
    }

    // Store view preference in localStorage
    localStorage.setItem('inventory_view_preference', isTableView ? 'card' : 'table');
  });

  // Restore view preference if available
  const viewPreference = localStorage.getItem('inventory_view_preference');
  if (viewPreference === 'card') {
    elements.tableView.classList.add('d-none');
    elements.cardView.classList.remove('d-none');
    elements.toggleViewBtn.innerHTML = '<i class="bi bi-table"></i> Table View';
  }

  // ===== FILTERING FUNCTIONALITY =====
  // Debounce function to limit filtering frequency
  function debounce(func, wait = 200) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Function to load inventory data from API
  function loadInventoryData(page = 1, showLoading = true) {
    if (state.loading) return;
    
    state.loading = true;
    
    // Show loading overlay
    if (showLoading) {
      elements.loadingOverlay.classList.add('d-flex');
      elements.loadingOverlay.classList.remove('d-none');
    }
    
    const startTime = performance.now();
    
    // Build API URL with filters
    const url = new URL('/inventory/api/products/', window.location.origin);
    
    // Add pagination parameters
    url.searchParams.append('page', page);
    url.searchParams.append('per_page', 50);
    
    // Add filter parameters
    const filters = getActiveFilters();
    Object.keys(filters).forEach(key => {
      if (filters[key] && filters[key] !== 'all') {
        url.searchParams.append(key, filters[key]);
      }
    });
    
    // Add search parameter
    if (elements.searchInput && elements.searchInput.value) {
      url.searchParams.append('search', elements.searchInput.value);
    }
    
    // Fetch data from API
    fetch(url.toString())
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        if (!data.success) {
          throw new Error(data.error || 'Unknown error');
        }
        
        // Clear existing items if this is page 1
        if (page === 1) {
          clearInventoryItems();
          state.inventory = [];
        }
        
        // Update state
        state.currentPage = page;
        state.hasMore = page < data.pages;
        
        // Add to state inventory
        state.inventory = state.inventory.concat(data.products);
        
        // Display products
        displayProducts(data.products, page > 1);
        
        // Update counters
        if (elements.visibleCount) {
          elements.visibleCount.textContent = state.inventory.length;
        }
        
        if (elements.totalCount) {
          elements.totalCount.textContent = data.total;
        }
        
        // Calculate and display loading time
        const endTime = performance.now();
        const loadingTime = (endTime - startTime).toFixed(0);
        
        if (elements.loadingTime) {
          elements.loadingTime.textContent = `Loaded in ${loadingTime}ms`;
        }
      })
      .catch(error => {
        console.error('Error loading inventory data:', error);
        showToast('Failed to load inventory data. Please try again.', 'danger');
      })
      .finally(() => {
        // Hide loading overlay
        elements.loadingOverlay.classList.remove('d-flex');
        elements.loadingOverlay.classList.add('d-none');
        
        // Reset loading state
        state.loading = false;
      });
  }
  
  // Clear all inventory items from DOM
  function clearInventoryItems() {
    const tableBody = document.querySelector('#inventory-table tbody');
    if (tableBody) {
      tableBody.innerHTML = '';
    }
    
    const cardView = document.getElementById('card-view');
    if (cardView) {
      cardView.innerHTML = '';
    }
  }
  
  // Display products in both table and card view
  function displayProducts(products, append = false) {
    if (!products || products.length === 0) {
      if (!append) {
        displayEmptyState();
      }
      return;
    }
    
    // Get DOM elements
    const tableBody = document.querySelector('#inventory-table tbody');
    const cardView = document.getElementById('card-view');
    
    // Starting index for new items
    const startIndex = append ? 
      (tableBody ? tableBody.querySelectorAll('tr').length : 0) : 0;
    
    // Create fragments for better performance
    const tableFragment = document.createDocumentFragment();
    const cardFragment = document.createDocumentFragment();
    
    // Process each product
    products.forEach((product, index) => {
      const itemIndex = startIndex + index;
      
      // Create table row
      if (tableBody) {
        const tableRow = createTableRow(product, itemIndex);
        tableFragment.appendChild(tableRow);
      }
      
      // Create card
      if (cardView) {
        const card = createCardItem(product, itemIndex);
        cardFragment.appendChild(card);
      }
    });
    
    // Append to DOM
    if (tableBody) {
      tableBody.appendChild(tableFragment);
    }
    
    if (cardView) {
      cardView.appendChild(cardFragment);
    }
    
    // Initialize lazy loading for new images
    initializeLazyLoad();
  }
  
  // Display empty state when no products are found
  function displayEmptyState() {
    const tableBody = document.querySelector('#inventory-table tbody');
    if (tableBody) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="7" class="text-center py-4">
            <div class="empty-state">
              <i class="bi bi-box"></i>
              <p>No inventory items found.</p>
              <p class="small text-muted">Try adjusting your filters or check back later.</p>
            </div>
          </td>
        </tr>
      `;
    }
    
    const cardView = document.getElementById('card-view');
    if (cardView) {
      cardView.innerHTML = `
        <div class="col-12">
          <div class="empty-state my-5">
            <i class="bi bi-box"></i>
            <p>No inventory items found</p>
            <p class="small text-muted">Try adjusting your filters or check back later.</p>
          </div>
        </div>
      `;
    }
  }
  
  // Create table row for a product
  function createTableRow(product, index) {
    const tr = document.createElement('tr');
    tr.dataset.type = (product.category || '').toLowerCase();
    tr.dataset.gender = (product.gender || '').toLowerCase();
    tr.dataset.collection = (product.collection || '').toLowerCase();
    tr.dataset.subcategory = (product.subcategory || '').toLowerCase();
    tr.dataset.producttype = (product.producttype || '').toLowerCase();
    tr.dataset.status = (product.status || '').toLowerCase();
    
    // Set job numbers for search
    const inStockJobs = product.in_stock_jobs || [];
    const memoJobs = product.memo_jobs || [];
    
    tr.dataset.jobs = inStockJobs.map(job => job.job_no).join(' ');
    tr.dataset.memojobs = memoJobs.map(job => job.job_no).join(' ');
    
    // Get image URL with fallback
    const imageUrl = `https://dev-jewels.s3.us-east-2.amazonaws.com/products/${product.design_no}/White/D_${product.design_no}-1.jpg`;
    
    tr.innerHTML = `
      <td>${index + 1}</td>
      <td>
        <img src="/static/inventory/placeholder.jpg"
          data-src="${imageUrl}"
          class="img-thumbnail lazy" alt="${product.design_no}"
          data-bs-toggle="modal" data-bs-target="#imageModal-${index}">
      </td>
      <td><strong>${product.design_no}</strong></td>
      <td>${product.category || ''}</td>
      <td>
        <a href="#" class="pcs-btn" data-bs-toggle="modal" data-bs-target="#modal-${index}">
          ${product.pcs}
        </a>
      </td>
      <td>
        <span class="badge ${product.pcs > 0 ? 'bg-success' : 'bg-danger'}">
          ${product.status}
        </span>
      </td>
      <td>
        <div class="btn-group">
          <button class="btn btn-sm btn-outline-primary" onclick="addToWishlist('${product.design_no}')" title="Add to Wishlist">
            <i class="bi bi-heart"></i>
          </button>
          <button class="btn btn-sm btn-outline-secondary" data-bs-toggle="modal" data-bs-target="#imageModal-${index}" title="View Images">
            <i class="bi bi-images"></i>
          </button>
        </div>
      </td>
    `;
    
    return tr;
  }
  
  // Create card item for a product
  function createCardItem(product, index) {
    const div = document.createElement('div');
    div.className = 'col-xl-2 col-lg-3 col-md-4 col-sm-6';
    div.dataset.type = (product.category || '').toLowerCase();
    div.dataset.gender = (product.gender || '').toLowerCase();
    div.dataset.collection = (product.collection || '').toLowerCase();
    div.dataset.subcategory = (product.subcategory || '').toLowerCase();
    div.dataset.producttype = (product.producttype || '').toLowerCase();
    div.dataset.status = (product.status || '').toLowerCase();
    
    // Set job numbers for search
    const inStockJobs = product.in_stock_jobs || [];
    div.dataset.jobs = inStockJobs.map(job => job.job_no).join(' ');
    
    // Get image URL with fallback
    const imageUrl = `https://dev-jewels.s3.us-east-2.amazonaws.com/products/${product.design_no}/White/D_${product.design_no}-1.jpg`;
    
    div.innerHTML = `
      <div class="card h-100 shadow-sm inventory-card">
        <div class="card-img-container position-relative">
          <div class="position-absolute top-0 end-0 m-2">
            <button class="btn btn-sm btn-light opacity-75" onclick="addToWishlist('${product.design_no}')" title="Add to Wishlist">
              <i class="bi bi-heart"></i>
            </button>
          </div>
          <img class="card-img-top lazy"
            src="/static/inventory/placeholder.jpg"
            data-src="${imageUrl}"
            alt="${product.design_no}" 
            data-bs-toggle="modal" 
            data-bs-target="#imageModal-${index}">
        </div>

        <div class="card-body">
          <h6 class="card-title">${product.design_no}</h6>
          <p class="mb-1 text-muted small">${product.category || ''}</p>
          <div class="d-flex justify-content-between align-items-center mt-2">
            <a href="#" class="pcs-btn" data-bs-toggle="modal" data-bs-target="#modal-${index}">
              ${product.pcs} pcs
            </a>
            <span class="badge ${product.pcs > 0 ? 'bg-success' : 'bg-danger'}">
              ${product.status}
            </span>
          </div>
        </div>
      </div>
    `;
    
    return div;
  }
  
  // Initialize lazy loading for images
  function initializeLazyLoad() {
    const lazyImages = document.querySelectorAll('img.lazy:not(.loaded)');
    
    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.classList.remove('lazy');
            img.classList.add('loaded');
            obs.unobserve(img);
          }
        });
      }, { rootMargin: '100px 0px', threshold: 0.1 });
      
      lazyImages.forEach(img => imageObserver.observe(img));
    } else {
      // Fallback for browsers without IntersectionObserver
      lazyImages.forEach(img => {
        img.src = img.dataset.src;
        img.classList.remove('lazy');
        img.classList.add('loaded');
      });
    }
  }
  
  // Function to get active filters
  function getActiveFilters() {
    return {
      category: elements.categoryFilter ? elements.categoryFilter.value : 'all',
      gender: elements.genderFilter ? elements.genderFilter.value : 'all',
      collection: elements.collectionFilter ? elements.collectionFilter.value : 'all',
      subcategory: elements.subcategoryFilter ? elements.subcategoryFilter.value : 'all',
      producttype: elements.producttypeFilter ? elements.producttypeFilter.value : 'all',
      status: getActiveStatusFilter()
    };
  }
  
  // Get active status filter
  function getActiveStatusFilter() {
    if (elements.btnInStock && elements.btnInStock.classList.contains('active')) {
      return 'instock';
    }
    if (elements.btnNotInStock && elements.btnNotInStock.classList.contains('active')) {
      return 'notinstock';
    }
    return '';
  }
  
  // Apply filters with debounce
  const applyFilters = debounce(function() {
    // Reset to page 1 for new filter
    state.currentPage = 1;
    state.hasMore = true;
    
    // Load data with filters
    loadInventoryData(1, true);
  }, 300);
  
  // Set up event listeners for filter inputs
  [
    elements.searchInput, 
    elements.categoryFilter, 
    elements.genderFilter, 
    elements.collectionFilter,
    elements.subcategoryFilter, 
    elements.producttypeFilter
  ].forEach(element => {
    if (element) {
      element.addEventListener('input', applyFilters);
    }
  });
  
  // Status filter buttons
  [elements.btnAll, elements.btnInStock, elements.btnNotInStock].forEach(btn => {
    if (btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        
        // Remove active class from all status buttons
        [elements.btnAll, elements.btnInStock, elements.btnNotInStock].forEach(button => {
          if (button) {
            button.classList.remove('active');
          }
        });
        
        // Add active class to clicked button
        this.classList.add('active');
        
        // Apply filters
        applyFilters();
      });
    }
  });
  
  // Clear filters button
  if (elements.clearFiltersBtn) {
    elements.clearFiltersBtn.addEventListener('click', function() {
      // Reset all filters
      if (elements.searchInput) elements.searchInput.value = '';
      if (elements.categoryFilter) elements.categoryFilter.value = 'all';
      if (elements.genderFilter) elements.genderFilter.value = 'all';
      if (elements.collectionFilter) elements.collectionFilter.value = 'all';
      if (elements.subcategoryFilter) elements.subcategoryFilter.value = 'all';
      if (elements.producttypeFilter) elements.producttypeFilter.value = 'all';
      
      // Reset status buttons
      if (elements.btnInStock) elements.btnInStock.classList.remove('active');
      if (elements.btnNotInStock) elements.btnNotInStock.classList.remove('active');
      if (elements.btnAll) elements.btnAll.classList.add('active');
      
      // Apply filters
      applyFilters();
    });
  }
  
  // Refresh button
  if (elements.refreshInventoryBtn) {
    elements.refreshInventoryBtn.addEventListener('click', function() {
      // Force reload data from API
      const url = new URL('/inventory/api/products/', window.location.origin);
      url.searchParams.append('refresh', 'true');
      
      // Show loading overlay
      elements.loadingOverlay.classList.add('d-flex');
      elements.loadingOverlay.classList.remove('d-none');
      
      fetch(url.toString())
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // Reload the current view
            applyFilters();
            showToast('Inventory data refreshed successfully.', 'success');
          } else {
            showToast('Failed to refresh inventory data.', 'danger');
          }
        })
        .catch(error => {
          console.error('Error refreshing inventory:', error);
          showToast('Error refreshing inventory data.', 'danger');
        })
        .finally(() => {
          // Hide loading overlay after a minimum time to avoid flickering
          setTimeout(() => {
            elements.loadingOverlay.classList.remove('d-flex');
            elements.loadingOverlay.classList.add('d-none');
          }, 500);
        });
    });
  }
  
  // Infinite scroll functionality
  window.addEventListener('scroll', debounce(function() {
    // Don't process if already loading or if no more products
    if (state.loading || !state.hasMore) return;
    
    // Calculate scroll position
    const scrollY = window.scrollY || window.pageYOffset;
    const currentScrollDirection = scrollY > state.lastScrollPosition ? 'down' : 'up';
    state.lastScrollPosition = scrollY;
    
    // Only load more when scrolling down
    if (currentScrollDirection !== 'down') return;
    
    // Check if we're near the bottom of the page
    const windowHeight = window.innerHeight;
    const documentHeight = document.documentElement.scrollHeight;
    const scrollPosition = scrollY + windowHeight;
    
    if (documentHeight - scrollPosition <= 200) {
      // Load next page
      loadInventoryData(state.currentPage + 1, false);
    }
  }, 100));
  
  // ===== TOAST NOTIFICATION UTILITY =====
  window.showToast = function(message, type = 'success') {
    const toastEl = document.getElementById('cartToast');
    if (!toastEl) return;
    
    // Set toast style based on type
    toastEl.className = 'toast align-items-center border-0 shadow-lg';
    toastEl.classList.add(`text-bg-${type}`);
    
    // Set message
    const toastBody = toastEl.querySelector('.toast-body');
    if (toastBody) {
      const icon = type === 'success' ? '✅' : 
                  type === 'warning' ? '⚠️' : 
                  type === 'danger' ? '❌' : 'ℹ️';
      toastBody.textContent = `${icon} ${message}`;
    }
    
    // Show toast
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
  };
  
  // ===== WISHLIST FUNCTIONALITY =====
  window.addToWishlist = function(designNo) {
    if (!designNo) return;
    
    // Get CSRF token
    const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
    if (!csrfToken) {
      showToast('CSRF token not found. Please refresh the page and try again.', 'danger');
      return;
    }
    
    // Send request to add to wishlist
    fetch('/inventory/wishlist/add/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ design_no: designNo })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showToast(data.message || 'Item added to wishlist.', 'success');
      } else {
        showToast(data.error || 'Failed to add item to wishlist.', 'danger');
      }
    })
    .catch(error => {
      console.error('Error adding to wishlist:', error);
      showToast('Error adding to wishlist. Please try again.', 'danger');
    });
  };
  
  // Initialize page by loading first batch of products
  loadInventoryData(1, true);
});