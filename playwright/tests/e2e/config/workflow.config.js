export const workflowConfig = {
    moduleWorkflow: {
        query: [
            "tests/e2e/landing-to-editor-query.spec.js"
        ],
        comment: [
            "tests/e2e/landing-to-editor-comment.spec.js"
        ]
    },
    basicWorkflow: {
        name: "landing-editor-module-basic",
        description: "Landing -> Accept -> Editor -> Core module health checks",
        specs: [
            "tests/e2e/landing-editor-module-basic.spec.js"
        ],
        requiredModules: [
            "querySystem",
            "queryDialog"
        ]
    },
    regressionWorkflow: {
        name: "landing-editor-regression",
        description: "Basic workflow + role/menu/toolbar + query/comment module tests",
        specs: [
            "tests/e2e/landing-editor-module-basic.spec.js",
            "tests/e2e/landing-to-editor6.spec.js",
            "tests/e2e/landing-to-editor-query.spec.js",
            "tests/e2e/landing-to-editor-comment.spec.js"
        ]
    },
    fullWorkflow: {
        name: "full-e2e-suite",
        description: "All E2E specs in tests/e2e",
        specGlob: "tests/e2e/**/*.spec.js"
    }
};

export default workflowConfig;
