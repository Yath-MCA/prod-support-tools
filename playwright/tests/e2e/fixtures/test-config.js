/**
 * Test Configuration for IMPACT Editor E2E Tests
 * Single source of truth for selectors, timeouts, and test data.
 */

const config = {

    // ==========================================
    // URLs
    // ==========================================
    urls: {
        landing: '/landingPage.html',
        editor:  '/editor.html',
        sampleDocument: '?docid=TEST_DOC_001&client=TEST_CLIENT'
    },

    // ==========================================
    // Selectors — Landing Page
    // ==========================================
    landing: {
        // Accept button (Non-PLOS single-author active flow)
        acceptButton:   "#ValidateBtnOpt",

        // Article metadata
        title1:         "#title1",
        title2:         "#title2",
        authorname:     "#authorname",
        clientIcon:     ".navbar-brand img",
        supportEmail:   "#support_mail_id",

        // Loading indicators
        loadingOverlay: '#blurOverlay, .blur-overlay',
        loadingDialog:  '#loadingDialog, .loading-dialog',
        progressBar:    '.circular-progress',
        progressValue:  '.value-container',
        statusText:     '.status',

        // Assets / help links
        faqPdf:         "a[title='Frequently Asked Questions']",
        userGuidePdf:   "a[title='User Guide']",

        // Alternate flow buttons
        proceedButton:  '#btnProceed, .btn-proceed',
        continueButton: '#btnContinue, .btn-continue'
    },

    // ==========================================
    // Selectors — PLOS Access Code Dialog
    // (active + PLOS + single author)
    // ==========================================
    plosAccessCode: {
        dialog:     '#authorAccessDialog, .access-code-dialog',
        prompt:     '.access-code-prompt, #accessCodeLabel',
        input:      '#authorAccessCode, input[name="accessCode"]',
        submitBtn:  '#btnValidateCode, .btn-validate-code',
        errorMsg:   '#accessCodeError, .access-code-error'
    },

    // ==========================================
    // Selectors — Multi-Author Email Picker
    // (active + any client + author_count > 1)
    // ==========================================
    multiAuthor: {
        dialog:    '#authorEmailDialog, .author-select-dialog',
        prompt:    '.author-select-prompt',
        emailInput:'#authorEmail, input[name="authorEmail"]',
        submitBtn: '#btnVerifyEmail, .btn-verify-email',
        errorMsg:  '#emailVerifyError, .email-verify-error'
    },

    // ==========================================
    // Selectors — Signoff / Deactive Alerts
    // (SweetAlert2-based blocking dialogs)
    // ==========================================
    statusAlert: {
        container:    '.swal2-container',
        title:        '.swal2-title',
        text:         '.swal2-html-container',
        okButton:     '.swal2-confirm',
        cancelButton: '.swal2-cancel'
    },

    // ==========================================
    // Selectors — LWW Author Sign Time
    // (signoff + client=LWW + role=author)
    // ==========================================
    lwwSignoff: {
        signTimeLabel: '#authorSignTime, .author-sign-time',
        signTimeValue: '#authorSignTimeValue, .sign-time-value'
    },

    // ==========================================
    // Selectors — Read-only / Archive Pages
    // ==========================================
    readOnly: {
        pageMarker:  '[data-mode="readonly"], .readonly-view',
        headerBadge: '.readonly-badge, #readonlyBadge'
    },
    archive: {
        pageMarker:  '[data-mode="archive"], .archive-view',
        headerBadge: '.archive-badge, #archiveBadge'
    },

    // ==========================================
    // Selectors — Editor Page (CKEditor 4)
    // ==========================================
    editor6: {
        editorInstance:  '.cke_editable, #cke_mainDiv, [contenteditable="true"]',
        editorIframe:    'iframe.cke_wysiwyg_frame',
        editorBody:      'body.cke_editable',
        toolbar:         '.cke_top, .cke_toolbar',
        queryElement:    '[data-class="ckcommentsfull"]:not([data-ignore-comment])',
        queryOpen:       '[data-class="ckcommentsfull"][data-status="Open"], [data-class="ckcommentsfull"][data-status="open"]',
        queryClosed:     '[data-class="ckcommentsfull"][data-status="Closed"], [data-class="ckcommentsfull"][data-status="closed"]',
        queryComment:    '[data-class="ckcommentsfull"][data-status="comment"]',
        aqSpan:          '[data-name="AQ"][data-role="Query to Author"]',
        responseSpan:    '[data-name="Response"], [data-name="response"]',
        commentSpan:     '[data-name="comment"]'
    },

    // ==========================================
    // Selectors — Query Panel
    // ==========================================
    queryPanel: {
        container:          '#queryPanel, .query-panel, [data-panel="query"]',
        tabQueries:         '.tab-queries, [data-tab="queries"]',
        tabComments:        '.tab-comments, [data-tab="comments"]',
        queryItem:          '.query-item, [data-query-id]',
        queryLabel:         '.data-label, .query-label',
        queryStatus:        '.query-status, [data-status]',
        totalCount:         '.total-count, #totalQueries',
        openCount:          '.open-count, #openQueries',
        closedCount:        '.closed-count, #closedQueries',
        commentCount:       '.comment-count, #totalComments',
        refreshButton:      '.refresh-btn, [data-action="refresh"]',
        expandAllButton:    '.expand-all, [data-action="expand-all"]',
        collapseAllButton:  '.collapse-all, [data-action="collapse-all"]'
    },

    // ==========================================
    // Selectors — Comment Panel
    // ==========================================
    commentPanel: {
        comment_tab:  '[id^="btn_cts"]',
        add_comment:  '[id^="addcmt"]',
        group:        '.comment-group#comment',
        total:        '[id="cTotal"]',
        comment_list: '.comment-list',
        comment_item: '.query-item[data-status="comment"]'
    },

    // ==========================================
    // Selectors — Query/Comment Dialog
    // ==========================================
    query_comment_dialog: {
        dialog:       '#queryDialog',
        header:       '#header_text',
        label:        '.user-detail-info[data-role]',
        commentInput: '#dialog-reply-input',
        attachBtn:    '.attach-btn',
        clearBtn:     '.clear-btn',
        insertBtn:    '.save-btn',
        closeIcon:    '.closeIcons img.n_Img',
        fileInput:    'input.file-input[type="file"]'
    },

    // ==========================================
    // Selectors — Initial Load Dialog
    // ==========================================
    initialLoad: {
        dialog:   '#loadingDialog',
        overlay:  '#blurOverlay',
        progress: '.circular-progress',
        status:   '.status',
        statusMessages: {
            loading:   'Loading ...',
            fetching:  'Fetching Info ...',
            setting:   'Setting Profile ...',
            document:  'Get document ...',
            initiated: 'Initiated IMPACT',
            completed: 'Completed'
        }
    },

    // ==========================================
    // Timeouts (ms)
    // ==========================================
    timeouts: {
        pageLoad:       6000,
        editorReady:    4500,
        panelLoad:      3000,
        elementVisible: 1000,
        animation:      1000,
        networkIdle:    5000,
        apiResponse:    5000
    },

    // ==========================================
    // Test Data
    // ==========================================
    testData: {
        sampleQuery: {
            content:        'This is a test query for automation testing',
            expectedStatus: 'open'
        },
        sampleResponse: {
            content:        'This is a test response',
            expectedStatus: 'closed'
        }
    }
};

export default config;
