// Manufacturing Maintenance Agent - Frontend JavaScript

class MaintenanceAgent {
    constructor() {
        this.apiBase = '';  // Use relative URLs since we're serving from the same server
        this.chatHistory = [];  // Store chat history
        this.initializeEventListeners();
        this.loadDocuments();
    }

    initializeEventListeners() {
        // File upload
        const fileInput = document.getElementById('fileInput');
        const dropZone = document.getElementById('dropZone');
        const uploadBtn = document.getElementById('uploadBtn');
        const documentsBtn = document.getElementById('documentsBtn');
        const askBtn = document.getElementById('askBtn');
        const questionInput = document.getElementById('questionInput');
        const refreshDocsBtn = document.getElementById('refreshDocsBtn');

        // File input events
        dropZone.addEventListener('click', (e) => {
            e.preventDefault();
            fileInput.click();
        });
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e.target.files));

        // Drag and drop
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('border-blue-400', 'bg-blue-50');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-blue-400', 'bg-blue-50');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-blue-400', 'bg-blue-50');
            this.handleFileSelect(e.dataTransfer.files);
        });

        // Button events
        uploadBtn.addEventListener('click', () => this.showSection('upload'));
        documentsBtn.addEventListener('click', () => this.showSection('documents'));
        askBtn.addEventListener('click', () => this.askQuestion());
        refreshDocsBtn.addEventListener('click', () => this.loadDocuments());

        // Question input enter key
        questionInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.askQuestion();
            }
        });

        // Suggestion buttons
        document.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                questionInput.value = e.target.textContent;
                questionInput.focus();
            });
        });

        // Chat box functionality
        const chatInput = document.getElementById('chatInput');
        const chatSend = document.getElementById('chatSend');

        // Chat send button
        chatSend.addEventListener('click', () => this.sendChatMessage());

        // Chat input enter key
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendChatMessage();
            }
        });
    }

    async handleFileSelect(files) {
        if (files.length === 0) return;

        const validFiles = Array.from(files).filter(file => 
            file.type === 'application/pdf' || file.type === 'text/plain'
        );

        if (validFiles.length === 0) {
            this.showToast('Please select PDF or TXT files only.', 'error');
            return;
        }

        if (validFiles.length !== files.length) {
            this.showToast(`Uploading ${validFiles.length} valid files (${files.length - validFiles.length} invalid files skipped).`, 'warning');
        }

        await this.uploadFiles(validFiles);
    }

    async uploadFiles(files) {
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));

        this.showLoading('Uploading and processing documents...');

        try {
            const response = await fetch(`${this.apiBase}/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const result = await response.json();
            this.showToast(`Successfully processed ${result.processed_documents.length} documents!`, 'success');
            this.loadDocuments();
            this.showSection('query');

        } catch (error) {
            console.error('Upload error:', error);
            this.showToast(`Upload failed: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async askQuestion() {
        const question = document.getElementById('questionInput').value.trim();
        if (!question) {
            this.showToast('Please enter a question.', 'warning');
            return;
        }

        // Disable the ask button to prevent multiple requests
        const askBtn = document.getElementById('askBtn');
        const originalText = askBtn.innerHTML;
        askBtn.disabled = true;
        askBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Searching...';

        // Clear previous results
        document.getElementById('resultsSection').classList.add('hidden');
        
        this.showLoading('Searching for relevant information...');

        try {
            const response = await fetch(`${this.apiBase}/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question })
            });

            if (!response.ok) {
                throw new Error(`Query failed: ${response.statusText}`);
            }

            const result = await response.json();
            this.displayResults(result);
            
            // Clear the question input for next question
            document.getElementById('questionInput').value = '';

        } catch (error) {
            console.error('Query error:', error);
            this.showToast(`Query failed: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
            // Re-enable the ask button
            askBtn.disabled = false;
            askBtn.innerHTML = originalText;
        }
    }

    displayResults(result) {
        const resultsSection = document.getElementById('resultsSection');
        const answerContent = document.getElementById('answerContent');
        const relevantSections = document.getElementById('relevantSections');

        // Display answer
        answerContent.innerHTML = `
            <div class="bg-green-50 border-l-4 border-green-400 p-4 rounded">
                <div class="flex items-start">
                    <i class="fas fa-check-circle text-green-400 mt-1 mr-3"></i>
                    <div class="flex-1">
                        <div class="text-gray-800 leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto">${this.escapeHtml(result.answer)}</div>
                    </div>
                </div>
            </div>
        `;

        // Display relevant sections
        if (result.relevant_sections && result.relevant_sections.length > 0) {
            relevantSections.innerHTML = result.relevant_sections.map((section, index) => `
                <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <div class="flex items-center mb-2">
                        <span class="text-sm font-medium text-blue-600">${this.escapeHtml(section.source)}</span>
                    </div>
                    <div class="text-gray-700 text-sm leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto">${this.escapeHtml(section.content)}</div>
                </div>
            `).join('');
        } else {
            relevantSections.innerHTML = '<p class="text-gray-500 text-center py-4">No relevant sections found.</p>';
        }

        resultsSection.classList.remove('hidden');
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    async loadDocuments() {
        try {
            const response = await fetch(`${this.apiBase}/documents`);
            if (!response.ok) {
                throw new Error(`Failed to load documents: ${response.statusText}`);
            }

            const result = await response.json();
            this.displayDocuments(result.documents);

        } catch (error) {
            console.error('Error loading documents:', error);
            this.showToast('Failed to load documents.', 'error');
        }
    }

    displayDocuments(documents) {
        const documentsList = document.getElementById('documentsList');

        if (documents.length === 0) {
            documentsList.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <i class="fas fa-folder-open text-4xl mb-4"></i>
                    <p>No documents uploaded yet.</p>
                    <p class="text-sm">Upload some equipment manuals to get started.</p>
                </div>
            `;
            return;
        }

        documentsList.innerHTML = documents.map(doc => `
            <div class="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div class="flex items-center space-x-3">
                    <i class="fas fa-file-pdf text-red-500 text-xl"></i>
                    <div>
                        <h4 class="font-medium text-gray-800">${this.escapeHtml(doc.filename)}</h4>
                        <p class="text-sm text-gray-600">${doc.chunk_count} chunks • ${this.formatFileSize(doc.total_size)}</p>
                    </div>
                </div>
                <button onclick="maintenanceAgent.deleteDocument('${this.escapeHtml(doc.filename)}')" 
                        class="text-red-500 hover:text-red-700 transition-colors">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `).join('');
    }

    async deleteDocument(filename) {
        if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
            return;
        }

        try {
            const response = await fetch(`${this.apiBase}/documents/${encodeURIComponent(filename)}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`Failed to delete document: ${response.statusText}`);
            }

            this.showToast('Document deleted successfully.', 'success');
            this.loadDocuments();

        } catch (error) {
            console.error('Error deleting document:', error);
            this.showToast('Failed to delete document.', 'error');
        }
    }

    showSection(section) {
        // Hide all sections
        document.getElementById('uploadSection').classList.add('hidden');
        document.getElementById('querySection').classList.add('hidden');
        document.getElementById('resultsSection').classList.add('hidden');
        document.getElementById('documentsSection').classList.add('hidden');

        // Show selected section
        document.getElementById(`${section}Section`).classList.remove('hidden');
    }

    showLoading(text = 'Processing...') {
        document.getElementById('loadingText').textContent = text;
        document.getElementById('loadingOverlay').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loadingOverlay').classList.add('hidden');
    }

    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer');
        const toastId = Date.now();
        
        const colors = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-yellow-500',
            info: 'bg-blue-500'
        };

        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        const toast = document.createElement('div');
        toast.id = `toast-${toastId}`;
        toast.className = `${colors[type]} text-white px-4 py-3 rounded-lg shadow-lg flex items-center space-x-2 fade-in`;
        toast.innerHTML = `
            <i class="${icons[type]}"></i>
            <span>${this.escapeHtml(message)}</span>
            <button onclick="this.parentElement.remove()" class="ml-2 text-white hover:text-gray-200">
                <i class="fas fa-times"></i>
            </button>
        `;

        toastContainer.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            const toastElement = document.getElementById(`toast-${toastId}`);
            if (toastElement) {
                toastElement.remove();
            }
        }, 5000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async sendChatMessage() {
        const chatInput = document.getElementById('chatInput');
        const chatSend = document.getElementById('chatSend');
        
        const message = chatInput.value.trim();
        if (!message) return;

        // Clear input and disable send button
        chatInput.value = '';
        chatSend.disabled = true;
        chatSend.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        try {
            // Send to API
            const response = await fetch(`${this.apiBase}/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question: message })
            });

            if (!response.ok) {
                throw new Error(`Query failed: ${response.statusText}`);
            }

            const result = await response.json();
            
            // Show result in main query section
            this.displayResults(result);
            
            // Store in chat history
            this.chatHistory.push({
                question: message,
                answer: result.answer,
                timestamp: new Date()
            });

            // Show success toast
            this.showToast('Answer displayed above!', 'success');

        } catch (error) {
            console.error('Chat error:', error);
            this.showToast('Sorry, I encountered an error. Please try again.', 'error');
        } finally {
            // Re-enable send button
            chatSend.disabled = false;
            chatSend.innerHTML = '<i class="fas fa-paper-plane"></i>';
        }
    }


}

// Initialize the application
const maintenanceAgent = new MaintenanceAgent();
