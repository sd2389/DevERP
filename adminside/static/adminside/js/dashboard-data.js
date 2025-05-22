// Dashboard Data Integration Script
// This script connects the admin dashboard to real data stored in localStorage

document.addEventListener('DOMContentLoaded', function() {
    // Constants
    const STORAGE_KEYS = {
      ORDERS: 'customer_orders',
      CART: 'cart_customer',
      MEMO_REQUESTS: 'memoRequests',
      CUSTOM_ORDERS: 'custom_orders',
      WISHLIST: 'user_wishlist'
    };
  
    // Helper function to safely retrieve data from localStorage
    function getStorageData(key, defaultValue = []) {
      try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : defaultValue;
      } catch (error) {
        console.error(`Error retrieving data from ${key}:`, error);
        return defaultValue;
      }
    }
    
    // Helper function to format currency
    function formatCurrency(amount) {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 2
      }).format(amount);
    }
    
    // Helper function to format date
    function formatDate(dateString) {
      const options = { year: 'numeric', month: 'long', day: 'numeric' };
      return new Date(dateString).toLocaleDateString('en-US', options);
    }
    
    // Helper function to get time ago string
    function getTimeAgo(dateString) {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now - date;
      const diffSec = Math.round(diffMs / 1000);
      const diffMin = Math.round(diffSec / 60);
      const diffHour = Math.round(diffMin / 60);
      const diffDay = Math.round(diffHour / 24);
      
      if (diffSec < 60) return `${diffSec} seconds ago`;
      if (diffMin < 60) return `${diffMin} minutes ago`;
      if (diffHour < 24) return `${diffHour} hours ago`;
      if (diffDay < 7) return `${diffDay} days ago`;
      return formatDate(dateString);
    }
    
    // Get data from localStorage
    const orders = getStorageData(STORAGE_KEYS.ORDERS);
    const stockItems = getStorageData(STORAGE_KEYS.CART);
    const memoItems = getStorageData(STORAGE_KEYS.MEMO_REQUESTS);
    const customItems = getStorageData(STORAGE_KEYS.CUSTOM_ORDERS);
    
    // Calculate dashboard statistics
    
    // 1. Total Orders
    const totalOrders = orders.length;
    document.getElementById('totalOrdersValue').textContent = totalOrders;
    
    // 2. Total Revenue
    let totalRevenue = 0;
    orders.forEach(order => {
      totalRevenue += order.payment?.total || 0;
    });
    document.getElementById('totalRevenueValue').textContent = formatCurrency(totalRevenue);
    
    // 3. Custom Orders Count
    let customOrdersCount = 0;
    orders.forEach(order => {
      customOrdersCount += order.items?.custom?.length || 0;
    });
    // Add current custom orders that haven't been purchased
    customOrdersCount += customItems.length;
    document.getElementById('customOrdersValue').textContent = customOrdersCount;
    
    // 4. Memo Requests Count
    let memoRequestsCount = 0;
    orders.forEach(order => {
      memoRequestsCount += order.items?.memo?.length || 0;
    });
    // Add current memo requests that haven't been purchased
    memoRequestsCount += memoItems.length;
    document.getElementById('memoRequestsValue').textContent = memoRequestsCount;
    
    // Populate Recent Orders table
    const recentOrdersTableBody = document.getElementById('recentOrdersTableBody');
    if (recentOrdersTableBody) {
      recentOrdersTableBody.innerHTML = '';
      
      if (orders.length === 0) {
        // No orders yet
        const emptyRow = document.createElement('tr');
        emptyRow.innerHTML = `
          <td colspan="7" class="text-center py-4">No orders found</td>
        `;
        recentOrdersTableBody.appendChild(emptyRow);
      } else {
        // Sort by date (newest first) and take first 5
        const recentOrders = [...orders]
          .sort((a, b) => new Date(b.date) - new Date(a.date))
          .slice(0, 5);
        
        recentOrders.forEach(order => {
          // Count items by type
          const stockCount = order.items?.stock?.length || 0;
          const memoCount = order.items?.memo?.length || 0;
          const customCount = order.items?.custom?.length || 0;
          
          // Create badges for item types
          let itemBadges = '';
          if (stockCount > 0) {
            itemBadges += `<span class="item-type-badge item-stock">${stockCount} Stock</span>`;
          }
          if (memoCount > 0) {
            itemBadges += `<span class="item-type-badge item-memo">${memoCount} Memo</span>`;
          }
          if (customCount > 0) {
            itemBadges += `<span class="item-type-badge item-custom">${customCount} Custom</span>`;
          }
          
          // Create status badge
          const statusClass = `status-${(order.status || 'Pending').replace(/\s+/g, '-')}`;
          const statusBadge = `<span class="badge status-badge ${statusClass}">${order.status || 'Pending'}</span>`;
          
          // Create table row
          const row = document.createElement('tr');
          row.innerHTML = `
            <td>${order.order_id}</td>
            <td>${formatDate(order.date)}</td>
            <td>${order.customer?.name || 'Customer'}</td>
            <td>${itemBadges}</td>
            <td>${formatCurrency(order.payment?.total || 0)}</td>
            <td>${statusBadge}</td>
            <td>
              <button class="btn btn-sm btn-outline-primary" onclick="viewOrderDetails('${order.order_id}')">
                <i class="bi bi-eye"></i>
              </button>
            </td>
          `;
          recentOrdersTableBody.appendChild(row);
        });
      }
    }
    
    // Generate activity feed
    const activityList = document.querySelector('.activity-list');
    if (activityList) {
      // Clear current activities
      activityList.innerHTML = '';
      
      if (orders.length === 0) {
        // No orders yet
        const emptyActivity = document.createElement('li');
        emptyActivity.className = 'activity-item p-3';
        emptyActivity.innerHTML = `
          <div class="activity-icon bg-light-secondary">
            <i class="bi bi-info-circle"></i>
          </div>
          <div class="activity-content">
            <div class="activity-title">No activities yet</div>
            <div class="activity-text">Activities will appear as orders are processed</div>
            <div class="activity-time">Just now</div>
          </div>
        `;
        activityList.appendChild(emptyActivity);
      } else {
        // Create a combined list of activities from orders
        const activities = [];
        
        // Add order placed activities
        orders.forEach(order => {
          activities.push({
            type: 'order_placed',
            order_id: order.order_id,
            customer: order.customer?.name || 'Customer',
            date: order.date,
            icon: 'bi-box',
            iconClass: 'bg-light-primary'
          });
          
          // Add status change activities if they exist
          if (order.processed_at) {
            activities.push({
              type: 'status_change',
              order_id: order.order_id,
              status: 'In Process',
              date: order.processed_at,
              icon: 'bi-gear',
              iconClass: 'bg-light-warning'
            });
          }
          
          if (order.completed_at) {
            activities.push({
              type: 'status_change',
              order_id: order.order_id,
              status: 'Completed',
              date: order.completed_at,
              icon: 'bi-check-circle',
              iconClass: 'bg-light-success'
            });
          }
          
          if (order.cancelled_at) {
            activities.push({
              type: 'status_change',
              order_id: order.order_id,
              status: 'Cancelled',
              date: order.cancelled_at,
              icon: 'bi-x-circle',
              iconClass: 'bg-light-danger'
            });
          }
        });
        
        // Sort by date (newest first) and take first 4
        const recentActivities = activities
          .sort((a, b) => new Date(b.date) - new Date(a.date))
          .slice(0, 4);
        
        // Create activity items
        recentActivities.forEach(activity => {
          const activityItem = document.createElement('li');
          activityItem.className = 'activity-item p-3';
          
          let title = '';
          let text = '';
          
          if (activity.type === 'order_placed') {
            title = 'New order received';
            text = `Order #${activity.order_id} placed by ${activity.customer}`;
          } else if (activity.type === 'status_change') {
            title = 'Order status updated';
            text = `Order #${activity.order_id} marked as ${activity.status}`;
          }
          
          activityItem.innerHTML = `
            <div class="activity-icon ${activity.iconClass}">
              <i class="bi ${activity.icon}"></i>
            </div>
            <div class="activity-content">
              <div class="activity-title">${title}</div>
              <div class="activity-text">${text}</div>
              <div class="activity-time">${getTimeAgo(activity.date)}</div>
            </div>
          `;
          activityList.appendChild(activityItem);
        });
      }
    }
    
    // Update charts with real data
    
    // 1. Order Trends Chart
    const orderTrendsChart = Chart.getChart('orderTrendsChart');
    if (orderTrendsChart) {
      // Group orders by week
      const sixWeeksAgo = new Date();
      sixWeeksAgo.setDate(sixWeeksAgo.getDate() - 6 * 7);
      
      // Create 6 week periods
      const weekLabels = [];
      const weeklyData = {
        total: Array(6).fill(0),
        custom: Array(6).fill(0),
        memo: Array(6).fill(0)
      };
      
      for (let i = 0; i < 6; i++) {
        const weekStart = new Date(sixWeeksAgo);
        weekStart.setDate(weekStart.getDate() + i * 7);
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekEnd.getDate() + 6);
        
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const label = `${monthNames[weekStart.getMonth()]} ${weekStart.getDate()}`;
        weekLabels.push(label);
        
        // Count orders in this week
        orders.forEach(order => {
          const orderDate = new Date(order.date);
          if (orderDate >= weekStart && orderDate <= weekEnd) {
            weeklyData.total[i]++;
            
            // Count custom orders
            const customCount = order.items?.custom?.length || 0;
            if (customCount > 0) {
              weeklyData.custom[i] += customCount;
            }
            
            // Count memo requests
            const memoCount = order.items?.memo?.length || 0;
            if (memoCount > 0) {
              weeklyData.memo[i] += memoCount;
            }
          }
        });
      }
      
      // Update chart data
      orderTrendsChart.data.labels = weekLabels;
      orderTrendsChart.data.datasets[0].data = weeklyData.total;
      orderTrendsChart.data.datasets[1].data = weeklyData.custom;
      orderTrendsChart.data.datasets[2].data = weeklyData.memo;
      orderTrendsChart.update();
    }
    
    // 2. Order Types Pie Chart
    const orderTypesChart = Chart.getChart('orderTypesChart');
    if (orderTypesChart) {
      // Count items by type across all orders
      let totalStockCount = 0;
      let totalCustomCount = 0;
      let totalMemoCount = 0;
      
      orders.forEach(order => {
        totalStockCount += order.items?.stock?.length || 0;
        totalCustomCount += order.items?.custom?.length || 0;
        totalMemoCount += order.items?.memo?.length || 0;
      });
      
      // Add current cart, memo requests and custom orders
      totalStockCount += stockItems.length;
      totalCustomCount += customItems.length;
      totalMemoCount += memoItems.length;
      
      // Calculate percentages
      const totalItems = totalStockCount + totalCustomCount + totalMemoCount;
      let stockPercentage = 0;
      let customPercentage = 0;
      let memoPercentage = 0;
      
      if (totalItems > 0) {
        stockPercentage = Math.round((totalStockCount / totalItems) * 100);
        customPercentage = Math.round((totalCustomCount / totalItems) * 100);
        memoPercentage = Math.round((totalMemoCount / totalItems) * 100);
        
        // Ensure percentages add up to 100%
        const totalPercentage = stockPercentage + customPercentage + memoPercentage;
        if (totalPercentage < 100) {
          // Add the remainder to the largest segment
          if (stockPercentage >= customPercentage && stockPercentage >= memoPercentage) {
            stockPercentage += 100 - totalPercentage;
          } else if (customPercentage >= stockPercentage && customPercentage >= memoPercentage) {
            customPercentage += 100 - totalPercentage;
          } else {
            memoPercentage += 100 - totalPercentage;
          }
        }
      }
      
      // Update chart data
      orderTypesChart.data.datasets[0].data = [stockPercentage, customPercentage, memoPercentage];
      orderTypesChart.update();
    }
    
    // Show toast notification that data has been loaded
    showToast('Dashboard data loaded successfully', 'success');
  });
  
  // Function to refresh dashboard data
  function refreshDashboard() {
    // Simply reload the current page to refresh data
    location.reload();
  }
  
  // Connect refresh button to the refreshDashboard function
  document.getElementById('refreshDashboard')?.addEventListener('click', refreshDashboard);