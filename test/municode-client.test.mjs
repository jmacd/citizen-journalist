import assert from "node:assert/strict";
import test from "node:test";
import { MunicodeClient, parseSectionReference } from "../lib/municode-client.mjs";

test("parses a section reference", () => {
  assert.deepEqual(parseSectionReference("20.376.015"), {
    chapter: "20.376",
    section: "20.376.015",
    title: "20",
  });
});

test("rejects malformed section references", () => {
  assert.throws(() => parseSectionReference("20.376"), /Invalid section/);
});

test("resolves a section through the current TOC", async () => {
  const responses = new Map([
    ["/localapi/Organizations/GetByUrlEncodedNames/ca/mendocino_county", { ClientID: 6834 }],
    [
      "/api/Products/name?clientId=6834&productName=code+of+ordinances",
      { Model: { ProductID: 16484, ProductName: "Code of Ordinances" } },
    ],
    [
      "/localapi/PublicationVersion/GetViewModel/6834/code%20of%20ordinances",
      { id: 152855, isLatest: true, name: "Supplement 75" },
    ],
    [
      "/api/Jobs/latest/16484",
      { Id: 493944, IsLatest: true, Name: "Supplement 75" },
    ],
    [
      "/api/codesToc?jobId=493944&productId=16484",
      {
        Children: [
          {
            Id: "title-20",
            Heading: "Title 20 - ZONING ORDINANCE",
            HasChildren: true,
          },
        ],
      },
    ],
    [
      "/api/codesToc/children?jobId=493944&nodeId=title-20&productId=16484",
      [
        {
          Id: "division-ii",
          Heading: "DIVISION II - COASTAL ZONING CODE",
          HasChildren: true,
        },
      ],
    ],
    [
      "/api/codesToc/children?jobId=493944&nodeId=division-ii&productId=16484",
      [
        {
          Id: "chapter-20.376",
          Heading: "CHAPTER 20.376 - RR—RURAL RESIDENTIAL DISTRICT",
          HasChildren: true,
        },
      ],
    ],
    [
      "/api/codesToc/children?jobId=493944&nodeId=chapter-20.376&productId=16484",
      [
        {
          Id: "section-20.376.015",
          Heading: "Sec. 20.376.015 - Conditional Uses for RR Districts.",
          HasChildren: false,
        },
      ],
    ],
  ]);
  const fetchImpl = async (url) => {
    const key = `${url.pathname}${url.search}`;
    const body = responses.get(key);
    assert.ok(body, `Unexpected request: ${key}`);
    return new Response(JSON.stringify(body), {
      headers: { "content-type": "application/json" },
      status: 200,
    });

    test("resolves a title nested beneath a legacy container", async () => {
      const responses = new Map([
        ["/localapi/Organizations/GetByUrlEncodedNames/ca/mendocino_county", { ClientID: 6834 }],
        [
          "/api/Products/name?clientId=6834&productName=code+of+ordinances",
          { Model: { ProductID: 16484, ProductName: "Code of Ordinances" } },
        ],
        [
          "/localapi/PublicationVersion/GetViewModel/6834/code%20of%20ordinances",
          { id: 1, isLatest: true, name: "Supplement 1" },
        ],
        [
          "/api/Jobs/latest/16484",
          { Id: 10, IsLatest: true, Name: "Supplement 1" },
        ],
        [
          "/api/codesToc?jobId=10&productId=16484",
          {
            Children: [
              { Id: "legacy", Heading: "LEGACY CONTAINER", HasChildren: true },
            ],
          },
        ],
        [
          "/api/codesToc/children?jobId=10&nodeId=legacy&productId=16484",
          [
            {
              Id: "title-20",
              Heading: "Title 20 - ZONING ORDINANCE",
              HasChildren: true,
            },
          ],
        ],
        [
          "/api/codesToc/children?jobId=10&nodeId=title-20&productId=16484",
          [
            {
              Id: "division-ii",
              Heading: "DIVISION II - COASTAL ZONING CODE",
              HasChildren: true,
            },
          ],
        ],
        [
          "/api/codesToc/children?jobId=10&nodeId=division-ii&productId=16484",
          [
            {
              Id: "chapter",
              Heading: "CHAPTER 20.376 - RR",
              HasChildren: true,
            },
          ],
        ],
        [
          "/api/codesToc/children?jobId=10&nodeId=chapter&productId=16484",
          [
            {
              Id: "section",
              Heading: "Sec. 20.376.015 - Conditional Uses.",
              HasChildren: false,
            },
          ],
        ],
      ]);
      const client = new MunicodeClient({
        baseUrl: "https://example.test",
        fetchImpl: async (url) => {
          const key = `${url.pathname}${url.search}`;
          assert.ok(responses.has(key), `Unexpected request: ${key}`);
          return new Response(JSON.stringify(responses.get(key)), { status: 200 });
        },
        requestDelayMs: 0,
      });

      const result = await client.resolveSection("20.376.015", { division: "II" });

      assert.equal(result.node.Id, "section");
      assert.deepEqual(
        result.lineage.map((node) => node.Id),
        ["legacy", "title-20", "division-ii", "chapter", "section"],
      );
    });
  };
  const client = new MunicodeClient({
    baseUrl: "https://example.test",
    fetchImpl,
    requestDelayMs: 0,
  });

  const result = await client.resolveSection("20.376.015");

  assert.equal(result.node.Id, "section-20.376.015");
  assert.deepEqual(
    result.lineage.map((node) => node.Id),
    ["title-20", "division-ii", "chapter-20.376", "section-20.376.015"],
  );
});
