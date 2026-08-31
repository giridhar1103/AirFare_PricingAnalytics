import { mkdir, readFile, writeFile } from "node:fs/promises";

const outputRoot = new URL("../dist/", import.meta.url);
const entrypoint = await readFile(new URL("index.html", outputRoot), "utf8");
const workspaceRoutes = ["markets", "models", "scenario", "methodology"];

for (const route of workspaceRoutes) {
  const destination = new URL(`${route}/`, outputRoot);
  await mkdir(destination, { recursive: true });
  await writeFile(new URL("index.html", destination), entrypoint);
}

const routeList = workspaceRoutes.join(", ");
console.log(`Created static workspace entry points: ${routeList}`);
