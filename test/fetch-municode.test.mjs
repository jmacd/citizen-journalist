import assert from "node:assert/strict";
import test from "node:test";
import {
  parseArgs,
  sanitizeHar,
  sha256,
} from "../scripts/fetch-municode.mjs";

const URL =
  "https://library.municode.com/ca/mendocino_county/codes/code_of_ordinances?nodeId=SECTION";

test("parses a public MuniCode URL and repeated expectations", () => {
  const options = parseArgs([
    URL,
    "--expect",
    "20.376.015",
    "--expect",
    "Off-site",
    "--timeout",
    "30",
  ]);

  assert.equal(options.url, URL);
  assert.deepEqual(options.expects, ["20.376.015", "Off-site"]);
  assert.equal(options.timeout, 30_000);
});

test("rejects non-MuniCode targets", () => {
  assert.throws(
    () => parseArgs(["https://example.com/"]),
    /Only public HTTPS pages/,
  );
});

test("removes sensitive HAR headers and cookies", () => {
  const sanitized = sanitizeHar({
    log: {
      entries: [
        {
          request: {
            cookies: [{ name: "session", value: "secret" }],
            headers: [
              { name: "Cookie", value: "session=secret" },
              { name: "Accept", value: "text/html" },
            ],
          },
          response: {
            headers: [{ name: "Set-Cookie", value: "session=secret" }],
          },
        },
      ],
    },
  });

  assert.deepEqual(sanitized.log.entries[0].request.cookies, []);
  assert.deepEqual(sanitized.log.entries[0].request.headers, [
    { name: "Accept", value: "text/html" },
  ]);
  assert.deepEqual(sanitized.log.entries[0].response.headers, []);
});

test("computes stable SHA-256 hashes", () => {
  assert.equal(
    sha256("mendocino"),
    "de2515290a5d39dade325bbef366d8ae7f49ce009767438cb72e4934e50c7efb",
  );
});
