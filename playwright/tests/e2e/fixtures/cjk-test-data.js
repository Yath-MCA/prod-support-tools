/**
 * CJK Validator Test Data
 * Contains test cases for CJK character validation
 */

const cjkTestCases = {
    // ==========================================
    // Basic CJK Ideograph Test Cases
    // ==========================================
    basicIdeographs: [
        {
            id: 'basic-001',
            description: 'Simple Chinese characters',
            text: '你好世界',
            expectedCount: 4,
            expectedType: 'cjk_ideograph'
        },
        {
            id: 'basic-002',
            description: 'Japanese Kanji',
            text: '東京',
            expectedCount: 2,
            expectedType: 'cjk_ideograph'
        },
        {
            id: 'basic-003',
            description: 'Korean Hanja',
            text: '韓國',
            expectedCount: 2,
            expectedType: 'cjk_ideograph'
        },
        {
            id: 'basic-004',
            description: 'Mixed CJK languages',
            text: '中文日本語한국어',
            expectedCount: 8,
            expectedType: 'cjk_ideograph'
        },
    ],

    // ==========================================
    // CJK Punctuation Test Cases (Should be EXCLUDED)
    // ==========================================
    punctuation: [
        {
            id: 'punct-001',
            description: 'CJK brackets',
            text: '【】',
            expectedCount: 0,
            characters: [
                { char: '【', hex: 'U+3010', shouldCount: false },
                { char: '】', hex: 'U+3011', shouldCount: false }
            ]
        },
        {
            id: 'punct-002',
            description: 'CJK quotation marks',
            text: '「」『』',
            expectedCount: 0,
            characters: [
                { char: '「', hex: 'U+300C', shouldCount: false },
                { char: '」', hex: 'U+300D', shouldCount: false },
                { char: '『', hex: 'U+300E', shouldCount: false },
                { char: '』', hex: 'U+300F', shouldCount: false }
            ]
        },
        {
            id: 'punct-003',
            description: 'CJK angle brackets',
            text: '〈〉《》',
            expectedCount: 0,
            characters: [
                { char: '〈', hex: 'U+3008', shouldCount: false },
                { char: '〉', hex: 'U+3009', shouldCount: false },
                { char: '《', hex: 'U+300A', shouldCount: false },
                { char: '》', hex: 'U+300B', shouldCount: false }
            ]
        },
        {
            id: 'punct-004',
            description: 'CJK period and comma',
            text: '。、',
            expectedCount: 0,
            characters: [
                { char: '。', hex: 'U+3002', shouldCount: false },
                { char: '、', hex: 'U+3001', shouldCount: false }
            ]
        },
        {
            id: 'punct-005',
            description: 'Full-width space',
            text: '　',
            expectedCount: 0,
            hex: 'U+3000',
            shouldCount: false
        },
    ],

    // ==========================================
    // Mixed Content Test Cases
    // ==========================================
    mixedContent: [
        {
            id: 'mixed-001',
            description: 'CJK with English',
            text: 'Hello 你好 World 世界',
            expectedCount: 4, // Only 你好世界
            ideographCount: 4,
            punctuationCount: 0
        },
        {
            id: 'mixed-002',
            description: 'CJK ideographs with CJK punctuation',
            text: '「你好」世界【Test】',
            expectedCount: 4, // Only 你好世界
            ideographCount: 4,
            punctuationCount: 4 // 「」【】
        },
        {
            id: 'mixed-003',
            description: 'Numbers with CJK',
            text: '123你好456世界789',
            expectedCount: 4,
            ideographCount: 4,
            punctuationCount: 0
        },
        {
            id: 'mixed-004',
            description: 'HTML entities mixed',
            text: 'Test&nbsp;你好&amp;世界',
            expectedCount: 4,
            note: 'HTML entities should not affect CJK count'
        },
    ],

    // ==========================================
    // Validation Scenarios - Valid Tracking
    // ==========================================
    validTracking: [
        {
            id: 'valid-001',
            description: 'Properly tracked insertion',
            original: '<p>你好世界</p>',
            updated: '<p>你好<insert>美丽的</insert>世界</p>',
            expectedValid: true,
            expectedStatus: 'VALID',
            counts: {
                original: 4,
                updated: { overall: 7, insert: 3, del: 0 }
            }
        },
        {
            id: 'valid-002',
            description: 'Properly tracked deletion',
            original: '<p>你好美丽的世界</p>',
            updated: '<p>你好<del>美丽的</del>世界</p>',
            expectedValid: true,
            expectedStatus: 'VALID',
            counts: {
                original: 7,
                updated: { overall: 7, insert: 0, del: 3 }
            }
        },
        {
            id: 'valid-003',
            description: 'Mixed insert and delete',
            original: '<p>你好世界</p>',
            updated: '<p><del>你好</del><insert>再见</insert>世界</p>',
            expectedValid: true,
            counts: {
                original: 4,
                updated: { overall: 6, insert: 2, del: 2 }
            }
        },
        {
            id: 'valid-004',
            description: 'No CJK content',
            original: '<p>Hello World</p>',
            updated: '<p>Hello World Changed</p>',
            expectedValid: true,
            expectedStatus: 'VALID',
            counts: {
                original: 0,
                updated: { overall: 0, insert: 0, del: 0 }
            }
        },
    ],

    // ==========================================
    // Validation Scenarios - Invalid/Untracked
    // ==========================================
    invalidTracking: [
        {
            id: 'invalid-001',
            description: 'Untracked insertion',
            original: '<p>你好</p>',
            updated: '<p>你好世界</p>', // No insert tag!
            expectedValid: false,
            expectedStatus: 'UNTRACKED_ADDITIONS',
            untracked: 2,
            counts: {
                original: 2,
                updated: { overall: 4, insert: 0, del: 0 }
            }
        },
        {
            id: 'invalid-002',
            description: 'Untracked deletion',
            original: '<p>你好世界</p>',
            updated: '<p>你好</p>', // No del tag!
            expectedValid: false,
            expectedStatus: 'UNTRACKED_DELETIONS',
            untracked: 2,
            counts: {
                original: 4,
                updated: { overall: 2, insert: 0, del: 0 }
            }
        },
        {
            id: 'invalid-003',
            description: 'Partial tracking - some untracked',
            original: '<p>你好</p>',
            updated: '<p>你好<insert>世</insert>界</p>', // 界 is untracked
            expectedValid: false,
            expectedStatus: 'UNTRACKED_ADDITIONS',
            untracked: 1,
            counts: {
                original: 2,
                updated: { overall: 4, insert: 1, del: 0 }
            }
        },
    ],

    // ==========================================
    // Nested Tag Patterns
    // ==========================================
    nestedPatterns: [
        {
            id: 'nested-001',
            description: 'Insert inside Delete',
            html: '<del>deleted text<insert>新增</insert></del>',
            expectedPatterns: ['del>insert'],
            shouldIgnore: true
        },
        {
            id: 'nested-002',
            description: 'Delete inside Insert',
            html: '<insert>新增<del>删除</del>内容</insert>',
            expectedPatterns: ['insert>del'],
            shouldIgnore: true
        },
        {
            id: 'nested-003',
            description: 'Nested inserts',
            html: '<insert>level1<insert>level2</insert></insert>',
            expectedPatterns: ['insert>insert'],
            shouldIgnore: true
        },
        {
            id: 'nested-004',
            description: 'Complex nesting',
            html: '<del>a<insert>b<del>c</del></insert></del>',
            expectedPatterns: ['del>insert', 'insert>del'],
            shouldIgnore: true
        },
        {
            id: 'nested-005',
            description: 'Real-world problematic pattern',
            html: `<span class="kwd">
                <insert>pulmonary hypertension</insert>
                <del>bone marrow
                    <span><u><font>pu l</font>m l
                        <insert>】</insert>
                    </u></span>
                </del>
            </span>`,
            expectedPatterns: ['del>insert'],
            shouldIgnore: true,
            note: 'CJK punctuation inside nested insert-del'
        },
    ],

    // ==========================================
    // Edge Cases
    // ==========================================
    edgeCases: [
        {
            id: 'edge-001',
            description: 'Empty document',
            original: '<p></p>',
            updated: '<p></p>',
            expectedValid: true
        },
        {
            id: 'edge-002',
            description: 'Only whitespace',
            original: '<p>   </p>',
            updated: '<p>   </p>',
            expectedValid: true
        },
        {
            id: 'edge-003',
            description: 'Only CJK punctuation',
            original: '<p>【】「」</p>',
            updated: '<p>【】「」</p>',
            expectedValid: true,
            note: 'Punctuation should not trigger validation issues'
        },
        {
            id: 'edge-004',
            description: 'CJK Extension B characters (Surrogate pairs)',
            text: '𠀀', // U+20000 - CJK Extension B
            expectedCount: 1,
            note: 'Requires proper surrogate pair handling'
        },
        {
            id: 'edge-005',
            description: 'Very long content',
            generateText: (count) => '你'.repeat(count),
            testCounts: [100, 1000, 5000],
            note: 'Performance test for large documents'
        },
    ],

    // ==========================================
    // Unicode Range Reference
    // ==========================================
    unicodeRanges: {
        counted: [
            { name: 'CJK Unified Ideographs', range: 'U+4E00-U+9FFF', example: '你' },
            { name: 'CJK Extension A', range: 'U+3400-U+4DBF', example: '㐀' },
            { name: 'CJK Radicals Supplement', range: 'U+2E80-U+2EFF', example: '⺀' },
            { name: 'Kangxi Radicals', range: 'U+2F00-U+2FDF', example: '⼀' },
            { name: 'CJK Strokes', range: 'U+31C0-U+31EF', example: '㇀' },
            { name: 'CJK Compatibility Ideographs', range: 'U+F900-U+FAFF', example: '豈' },
            { name: 'CJK Extension B', range: 'U+20000-U+2A6DF', example: '𠀀' },
        ],
        excluded: [
            { name: 'CJK Symbols and Punctuation', range: 'U+3000-U+303F', examples: '。、【】「」' },
        ]
    }
};

// Export for use in tests
module.exports = {
    cjkTestCases
};
