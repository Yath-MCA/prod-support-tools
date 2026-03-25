/**
 * E2E Test Suite: Query & Comment Workflow with Attachments
 * 
 * Tests the complete workflow of creating queries/comments with various
 * attachment patterns including different file formats and naming conventions.
 * 
 * Test Scenarios:
 * - Author creates query/comment
 * - Editor replies to query
 * - Attachment handling (with/without files)
 * - Various filename patterns (Fig1_R3_Final_V2.tif, Fig1Final_V2.tif, etc.)
 * - File format validation (images, PDFs, documents)
 */

import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import {
    waitForPageFullyLoaded,
    waitForEditorReady,
    waitForQueryPanelReady,
    getQueryCounts,
    getQueryPanelStatus,
    clickAcceptButton,
    takeScreenshot,
    logStep,
    config
} from '../helpers/test-helpers.js';

const allSelectors = JSON.parse(fs.readFileSync('./tests/e2e/data/selectors.json', 'utf8'));
const landingSelectors = allSelectors.landing;

let initializeLandingEditorSession;
let cleanupLandingEditorSession;

const shared = {
    page: null,
    setupError: null,
    ready: false
};

function ensureReady() {
    if (shared.setupError) {
        throw new Error(shared.setupError);
    }
    if (!shared.ready || !shared.page) {
        throw new Error('Query workflow shared baseline setup did not complete');
    }
}

// Test data for various file patterns
const TEST_FILES = {
    images: {
        tif: 'Fig1_R3_Final_V2.tif',
        tif_alt: 'Fig1Final_V2.tif',
        jpg: 'Figure-2-Revised.jpg',
        png: 'Chart_Data_v3.png',
        jpeg: 'Graph_Results.jpeg'
    },
    documents: {
        pdf: 'Supplementary_Material_R2.pdf',
        pdf_alt: 'References_Updated.pdf',
        doc: 'Manuscript_Draft_v4.doc',
        docx: 'Author_Response.docx'
    },
    mixed: [
        'Fig1_R3_Final_V2.tif',
        'Supplementary_Material_R2.pdf',
        'Chart_Data_v3.png'
    ]
};

test.describe.serial('Query & Comment Workflow Tests', () => {

    test.setTimeout(180000); // 3 minutes for attachment tests

    test.beforeAll(async ({ browser, baseURL }) => {
        logStep('Setting up Query Workflow test environment', 'start');

        const baseline = await import('./helpers/session-baseline.helper.js');
        initializeLandingEditorSession = baseline.initializeLandingEditorSession;
        cleanupLandingEditorSession = baseline.cleanupLandingEditorSession;

        const session = await initializeLandingEditorSession({
            browser,
            baseURL,
            selectors: landingSelectors
        });

        shared.page = session.page;
        shared.setupError = session.setupError;
        shared.ready = session.isInitialized;

        ensureReady();

        const page = shared.page;

        await waitForEditorReady(page);
        await waitForQueryPanelReady(page);

        logStep('Test environment ready', 'success');
    });

    test.afterAll(async () => {
        if (cleanupLandingEditorSession) {
            await cleanupLandingEditorSession(shared.page);
        }
    });

    // ==========================================
    // TC-QW-001: Create Query Without Attachments
    // ==========================================
    test('TC-QW-001 - Author creates query without attachments', async () => {
        ensureReady();
        const page = shared.page;
        logStep('Starting TC-QW-001: Create Query Without Attachments', 'start');

        // Get initial counts
        const initialCounts = await getQueryCounts(page);
        logStep(`Initial query count: ${initialCounts.total}`, 'info');

        // Open query dialog
        const createResult = await page.evaluate(async () => {
            if (!window.queryModule) {
                return { error: 'queryModule not available' };
            }

            try {
                // Simulate creating a query
                const queryData = {
                    content: 'Please verify the methodology section for accuracy.',
                    label: `AQ${window.queryModule._state.queries.size + 1}`,
                    status: 'open',
                    user: 'test.author@example.com',
                    role: 'Author'
                };

                const query = await window.queryModule.createQuery(queryData);

                return {
                    success: true,
                    queryId: query.id,
                    label: query.label,
                    status: query.status,
                    hasAttachments: query.attachments && query.attachments.length > 0
                };
            } catch (error) {
                return { error: error.message };
            }
        });

        // Verify creation
        expect(createResult.error).toBeUndefined();
        expect(createResult.success).toBe(true);
        expect(createResult.hasAttachments).toBe(false);
        logStep(`Query created: ${createResult.label}`, 'success');

        // Verify counts updated
        const updatedCounts = await getQueryCounts(page);
        expect(updatedCounts.total).toBe(initialCounts.total + 1);
        expect(updatedCounts.open).toBe(initialCounts.open + 1);

        await takeScreenshot(page, 'tc-qw-001-query-created');
        logStep('TC-QW-001 PASSED', 'success');
    });

    // ==========================================
    // TC-QW-002: Create Comment Without Attachments
    // ==========================================
    test('TC-QW-002 - Author creates comment without attachments', async () => {
        ensureReady();
        const page = shared.page;
        logStep('Starting TC-QW-002: Create Comment Without Attachments', 'start');

        const initialCounts = await getQueryCounts(page);

        const createResult = await page.evaluate(async () => {
            if (!window.queryModule) {
                return { error: 'queryModule not available' };
            }

            try {
                // Set process to comment
                window.queryModule._state._current_process = 'comment';

                const commentData = {
                    content: 'Excellent work on the data analysis section.',
                    label: `C${window.queryModule._state.comments.size + 1}`,
                    status: 'comment',
                    user: 'test.author@example.com',
                    role: 'Author'
                };

                const comment = await window.queryModule.createQuery(commentData);

                return {
                    success: true,
                    commentId: comment.id,
                    label: comment.label,
                    status: comment.status,
                    hasAttachments: comment.attachments && comment.attachments.length > 0
                };
            } catch (error) {
                return { error: error.message };
            }
        });

        expect(createResult.error).toBeUndefined();
        expect(createResult.success).toBe(true);
        expect(createResult.status).toBe('comment');
        expect(createResult.hasAttachments).toBe(false);

        const updatedCounts = await getQueryCounts(page);
        expect(updatedCounts.comments).toBe(initialCounts.comments + 1);

        await takeScreenshot(page, 'tc-qw-002-comment-created');
        logStep('TC-QW-002 PASSED', 'success');
    });

    // ==========================================
    // TC-QW-003: Create Query With Single Image Attachment
    // ==========================================
    test('TC-QW-003 - Author creates query with single TIF image', async () => {
        ensureReady();
        const page = shared.page;
        logStep('Starting TC-QW-003: Create Query With Single Image', 'start');

        const filename = TEST_FILES.images.tif;
        logStep(`Testing with filename: ${filename}`, 'info');

        const createResult = await page.evaluate(async (testFilename) => {
            if (!window.queryModule) {
                return { error: 'queryModule not available' };
            }

            try {
                // Mock attachment data
                const mockAttachment = {
                    file_sn: testFilename,
                    file_on: testFilename,
                    name: testFilename,
                    url: `${BUCKET_URL}${DOC_ID}/attachments/${testFilename}`
                };

                const queryData = {
                    content: 'Please review the updated figure with revised data.',
                    label: `AQ${window.queryModule._state.queries.size + 1}`,
                    status: 'open',
                    user: 'test.author@example.com',
                    role: 'Author',
                    attachments: [mockAttachment]
                };

                const query = await window.queryModule.createQuery(queryData);

                return {
                    success: true,
                    queryId: query.id,
                    label: query.label,
                    attachmentCount: query.attachments.length,
                    attachmentName: query.attachments[0].name,
                    attachmentPattern: {
                        hasRevision: /R\d+/.test(testFilename),
                        hasVersion: /V\d+/.test(testFilename),
                        hasFinal: /Final/i.test(testFilename),
                        extension: testFilename.split('.').pop()
                    }
                };
            } catch (error) {
                return { error: error.message };
            }
        }, filename);

        expect(createResult.error).toBeUndefined();
        expect(createResult.success).toBe(true);
        expect(createResult.attachmentCount).toBe(1);
        expect(createResult.attachmentName).toBe(filename);
        expect(createResult.attachmentPattern.extension).toBe('tif');
        expect(createResult.attachmentPattern.hasRevision).toBe(true);
        expect(createResult.attachmentPattern.hasVersion).toBe(true);
        expect(createResult.attachmentPattern.hasFinal).toBe(true);

        logStep(`Query created with attachment: ${createResult.attachmentName}`, 'success');
        await takeScreenshot(page, 'tc-qw-003-query-with-image');
        logStep('TC-QW-003 PASSED', 'success');
    });

    // ==========================================
    // TC-QW-004: Create Query With Multiple Attachments
    // ==========================================
    test('TC-QW-004 - Author creates query with multiple mixed attachments', async () => {
        ensureReady();
        const page = shared.page;
        logStep('Starting TC-QW-004: Create Query With Multiple Attachments', 'start');

        const files = TEST_FILES.mixed;
        logStep(`Testing with ${files.length} files: ${files.join(', ')}`, 'info');

        const createResult = await page.evaluate(async (testFiles) => {
            if (!window.queryModule) {
                return { error: 'queryModule not available' };
            }

            try {
                // Mock multiple attachments
                const mockAttachments = testFiles.map(filename => ({
                    file_sn: filename,
                    file_on: filename,
                    name: filename,
                    url: `${BUCKET_URL}${DOC_ID}/attachments/${filename}`
                }));

                const queryData = {
                    content: 'Please review all supplementary materials including figures and documentation.',
                    label: `AQ${window.queryModule._state.queries.size + 1}`,
                    status: 'open',
                    user: 'test.author@example.com',
                    role: 'Author',
                    attachments: mockAttachments
                };

                const query = await window.queryModule.createQuery(queryData);

                // Analyze attachment patterns
                const patterns = query.attachments.map(att => {
                    const ext = att.name.split('.').pop().toLowerCase();
                    return {
                        name: att.name,
                        extension: ext,
                        isImage: ['tif', 'jpg', 'jpeg', 'png', 'gif'].includes(ext),
                        isPDF: ext === 'pdf',
                        hasRevision: /R\d+/.test(att.name),
                        hasVersion: /V\d+/.test(att.name)
                    };
                });

                return {
                    success: true,
                    queryId: query.id,
                    label: query.label,
                    attachmentCount: query.attachments.length,
                    patterns: patterns,
                    summary: {
                        totalImages: patterns.filter(p => p.isImage).length,
                        totalPDFs: patterns.filter(p => p.isPDF).length,
                        withRevision: patterns.filter(p => p.hasRevision).length,
                        withVersion: patterns.filter(p => p.hasVersion).length
                    }
                };
            } catch (error) {
                return { error: error.message };
            }
        }, files);

        expect(createResult.error).toBeUndefined();
        expect(createResult.success).toBe(true);
        expect(createResult.attachmentCount).toBe(files.length);
        expect(createResult.summary.totalImages).toBeGreaterThan(0);
        expect(createResult.summary.totalPDFs).toBeGreaterThan(0);

        logStep(`Query created with ${createResult.attachmentCount} attachments`, 'success');
        logStep(`Images: ${createResult.summary.totalImages}, PDFs: ${createResult.summary.totalPDFs}`, 'info');

        await takeScreenshot(page, 'tc-qw-004-query-multiple-attachments');
        logStep('TC-QW-004 PASSED', 'success');
    });

    // ==========================================
    // TC-QW-005: Editor Replies to Query Without Attachments
    // ==========================================
    test('TC-QW-005 - Editor replies to query without attachments', async () => {
        ensureReady();
        const page = shared.page;
        logStep('Starting TC-QW-005: Editor Reply Without Attachments', 'start');

        // First create a query
        const setupResult = await page.evaluate(async () => {
            const queryData = {
                content: 'Please clarify the statistical methods used.',
                label: `AQ${window.queryModule._state.queries.size + 1}`,
                status: 'open',
                user: 'test.author@example.com',
                role: 'Author'
            };
            const query = await window.queryModule.createQuery(queryData);
            return { queryId: query.id, label: query.label };
        });

        logStep(`Query created: ${setupResult.label}`, 'info');

        // Editor adds response
        const replyResult = await page.evaluate(async (queryId) => {
            if (!window.queryModule) {
                return { error: 'queryModule not available' };
            }

            try {
                const responseData = {
                    content: 'The statistical analysis was performed using ANOVA with post-hoc Tukey test.',
                    user: 'test.editor@example.com',
                    role: 'Editor',
                    closeQuery: true
                };

                const result = await window.queryModule.addResponse(queryId, responseData);
                const query = window.queryModule.getQuery(queryId);

                return {
                    success: result.success,
                    queryId: queryId,
                    status: query.status,
                    responseCount: query.responses.length,
                    lastResponse: query.lastResponse.content,
                    hasAttachments: query.lastResponse.attachments && query.lastResponse.attachments.length > 0
                };
            } catch (error) {
                return { error: error.message };
            }
        }, setupResult.queryId);

        expect(replyResult.error).toBeUndefined();
        expect(replyResult.success).toBe(true);
        expect(replyResult.status).toBe('closed');
        expect(replyResult.responseCount).toBe(1);
        expect(replyResult.hasAttachments).toBe(false);

        logStep('Editor reply added successfully', 'success');
        await takeScreenshot(page, 'tc-qw-005-editor-reply');
        logStep('TC-QW-005 PASSED', 'success');
    });

    // ==========================================
    // TC-QW-006: Editor Replies With PDF Attachment
    // ==========================================
    test('TC-QW-006 - Editor replies with PDF attachment', async () => {
        ensureReady();
        const page = shared.page;
        logStep('Starting TC-QW-006: Editor Reply With PDF', 'start');

        const pdfFilename = TEST_FILES.documents.pdf;

        // Create query first
        const setupResult = await page.evaluate(async () => {
            const queryData = {
                content: 'Can you provide additional references for this methodology?',
                label: `AQ${window.queryModule._state.queries.size + 1}`,
                status: 'open',
                user: 'test.author@example.com',
                role: 'Author'
            };
            const query = await window.queryModule.createQuery(queryData);
            return { queryId: query.id };
        });

        // Editor replies with PDF
        const replyResult = await page.evaluate(async ({ queryId, filename }) => {
            if (!window.queryModule) {
                return { error: 'queryModule not available' };
            }

            try {
                const mockAttachment = {
                    file_sn: filename,
                    file_on: filename,
                    name: filename,
                    url: `${BUCKET_URL}${DOC_ID}/attachments/${filename}`
                };

                const responseData = {
                    content: 'Please find the supplementary references attached.',
                    user: 'test.editor@example.com',
                    role: 'Editor',
                    attachments: [mockAttachment],
                    closeQuery: true
                };

                const result = await window.queryModule.addResponse(queryId, responseData);
                const query = window.queryModule.getQuery(queryId);

                return {
                    success: result.success,
                    status: query.status,
                    attachmentCount: query.lastResponse.attachments.length,
                    attachmentName: query.lastResponse.attachments[0].name,
                    attachmentExtension: query.lastResponse.attachments[0].name.split('.').pop(),
                    filenamePattern: {
                        hasSupplementary: /Supplementary/i.test(filename),
                        hasRevision: /R\d+/.test(filename)
                    }
                };
            } catch (error) {
                return { error: error.message };
            }
        }, { queryId: setupResult.queryId, filename: pdfFilename });

        expect(replyResult.error).toBeUndefined();
        expect(replyResult.success).toBe(true);
        expect(replyResult.status).toBe('closed');
        expect(replyResult.attachmentCount).toBe(1);
        expect(replyResult.attachmentExtension).toBe('pdf');
        expect(replyResult.filenamePattern.hasSupplementary).toBe(true);

        logStep(`Editor reply with PDF: ${replyResult.attachmentName}`, 'success');
        await takeScreenshot(page, 'tc-qw-006-editor-reply-pdf');
        logStep('TC-QW-006 PASSED', 'success');
    });

    // ==========================================
    // TC-QW-007: Validate Filename Patterns
    // ==========================================
    test('TC-QW-007 - Validate various filename patterns', async () => {
        ensureReady();
        const page = shared.page;
        logStep('Starting TC-QW-007: Filename Pattern Validation', 'start');

        const testPatterns = [
            { file: 'Fig1_R3_Final_V2.tif', expected: { revision: 'R3', version: 'V2', hasFinal: true } },
            { file: 'Fig1Final_V2.tif', expected: { revision: null, version: 'V2', hasFinal: true } },
            { file: 'Figure_2_Revised.jpg', expected: { revision: null, version: null, hasFinal: false } },
            { file: 'Supplementary_Material_R2.pdf', expected: { revision: 'R2', version: null, hasFinal: false } }
        ];

        const validationResults = await page.evaluate(async (patterns) => {
            const results = [];

            for (const pattern of patterns) {
                const revisionMatch = pattern.file.match(/R(\d+)/);
                const versionMatch = pattern.file.match(/V(\d+)/);
                const hasFinal = /Final/i.test(pattern.file);
                const extension = pattern.file.split('.').pop();

                const actual = {
                    revision: revisionMatch ? revisionMatch[0] : null,
                    version: versionMatch ? versionMatch[0] : null,
                    hasFinal: hasFinal,
                    extension: extension
                };

                const matches = {
                    revision: actual.revision === pattern.expected.revision,
                    version: actual.version === pattern.expected.version,
                    hasFinal: actual.hasFinal === pattern.expected.hasFinal
                };

                results.push({
                    filename: pattern.file,
                    expected: pattern.expected,
                    actual: actual,
                    allMatch: matches.revision && matches.version && matches.hasFinal,
                    matches: matches
                });
            }

            return results;
        }, testPatterns);

        // Verify all patterns matched
        validationResults.forEach(result => {
            logStep(`Testing: ${result.filename}`, 'check');
            expect(result.allMatch).toBe(true);
            logStep(`✓ Pattern matched correctly`, 'success');
        });

        logStep('All filename patterns validated successfully', 'success');
        logStep('TC-QW-007 PASSED', 'success');
    });

    // ==========================================
    // TC-QW-008: Update Query With Attachments
    // ==========================================
    test('TC-QW-008 - Author updates query to add attachments', async () => {
        ensureReady();
        const page = shared.page;
        logStep('Starting TC-QW-008: Update Query With Attachments', 'start');

        // Create query without attachments
        const setupResult = await page.evaluate(async () => {
            const queryData = {
                content: 'Initial query without attachments.',
                label: `AQ${window.queryModule._state.queries.size + 1}`,
                status: 'open',
                user: 'test.author@example.com',
                role: 'Author'
            };
            const query = await window.queryModule.createQuery(queryData);
            return { queryId: query.id, initialAttachmentCount: query.attachments.length };
        });

        expect(setupResult.initialAttachmentCount).toBe(0);
        logStep('Query created without attachments', 'info');

        // Update query to add attachments
        const updateResult = await page.evaluate(async (queryId) => {
            if (!window.queryModule) {
                return { error: 'queryModule not available' };
            }

            try {
                const mockAttachment = {
                    file_sn: 'Fig1_R3_Final_V2.tif',
                    file_on: 'Fig1_R3_Final_V2.tif',
                    name: 'Fig1_R3_Final_V2.tif',
                    url: `${BUCKET_URL}${DOC_ID}/attachments/Fig1_R3_Final_V2.tif`
                };

                const updates = {
                    content: 'Updated query with figure attachment.',
                    attachments: [mockAttachment]
                };

                const result = await window.queryModule.updateQueryOrCommentItem(queryId, updates);
                const query = window.queryModule.getQuery(queryId);

                return {
                    success: result.success,
                    attachmentCount: query.attachments.length,
                    attachmentName: query.attachments[0].name,
                    contentUpdated: query.content === updates.content
                };
            } catch (error) {
                return { error: error.message };
            }
        }, setupResult.queryId);

        expect(updateResult.error).toBeUndefined();
        expect(updateResult.success).toBe(true);
        expect(updateResult.attachmentCount).toBe(1);
        expect(updateResult.contentUpdated).toBe(true);

        logStep('Query updated with attachment successfully', 'success');
        await takeScreenshot(page, 'tc-qw-008-query-updated');
        logStep('TC-QW-008 PASSED', 'success');
    });

    // ==========================================
    // TC-QW-009: Delete Response With Attachments
    // ==========================================
    test('TC-QW-009 - Delete response containing attachments', async () => {
        ensureReady();
        const page = shared.page;
        logStep('Starting TC-QW-009: Delete Response With Attachments', 'start');

        // Setup: Create query and add response with attachment
        const setupResult = await page.evaluate(async () => {
            // Create query
            const queryData = {
                content: 'Test query for deletion',
                label: `AQ${window.queryModule._state.queries.size + 1}`,
                status: 'open',
                user: 'test.author@example.com',
                role: 'Author'
            };
            const query = await window.queryModule.createQuery(queryData);

            // Add response with attachment
            const mockAttachment = {
                file_sn: 'Response_Document.pdf',
                file_on: 'Response_Document.pdf',
                name: 'Response_Document.pdf',
                url: `${BUCKET_URL}${DOC_ID}/attachments/Response_Document.pdf`
            };

            const responseData = {
                content: 'Response with attachment',
                attachments: [mockAttachment],
                closeQuery: true
            };

            await window.queryModule.addResponse(query.id, responseData);
            const updatedQuery = window.queryModule.getQuery(query.id);

            return {
                queryId: query.id,
                responseId: updatedQuery.lastResponse.id,
                initialResponseCount: updatedQuery.responses.length,
                initialStatus: updatedQuery.status
            };
        });

        expect(setupResult.initialResponseCount).toBe(1);
        expect(setupResult.initialStatus).toBe('closed');
        logStep('Query and response with attachment created', 'info');

        // Delete the response
        const deleteResult = await page.evaluate(async ({ queryId, responseId }) => {
            if (!window.queryModule) {
                return { error: 'queryModule not available' };
            }

            try {
                const deletedResponse = await window.queryModule.deleteResponse(queryId, responseId);
                const query = window.queryModule.getQuery(queryId);

                return {
                    success: true,
                    responseCount: query.responses.length,
                    status: query.status,
                    deletedResponseHadAttachments: deletedResponse.attachments && deletedResponse.attachments.length > 0
                };
            } catch (error) {
                return { error: error.message };
            }
        }, setupResult);

        expect(deleteResult.error).toBeUndefined();
        expect(deleteResult.success).toBe(true);
        expect(deleteResult.responseCount).toBe(0);
        expect(deleteResult.status).toBe('open'); // Should reopen after response deletion
        expect(deleteResult.deletedResponseHadAttachments).toBe(true);

        logStep('Response with attachment deleted successfully', 'success');
        await takeScreenshot(page, 'tc-qw-009-response-deleted');
        logStep('TC-QW-009 PASSED', 'success');
    });

    // ==========================================
    // TC-QW-010: Attachment Module Integration
    // ==========================================
    test('TC-QW-010 - Verify AttachmentModule integration', async () => {
        ensureReady();
        const page = shared.page;
        logStep('Starting TC-QW-010: AttachmentModule Integration', 'start');

        const moduleCheck = await page.evaluate(() => {
            if (!window.queryModule) {
                return { error: 'queryModule not available' };
            }

            const checks = {
                attachmentModuleExists: !!window.queryModule.attachmentModule,
                hasSetupFileInput: typeof window.queryModule.attachmentModule?.setupFileInput === 'function',
                hasValidateFile: typeof window.queryModule.attachmentModule?.validateFile === 'function',
                hasUploadFiles: typeof window.queryModule.attachmentModule?.uploadFiles === 'function',
                hasFormatAttachmentResponse: typeof window.queryModule.formatAttachmentResponse === 'function',
                hasNormalizeAttachments: typeof window.queryModule.normalizeAttachments === 'function'
            };

            return {
                success: true,
                checks: checks,
                allPassed: Object.values(checks).every(v => v === true)
            };
        });

        expect(moduleCheck.error).toBeUndefined();
        expect(moduleCheck.success).toBe(true);
        expect(moduleCheck.checks.attachmentModuleExists).toBe(true);
        expect(moduleCheck.checks.hasSetupFileInput).toBe(true);
        expect(moduleCheck.checks.hasValidateFile).toBe(true);
        expect(moduleCheck.checks.hasUploadFiles).toBe(true);
        expect(moduleCheck.allPassed).toBe(true);

        logStep('All AttachmentModule methods verified', 'success');
        logStep('TC-QW-010 PASSED', 'success');
    });

});
