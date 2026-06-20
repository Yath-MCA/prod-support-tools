// ===================================
// IMPACT Search - Application Logic
// ===================================

class SearchApp {
    constructor() {
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.searchResults = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupDateTypeToggle();
    }

    // ===================================
    // EVENT LISTENERS
    // ===================================

    setupEventListeners() {
        // Fetch button
        document.getElementById('fetchBtn').addEventListener('click', () => {
            this.fetchDocuments();
        });

        // Copy button
        document.getElementById('copyBtn').addEventListener('click', () => {
            this.copyFiles();
        });

        // Search button
        document.getElementById('searchBtn').addEventListener('click', () => {
            this.searchFiles();
        });
    }

    setupDateTypeToggle() {
        const radioButtons = document.querySelectorAll('input[name="dateType"]');
        const daysGroup = document.getElementById('daysGroup');
        const dateGroup = document.getElementById('dateGroup');

        radioButtons.forEach(radio => {
            radio.addEventListener('change', (e) => {
                if (e.target.value === 'days') {
                    daysGroup.classList.remove('hidden');
                    dateGroup.classList.add('hidden');
                } else {
                    daysGroup.classList.add('hidden');
                    dateGroup.classList.remove('hidden');
                }
            });
        });
    }

    // ===================================
    // API CALLS
    // ===================================

    async fetchDocuments() {
        const dateType = document.querySelector('input[name="dateType"]:checked').value;
        const daysInput = document.getElementById('daysInput').value;
        const dateInput = document.getElementById('dateInput').value;
        const rootFolder = document.getElementById('rootFolderInput').value.trim();
        const outputFolder = document.getElementById('outputFolderInput').value.trim();

        const requestBody = {};

        if (dateType === 'days') {
            requestBody.days = parseInt(daysInput);
        } else {
            if (!dateInput) {
                this.showToast('Please select a date', 'error');
                return;
            }
            requestBody.date_str = dateInput;
        }

        // Add root folder if specified
        if (rootFolder) {
            requestBody.root_folder = rootFolder;
        }
        if (outputFolder) {
            requestBody.output_folder = outputFolder;
        }

        this.showLoading(true);

        try {
            const response = await fetch('/fetch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                const errorData = await this.readErrorDetail(response);
                throw new Error(errorData || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.displayFetchResults(data);
            this.showToast('Documents fetched successfully!', 'success');
        } catch (error) {
            console.error('Error fetching documents:', error);
            this.showToast('Error fetching documents: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async readErrorDetail(response) {
        try {
            const payload = await response.json();
            return payload.detail || payload.message || '';
        } catch (error) {
            return '';
        }
    }

    async copyFiles() {
        const batchFile = document.getElementById('batchFileInput').value.trim();
        const rootFolder = document.getElementById('rootFolderInput').value.trim();

        if (!batchFile) {
            this.showToast('Please enter a batch file path', 'error');
            return;
        }

        this.showLoading(true);

        try {
            const requestBody = {
                batch_file: batchFile
            };

            // Add root folder if specified
            if (rootFolder) {
                requestBody.root_folder = rootFolder;
            }

            console.log('📤 Sending /copy request with body:', requestBody);

            const response = await fetch('/copy', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                const errorData = await this.readErrorDetail(response);
                throw new Error(errorData || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.displayCopyResults(data);
            this.showToast('Files copied successfully!', 'success');
        } catch (error) {
            console.error('Error copying files:', error);
            this.showToast('Error copying files: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async searchFiles() {
        const batchFolder = document.getElementById('batchFolderInput').value.trim();
        const searchTermsText = document.getElementById('searchTermsInput').value.trim();

        if (!batchFolder) {
            this.showToast('Please enter a batch folder path', 'error');
            return;
        }

        if (!searchTermsText) {
            this.showToast('Please enter at least one search term', 'error');
            return;
        }

        // Parse search terms
        const searchTerms = searchTermsText
            .split('\n')
            .map(term => term.trim())
            .filter(term => term.length > 0);

        if (searchTerms.length === 0) {
            this.showToast('Please enter valid search terms', 'error');
            return;
        }

        this.showLoading(true);

        try {
            const response = await fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    batch_folder: batchFolder,
                    search_terms: searchTerms
                })
            });

            if (!response.ok) {
                const errorData = await this.readErrorDetail(response);
                throw new Error(errorData || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.searchResults = data.results || [];
            this.currentPage = 1;
            this.displaySearchResults();
            this.showToast(`Found ${this.searchResults.length} results!`, 'success');
        } catch (error) {
            console.error('Error searching files:', error);
            this.showToast('Error searching files: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // ===================================
    // DISPLAY METHODS
    // ===================================

    displayFetchResults(data) {
        const resultsContainer = document.getElementById('fetchResults');
        const batchList = document.getElementById('batchList');
        const batchCount = document.getElementById('batchCount');

        if (!data.batches || data.batches.length === 0) {
            this.showToast('No batches generated. Try a different date range.', 'warning');
            resultsContainer.classList.add('hidden');
            return;
        }

        batchCount.textContent = data.batches.length;
        batchList.innerHTML = '';

        data.batches.forEach((batch, index) => {
            const batchItem = document.createElement('div');
            batchItem.className = 'batch-item';
            batchItem.textContent = batch;
            batchItem.title = 'Click to copy path';
            batchItem.addEventListener('click', () => {
                this.copyToClipboard(batch);
                this.showToast('Batch path copied to clipboard!', 'success');
            });
            batchList.appendChild(batchItem);
        });

        document.getElementById('batchFileInput').value = data.batches[0];

        resultsContainer.classList.remove('hidden');
    }

    displayCopyResults(data) {
        const resultsContainer = document.getElementById('copyResults');
        const copiedCount = document.getElementById('copiedCount');
        const skippedCount = document.getElementById('skippedCount');
        const totalCount = document.getElementById('totalCount');
        const destPath = document.getElementById('destPath');

        copiedCount.textContent = data.copied || 0;
        skippedCount.textContent = data.skipped || 0;
        totalCount.textContent = data.total || 0;
        destPath.textContent = data.destination || 'N/A';

        if (data.destination) {
            document.getElementById('batchFolderInput').value = data.destination;
        }

        resultsContainer.classList.remove('hidden');
    }

    displaySearchResults() {
        const resultsCard = document.getElementById('searchResults');
        const resultCount = document.getElementById('resultCount');
        const tableBody = document.getElementById('resultsTableBody');

        if (this.searchResults.length === 0) {
            resultsCard.classList.add('hidden');
            return;
        }

        resultCount.textContent = this.searchResults.length;
        tableBody.innerHTML = '';

        // Pagination
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = Math.min(startIndex + this.itemsPerPage, this.searchResults.length);
        const paginatedResults = this.searchResults.slice(startIndex, endIndex);

        paginatedResults.forEach(result => {
            const row = document.createElement('tr');

            // Document ID
            const docIdCell = document.createElement('td');
            docIdCell.textContent = result.doc_id || 'N/A';
            row.appendChild(docIdCell);

            // Client
            const clientCell = document.createElement('td');
            clientCell.textContent = result.client || 'N/A';
            row.appendChild(clientCell);

            // File ID
            const fileIdCell = document.createElement('td');
            fileIdCell.textContent = result.file_id || 'N/A';
            row.appendChild(fileIdCell);

            // Emails
            const emailsCell = document.createElement('td');
            if (result.emails && result.emails.length > 0) {
                const emailPills = document.createElement('div');
                emailPills.className = 'email-pills';
                result.emails.forEach(email => {
                    const pill = document.createElement('span');
                    pill.className = 'email-pill';
                    pill.textContent = email;
                    emailPills.appendChild(pill);
                });
                emailsCell.appendChild(emailPills);
            } else {
                emailsCell.textContent = 'N/A';
            }
            row.appendChild(emailsCell);

            // Found Terms
            const termsCell = document.createElement('td');
            if (result.found_keys && result.found_keys.length > 0) {
                const termPills = document.createElement('div');
                termPills.className = 'term-pills';
                result.found_keys.forEach(term => {
                    const pill = document.createElement('span');
                    pill.className = 'term-pill';
                    pill.textContent = term;
                    termPills.appendChild(pill);
                });
                termsCell.appendChild(termPills);
            } else {
                termsCell.textContent = 'N/A';
            }
            row.appendChild(termsCell);

            // Actions
            const actionsCell = document.createElement('td');
            const copyBtn = document.createElement('button');
            copyBtn.className = 'btn btn-primary';
            copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
            copyBtn.style.padding = '0.5rem';
            copyBtn.title = 'Copy Document ID';
            copyBtn.addEventListener('click', () => {
                this.copyToClipboard(result.doc_id);
                this.showToast('Document ID copied!', 'success');
            });
            actionsCell.appendChild(copyBtn);
            row.appendChild(actionsCell);

            tableBody.appendChild(row);
        });

        this.renderPagination();
        resultsCard.classList.remove('hidden');
    }

    renderPagination() {
        const pagination = document.getElementById('pagination');
        const totalPages = Math.ceil(this.searchResults.length / this.itemsPerPage);

        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }

        pagination.innerHTML = '';

        // Previous button
        const prevBtn = document.createElement('button');
        prevBtn.className = 'page-btn';
        prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
        prevBtn.disabled = this.currentPage === 1;
        prevBtn.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.displaySearchResults();
            }
        });
        pagination.appendChild(prevBtn);

        // Page numbers
        const maxVisiblePages = 5;
        let startPage = Math.max(1, this.currentPage - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

        if (endPage - startPage < maxVisiblePages - 1) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('button');
            pageBtn.className = 'page-btn';
            if (i === this.currentPage) {
                pageBtn.classList.add('active');
            }
            pageBtn.textContent = i;
            pageBtn.addEventListener('click', () => {
                this.currentPage = i;
                this.displaySearchResults();
            });
            pagination.appendChild(pageBtn);
        }

        // Next button
        const nextBtn = document.createElement('button');
        nextBtn.className = 'page-btn';
        nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
        nextBtn.disabled = this.currentPage === totalPages;
        nextBtn.addEventListener('click', () => {
            if (this.currentPage < totalPages) {
                this.currentPage++;
                this.displaySearchResults();
            }
        });
        pagination.appendChild(nextBtn);
    }

    // ===================================
    // UTILITY METHODS
    // ===================================

    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (show) {
            overlay.classList.remove('hidden');
        } else {
            overlay.classList.add('hidden');
        }
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        let icon = 'fa-info-circle';
        if (type === 'success') icon = 'fa-check-circle';
        if (type === 'error') icon = 'fa-exclamation-circle';
        if (type === 'warning') icon = 'fa-exclamation-triangle';

        toast.innerHTML = `
            <i class="fas ${icon}"></i>
            <div class="toast-message">${message}</div>
        `;

        container.appendChild(toast);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 5000);
    }

    copyToClipboard(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
        }
    }
}

// ===================================
// INITIALIZE APP
// ===================================

document.addEventListener('DOMContentLoaded', () => {
    new SearchApp();
});
