/**
 * Infinite Scroll for DevERP Inventory
 * Enhances user experience by loading more products as the user scrolls
 */

document.addEventListener('DOMContentLoaded', function() {
    // Configuration
    const config = {
      loadMoreThreshold: 200, // Load more when user is 200px from bottom
      initialPage: 2, // Start with page 2 (page 1 is loaded on initial page load)
      perPage: 50,    // Items per page
      loadingDelay: 300, // Min delay to show loading indicator (ms)
      tableBodySelector: '#inventory-table tbody',
      cardViewSelector: '#card-view',
      loadingOverlaySelector: '#loading-overlay'
    };
    
    // State management
    const state = {
      loading: false,
      currentPage: config.initialPage,
      hasMore: true,
      lastScrollPosition: 0,
      scrollDirection: 'down'
    };
    
    // DOM elements
    const elements = {
      tableView: document.getElementById('table-view'),
      cardView: document.getElementById('card-view'),
      tableBody: document.querySelector(config.tableBodySelector),
      loadingOverlay: document.querySelector(config.loadingOverlaySelector),
      totalResults: document.getElementById('totalResults'),
      visibleCount: document.getElementById('visibleCount'),
      totalCount: document.getElementById('totalCount')
    };
    
    // Add scroll event listener
    window.addEventListener('scroll', debounce(handleScroll, 100));
    
    /**
     * Main scroll handler function
     */
    function handleScroll() {
      // Don't process if already loading or if no more products
      if (state.loading || !state.hasMore) return;
      
      // Calculate scroll position
      const scrollY = window.scrollY || window.pageYOffset;
      const currentScrollDirection = scrollY > state.lastScrollPosition ? 'down' : 'up';
      state.lastScrollPosition = scrollY;
      state.scrollDirection = currentScrollDirection;
      
      // Only load more when scrolling down
      if (currentScrollDirection !== 'down') return;
      
      // Check if we're near the bottom of the page
      const windowHeight = window.innerHeight;
      const documentHeight = document.documentElement.scrollHeight;
      const scrollPosition = scrollY + windowHeight;
      
      if (documentHeight - scrollPosition <= config.loadMoreThreshold) {
        loadMoreProducts();
      }
    }
    
    /**
     * Load more products via AJAX
     */
    function loadMoreProducts() {
      // Set loading state
      state.loading = true;
      
      // Show loading overlay with a slight delay
      const loadingTimer = setTimeout(() => {
        if (state.loading) {
          elements.loadingOverlay.classList.add('d-flex');
          elements.loadingOverlay.classList.remove('d-none');
        }
      }, config.loadingDelay);
      
      // Get active filters
      const filters = getActiveFilters();
      
      // Prepare URL with query parameters
      const url = new URL(`${window.location.origin}/inventory/load-more/`);
      url.searchParams.append('page', state.currentPage);
      url.searchParams.append('per_page', config.perPage);
      
      // Add filters to query params
      Object.keys(filters).forEach(key => {
        if (filters[key]) {
          url.searchParams.append(key, filters[key]);
        }
      });
      
      // Fetch products
      fetch(url)
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          if (data.success) {
            // Append products to the DOM
            appendProducts(data.products);
            
            // Update state
            state.hasMore = data.has_more;
            if (data.has_more) {
              state.currentPage = data.next_page;
            }
            
            // Update visible product count
            updateProductCount();
          } else {
            console.error('Error loading more products:', data.error);
            showToast('Failed to load more products. Please try again.', 'danger');
          }
        })
        .catch(error => {
          console.error('Error loading more products:', error);
          showToast('Failed to load more products. Please try again.', 'danger');
        })
        .finally(() => {
          // Clear loading timer and hide overlay
          clearTimeout(loadingTimer);
          elements.loadingOverlay.classList.remove('d-flex');
          elements.loadingOverlay.classList.add('d-none');
          
          // Reset loading state
          state.loading = false;
        });
    }
    
    /**
     * Append new products to both table and card views
     */
    function appendProducts(products) {
      if (!products || products.length === 0) return;
      
      // Get current item count for indexing
      const startIndex = document.querySelectorAll(`${config.tableBodySelector} tr`).length;
      
      // Create document fragments for better performance
      const tableFragment = document.createDocumentFragment();
      const cardFragment = document.createDocumentFragment();
      
      // Process each product
      products.forEach((prod, index) => {
        const counter = startIndex + index;
        
        // Create table row
        const tableRow = createTableRow(prod, counter);
        tableFragment.appendChild(tableRow);
        
        // Create card
        const card = createCard(prod, counter);
        cardFragment.appendChild(card);
      });
      
      // Append to DOM
      elements.tableBody.appendChild(tableFragment);
      elements.cardView.appendChild(cardFragment);
      
      // Initialize new items
      initializeNewItems(startIndex, products.length);
    }
    
    /**
     * Create a table row for a product
     */
    function createTableRow(prod, counter) {
      const tr = document.createElement('tr');
      tr.dataset.type = prod.category.toLowerCase();
      tr.dataset.gender = prod.gender.toLowerCase();
      tr.dataset.collection = prod.collection.toLowerCase();
      tr.dataset.subcategory = prod.subcategory.toLowerCase();
      tr.dataset.producttype = prod.producttype.toLowerCase();
      tr.dataset.status = prod.status.toLowerCase();
      
      // Set job numbers for search
      tr.dataset.jobs = prod.in_stock_jobs.map(job => job.job_no).join(' ');
      tr.dataset.memojobs = prod.memo_jobs.map(job => job.job_no).join(' ');
      
      // Create table cells
      tr.innerHTML = `
        <td>${counter + 1}</td>
        <td>
          <img src="/static/inventory/placeholder.jpg"
            data-src="https://dev-jewels.s3.us-east-2.amazonaws.com/products/${prod.design_no}/White/D_${prod.design_no}-1.jpg"
            class="img-thumbnail lazy" alt="${prod.design_no}"
            data-bs-toggle="modal" data-bs-target="#imageModal-${counter}">
        </td>
        <td><strong>${prod.design_no}</strong></td>
        <td>${prod.category}</td>
        <td>
          <a href="#" class="pcs-btn" data-bs-toggle="modal" data-bs-target="#modal-${counter}">
            ${prod.pcs}
          </a>
        </td>
        <td>
          <span class="badge ${prod.pcs > 0 ? 'bg-success' : 'bg-danger'}">
            ${prod.status}
          </span>
        </td>
        <td>
          <div class="btn-group">
            <button class="btn btn-sm btn-outline-primary" onclick="addToWishlist('${prod.design_no}')" title="Add to Wishlist">
              <i class="bi bi-heart"></i>
            </button>
            <button class="btn btn-sm btn-outline-secondary" data-bs-toggle="modal" data-bs-target="#imageModal-${counter}" title="View Images">
              <i class="bi bi-images"></i>
            </button>
          </div>
        </td>
      `;
      
      return tr;
    }
    
    /**
     * Create a card for a product
     */
    function createCard(prod, counter) {
      const div = document.createElement('div');
      div.className = 'col-xl-2 col-lg-3 col-md-4 col-sm-6';
      div.dataset.type = prod.category.toLowerCase();
      div.dataset.gender = prod.gender.toLowerCase();
      div.dataset.collection = prod.collection.toLowerCase();
      div.dataset.subcategory = prod.subcategory.toLowerCase();
      div.dataset.producttype = prod.producttype.toLowerCase();
      div.dataset.status = prod.status.toLowerCase();
      div.dataset.jobs = prod.in_stock_jobs.map(job => job.job_no).join(' ');
      
      div.innerHTML = `
        <div class="card h-100 shadow-sm inventory-card">
          <div class="card-img-container position-relative">
            <div class="position-absolute top-0 end-0 m-2">
              <button class="btn btn-sm btn-light opacity-75" onclick="addToWishlist('${prod.design_no}')" title="Add to Wishlist">
                <i class="bi bi-heart"></i>
              </button>
            </div>
            <img class="card-img-top lazy"
              src="/static/inventory/placeholder.jpg"
              data-src="https://dev-jewels.s3.us-east-2.amazonaws.com/products/${prod.design_no}/White/D_${prod.design_no}-1.jpg"
              alt="${prod.design_no}" 
              data-bs-toggle="modal" 
              data-bs-target="#imageModal-${counter}">
          </div>
  
          <div class="card-body">
            <h6 class="card-title">${prod.design_no}</h6>
            <p class="mb-1 text-muted small">${prod.category}</p>
            <div class="d-flex justify-content-between align-items-center mt-2">
              <a href="#" class="pcs-btn" data-bs-toggle="modal" data-bs-target="#modal-${counter}">
                ${prod.pcs} pcs
              </a>
              <span class="badge ${prod.pcs > 0 ? 'bg-success' : 'bg-danger'}">
                ${prod.status}
              </span>
            </div>
          </div>
        </div>
      `;
      
      return div;
    }
    
    /**
     * Initialize newly added items (lazy loading, modals, etc.)
     */
    function initializeNewItems(startIndex, count) {
      // Dynamic modals creation
      createModals(startIndex, count);
      
      // Re-initialize lazy loading for new images
      initializeLazyLoad();
      
      // Apply current filters to new items
      window.applyFilters();
      
      // Track product views
      trackProductViews(startIndex, count);
    }
    
    /**
     * Create modals for new products dynamically
     */
    function createModals(startIndex, count) {
      // Create a fragment to hold all modals
      const fragment = document.createDocumentFragment();
      const products = getProductsByRange(startIndex, count);
      
      for (let i = 0; i < count; i++) {
        const index = startIndex + i;
        const prod = products[i];
        
        if (!prod) continue;
        
        // Create PCS Modal
        const pcsModal = createPcsModal(prod, index);
        fragment.appendChild(pcsModal);
        
        // Create Image Modal
        const imageModal = createImageModal(prod, index);
        fragment.appendChild(imageModal);
      }
      
      // Append all modals to the body
      document.body.appendChild(fragment);
      
      // Initialize modal functionality
      initializeModals(startIndex, count);
    }
    
    /**
     * Get products data from DOM by range
     */
    function getProductsByRange(startIndex, count) {
      const products = [];
      const rows = document.querySelectorAll(`${config.tableBodySelector} tr`);
      
      for (let i = startIndex; i < startIndex + count; i++) {
        if (i >= rows.length) break;
        
        const row = rows[i];
        const designNo = row.querySelector('td:nth-child(3)').textContent.trim();
        const category = row.querySelector('td:nth-child(4)').textContent.trim();
        const pcs = parseInt(row.querySelector('.pcs-btn').textContent.trim(), 10);
        const status = row.querySelector('.badge').textContent.trim();
        
        products.push({
          design_no: designNo,
          category: category,
          pcs: pcs,
          status: status,
          in_stock_jobs: [], // Would be populated from API
          memo_jobs: []      // Would be populated from API
        });
      }
      
      return products;
    }
    
    /**
     * Create PCS Modal for a product
     */
    function createPcsModal(prod, index) {
      const template = document.createElement('template');
      template.innerHTML = `
        <!-- PCS Modal template would go here -->
        <!-- This would be dynamically populated based on the product data -->
      `;
      return template.content.firstChild;
    }
    
    /**
     * Create Image Modal for a product
     */
    function createImageModal(prod, index) {
      const template = document.createElement('template');
      template.innerHTML = `
        <!-- Image Modal template would go here -->
        <!-- This would be dynamically populated based on the product data -->
      `;
      return template.content.firstChild;
    }
    
    /**
     * Initialize modal functionality
     */
    function initializeModals(startIndex, count) {
      // Initialize functionality for newly created modals
      // This would include event listeners, checkbox behavior, etc.
    }
    
    /**
     * Track product views for analytics
     */
    function trackProductViews(startIndex, count) {
      const products = getProductsByRange(startIndex, count);
      
      products.forEach(prod => {
        // Use a throttled fetch to avoid too many requests
        fetch(`/inventory/track-view/${prod.design_no}/`, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken()
          }
        }).catch(error => console.error('Error tracking product view:', error));
      });
    }
    
    /**
     * Get CSRF token from cookies
     */
    function getCsrfToken() {
      return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';
    }
    
    /**
     * Initialize lazy loading for images
     */
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
    
    /**
     * Get current active filters
     */
    function getActiveFilters() {
      // This function would collect filter values from the UI
      return {
        category: document.getElementById('categoryFilter')?.value || 'all',
        gender: document.getElementById('genderFilter')?.value || 'all',
        collection: document.getElementById('collectionFilter')?.value || 'all',
        subcategory: document.getElementById('subcategoryFilter')?.value || 'all',
        producttype: document.getElementById('producttypeFilter')?.value || 'all',
        status: getActiveStatusFilter(),
        search: document.getElementById('searchInput')?.value || ''
      };
    }
    
    /**
     * Get active status filter value
     */
    function getActiveStatusFilter() {
      if (document.getElementById('btn-instock')?.classList.contains('active')) {
        return 'instock';
      }
      if (document.getElementById('btn-notinstock')?.classList.contains('active')) {
        return 'notinstock';
      }
      return 'all';
    }
    
    /**
     * Update product count display
     */
    function updateProductCount() {
      const visibleProducts = Array.from(
        document.querySelectorAll(`${config.tableBodySelector} tr, ${config.cardViewSelector} > div`)
      ).filter(item => item.style.display !== 'none');
      
      const totalProducts = document.querySelectorAll(`${config.tableBodySelector} tr`).length;
      
      if (elements.visibleCount) {
        elements.visibleCount.textContent = visibleProducts.length;
      }
      
      if (elements.totalCount) {
        elements.totalCount.textContent = totalProducts;
      }
    }
    
    /**
     * Utility function for debouncing
     */
    function debounce(func, wait) {
      let timeout;
      return function() {
        const context = this;
        const args = arguments;
        const later = function() {
          timeout = null;
          func.apply(context, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
      };
    }
    
    // Initialize infinite scroll on page load
    function initialize() {
      // Update initial product counts
      updateProductCount();
      
      // Expose necessary functions to global scope for use in other scripts
      window.infiniteScroll = {
        loadMoreProducts,
        resetScroll: () => {
          state.currentPage = config.initialPage;
          state.hasMore = true;
          state.loading = false;
        }
      };
    }
    
    // Start initialization
    initialize();
  });