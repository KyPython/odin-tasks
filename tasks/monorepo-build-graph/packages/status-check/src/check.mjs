import assert from "node:assert/strict";

const status = { name: "harbor", ready: true };
assert.equal(status.ready, true);
console.log("status check passed");
