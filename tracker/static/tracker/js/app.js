document.addEventListener('DOMContentLoaded', function() {
    // Toast notifications
    window.showToast = function(message, duration = 3000) {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toast-message');
        
        if (!toast || !toastMessage) return;
        
        toastMessage.textContent = message;
        toast.classList.remove('hidden', 'translate-y-32');
        toast.classList.add('block');
        
        setTimeout(() => {
            toast.classList.add('translate-y-32');
            setTimeout(() => {
                toast.classList.remove('block');
                toast.classList.add('hidden');
            }, 300);
        }, duration);
    };
    
    // Mobile menu toggle
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenuClose = document.getElementById('mobile-menu-close');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    
    function openMobileMenu() {
        if (sidebar) sidebar.classList.remove('-translate-x-full');
        if (sidebarOverlay) sidebarOverlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
    
    function closeMobileMenu() {
        if (sidebar) sidebar.classList.add('-translate-x-full');
        if (sidebarOverlay) sidebarOverlay.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }
    
    function toggleMobileMenu() {
        if (sidebar.classList.contains('-translate-x-full')) {
            openMobileMenu();
        } else {
            closeMobileMenu();
        }
    }
    
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleMobileMenu();
        });
    }
    
    if (mobileMenuClose) {
        mobileMenuClose.addEventListener('click', (e) => {
            e.stopPropagation();
            closeMobileMenu();
        });
    }
    
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeMobileMenu);
    }
    
    // Close mobile menu when clicking outside on mobile
    document.addEventListener('click', (e) => {
        if (window.innerWidth < 768 && sidebar && !sidebar.contains(e.target) && 
            mobileMenuBtn && !mobileMenuBtn.contains(e.target) &&
            !sidebar.classList.contains('-translate-x-full')) {
            closeMobileMenu();
        }
    });
    
    // Close mobile menu on window resize
    window.addEventListener('resize', () => {
        if (window.innerWidth >= 768) {
            closeMobileMenu();
        }
    });
    
    // CSRF token setup for AJAX
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    const csrftoken = getCookie('csrftoken');
    
    // AJAX setup with CSRF token
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
    
    // Function to update category dropdown based on transaction type
    function updateCategoryDropdown(transactionType) {
        const categorySelect = document.getElementById('transaction-category');
        if (!categorySelect) return;
        
        // Get all categories from hidden data
        const categoriesData = document.getElementById('categories-data');
        let categories = [];
        
        if (categoriesData) {
            try {
                categories = JSON.parse(categoriesData.textContent || '[]');
            } catch (e) {
                console.error('Error parsing categories data:', e);
            }
        }
        
        // Filter categories by type
        const filteredCategories = categories.filter(cat => cat.type === transactionType);
        
        // Clear and repopulate dropdown
        categorySelect.innerHTML = '<option value="">Select category...</option>';
        
        filteredCategories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id;
            option.textContent = `${cat.icon || '📦'} ${cat.name}`;
            categorySelect.appendChild(option);
        });
        
        // If no categories, add a disabled option
        if (filteredCategories.length === 0) {
            const option = document.createElement('option');
            option.value = "";
            option.textContent = `No ${transactionType} categories found`;
            option.disabled = true;
            categorySelect.appendChild(option);
        }
    }
    
    // Transaction form handling
    const transactionForm = document.getElementById('transaction-form');
    if (transactionForm) {
        // Set today's date by default
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('transaction-date').value = today;
        
        // Set default transaction type to expense
        document.getElementById('expense-type').checked = true;
        updateCategoryDropdown('expense');
        
        // Update category dropdown when transaction type changes
        document.querySelectorAll('input[name="transaction-type"]').forEach(radio => {
            radio.addEventListener('change', function() {
                updateCategoryDropdown(this.value);
            });
        });
        
        // Handle form submission
        transactionForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const saveBtn = document.getElementById('save-transaction-btn');
            const originalText = saveBtn.textContent;
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';
            
            const formData = new FormData(this);
            let url = this.action;
            
            // If editing, get the transaction ID from hidden field
            const transactionId = document.getElementById('transaction-id').value;
            if (transactionId) {
                url = url.replace('create', transactionId + '/update');
            }
            
            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrftoken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast(data.message);
                    hideModal('transaction-modal');
                    // Refresh page to show new transaction
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    showToast(data.errors || 'Please check the form for errors');
                }
            })
            .catch(error => {
                showToast('An error occurred. Please try again.');
                console.error('Error:', error);
            })
            .finally(() => {
                saveBtn.disabled = false;
                saveBtn.textContent = originalText;
            });
        });
    }
    
    // Category form handling
    const categoryForm = document.getElementById('category-form');
    if (categoryForm) {
        // Show/hide budget field based on category type
        const categoryTypeRadios = document.querySelectorAll('input[name="category-type"]');
        const budgetField = document.getElementById('category-budget-field');
        
        function updateBudgetFieldVisibility() {
            const selectedType = document.querySelector('input[name="category-type"]:checked').value;
            if (selectedType === 'expense') {
                budgetField.style.display = 'block';
            } else {
                budgetField.style.display = 'none';
                document.getElementById('category-budget').value = '';
            }
        }
        
        categoryTypeRadios.forEach(radio => {
            radio.addEventListener('change', updateBudgetFieldVisibility);
        });
        
        // Initialize visibility
        updateBudgetFieldVisibility();
        
        // Handle form submission
        categoryForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const saveBtn = this.querySelector('button[type="submit"]');
            const originalText = saveBtn.textContent;
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';
            
            const formData = new FormData(this);
            let url = this.action;
            
            // If editing, get the category ID from hidden field
            const categoryId = document.getElementById('category-id').value;
            if (categoryId) {
                url = url.replace('create', categoryId + '/update');
            }
            
            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrftoken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast(data.message);
                    hideModal('category-modal');
                    // Refresh page to show new category
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    showToast(data.errors || 'Please check the form for errors');
                }
            })
            .catch(error => {
                showToast('An error occurred. Please try again.');
                console.error('Error:', error);
            })
            .finally(() => {
                saveBtn.disabled = false;
                saveBtn.textContent = originalText;
            });
        });
    }
    
    // Modal functions
    window.showModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
    };
    
    window.hideModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    };
    
    // Close modal buttons
    document.getElementById('close-transaction-modal')?.addEventListener('click', function() {
        hideModal('transaction-modal');
    });
    
    document.getElementById('cancel-transaction-btn')?.addEventListener('click', function() {
        hideModal('transaction-modal');
    });
    
    document.getElementById('close-category-modal')?.addEventListener('click', function() {
        hideModal('category-modal');
    });
    
    document.getElementById('cancel-category-btn')?.addEventListener('click', function() {
        hideModal('category-modal');
    });
    
    // Close modals when clicking outside
    document.querySelectorAll('.modal-container').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                hideModal(this.id);
            }
        });
    });
    
    // Escape key to close modals
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-container[style*="display: flex"]').forEach(modal => {
                hideModal(modal.id);
            });
            closeMobileMenu();
        }
    });
    
    // Add Transaction button
    const addTransactionBtn = document.getElementById('add-transaction-btn');
    if (addTransactionBtn) {
        addTransactionBtn.addEventListener('click', function() {
            // Reset form
            document.getElementById('transaction-form').reset();
            document.getElementById('transaction-id').value = '';
            document.getElementById('transaction-modal-title').textContent = 'Add Transaction';
            
            // Set today's date
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('transaction-date').value = today;
            
            // Set default transaction type to expense
            document.getElementById('expense-type').checked = true;
            updateCategoryDropdown('expense');
            
            // Set default payment method
            document.getElementById('transaction-payment').value = 'cash';
            
            // Set form action to create
            document.getElementById('transaction-form').action = '/api/transactions/create/';
            
            showModal('transaction-modal');
        });
    }
    
    // Add Transaction from empty state
    document.getElementById('add-transaction-btn-empty')?.addEventListener('click', function() {
        document.getElementById('add-transaction-btn').click();
    });
    
    // Add Category button
    const addCategoryBtn = document.getElementById('add-category-btn');
    if (addCategoryBtn) {
        addCategoryBtn.addEventListener('click', function() {
            // Reset form
            document.getElementById('category-form').reset();
            document.getElementById('category-id').value = '';
            document.getElementById('category-modal-title').textContent = 'Add Category';
            
            // Set default type to expense
            document.getElementById('category-expense').checked = true;
            
            // Show budget field for expense (default)
            document.getElementById('category-budget-field').style.display = 'block';
            
            // Set form action to create
            document.getElementById('category-form').action = '/api/categories/create/';
            
            showModal('category-modal');
        });
    }
    
    // Add Category from empty states
    document.getElementById('add-expense-category-btn')?.addEventListener('click', function() {
        document.getElementById('add-category-btn').click();
    });
    
    document.getElementById('add-income-category-btn')?.addEventListener('click', function() {
        document.getElementById('add-category-btn').click();
    });
    
    // Delete functionality
    let deleteTarget = null;
    let deleteUrl = null;
    
    window.confirmDelete = function(target, url) {
        deleteTarget = target;
        deleteUrl = url;
        document.getElementById('delete-message').textContent = 
            'Are you sure you want to delete this item? This action cannot be undone.';
        showModal('delete-modal');
    };
    
    document.getElementById('confirm-delete-btn')?.addEventListener('click', function() {
        if (deleteTarget && deleteUrl) {
            fetch(deleteUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ target: deleteTarget })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast(data.message);
                    // Remove the deleted item from the DOM
                    const element = document.querySelector(`[data-id="${deleteTarget}"]`);
                    if (element) {
                        element.closest('tr, .category-item').remove();
                    }
                } else {
                    showToast(data.errors || 'Failed to delete item');
                }
            })
            .catch(error => {
                showToast('An error occurred');
                console.error('Error:', error);
            })
            .finally(() => {
                hideModal('delete-modal');
                deleteTarget = null;
                deleteUrl = null;
            });
        }
    });
    
    document.getElementById('cancel-delete-btn')?.addEventListener('click', function() {
        hideModal('delete-modal');
        deleteTarget = null;
        deleteUrl = null;
    });
    
    // Filter forms auto-submit
    document.querySelectorAll('.filter-form select, .filter-form input').forEach(element => {
        element.addEventListener('change', function() {
            this.closest('form').submit();
        });
    });
    
    // Edit transaction buttons
    document.querySelectorAll('.edit-transaction').forEach(button => {
        button.addEventListener('click', function() {
            const transactionId = this.dataset.id;
            
            // Populate form with transaction data
            document.getElementById('transaction-id').value = transactionId;
            document.getElementById('transaction-modal-title').textContent = 'Edit Transaction';
            document.querySelector(`input[name="transaction-type"][value="${this.dataset.type}"]`).checked = true;
            document.getElementById('transaction-amount').value = this.dataset.amount;
            document.getElementById('transaction-date').value = this.dataset.date;
            document.getElementById('transaction-description').value = this.dataset.description;
            document.getElementById('transaction-payment').value = this.dataset.payment;
            
            // Update category dropdown based on type
            updateCategoryDropdown(this.dataset.type);
            
            // Set category after dropdown is populated
            setTimeout(() => {
                const categorySelect = document.getElementById('transaction-category');
                if (categorySelect && this.dataset.category) {
                    categorySelect.value = this.dataset.category;
                }
            }, 100);
            
            // Set form action to update
            document.getElementById('transaction-form').action = `/api/transactions/${transactionId}/update/`;
            
            showModal('transaction-modal');
        });
    });
    
    // Edit category buttons
    document.querySelectorAll('.edit-category').forEach(button => {
        button.addEventListener('click', function() {
            const categoryId = this.dataset.id;
            
            // Populate form with category data
            document.getElementById('category-id').value = categoryId;
            document.getElementById('category-modal-title').textContent = 'Edit Category';
            document.querySelector(`input[name="category-type"][value="${this.dataset.type}"]`).checked = true;
            document.getElementById('category-name').value = this.dataset.name;
            document.getElementById('category-icon').value = this.dataset.icon || '';
            
            // Show/hide budget field
            const budgetField = document.getElementById('category-budget-field');
            if (this.dataset.type === 'expense') {
                budgetField.style.display = 'block';
                document.getElementById('category-budget').value = this.dataset.budget || '';
            } else {
                budgetField.style.display = 'none';
                document.getElementById('category-budget').value = '';
            }
            
            // Set form action to update
            document.getElementById('category-form').action = `/api/categories/${categoryId}/update/`;
            
            showModal('category-modal');
        });
    });
    
    // Delete transaction buttons
    document.querySelectorAll('.delete-transaction').forEach(button => {
        button.addEventListener('click', function() {
            const transactionId = this.dataset.id;
            const transactionRow = this.closest('tr');
            const description = transactionRow.querySelector('td:nth-child(2)').textContent.trim();
            
            document.getElementById('delete-message').textContent = 
                `Are you sure you want to delete transaction "${description}"? This action cannot be undone.`;
            
            window.confirmDelete(transactionId, `/api/transactions/${transactionId}/delete/`);
        });
    });
    
    document.addEventListener('DOMContentLoaded', function() {

    // ----------------------------
    // CSRF helper
    // ----------------------------
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                cookie = cookie.trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    // ----------------------------
    // Toast
    // ----------------------------
    window.showToast = function(message, duration = 3000) {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toast-message');
        if (!toast || !toastMessage) return;

        toastMessage.textContent = message;
        toast.classList.remove('hidden', 'translate-y-32');
        toast.classList.add('block');

        setTimeout(() => {
            toast.classList.add('translate-y-32');
            setTimeout(() => {
                toast.classList.remove('block');
                toast.classList.add('hidden');
            }, 300);
        }, duration);
    };

    // ----------------------------
    // Modal helpers
    // ----------------------------
    window.showModal = id => {
        const modal = document.getElementById(id);
        if (modal) { modal.style.display = 'flex'; document.body.style.overflow = 'hidden'; }
    };
    window.hideModal = id => {
        const modal = document.getElementById(id);
        if (modal) { modal.style.display = 'none'; document.body.style.overflow = 'auto'; }
    };

    // ----------------------------
    // Category Modal Add/Edit
    // ----------------------------
    const categoryForm = document.getElementById('category-form');
    const categoryBudgetField = document.getElementById('category-budget-field');

    function openCategoryModal(mode, data = {}) {
        categoryForm.reset();
        document.getElementById('category-id').value = data.id || '';
        document.getElementById('category-modal-title').textContent = mode === 'edit' ? 'Edit Category' : 'Add Category';
        document.getElementById('category-name').value = data.name || '';
        document.getElementById('category-icon').value = data.icon || '';
        document.querySelector(`input[name="category-type"][value="${data.type || 'expense'}"]`).checked = true;
        document.getElementById('category-budget').value = data.budget || '';

        categoryBudgetField.style.display = (data.type === 'expense' || !data.type) ? 'block' : 'none';
        categoryForm.action = data.id ? `/api/categories/${data.id}/update/` : `/api/categories/create/`;

        showModal('category-modal');
    }

    // Edit buttons
    document.querySelectorAll('.edit-category').forEach(btn => {
        btn.addEventListener('click', () => {
            openCategoryModal('edit', {
                id: btn.dataset.id,
                name: btn.dataset.name,
                icon: btn.dataset.icon,
                type: btn.dataset.type,
                budget: btn.dataset.budget
            });
        });
    });

    // Add button
    document.getElementById('add-category-btn')?.addEventListener('click', () => openCategoryModal('add'));

    // Type change
    document.querySelectorAll('input[name="category-type"]').forEach(radio => {
        radio.addEventListener('change', () => {
            categoryBudgetField.style.display = document.querySelector('input[name="category-type"]:checked').value === 'expense' ? 'block' : 'none';
        });
    });

    // Submit category form via AJAX
    categoryForm?.addEventListener('submit', function(e) {
        e.preventDefault();
        const btn = this.querySelector('button[type="submit"]');
        const originalText = btn.textContent;
        btn.disabled = true; btn.textContent = 'Saving...';

        const formData = new FormData(this);
        fetch(this.action, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            body: new URLSearchParams(formData)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) { showToast(data.message); hideModal('category-modal'); setTimeout(() => location.reload(), 800); }
            else showToast(data.errors || 'Error saving category');
        })
        .catch(err => { console.error(err); showToast('Error saving category'); })
        .finally(() => { btn.disabled = false; btn.textContent = originalText; });
    });

    // Delete category
    document.querySelectorAll('.delete-category').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            const name = btn.dataset.name;
            if (!confirm(`Delete "${name}"?`)) return;

            fetch(`/api/categories/${id}/delete/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/x-www-form-urlencoded' }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) { showToast(data.message); btn.closest('.category-item').remove(); }
                else showToast(data.errors || 'Failed to delete category');
            }).catch(err => { console.error(err); showToast('Failed to delete category'); });
        });
    });

    // ----------------------------
    // Transaction Modal Add/Edit
    // ----------------------------
    const transactionForm = document.getElementById('transaction-form');
    function updateCategoryDropdown(type) {
        const select = document.getElementById('transaction-category');
        if (!select) return;

        const data = document.getElementById('categories-data');
        let categories = [];
        if (data) {
            try { categories = JSON.parse(data.textContent); } catch(e){ console.error(e); }
        }

        select.innerHTML = '<option value="">Select category...</option>';
        const filtered = categories.filter(c => c.type === type);
        if (filtered.length) filtered.forEach(c => select.appendChild(Object.assign(document.createElement('option'), { value: c.id, textContent: `${c.icon || '📦'} ${c.name}` })));
        else select.appendChild(Object.assign(document.createElement('option'), { value:'', textContent: `No ${type} categories`, disabled:true }));
    }

    function openTransactionModal(mode, data={}) {
        transactionForm.reset();
        document.getElementById('transaction-id').value = data.id || '';
        document.getElementById('transaction-modal-title').textContent = mode==='edit'?'Edit Transaction':'Add Transaction';
        document.getElementById('transaction-amount').value = data.amount||'';
        document.getElementById('transaction-date').value = data.date || new Date().toISOString().split('T')[0];
        document.getElementById('transaction-description').value = data.description||'';
        document.getElementById('transaction-payment').value = data.payment || 'cash';
        document.querySelector(`input[name="transaction-type"][value="${data.type||'expense'}"]`).checked = true;
        updateCategoryDropdown(data.type||'expense');
        setTimeout(() => { if(data.category) document.getElementById('transaction-category').value = data.category; }, 100);
        transactionForm.action = data.id ? `/api/transactions/${data.id}/update/` : `/api/transactions/create/`;
        showModal('transaction-modal');
    }

    // Add transaction
    document.getElementById('add-transaction-btn')?.addEventListener('click', () => openTransactionModal('add'));

    // Edit transaction
    document.querySelectorAll('.edit-transaction').forEach(btn => {
        btn.addEventListener('click', () => {
            openTransactionModal('edit', {
                id: btn.dataset.id,
                type: btn.dataset.type,
                amount: btn.dataset.amount,
                date: btn.dataset.date,
                description: btn.dataset.description,
                payment: btn.dataset.payment,
                category: btn.dataset.category
            });
        });
    });

    // Change category dropdown when type changes
    document.querySelectorAll('input[name="transaction-type"]').forEach(radio => radio.addEventListener('change', e=>updateCategoryDropdown(e.target.value)));

    // Submit transaction form
    transactionForm?.addEventListener('submit', function(e){
        e.preventDefault();
        const btn = this.querySelector('button[type="submit"]'); const orig = btn.textContent;
        btn.disabled=true; btn.textContent='Saving...';
        fetch(this.action, { method:'POST', headers:{ 'X-CSRFToken':csrftoken }, body:new FormData(this) })
            .then(r=>r.json())
            .then(d=>{ if(d.success){ showToast(d.message); hideModal('transaction-modal'); setTimeout(()=>location.reload(),800);} else showToast(d.errors||'Error'); })
            .catch(e=>{ console.error(e); showToast('Error'); })
            .finally(()=>{ btn.disabled=false; btn.textContent=orig; });
    });

    // ----------------------------
    // Delete transaction
    // ----------------------------
    document.querySelectorAll('.delete-transaction').forEach(btn=>{
        btn.addEventListener('click', ()=>{
            const id = btn.dataset.id;
            if(!confirm('Are you sure you want to delete this transaction?')) return;
            fetch(`/api/transactions/${id}/delete/`, { method:'POST', headers:{'X-CSRFToken':csrftoken,'Content-Type':'application/x-www-form-urlencoded'} })
            .then(r=>r.json())
            .then(d=>{ if(d.success){ showToast(d.message); btn.closest('tr').remove(); } else showToast(d.errors||'Error'); })
            .catch(e=>{ console.error(e); showToast('Error'); });
        });
    });

    // ----------------------------
    // Close modal buttons
    // ----------------------------
    document.querySelectorAll('.close-modal, .cancel-btn').forEach(btn=>{
        btn.addEventListener('click',()=>hideModal(btn.dataset.modal));
    });

    // Click outside to close modal
    document.querySelectorAll('.modal-container').forEach(modal=>{
        modal.addEventListener('click', e=>{ if(e.target===modal) hideModal(modal.id); });
    });

    // Escape key closes modals
    document.addEventListener('keydown', e=>{ if(e.key==='Escape') document.querySelectorAll('.modal-container[style*="display: flex"]').forEach(m=>hideModal(m.id)); });

});
document.querySelectorAll('.save-budget').forEach(button => {
    button.addEventListener('click', function () {
        const categoryItem = this.closest('.category-item');
        const categoryId = categoryItem.dataset.id;
        const budgetInput = categoryItem.querySelector('.budget-input');
        const budgetValue = budgetInput.value;

        if (budgetValue === '' || Number(budgetValue) < 0) {
            showToast('Please enter a valid budget');
            return;
        }

        fetch(`/api/categories/${categoryId}/update/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                monthly_budget: budgetValue
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast('Budget updated');
                setTimeout(() => location.reload(), 700);
            } else {
                showToast(data.errors || 'Failed to update budget');
            }
        })
        .catch(err => {
            console.error(err);
            showToast('Error updating budget');
        });
    });
});

});


