#!/usr/bin/env node

import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { pathToFileURL } from "node:url";

export function polygons(geometry) {
  if (geometry.type === "Polygon") return [geometry.coordinates];
  if (geometry.type === "MultiPolygon") return geometry.coordinates;
  throw new Error(`Unsupported geometry type: ${geometry.type}`);
}

export function bbox(geometries) {
  const result = [Infinity, Infinity, -Infinity, -Infinity];
  for (const geometry of geometries) {
    for (const polygon of polygons(geometry)) {
      for (const ring of polygon) {
        for (const [longitude, latitude] of ring) {
          result[0] = Math.min(result[0], longitude);
          result[1] = Math.min(result[1], latitude);
          result[2] = Math.max(result[2], longitude);
          result[3] = Math.max(result[3], latitude);
        }
      }
    }
  }
  return result;
}

function ringAreaSquareMeters(ring) {
  const meanLatitude = ring.reduce((sum, point) => sum + point[1], 0) / ring.length;
  const xScale = 111_320 * Math.cos(meanLatitude * Math.PI / 180);
  const yScale = 110_574;
  let twiceArea = 0;
  for (let index = 0; index < ring.length - 1; index += 1) {
    const [x1, y1] = ring[index];
    const [x2, y2] = ring[index + 1];
    twiceArea += (x1 * xScale) * (y2 * yScale)
      - (x2 * xScale) * (y1 * yScale);
  }
  return Math.abs(twiceArea) / 2;
}

export function geometryAreaSquareMeters(geometry) {
  return polygons(geometry).reduce((total, polygon) => {
    const [outer, ...holes] = polygon;
    return total + ringAreaSquareMeters(outer)
      - holes.reduce((sum, ring) => sum + ringAreaSquareMeters(ring), 0);
  }, 0);
}

function pointInRing([x, y], ring) {
  let inside = false;
  for (let current = 0, previous = ring.length - 1;
    current < ring.length;
    previous = current, current += 1) {
    const [xi, yi] = ring[current];
    const [xj, yj] = ring[previous];
    const crosses = (yi > y) !== (yj > y)
      && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (crosses) inside = !inside;
  }
  return inside;
}

export function pointInGeometry(point, geometry) {
  return polygons(geometry).some(([outer, ...holes]) => (
    pointInRing(point, outer)
      && !holes.some((hole) => pointInRing(point, hole))
  ));
}

function orientation(a, b, c) {
  return (b[0] - a[0]) * (c[1] - a[1])
    - (b[1] - a[1]) * (c[0] - a[0]);
}

function segmentsIntersect(a, b, c, d) {
  const first = orientation(a, b, c);
  const second = orientation(a, b, d);
  const third = orientation(c, d, a);
  const fourth = orientation(c, d, b);
  return ((first > 0 && second < 0) || (first < 0 && second > 0))
    && ((third > 0 && fourth < 0) || (third < 0 && fourth > 0));
}

function boundaryIntersections(component, container) {
  const componentRings = component;
  const containerRings = polygons(container).flat();
  let count = 0;
  for (const componentRing of componentRings) {
    for (let first = 0; first < componentRing.length - 1; first += 1) {
      for (const containerRing of containerRings) {
        for (let second = 0; second < containerRing.length - 1; second += 1) {
          if (segmentsIntersect(
            componentRing[first],
            componentRing[first + 1],
            containerRing[second],
            containerRing[second + 1],
          )) {
            count += 1;
          }
        }
      }
    }
  }
  return count;
}

export function componentContainment(component, container) {
  const vertices = component[0].slice(0, -1);
  const insideCount = vertices.filter((point) => (
    pointInGeometry(point, container)
  )).length;
  const intersections = boundaryIntersections(component, container);
  let relation = "outside_mccsd";
  if (intersections > 0) {
    relation = "crosses_mccsd_boundary";
  } else if (insideCount === vertices.length) {
    relation = "inside_mccsd";
  } else if (insideCount > 0) {
    relation = "mixed_without_detected_intersection";
  }
  return {
    vertex_count: vertices.length,
    vertices_inside_mccsd: insideCount,
    boundary_intersection_count: intersections,
    all_vertices_inside_mccsd: insideCount === vertices.length,
    mapped_relation: relation,
  };
}

function digest(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

function svgPath(geometry, project) {
  return polygons(geometry).flatMap((polygon) => polygon.map((ring) => (
    `${ring.map(([x, y], index) => {
      const [px, py] = project(x, y);
      return `${index ? "L" : "M"}${px.toFixed(2)},${py.toFixed(2)}`;
    }).join(" ")} Z`
  ))).join(" ");
}

function buildSvg(mccsd, ddw, metrics) {
  const width = 1100;
  const height = 760;
  const margin = { left: 70, right: 300, top: 85, bottom: 65 };
  const [minX, minY, maxX, maxY] = metrics.combined_bbox;
  const mapWidth = width - margin.left - margin.right;
  const mapHeight = height - margin.top - margin.bottom;
  const scale = Math.min(mapWidth / (maxX - minX), mapHeight / (maxY - minY));
  const renderedWidth = (maxX - minX) * scale;
  const renderedHeight = (maxY - minY) * scale;
  const offsetX = margin.left + (mapWidth - renderedWidth) / 2;
  const offsetY = margin.top + (mapHeight - renderedHeight) / 2;
  const project = (x, y) => [
    offsetX + (x - minX) * scale,
    offsetY + (maxY - y) * scale,
  ];
  const mccsdPath = svgPath(mccsd.geometry, project);
  const ddwPath = svgPath(ddw.geometry, project);
  const ratio = metrics.ddw_area_as_percent_of_mccsd.toFixed(2);
  const containment = metrics.ddw_components.map((component, index) => (
    `Component ${index + 1}: ${component.mapped_relation.replaceAll("_", " ")}`
  ));
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="title description">
  <title id="title">MCCSD jurisdiction and CA2300584 DDW system-area comparison</title>
  <description id="description">Derived overlay of two official geographic layers. It does not establish service authority.</description>
  <rect width="${width}" height="${height}" fill="#f5f1e8"/>
  <text x="45" y="38" font-family="system-ui, sans-serif" font-size="24" font-weight="700" fill="#193a39">MCCSD jurisdiction and CA2300584 mapped area</text>
  <text x="45" y="63" font-family="system-ui, sans-serif" font-size="13" fill="#526363">Derived orientation aid - EPSG:4326 - not a legal service determination</text>
  <path d="${mccsdPath}" fill="#2d746b" fill-opacity=".22" stroke="#19564f" stroke-width="2.2" fill-rule="evenodd"/>
  <path d="${ddwPath}" fill="#db7c32" fill-opacity=".58" stroke="#9c4718" stroke-width="2.5" fill-rule="evenodd"/>
  <g transform="translate(830 105)" font-family="system-ui, sans-serif">
    <text x="0" y="0" font-size="16" font-weight="700" fill="#193a39">Boundary kinds</text>
    <rect x="0" y="22" width="24" height="16" fill="#2d746b" fill-opacity=".35" stroke="#19564f"/>
    <text x="34" y="35" font-size="12">MCCSD jurisdiction</text>
    <rect x="0" y="52" width="24" height="16" fill="#db7c32" fill-opacity=".65" stroke="#9c4718"/>
    <text x="34" y="65" font-size="12">DDW CA2300584 area</text>
    <text x="0" y="105" font-size="14" font-weight="700">Mapped-area comparison</text>
    <text x="0" y="127" font-size="12">DDW / MCCSD: ${ratio}%</text>
    ${containment.map((line, index) => `<text x="0" y="${151 + index * 19}" font-size="11">${line}</text>`).join("\n    ")}
    <text x="0" y="215" font-size="14" font-weight="700">What this answers</text>
    <text x="0" y="237" font-size="11">Where the two published</text>
    <text x="0" y="253" font-size="11">geometries lie relative to each other.</text>
    <text x="0" y="287" font-size="14" font-weight="700">What it does not answer</text>
    <text x="0" y="309" font-size="11">Customers, legal service scope,</text>
    <text x="0" y="325" font-size="11">LAFCo approval, permit conditions,</text>
    <text x="0" y="341" font-size="11">or authority to serve non-school users.</text>
    <text x="0" y="385" font-size="11" font-weight="700">DDW warns its layer is a general</text>
    <text x="0" y="401" font-size="11" font-weight="700">representation, not a binding document.</text>
  </g>
  <g transform="translate(75 680)" font-family="system-ui, sans-serif" font-size="10" fill="#526363">
    <text x="0" y="0">Sources: county_2026_mccsd_boundary; ddw_2021_service_area</text>
    <text x="0" y="18">Generated deterministically from registered source bytes; no geometry was inferred or edited.</text>
  </g>
  <g transform="translate(765 105)" stroke="#193a39" fill="none">
    <path d="M0 30 L0 0 M0 0 L-6 11 M0 0 L6 11" stroke-width="2"/>
    <text x="-5" y="-8" fill="#193a39" stroke="none" font-family="system-ui, sans-serif" font-size="12">N</text>
  </g>
</svg>
`;
}

export async function buildBoundaryComparison(options = {}) {
  const mccsdPath = resolve(options.mccsdPath
    || "captures/cases/UM_2025-0004/boundaries/2026-county-mccsd-boundary.geojson");
  const ddwPath = resolve(options.ddwPath
    || "captures/cases/UM_2025-0004/water-law/2021-ddw-service-area.geojson");
  const geojsonPath = resolve(options.geojsonPath
    || "captures/cases/UM_2025-0004/boundaries/derived/2026-mccsd-ca2300584-comparison.geojson");
  const metricsPath = resolve(options.metricsPath
    || "captures/cases/UM_2025-0004/boundaries/derived/2026-mccsd-ca2300584-comparison.json");
  const svgPathname = resolve(options.svgPath
    || "web/mccsd-ca2300584-boundary-comparison.svg");
  const [mccsdBytes, ddwBytes] = await Promise.all([
    readFile(mccsdPath),
    readFile(ddwPath),
  ]);
  const mccsd = JSON.parse(mccsdBytes);
  const ddw = JSON.parse(ddwBytes);
  if (mccsd.features.length !== 1 || ddw.features.length !== 1) {
    throw new Error("Each source must contain exactly one feature");
  }
  const mccsdFeature = mccsd.features[0];
  const ddwFeature = ddw.features[0];
  const mccsdArea = geometryAreaSquareMeters(mccsdFeature.geometry);
  const ddwArea = geometryAreaSquareMeters(ddwFeature.geometry);
  const metrics = {
    schema_version: 1,
    artifact_kind: "derived_boundary_comparison",
    coordinate_system: "EPSG:4326",
    source_sha256: {
      county_2026_mccsd_boundary: digest(mccsdBytes),
      ddw_2021_service_area: digest(ddwBytes),
    },
    combined_bbox: bbox([mccsdFeature.geometry, ddwFeature.geometry]),
    mccsd_area_square_meters_approximate: Math.round(mccsdArea),
    ddw_area_square_meters_approximate: Math.round(ddwArea),
    ddw_area_as_percent_of_mccsd: ddwArea / mccsdArea * 100,
    ddw_components: polygons(ddwFeature.geometry).map((component) => (
      componentContainment(component, mccsdFeature.geometry)
    )),
    establishes: [
      "The relative geometry of the two registered source layers.",
      "The approximate mapped-area ratio and vertex containment checks.",
    ],
    does_not_establish: [
      "LAFCo approval, exemption, annexation, or sphere amendment.",
      "The operative DDW permit service description or authorized customers.",
      "Historical service commencement, delivery points, or legal authority.",
    ],
  };
  const comparison = {
    type: "FeatureCollection",
    name: "MCCSD jurisdiction and CA2300584 DDW system-area comparison",
    metadata: metrics,
    features: [
      {
        type: "Feature",
        properties: {
          source_id: "county_2026_mccsd_boundary",
          boundary_kind: "district_jurisdiction",
          legal_effect: "MCCSD jurisdictional geometry",
        },
        geometry: mccsdFeature.geometry,
      },
      {
        type: "Feature",
        properties: {
          source_id: "ddw_2021_service_area",
          boundary_kind: "ddw_system_area_representation",
          legal_effect: "general representation; exact legal scope unknown",
        },
        geometry: ddwFeature.geometry,
      },
    ],
  };
  await Promise.all([
    mkdir(dirname(geojsonPath), { recursive: true }),
    mkdir(dirname(svgPathname), { recursive: true }),
  ]);
  await Promise.all([
    writeFile(geojsonPath, `${JSON.stringify(comparison, null, 2)}\n`),
    writeFile(metricsPath, `${JSON.stringify(metrics, null, 2)}\n`),
    writeFile(svgPathname, buildSvg(mccsdFeature, ddwFeature, metrics)),
  ]);
  return { geojsonPath, metricsPath, svgPathname, metrics };
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const result = await buildBoundaryComparison();
  console.log(JSON.stringify(result, null, 2));
}
