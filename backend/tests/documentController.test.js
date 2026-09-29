// Uses Node's built-in test runner (node:test) -- no new devDependency
// needed for this. This is the backend's first test file; see
// docs/WEEKS_1-3_STATUS_AND_PLAN.md for the broader gap this doesn't
// close (no test runner existed at all for backend/ before Weeks 1-3,
// and this file covers only the pure logic touched by that work, not
// the pre-existing controllers).
//
// Run with: npm test

import { test } from "node:test";
import assert from "node:assert/strict";

import { mapJobStateToStatus } from "../src/controllers/documentController.js";

test("SUCCESS maps to ready", () => {
    assert.equal(mapJobStateToStatus("SUCCESS"), "ready");
});

test("FAILURE maps to failed", () => {
    assert.equal(mapJobStateToStatus("FAILURE"), "failed");
});

test("STARTED maps to ocr_running", () => {
    assert.equal(mapJobStateToStatus("STARTED"), "ocr_running");
});

test("PENDING maps to queued", () => {
    assert.equal(mapJobStateToStatus("PENDING"), "queued");
});

test("RETRY maps to queued (still in flight)", () => {
    assert.equal(mapJobStateToStatus("RETRY"), "queued");
});

test("an unrecognized state defaults to queued, not a crash", () => {
    assert.equal(mapJobStateToStatus("SOME_FUTURE_CELERY_STATE"), "queued");
});

test("every mapped value is a valid Document.status enum member", async () => {
    // Document.js's status enum is the source of truth this must stay
    // inside -- read it back rather than duplicating the list here, so
    // this test breaks loudly if the two ever diverge.
    const { default: Document } = await import("../src/models/Document.js");
    const validStatuses = Document.schema.path("status").enumValues;

    for (const jobState of ["SUCCESS", "FAILURE", "STARTED", "PENDING", "RETRY", "unknown"]) {
        const mapped = mapJobStateToStatus(jobState);
        assert.ok(
            validStatuses.includes(mapped),
            `mapJobStateToStatus("${jobState}") = "${mapped}" is not in Document's status enum`
        );
    }
});
