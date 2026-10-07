import { readFile } from "node:fs/promises";

const dockerfile = await readFile(new URL("../container/Dockerfile", import.meta.url), "utf8");
const match = dockerfile.match(/--filter=([^\s]+)/);
if (!match) throw new Error("container build filter is missing");

const workspace = await readFile(new URL("../pnpm-workspace.yaml", import.meta.url), "utf8");
const packageFiles = [
  new URL("../apps/dispatch-service/package.json", import.meta.url),
  new URL("../packages/route-core/package.json", import.meta.url),
  new URL("../packages/status-check/package.json", import.meta.url)
];
const names = await Promise.all(packageFiles.map(async (url) => JSON.parse(await readFile(url, "utf8")).name));
if (!workspace.includes("apps/*") || !names.includes(match[1])) {
  throw new Error(`container target ${match[1]} is not a workspace package`);
}
console.log("container target is valid");
