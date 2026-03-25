/**
 * Attachment Helper Functions for Query/Comment Tests
 * Provides utilities for testing file attachments with various patterns
 */

/**
 * Generate mock attachment data for testing
 * @param {string} filename - Filename with extension
 * @param {Object} options - Additional options
 * @returns {Object} Mock attachment object
 */
function generateMockAttachment(filename, options = {}) {
    const {
        id = '',
        diskPath = null,
        bucketUrl = 'https://storage.example.com/',
        docId = 'test-doc-123'
    } = options;

    return {
        id: id,
        file_sn: filename,
        file_on: filename,
        name: filename,
        ext: filename.split('.').pop(),
        url: diskPath
            ? `${diskPath}${filename}`
            : `${bucketUrl}${docId}/attachments/${filename}`
    };
}

/**
 * Parse filename pattern for revision, version, and other metadata
 * @param {string} filename - Filename to parse
 * @returns {Object} Parsed metadata
 */
function parseFilenamePattern(filename) {
    const patterns = {
        revision: filename.match(/R(\d+)/),
        version: filename.match(/V(\d+)/),
        figure: filename.match(/Fig(?:ure)?[_\s]?(\d+)/i),
        final: /Final/i.test(filename),
        draft: /Draft/i.test(filename),
        revised: /Revised?/i.test(filename),
        supplementary: /Supp(?:lementary)?/i.test(filename)
    };

    const extension = filename.split('.').pop().toLowerCase();

    return {
        filename: filename,
        revision: patterns.revision ? patterns.revision[1] : null,
        version: patterns.version ? patterns.version[1] : null,
        figureNumber: patterns.figure ? patterns.figure[1] : null,
        isFinal: patterns.final,
        isDraft: patterns.draft,
        isRevised: patterns.revised,
        isSupplementary: patterns.supplementary,
        extension: extension,
        isImage: ['jpg', 'jpeg', 'png', 'gif', 'tif', 'tiff', 'bmp', 'svg'].includes(extension),
        isPDF: extension === 'pdf',
        isDocument: ['doc', 'docx', 'odt', 'rtf'].includes(extension)
    };
}

/**
 * Validate file against rules
 * @param {Object} file - File object or mock file
 * @param {Object} rules - Validation rules
 * @returns {Object} Validation result
 */
function validateFileAgainstRules(file, rules = {}) {
    const {
        maxSingleFileSizeMB = 100,
        maxMultiFileSizeMB = 500,
        invalidExtensions = /\.(exe|bat|cmd|sh|dll)$/i,
        allowedExtensions = null
    } = rules;

    const filename = file.name || file.filename || '';
    const fileSize = file.size || 0;
    const extension = filename.split('.').pop().toLowerCase();

    const errors = [];

    // Check invalid extensions
    if (invalidExtensions.test(filename)) {
        errors.push('Invalid file extension');
    }

    // Check allowed extensions if specified
    if (allowedExtensions && !allowedExtensions.includes(extension)) {
        errors.push(`Extension .${extension} not allowed`);
    }

    // Check file size
    const maxSizeBytes = maxSingleFileSizeMB * 1024 * 1024;
    if (fileSize > maxSizeBytes) {
        errors.push(`File size exceeds ${maxSingleFileSizeMB}MB limit`);
    }

    return {
        valid: errors.length === 0,
        errors: errors,
        filename: filename,
        extension: extension,
        size: fileSize
    };
}

/**
 * Create test file patterns for various scenarios
 * @returns {Object} Test file patterns organized by category
 */
function getTestFilePatterns() {
    return {
        images: {
            tif: [
                'Fig1_R3_Final_V2.tif',
                'Fig1Final_V2.tif',
                'Figure_1_Revised.tif',
                'Supplementary_Fig_S1.tif'
            ],
            jpg: [
                'Figure_2_Revised.jpg',
                'Chart_Data_v3.jpg',
                'Graph_Results_R2.jpg'
            ],
            png: [
                'Chart_Data_v3.png',
                'Diagram_Final.png',
                'Screenshot_V1.png'
            ]
        },
        documents: {
            pdf: [
                'Supplementary_Material_R2.pdf',
                'References_Updated.pdf',
                'Appendix_A_Final.pdf',
                'Methods_Detailed_V3.pdf'
            ],
            doc: [
                'Manuscript_Draft_v4.doc',
                'Author_Response.doc'
            ],
            docx: [
                'Author_Response.docx',
                'Cover_Letter_R1.docx'
            ]
        },
        mixed: [
            'Fig1_R3_Final_V2.tif',
            'Supplementary_Material_R2.pdf',
            'Chart_Data_v3.png',
            'Methods_Detailed_V3.pdf',
            'Figure_2_Revised.jpg'
        ],
        edgeCases: [
            'File with spaces.pdf',
            'File_with_multiple___underscores.jpg',
            'UPPERCASE_FILENAME.TIF',
            'lowercase_filename.png',
            'File.With.Multiple.Dots.v2.pdf'
        ]
    };
}

/**
 * Wait for attachment upload to complete
 * @param {import('@playwright/test').Page} page 
 * @param {string} storeId - Attachment store ID
 * @param {number} timeout - Timeout in ms
 */
async function waitForAttachmentUpload(page, storeId, timeout = 30000) {
    await page.waitForFunction(
        ({ id, maxWait }) => {
            if (!window.queryModule?.attachmentModule) return false;

            const store = window.queryModule.attachmentModule.getStore(id);
            if (!store) return false;

            // Check if upload is complete (no pending uploads)
            return store.pendingUploads.length === 0;
        },
        { storeId, maxWait: timeout },
        { timeout }
    );
}

/**
 * Get attachment store status
 * @param {import('@playwright/test').Page} page 
 * @param {string} storeId - Attachment store ID
 * @returns {Promise<Object>} Store status
 */
async function getAttachmentStoreStatus(page, storeId) {
    return await page.evaluate((id) => {
        if (!window.queryModule?.attachmentModule) {
            return { error: 'AttachmentModule not available' };
        }

        const store = window.queryModule.attachmentModule.getStore(id);
        if (!store) {
            return { error: 'Store not found' };
        }

        return {
            success: true,
            storeId: id,
            pendingCount: store.pendingUploads?.length || 0,
            existingCount: store.existingItems?.length || 0,
            deletedCount: store.deleted?.length || 0,
            pendingFiles: store.pendingUploads?.map(p => p.name) || [],
            existingFiles: store.existingItems?.map(e => e.name) || []
        };
    }, storeId);
}

/**
 * Simulate file selection in attachment module
 * @param {import('@playwright/test').Page} page 
 * @param {string} storeId - Attachment store ID
 * @param {Array<Object>} mockFiles - Array of mock file objects
 * @returns {Promise<Object>} Result of file selection
 */
async function simulateFileSelection(page, storeId, mockFiles) {
    return await page.evaluate(({ id, files }) => {
        if (!window.queryModule?.attachmentModule) {
            return { error: 'AttachmentModule not available' };
        }

        const store = window.queryModule.attachmentModule.getStore(id);
        if (!store) {
            return { error: 'Store not found' };
        }

        // Add files to pending uploads
        files.forEach(file => {
            const mockFile = {
                file: file,
                name: file.name,
                size: file.size || 1024,
                type: file.type || 'application/octet-stream',
                addedAt: Date.now()
            };
            store.pendingUploads.push(mockFile);
        });

        return {
            success: true,
            storeId: id,
            addedCount: files.length,
            totalPending: store.pendingUploads.length
        };
    }, { id: storeId, files: mockFiles });
}

/**
 * Verify attachment rendering in DOM
 * @param {import('@playwright/test').Page} page 
 * @param {string} queryId - Query/Comment ID
 * @returns {Promise<Object>} Attachment rendering status
 */
async function verifyAttachmentRendering(page, queryId) {
    return await page.evaluate((id) => {
        const query = window.queryModule?.getQuery(id);
        if (!query) {
            return { error: 'Query not found' };
        }

        const editorEl = query.editorEl;
        if (!editorEl) {
            return { error: 'Editor element not found' };
        }

        // Check for attachment attributes
        const hasDbId = editorEl.hasAttribute('data-db-id');
        const hasFileSn = editorEl.hasAttribute('data-file-sn');
        const hasFileOn = editorEl.hasAttribute('data-file-on');

        const fileSn = editorEl.getAttribute('data-file-sn') || '';
        const fileOn = editorEl.getAttribute('data-file-on') || '';

        const fileSnList = fileSn ? fileSn.split('||') : [];
        const fileOnList = fileOn ? fileOn.split('||') : [];

        return {
            success: true,
            queryId: id,
            hasAttachmentAttributes: hasDbId && hasFileSn && hasFileOn,
            attachmentCount: fileSnList.length,
            files: fileSnList.map((sn, i) => ({
                file_sn: sn,
                file_on: fileOnList[i] || ''
            })),
            stateAttachmentCount: query.attachments?.length || 0,
            synchronized: fileSnList.length === (query.attachments?.length || 0)
        };
    }, queryId);
}

/**
 * Test attachment download functionality
 * @param {import('@playwright/test').Page} page 
 * @param {string} attachmentUrl - URL of attachment to download
 * @returns {Promise<Object>} Download test result
 */
async function testAttachmentDownload(page, attachmentUrl) {
    // Note: Actual download testing would require file system access
    // This is a simulation for testing the download trigger
    return await page.evaluate((url) => {
        try {
            // Check if URL is valid
            const urlObj = new URL(url);

            return {
                success: true,
                url: url,
                protocol: urlObj.protocol,
                hostname: urlObj.hostname,
                pathname: urlObj.pathname,
                filename: urlObj.pathname.split('/').pop()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }, attachmentUrl);
}

module.exports = {
    generateMockAttachment,
    parseFilenamePattern,
    validateFileAgainstRules,
    getTestFilePatterns,
    waitForAttachmentUpload,
    getAttachmentStoreStatus,
    simulateFileSelection,
    verifyAttachmentRendering,
    testAttachmentDownload
};
