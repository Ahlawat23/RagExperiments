class FileUploader {

    escapeHTML(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    constructor() {
        this.selectedFiles = [];
        this.uploadedFiles = JSON.parse(localStorage.getItem('uploadedFiles')) || [];
        this.currentTab = 'upload';

        // Config
        this.ALLOWED_MIME = ['application/pdf']; // PDFs only (matches your endpoint)
        this.MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50MB, tweak if needed

        this.serverFiles = [];
        this.init();
    }

    init() {
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.chooseFileBtn = document.getElementById('chooseFileBtn');
        this.fileList = document.getElementById('fileList');
        this.filesContainer = document.getElementById('filesContainer');
        this.uploadBtn = document.getElementById('uploadBtn');
        this.uploadProgress = document.getElementById('uploadProgress');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        this.progressPercentage = document.getElementById('progressPercentage');

        // Tabs
        this.uploadTab = document.getElementById('uploadTab');
        this.uploadedTab = document.getElementById('uploadedTab');
        this.uploadTabContent = document.getElementById('uploadTabContent');
        this.uploadedTabContent = document.getElementById('uploadedTabContent');
        this.uploadedFilesContainer = document.getElementById('uploadedFilesContainer');
        this.uploadedCount = document.getElementById('uploadedCount');

        // Defensive: verify DOM nodes exist
        const required = [
            this.uploadArea, this.fileInput, this.chooseFileBtn, this.fileList,
            this.filesContainer, this.uploadBtn, this.uploadProgress,
            this.progressFill, this.progressText, this.progressPercentage,
            this.uploadTab, this.uploadedTab, this.uploadTabContent,
            this.uploadedTabContent, this.uploadedFilesContainer, this.uploadedCount
        ];
        if (required.some(el => !el)) {
            console.error('FileUploader: missing required DOM nodes.');
            return;
        }

        // Accessibility for drop zone
        this.uploadArea.setAttribute('role', 'button');
        this.uploadArea.setAttribute('tabindex', '0');
        this.uploadArea.setAttribute('aria-label', 'File upload area. Press Enter or Space to choose files, or drop files here.');
        this.uploadArea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.fileInput.click();
            }
        });

        this.bindEvents();
        this.updateUploadedFilesDisplay();
    }

    bindEvents() {
        // Click events
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        this.chooseFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.fileInput.click();
        });

        // File input change
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

        // Drag and drop
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));

        // Prevent default drag behaviors globally
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.addEventListener(eventName, this.preventDefaults, false);
        });

        // Upload button
        this.uploadBtn.addEventListener('click', () => this.handleUpload());

        // Tabs
        this.uploadTab.addEventListener('click', () => this.switchTab('upload'));
        this.uploadedTab.addEventListener('click', () => this.switchTab('uploaded'));

        // Delegated remove handler
        this.filesContainer.addEventListener('click', (e) => {
            const btn = e.target.closest('.remove-btn');
            if (!btn) return;
            const item = btn.closest('.file-item');
            if (!item) return;
            const idx = Number(item.dataset.index);
            if (!Number.isNaN(idx)) {
                this.removeFile(idx);
            }
        });
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    handleDragOver(e) {
        e.preventDefault();
        this.uploadArea.classList.add('drag-over');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('drag-over');
    }

    handleDrop(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        this.processFiles(files);
    }

    handleFileSelect(e) {
        const files = e.target.files;
        this.processFiles(files);
    }

    // Validation helpers
    isAllowed(file) {
        const typeOk = this.ALLOWED_MIME.includes(file.type);
        const sizeOk = file.size <= this.MAX_SIZE_BYTES;
        return { ok: typeOk && sizeOk, typeOk, sizeOk };
    }

    isDuplicate(file) {
        return this.selectedFiles.some(f =>
            f.name === file.name &&
            f.size === file.size &&
            f.lastModified === file.lastModified
        );
    }

    processFiles(files) {
        const warnings = [];
        Array.from(files).forEach(file => {
            if (this.isDuplicate(file)) {
                warnings.push(`Duplicate skipped: ${file.name}`);
                return;
            }
            const v = this.isAllowed(file);
            if (!v.ok) {
                if (!v.typeOk) warnings.push(`Only PDF allowed: ${file.name}`);
                else if (!v.sizeOk) warnings.push(`Too large: ${file.name}`);
                return;
            }
            this.selectedFiles.push(file);
        });

        if (warnings.length) {
            console.warn(warnings.join('\n'));
        }

        this.updateFileList();
        // Clear input so same file can be picked again
        this.fileInput.value = '';
    }

    updateFileList() {
        if (this.selectedFiles.length === 0) {
            this.fileList.style.display = 'none';
            return;
        }

        this.fileList.style.display = 'block';
        this.filesContainer.innerHTML = '';

        this.selectedFiles.forEach((file, index) => {
            const fileItem = this.createFileItem(file, index);
            this.filesContainer.appendChild(fileItem);
        });

        // Enable/disable upload button
        this.uploadBtn.disabled = this.selectedFiles.length === 0;
    }

    createFileItem(file, index) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.dataset.index = String(index);

        const fileExtension = this.getFileExtension(file.name);
        const fileSize = this.formatFileSize(file.size);

        fileItem.innerHTML = `
            <div class="file-info">
                <div class="file-icon">${fileExtension}</div>
                <div class="file-details">
                    <div class="file-name" title="${file.name}">${file.name}</div>
                    <div class="file-size">${fileSize}</div>
                </div>
            </div>
            <button class="remove-btn" aria-label="Remove file">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        `;

        return fileItem;
    }

    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.updateFileList();
    }

    getFileExtension(filename) {
        const hasDot = filename.lastIndexOf('.') !== -1;
        const extension = hasDot ? filename.split('.').pop().toUpperCase() : 'FILE';
        return extension.length > 4 ? 'FILE' : extension;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Public API
    getSelectedFiles() {
        return this.selectedFiles;
    }

    clearFiles() {
        this.selectedFiles = [];
        this.updateFileList();
    }

    // === Real upload wired to /upload-pdf/ ===
    async handleUpload() {
        if (this.selectedFiles.length === 0) return;

        this.uploadBtn.disabled = true;
        this.uploadProgress.style.display = 'block';
        this.resetProgress();
        this.progressText.textContent = 'Preparing upload...';

        // Build single FormData with multiple "files"
        const form = new FormData();
        this.selectedFiles.forEach(f => form.append('files', f)); // key MUST be 'files'

        // Use XHR to get real upload progress
        try {
            const responseText = await this.uploadMultiXHR('/upload-pdf/', form, (loaded, total) => {
                if (total > 0) {
                    const percent = Math.round((loaded / total) * 100);
                    this.updateProgress(percent, 'Uploading PDFs...');
                } else {
                    // Fallback: just animate text if total unknown
                    this.updateProgress(0, 'Uploading PDFs...');
                }
            });

            // Parse server summary
            let summary = {};
            try { summary = JSON.parse(responseText); } catch (_) { }

            // Compute client-side tally as backup
            const clientPdfCount = this.selectedFiles.length;

            // Update progress text based on server response contract
            if (summary && typeof summary === 'object') {
                const saved = Number(summary.saved ?? 0);
                const skipped = Number(summary.skipped ?? Math.max(0, clientPdfCount - saved));
                const message =
                    saved === 0 ? 'No PDFs saved'
                        : skipped > 0 ? 'Some files skipped (non-PDF)'
                            : 'All PDFs uploaded';

                this.updateProgress(100, message);

                // Persist uploaded metadata (no server IDs provided; store basic info)
                // If server returns details per file later, wire them here.
                if (saved > 0) {
                    const nowISO = new Date().toISOString();
                    // Add all PDFs that were in this batch; if server saved fewer,
                    // this is still fine for the UI list; your download flow is placeholder anyway.
                    this.selectedFiles.forEach(file => {
                        this.uploadedFiles.push({
                            id: Date.now() + Math.random(),
                            name: file.name,
                            size: file.size,
                            type: file.type,
                            uploadDate: nowISO
                        });
                    });
                    localStorage.setItem('uploadedFiles', JSON.stringify(this.uploadedFiles));
                }
            } else {
                // Unknown response shape
                this.updateProgress(100, 'Upload completed');
            }

            setTimeout(() => {
                this.uploadProgress.style.display = 'none';
                this.clearFiles();
                this.resetProgress();
                this.updateUploadedFilesDisplay();
            }, 1200);

        } catch (err) {
            console.error('Upload error:', err);
            this.progressText.textContent = 'Upload failed!';
            this.uploadBtn.disabled = false;
        }
    }

    uploadMultiXHR(url, formData, onProgress) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', url);

            // If you need auth:
            // xhr.setRequestHeader('Authorization', 'Bearer ...');

            xhr.upload.addEventListener('progress', (evt) => {
                if (evt.lengthComputable && typeof onProgress === 'function') {
                    onProgress(evt.loaded, evt.total);
                }
            });

            xhr.onreadystatechange = () => {
                if (xhr.readyState === 4) {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        resolve(xhr.responseText);
                    } else {
                        reject(new Error(`HTTP ${xhr.status}: ${xhr.responseText}`));
                    }
                }
            };

            xhr.onerror = () => reject(new Error('Network error'));
            xhr.send(formData);
        });
    }

    // Progress UI
    updateProgress(percentage, text) {
        const clamped = Math.max(0, Math.min(100, Number.isFinite(percentage) ? percentage : 0));
        this.progressPercentage.textContent = `${Math.round(clamped)}%`;
        this.progressFill.style.width = `${clamped}%`;
        if (text) {
            this.progressText.textContent = text;
        }
    }

    resetProgress() {
        this.progressFill.style.width = '0%';
        this.progressPercentage.textContent = '0%';
        this.progressText.textContent = 'Uploading...';
        this.uploadBtn.disabled = false;
    }

    // Tabs
    switchTab(tab) {
        this.currentTab = tab;

        this.uploadTab.classList.toggle('active', tab === 'upload');
        this.uploadedTab.classList.toggle('active', tab === 'uploaded');

        this.uploadTabContent.style.display = tab === 'upload' ? 'block' : 'none';
        this.uploadedTabContent.style.display = tab === 'uploaded' ? 'block' : 'none';

        if (tab === 'uploaded') {
            this.refreshServerUploads();
        }
    }

    updateUploadedFilesDisplay() {
        const list = this.serverFiles?.length ? this.serverFiles : this.uploadedFiles || [];
        this.uploadedCount.textContent = `${list.length} file${list.length !== 1 ? 's' : ''}`;

        if (!list.length) {
            this.uploadedFilesContainer.innerHTML = `
      <div class="empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14,2 14,8 20,8"></polyline>
        </svg>
        <p class="empty-text">No files uploaded yet</p>
        <p class="empty-subtext">Files will appear here after uploading</p>
      </div>
    `;
            return;
        }

        
        this.uploadedFilesContainer.innerHTML = list
            .map(f => this.createServerUploadedItem(f))
            .join('');
    }


    createServerUploadedItem(file) {
        const name = this.escapeHTML(file.name || '');
        const size = this.formatFileSize(file.size || 0);
        const modified = file.modified ? new Date(file.modified).toLocaleString() : '';
        const url = this.escapeHTML(file.url || '#');

        return `
    <div class="uploaded-file-item">
      <div class="uploaded-file-info">
        <div class="uploaded-file-icon">PDF</div>
        <div class="uploaded-file-details">
          <div class="uploaded-file-name" title="${name}">${name}</div>
          <div class="uploaded-file-meta">
            <span>${size}</span>
            <span>Modified: ${this.escapeHTML(modified)}</span>
          </div>
        </div>
      </div>
      <a class="download-btn" aria-label="Download file" href="${url}" download target="_blank" rel="noopener">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7,10 12,5 17,10"></polyline>
          <line x1="12" y1="5" x2="12" y2="15"></line>
        </svg>
      </a>
    </div>
  `;
    }




    createUploadedFileItem(file) {
        const fileExtension = this.getFileExtension(file.name);
        const fileSize = this.formatFileSize(file.size);
        const uploadDate = new Date(file.uploadDate).toLocaleDateString();

        return `
            <div class="uploaded-file-item">
                <div class="uploaded-file-info">
                    <div class="uploaded-file-icon">${fileExtension}</div>
                    <div class="uploaded-file-details">
                        <div class="uploaded-file-name">${file.name}</div>
                        <div class="uploaded-file-meta">
                            <span>${fileSize}</span>
                            <span>Uploaded: ${uploadDate}</span>
                        </div>
                    </div>
                </div>
                <button class="download-btn" aria-label="Download file" onclick="fileUploader.downloadFile('${file.id}')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7,10 12,5 17,10"></polyline>
                        <line x1="12" y1="5" x2="12" y2="15"></line>
                    </svg>
                </button>
            </div>
        `;
    }

    // Placeholder download
    downloadFile(fileId) {
        const file = this.uploadedFiles.find(f => f.id == fileId);
        if (file) {
            alert(`Downloading: ${file.name}`);
        }
    }

    async refreshServerUploads() {
        try {
            const res = await fetch('/list-uploads');
            if (!res.ok) throw new Error('Failed to fetch server uploads');
            const data = await res.json();
            this.serverFiles = Array.isArray(data.files) ? data.files : [];
            this.updateUploadedFilesDisplay(); // re-render with server files
        } catch (e) {
            console.error(e);
            // fallback: still render localStorage list if server call fails
            this.serverFiles = [];
            this.updateUploadedFilesDisplay();
        }
    }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    window.fileUploader = new FileUploader();
});

// Utils (optional)
window.FileUploaderUtils = {
    getFiles: () => window.fileUploader ? window.fileUploader.getSelectedFiles() : [],
    clearFiles: () => window.fileUploader ? window.fileUploader.clearFiles() : null,
    onFilesChange: (callback) => {
        if (window.fileUploader) {
            const originalUpdate = window.fileUploader.updateFileList;
            window.fileUploader.updateFileList = function () {
                originalUpdate.call(this);
                callback(this.selectedFiles);
            };
        }
    }
};
