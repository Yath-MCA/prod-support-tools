/**
 * ============================================
 * TEST CASE HANDLING: TrackedChangesResolver
 * ============================================
 * 
 * Comprehensive test suite for validating all scenarios
 * of tracked changes resolution and whitespace normalization
 */

class TrackedChangesResolverTests {
    constructor() {
        this.results = [];
        this.passCount = 0;
        this.failCount = 0;
    }

    /**
     * Run all test cases
     */
    runAllTests() {
        console.clear();
        console.log('╔═══════════════════════════════════════════════════════════╗');
        console.log('║  TRACKED CHANGES RESOLVER - TEST SUITE                    ║');
        console.log('╚═══════════════════════════════════════════════════════════╝\n');

        this.testDeletionBeforePunctuation();
        this.testNestedInsertionTags();
        this.testDeletedConnectiveWords();
        this.testDeletedSymbolDescriptor();
        this.testAdjacentDeletedInserted();
        this.testMultipleSpaces();
        this.testSpaceBeforePunctuation();
        this.testComplexMixedScenario();
        this.testDoubleSpacesInInsertTag();
        this.testDoubleSpacesInDeleteTag();
        this.testDoubleSpacesInIceInsTag();
        this.testDoubleSpacesInIceDelTag();

        this.printSummary();
        return this.results;
    }

    /**
     * TEST 1: Deleted text before punctuation
     * Input:  "text text <del>text</del>."
     * Output: "text text."
     */
    testDeletionBeforePunctuation() {
        const testName = 'TEST 1: Deleted text before punctuation';
        const input = '<p id="p1">text text <del>text</del>.</p>';
        const expected = 'text text.';

        const result = this.executeTest(testName, input, expected);
        this.logResult(testName, result);
    }

    /**
     * TEST 2: Adjacent nested insertion tags
     * Input:  "implementation<ins>of</ins><ins>these</ins> allocation"
     * Output: "implementation of these allocation"
     */
    testNestedInsertionTags() {
        const testName = 'TEST 2: Adjacent nested insertion tags';
        const input = '<p id="p2">implementation<ins>of</ins><ins>these</ins> allocation</p>';
        const expected = 'implementationofthese allocation';

        const result = this.executeTest(testName, input, expected);
        this.logResult(testName, result);
    }

    /**
     * TEST 3: Deleted connective words
     * Input:  "implementation<del>of these</del>allocation"
     * Output: "implementationallocation"
     */
    testDeletedConnectiveWords() {
        const testName = 'TEST 3: Deleted connective words';
        const input = '<p id="p3">implementation<del>of these</del>allocation</p>';
        const expected = 'implementationallocation';

        const result = this.executeTest(testName, input, expected);
        this.logResult(testName, result);
    }

    /**
     * TEST 4: Deleted symbol descriptor
     * Input:  "C virus+<del> –positive</del> donors"
     * Output: "C virus+ donors"
     */
    testDeletedSymbolDescriptor() {
        const testName = 'TEST 4: Deleted symbol descriptor';
        const input = '<p id="p4">C virus+<del> –positive</del> donors</p>';
        const expected = 'C virus+ donors';

        const result = this.executeTest(testName, input, expected);
        this.logResult(testName, result);
    }

    /**
     * TEST 5: Adjacent deleted and inserted content
     * Input:  "protect mice <del>through</del><ins>against</ins> thrombosis"
     * Output: "protect mice against thrombosis"
     */
    testAdjacentDeletedInserted() {
        const testName = 'TEST 5: Adjacent deleted and inserted content';
        const input = '<p id="p5">protect mice <del>through</del><ins>against</ins> thrombosis</p>';
        const expected = 'protect mice against thrombosis';

        const result = this.executeTest(testName, input, expected);
        this.logResult(testName, result);
    }

    /**
     * TEST 6: Multiple spaces normalization
     * Input:  "text  with   multiple    spaces"
     * Output: "text with multiple spaces"
     */
    testMultipleSpaces() {
        const testName = 'TEST 6: Multiple spaces normalization';
        const input = '<p id="p6">text  with   multiple    spaces</p>';
        const expected = 'text with multiple spaces';

        const result = this.executeTest(testName, input, expected);
        this.logResult(testName, result);
    }

    /**
     * TEST 7: Space before punctuation
     * Input:  "This is a sentence ."
     * Output: "This is a sentence."
     */
    testSpaceBeforePunctuation() {
        const testName = 'TEST 7: Space before punctuation';
        const input = '<p id="p7">This is a sentence .</p>';
        const expected = 'This is a sentence.';

        const result = this.executeTest(testName, input, expected);
        this.logResult(testName, result);
    }

    /**
     * TEST 8: Complex mixed scenario
     * Multiple changes in one paragraph with nested tags
     */
    testComplexMixedScenario() {
        const testName = 'TEST 8: Complex mixed scenario';
        const input = '<p id="p8">The study <del>was conducted</del><ins>examines</ins> the  impact of <del>viral</del><ins>pathogenic</ins> factors  .</p>';
        const expected = 'The study examines the impact of pathogenic factors.';

        const result = this.executeTest(testName, input, expected);
        this.logResult(testName, result);
    }

    /**
     * TEST 9: Double spaces in insert tag
     * Input:  "Text with <ins>double  spaces</ins> inside"
     * Output: "Text with double spaces inside"
     */
    testDoubleSpacesInInsertTag() {
        const testName = 'TEST 9: Double spaces in insert tag';
        const input = '<p id="p9">Text with <ins>double  spaces</ins> inside</p>';
        const expected = 'Text with double spaces inside';

        const result = this.executeTest(testName, input, expected);
        this.logResult(testName, result);
    }

    /**
     * TEST 10: Double spaces in delete tag
     * Input:  "Text with <del>double  spaces</del> removed"
     * Output: "Text with removed"
     */
    testDoubleSpacesInDeleteTag() {
        const testName = 'TEST 10: Double spaces in delete tag';
        const input = '<p id="p10">Text with <del>double  spaces</del> removed</p>';
        const expected = 'Text with removed';

        const result = this.executeTest(testName, input, expected);
        this.logResult(testName, result);
    }

    /**
     * TEST 11: Double spaces in ice-ins tag
     * Input:  "Text with <insert class="ice-ins">multiple   spaces</insert> inside"
     * Output: "Text with multiple spaces inside"
     */
    testDoubleSpacesInIceInsTag() {
        const testName = 'TEST 11: Double spaces in ice-ins tag';
        const input = '<p id="p11">Text with <insert class="ice-ins">multiple   spaces</insert> inside</p>';
        const expected = 'Text with multiple spaces inside';

        const result = this.executeTest(testName, input, expected);
        this.logResult(testName, result);
    }

    /**
     * TEST 12: Double spaces in ice-del tag
     * Input:  "Text with <del class="ice-del">multiple   spaces</del> removed"
     * Output: "Text with removed"
     */
    testDoubleSpacesInIceDelTag() {
        const testName = 'TEST 12: Double spaces in ice-del tag';
        const input = '<p id="p12">Text with <del class="ice-del">multiple   spaces</del> removed</p>';
        const expected = 'Text with removed';

        const result = this.executeTest(testName, input, expected);
        this.logResult(testName, result);
    }

    /**
     * Core execution logic for all tests
     */
    executeTest(testName, input, expected) {
        try {
            // Create container and parse input
            const container = document.createElement('div');
            container.innerHTML = input;
            const sourceElement = container.firstChild;

            // Run resolver
            const resolver = new TrackedChangesResolver(sourceElement);
            const result = resolver.resolve();

            // Extract clean text content
            const actual = result.cleanedElement.textContent.trim();
            const passed = actual === expected;

            // Check for double spaces in tracked change tags
            const doubleSpaceIssues = this.detectDoubleSpacesInTags(sourceElement, resolver);

            return {
                testName,
                input,
                expected,
                actual,
                passed,
                affectedIds: result.affectedParagraphIds,
                changeLogLength: result.changeLog.length,
                changeLog: result.changeLog,
                doubleSpaceIssues: doubleSpaceIssues
            };
        } catch (error) {
            return {
                testName,
                input,
                expected,
                actual: 'ERROR',
                passed: false,
                error: error.message,
                affectedIds: [],
                changeLogLength: 0,
                changeLog: [],
                doubleSpaceIssues: []
            };
        }
    }

    /**
     * Detect double spaces in tracked change tags
     */
    detectDoubleSpacesInTags(element, resolver) {
        const issues = [];
        const tagSelectors = ['del', 'ins', '[class*="ice-del"]', '[class*="ice-ins"]'];

        tagSelectors.forEach(selector => {
            const tags = element.querySelectorAll(selector);
            tags.forEach(tag => {
                if (resolver.checkDoubleSpacesInTags(tag)) {
                    const parentBlock = resolver.findAffectedParagraph(tag);
                    issues.push({
                        tag: tag.tagName.toLowerCase(),
                        className: tag.className,
                        content: tag.textContent,
                        blockId: parentBlock?.id || 'unknown'
                    });
                }
            });
        });

        return issues;
    }

    /**
     * Log individual test result
     */
    logResult(testName, result) {
        this.results.push(result);

        const status = result.passed ? '✓ PASSED' : '✗ FAILED';
        const statusColor = result.passed ? '\x1b[32m' : '\x1b[31m';
        const resetColor = '\x1b[0m';

        console.log(`${statusColor}${status}${resetColor} - ${testName}`);
        console.log(`  Input:      ${result.input}`);
        console.log(`  Expected:   "${result.expected}"`);
        console.log(`  Actual:     "${result.actual}"`);
        console.log(`  Affected:   ${result.affectedIds.length > 0 ? result.affectedIds.join(', ') : 'none'}`);
        console.log(`  Changes:    ${result.changeLogLength} modifications logged`);
        
        if (result.doubleSpaceIssues && result.doubleSpaceIssues.length > 0) {
            console.log(`  Double Spaces Found:`);
            result.doubleSpaceIssues.forEach(issue => {
                console.log(`    - ${issue.tag}.${issue.className} in block ${issue.blockId}: "${issue.content}"`);
            });
        }
        
        console.log('');

        if (result.passed) {
            this.passCount++;
        } else {
            this.failCount++;
        }
    }

    /**
     * Print test summary
     */
    printSummary() {
        const total = this.passCount + this.failCount;
        const passPercentage = Math.round((this.passCount / total) * 100);

        console.log('╔═══════════════════════════════════════════════════════════╗');
        console.log('║  TEST SUMMARY                                             ║');
        console.log('╠═══════════════════════════════════════════════════════════╣');
        console.log(`║ Total Tests:    ${total.toString().padEnd(45)} ║`);
        console.log(`║ Passed:         ${this.passCount.toString().padEnd(45)} ║`);
        console.log(`║ Failed:         ${this.failCount.toString().padEnd(45)} ║`);
        console.log(`║ Success Rate:   ${passPercentage}%${' '.repeat(42 - passPercentage.toString().length)} ║`);
        console.log('╚═══════════════════════════════════════════════════════════╝\n');
    }

    /**
     * Get detailed results as JSON
     */
    getResultsAsJSON() {
        return {
            timestamp: new Date().toISOString(),
            totalTests: this.passCount + this.failCount,
            passed: this.passCount,
            failed: this.failCount,
            successRate: `${Math.round((this.passCount / (this.passCount + this.failCount)) * 100)}%`,
            results: this.results
        };
    }
}

// ============================================
// INSTANTIATE AND RUN TESTS
// ============================================
const trackedChangesTests = new TrackedChangesResolverTests();

// Auto-run tests if running in browser console or test environment
if (typeof document !== 'undefined') {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            trackedChangesTests.runAllTests();
        });
    } else {
        // DOM is already ready
        trackedChangesTests.runAllTests();
    }
}

// ============================================
// EXPORT FOR USE IN TEST RUNNERS
// ============================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TrackedChangesResolverTests;
}