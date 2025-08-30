// Admin Panel JavaScript for Kshitiz Jaiswal Website
// Handles admin panel functionality, content management, and dynamic interactions

(function() {
    'use strict';

    // Global admin state
    let currentTab = 'dashboard';
    let unsavedChanges = false;

    // DOM Content Loaded
    document.addEventListener('DOMContentLoaded', function() {
        initializeAdminPanel();
    });

    // Initialize admin panel functionality
    function initializeAdminPanel() {
        initTabSwitching();
        initContentForms();
        initDataTables();
        initFileUploads();
        initFormValidations();
        initAutoSave();
        initConfirmations();
        initExportFunctions();
        initQuickActions();
    }

    // Initialize tab switching
    function initTabSwitching() {
        const navItems = document.querySelectorAll('.admin-nav-item');
        const tabs = document.querySelectorAll('.admin-tab');

        navItems.forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                
                const targetTab = this.getAttribute('data-tab');
                if (targetTab) {
                    switchTab(targetTab);
                }
            });
        });

        // Handle direct hash navigation
        const hash = window.location.hash.substring(1);
        if (hash && document.getElementById(hash)) {
            switchTab(hash);
        }
    }

    // Switch between tabs
    function switchTab(tabName) {
        // Check for unsaved changes
        if (unsavedChanges && !confirm('You have unsaved changes. Are you sure you want to leave?')) {
            return;
        }

        // Update navigation
        document.querySelectorAll('.admin-nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update content
        document.querySelectorAll('.admin-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        const targetTab = document.getElementById(tabName);
        if (targetTab) {
            targetTab.classList.add('active');
        }

        currentTab = tabName;
        unsavedChanges = false;
        
        // Update URL hash
        window.location.hash = tabName;

        // Load tab-specific data
        loadTabData(tabName);
    }

    // Load data for specific tab
    function loadTabData(tabName) {
        switch(tabName) {
            case 'dashboard':
                updateDashboardStats();
                break;
            case 'subscribers':
                loadSubscriberData();
                break;
            case 'reels':
                initReelManagement();
                break;
            case 'opinions':
                initOpinionManagement();
                break;
        }
    }

    // Initialize content forms
    function initContentForms() {
        const contentForm = document.getElementById('contentForm');
        if (contentForm) {
            contentForm.addEventListener('submit', function(e) {
                e.preventDefault();
                saveContentChanges(this);
            });

            // Track changes
            const inputs = contentForm.querySelectorAll('input, textarea, select');
            inputs.forEach(input => {
                input.addEventListener('change', function() {
                    unsavedChanges = true;
                    showUnsavedIndicator();
                });
            });
        }
    }

    // Save content changes
    function saveContentChanges(form) {
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;

        // Show loading state
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
        submitBtn.disabled = true;

        // Simulate save (in real implementation, this would be a server request)
        setTimeout(() => {
            showNotification('Content saved successfully!', 'success');
            unsavedChanges = false;
            hideUnsavedIndicator();
            
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }, 1000);
    }

    // Initialize data tables
    function initDataTables() {
        const tables = document.querySelectorAll('.admin-card table');
        
        tables.forEach(table => {
            // Add sorting functionality
            const headers = table.querySelectorAll('th');
            headers.forEach((header, index) => {
                if (header.textContent.trim() && index < headers.length - 1) { // Skip actions column
                    header.style.cursor = 'pointer';
                    header.innerHTML += ' <i class="fas fa-sort text-muted"></i>';
                    
                    header.addEventListener('click', function() {
                        sortTable(table, index);
                    });
                }
            });
        });
    }

    // Sort table by column
    function sortTable(table, columnIndex) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const header = table.querySelectorAll('th')[columnIndex];
        const isAscending = !header.classList.contains('sort-desc');

        // Sort rows
        rows.sort((a, b) => {
            const aValue = a.cells[columnIndex].textContent.trim();
            const bValue = b.cells[columnIndex].textContent.trim();
            
            // Try to parse as numbers
            const aNum = parseFloat(aValue);
            const bNum = parseFloat(bValue);
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return isAscending ? aNum - bNum : bNum - aNum;
            }
            
            // String comparison
            return isAscending ? 
                aValue.localeCompare(bValue) : 
                bValue.localeCompare(aValue);
        });

        // Update table
        tbody.innerHTML = '';
        rows.forEach(row => tbody.appendChild(row));

        // Update sort indicators
        table.querySelectorAll('th').forEach(th => {
            th.classList.remove('sort-asc', 'sort-desc');
            th.querySelector('i').className = 'fas fa-sort text-muted';
        });

        header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
        header.querySelector('i').className = `fas fa-sort-${isAscending ? 'up' : 'down'} text-primary`;
    }

    // Initialize file uploads
    function initFileUploads() {
        const fileInputs = document.querySelectorAll('input[type="file"]');
        
        fileInputs.forEach(input => {
            input.addEventListener('change', function() {
                handleFileUpload(this);
            });
        });
    }

    // Handle file upload
    function handleFileUpload(input) {
        const file = input.files[0];
        if (!file) return;

        // Validate file size (max 5MB)
        if (file.size > 5 * 1024 * 1024) {
            showNotification('File size must be less than 5MB', 'error');
            input.value = '';
            return;
        }

        // Validate file type
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
        if (!allowedTypes.includes(file.type)) {
            showNotification('Only JPG, PNG, and GIF files are allowed', 'error');
            input.value = '';
            return;
        }

        // Show preview
        showFilePreview(input, file);
    }

    // Show file preview
    function showFilePreview(input, file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            // Create preview element
            const preview = document.createElement('div');
            preview.className = 'file-preview mt-2';
            preview.innerHTML = `
                <img src="${e.target.result}" alt="Preview" style="max-width: 200px; max-height: 200px; border-radius: 5px;">
                <button type="button" class="btn btn-sm btn-danger ms-2" onclick="removeFilePreview(this)">
                    <i class="fas fa-times"></i>
                </button>
            `;

            // Remove existing preview
            const existingPreview = input.parentNode.querySelector('.file-preview');
            if (existingPreview) {
                existingPreview.remove();
            }

            // Add new preview
            input.parentNode.appendChild(preview);
        };
        reader.readAsDataURL(file);
    }

    // Remove file preview
    window.removeFilePreview = function(button) {
        const preview = button.closest('.file-preview');
        const input = preview.parentNode.querySelector('input[type="file"]');
        
        preview.remove();
        input.value = '';
    };

    // Initialize form validations
    function initFormValidations() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!validateForm(this)) {
                    e.preventDefault();
                    showNotification('Please correct the errors in the form', 'error');
                }
            });
        });
    }

    // Validate form
    function validateForm(form) {
        let isValid = true;
        const requiredFields = form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('is-invalid');
                isValid = false;
            } else {
                field.classList.remove('is-invalid');
            }
        });

        return isValid;
    }

    // Initialize auto-save
    function initAutoSave() {
        const autoSaveForms = document.querySelectorAll('[data-autosave="true"]');
        
        autoSaveForms.forEach(form => {
            const inputs = form.querySelectorAll('input, textarea, select');
            inputs.forEach(input => {
                input.addEventListener('input', debounce(function() {
                    autoSaveForm(form);
                }, 2000));
            });
        });
    }

    // Auto-save form
    function autoSaveForm(form) {
        const formData = new FormData(form);
        
        // Show auto-save indicator
        showAutoSaveIndicator();
        
        // Simulate auto-save
        setTimeout(() => {
            hideAutoSaveIndicator();
            console.log('Form auto-saved');
        }, 500);
    }

    // Initialize confirmation dialogs
    function initConfirmations() {
        const deleteButtons = document.querySelectorAll('[data-action="delete"]');
        
        deleteButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                const itemName = this.dataset.itemName || 'this item';
                if (confirm(`Are you sure you want to delete ${itemName}? This action cannot be undone.`)) {
                    // Proceed with deletion
                    handleDeletion(this);
                }
            });
        });
    }

    // Handle deletion
    function handleDeletion(button) {
        const row = button.closest('tr');
        const itemId = button.dataset.itemId;
        
        // Show loading state
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        button.disabled = true;
        
        // Simulate deletion
        setTimeout(() => {
            if (row) {
                row.style.transition = 'opacity 0.3s';
                row.style.opacity = '0';
                setTimeout(() => row.remove(), 300);
            }
            showNotification('Item deleted successfully', 'success');
        }, 1000);
    }

    // Initialize export functions
    function initExportFunctions() {
        // Export subscribers
        window.exportSubscribers = function() {
            const table = document.querySelector('#subscribers table');
            if (!table) {
                showNotification('No data to export', 'warning');
                return;
            }

            const csvData = tableToCSV(table);
            downloadCSV(csvData, 'subscribers.csv');
            showNotification('Subscribers exported successfully', 'success');
        };
    }

    // Convert table to CSV
    function tableToCSV(table) {
        const rows = table.querySelectorAll('tr');
        const csvData = [];

        rows.forEach(row => {
            const cols = row.querySelectorAll('td, th');
            const rowData = [];
            
            cols.forEach(col => {
                rowData.push('"' + col.textContent.trim().replace(/"/g, '""') + '"');
            });
            
            csvData.push(rowData.join(','));
        });

        return csvData.join('\n');
    }

    // Download CSV file
    function downloadCSV(csvData, filename) {
        const blob = new Blob([csvData], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        
        link.href = url;
        link.download = filename;
        link.click();
        
        window.URL.revokeObjectURL(url);
    }

    // Initialize quick actions
    function initQuickActions() {
        const quickActionBtns = document.querySelectorAll('.quick-action-btn');
        
        quickActionBtns.forEach(btn => {
            btn.addEventListener('click', function(e) {
                const targetTab = this.dataset.tab;
                if (targetTab) {
                    e.preventDefault();
                    switchTab(targetTab);
                }
            });
        });
    }

    // Update dashboard stats
    function updateDashboardStats() {
        const statCards = document.querySelectorAll('.stat-card');
        
        statCards.forEach(card => {
            const numberElement = card.querySelector('h3');
            if (numberElement) {
                const targetNumber = parseInt(numberElement.textContent);
                animateNumber(numberElement, 0, targetNumber, 1000);
            }
        });
    }

    // Animate number counting
    function animateNumber(element, start, end, duration) {
        const startTime = performance.now();
        
        function updateNumber(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const current = Math.floor(start + (end - start) * progress);
            
            element.textContent = current;
            
            if (progress < 1) {
                requestAnimationFrame(updateNumber);
            }
        }
        
        requestAnimationFrame(updateNumber);
    }

    // Load subscriber data
    function loadSubscriberData() {
        const subscriberTable = document.querySelector('#subscribers table tbody');
        if (subscriberTable && subscriberTable.children.length === 0) {
            // Add loading state if no data
            subscriberTable.innerHTML = '<tr><td colspan="5" class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
            
            // Simulate loading
            setTimeout(() => {
                if (subscriberTable.querySelector('.fa-spinner')) {
                    subscriberTable.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No subscribers yet</td></tr>';
                }
            }, 1000);
        }
    }

    // Initialize reel management
    function initReelManagement() {
        const reelTable = document.querySelector('#reels table');
        if (reelTable) {
            // Add row hover effects
            const rows = reelTable.querySelectorAll('tbody tr');
            rows.forEach(row => {
                row.addEventListener('mouseenter', function() {
                    this.style.backgroundColor = '#f8f9fa';
                });
                
                row.addEventListener('mouseleave', function() {
                    this.style.backgroundColor = '';
                });
            });
        }
    }

    // Initialize opinion management
    function initOpinionManagement() {
        const opinionCards = document.querySelectorAll('#opinions .admin-card');
        
        opinionCards.forEach(card => {
            // Add expand/collapse for poll results
            const pollResults = card.querySelector('.poll-results');
            if (pollResults) {
                const toggleBtn = document.createElement('button');
                toggleBtn.className = 'btn btn-sm btn-outline-info mt-2';
                toggleBtn.innerHTML = '<i class="fas fa-chart-bar me-1"></i>View Results';
                
                toggleBtn.addEventListener('click', function() {
                    if (pollResults.style.display === 'none') {
                        pollResults.style.display = 'block';
                        this.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Hide Results';
                    } else {
                        pollResults.style.display = 'none';
                        this.innerHTML = '<i class="fas fa-chart-bar me-1"></i>View Results';
                    }
                });
                
                card.appendChild(toggleBtn);
                pollResults.style.display = 'none';
            }
        });
    }

    // Show notification
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show admin-notification`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        `;
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    // Show unsaved changes indicator
    function showUnsavedIndicator() {
        let indicator = document.querySelector('.unsaved-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'unsaved-indicator';
            indicator.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Unsaved changes';
            indicator.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #f59e0b;
                color: white;
                padding: 10px 15px;
                border-radius: 5px;
                font-size: 14px;
                z-index: 9998;
            `;
            document.body.appendChild(indicator);
        }
    }

    // Hide unsaved changes indicator
    function hideUnsavedIndicator() {
        const indicator = document.querySelector('.unsaved-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    // Show auto-save indicator
    function showAutoSaveIndicator() {
        let indicator = document.querySelector('.autosave-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'autosave-indicator';
            indicator.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Auto-saving...';
            indicator.style.cssText = `
                position: fixed;
                bottom: 20px;
                left: 20px;
                background: #10b981;
                color: white;
                padding: 8px 12px;
                border-radius: 5px;
                font-size: 12px;
                z-index: 9998;
            `;
            document.body.appendChild(indicator);
        }
    }

    // Hide auto-save indicator
    function hideAutoSaveIndicator() {
        const indicator = document.querySelector('.autosave-indicator');
        if (indicator) {
            indicator.style.transition = 'opacity 0.3s';
            indicator.style.opacity = '0';
            setTimeout(() => indicator.remove(), 300);
        }
    }

    // Utility: Debounce function
    function debounce(func, wait) {
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

    // Handle page unload warning
    window.addEventListener('beforeunload', function(e) {
        if (unsavedChanges) {
            const message = 'You have unsaved changes. Are you sure you want to leave?';
            e.returnValue = message;
            return message;
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+S to save
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            const contentForm = document.getElementById('contentForm');
            if (contentForm && currentTab === 'content') {
                saveContentChanges(contentForm);
            }
        }
        
        // Ctrl+1-5 for tab switching
        if (e.ctrlKey && e.key >= '1' && e.key <= '5') {
            e.preventDefault();
            const tabs = ['dashboard', 'reels', 'opinions', 'subscribers', 'content'];
            const tabIndex = parseInt(e.key) - 1;
            if (tabs[tabIndex]) {
                switchTab(tabs[tabIndex]);
            }
        }
    });

    // Console log for debugging
    console.log('Admin Panel JS Loaded Successfully');

})();
