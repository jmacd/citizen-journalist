#!/usr/bin/env node

const DOTNET_UNIX_EPOCH_TICKS = 621355968000000000n;
const TICKS_PER_MILLISECOND = 10000n;

function parseGovAccessUrl(value) {
  const url = new URL(value);
  const match = url.pathname.match(
    /\/home\/showpublisheddocument\/(\d+)(?:\/(\d+))?$/i,
  );
  if (!match) {
    throw new Error(`Not a GovAccess published-document URL: ${value}`);
  }
  const [, documentId, revisionToken] = match;
  let revisionTime = null;
  if (revisionToken) {
    const milliseconds =
      (BigInt(revisionToken) - DOTNET_UNIX_EPOCH_TICKS) /
      TICKS_PER_MILLISECOND;
    revisionTime = new Date(Number(milliseconds)).toISOString();
  }
  return {
    documentId,
    revisionTime,
    revisionToken: revisionToken || null,
    url: value,
  };
}

const urls = process.argv.slice(2);
if (urls.length === 0) {
  console.error("Usage: npm run inspect:govaccess -- <document-url> [...]");
  process.exit(1);
}

for (const url of urls) {
  console.log(JSON.stringify(parseGovAccessUrl(url)));
}
