import { copyFile, mkdir } from "node:fs/promises";

const dist = new URL("../dist/", import.meta.url);
await mkdir(dist, { recursive: true });
await copyFile(new URL("../src/routes.json", import.meta.url), new URL("routes.json", dist));
console.log("built route-core");
