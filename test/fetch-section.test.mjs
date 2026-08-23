import assert from "node:assert/strict";
import test from "node:test";
import { parseArgs } from "../scripts/fetch-section.mjs";

test("defaults Title 20 captures to coastal Division II", () => {
  const options = parseArgs(["--section", "20.376.015"]);
  assert.equal(options.division, "II");
});

test("allows an explicit Title 20 division", () => {
  const options = parseArgs([
    "--section",
    "20.376.015",
    "--division",
    "III",
  ]);
  assert.equal(options.division, "III");
});

test("does not impose a division on other titles", () => {
  const options = parseArgs(["--section", "22.04.010"]);
  assert.equal(options.division, undefined);
});
