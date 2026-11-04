import assert from "node:assert/strict";
import test from "node:test";
import { spawnSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";

// GATEPASS-2.1: dispatch-service reads route-core/dist at build time, so the
// build task must order dependencies first.
test("GATEPASS-2.1: build task depends on dependency builds", () => {
  const turbo = JSON.parse(readFileSync("turbo.json", "utf8"));
  assert.ok(
    (turbo.tasks.build.dependsOn ?? []).includes("^build"),
    "turbo build task must declare dependsOn ^build",
  );
});

// GATEPASS-2.2: a forced (uncached) build produces the dispatch manifest,
// proving route-core built first.
test("GATEPASS-2.2: forced build produces the dispatch manifest", () => {
  const result = spawnSync("node_modules/.bin/turbo", ["run", "build", "--force"], {
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr);
  assert.ok(existsSync("apps/dispatch-service/dist/manifest.json"));
  const manifest = JSON.parse(readFileSync("apps/dispatch-service/dist/manifest.json", "utf8"));
  assert.equal(manifest.service, "dispatch");
  assert.ok(Array.isArray(manifest.routes));
});
