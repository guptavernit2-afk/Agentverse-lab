import assert from "node:assert/strict";
import test from "node:test";
import { display, human, needsResync } from "../src/model.ts";

test("unknown metrics and denominators remain missing", () => {
	assert.equal(display(null), "N/A");
	assert.equal(display(undefined), "N/A");
	assert.equal(display(0), "0");
	assert.equal(display(0.125, true), "12.5%");
	assert.equal(display(-1.234567), "-1.235");
});

test("cursor gaps and reconnects require authoritative resynchronization", () => {
	assert.equal(needsResync(9, { type: "gap", after: 9, head: 66 }), true);
	assert.equal(needsResync(2, { type: "update", after: 1, head: 9 }), true);
	assert.equal(needsResync(9, { type: "update", after: 9, head: 6 }), true);
	assert.equal(needsResync(9, { type: "update", after: 9, head: 10 }), false);
	assert.equal(human("rule_based"), "rule based");
});
