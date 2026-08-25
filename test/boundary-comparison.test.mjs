import assert from "node:assert/strict";
import { test } from "node:test";

import {
  bbox,
  componentContainment,
  geometryAreaSquareMeters,
  pointInGeometry,
  polygons,
} from "../scripts/build-boundary-comparison.mjs";

const square = {
  type: "Polygon",
  coordinates: [[
    [-123.8, 39.3],
    [-123.79, 39.3],
    [-123.79, 39.31],
    [-123.8, 39.31],
    [-123.8, 39.3],
  ]],
};

test("normalizes and measures polygon geometry", () => {
  assert.equal(polygons(square).length, 1);
  assert.deepEqual(bbox([square]), [-123.8, 39.3, -123.79, 39.31]);
  assert.ok(geometryAreaSquareMeters(square) > 900_000);
});

test("checks point containment without assigning legal meaning", () => {
  assert.equal(pointInGeometry([-123.795, 39.305], square), true);
  assert.equal(pointInGeometry([-123.78, 39.305], square), false);
});

test("classifies a polygon that crosses the comparison boundary", () => {
  const crossing = [[
    [-123.795, 39.305],
    [-123.785, 39.305],
    [-123.785, 39.307],
    [-123.795, 39.307],
    [-123.795, 39.305],
  ]];
  const result = componentContainment(crossing, square);
  assert.equal(result.mapped_relation, "crosses_mccsd_boundary");
  assert.equal(result.boundary_intersection_count, 2);
});
