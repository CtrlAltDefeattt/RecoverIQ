import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));

test("renders the RecoverIQ document title in the Next.js output", async () => {
  const html = await readFile(`${root}/.next/server/app/index.html`, "utf8");

  assert.match(html, /<title>RecoverIQ Command Center<\/title>/i);
});
