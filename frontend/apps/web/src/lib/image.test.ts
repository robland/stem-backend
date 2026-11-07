import { clampCrop, cropPixels, dragCrop, FULL_CROP, fitWithin, MIN_CROP } from "./image";

describe("fitWithin", () => {
  it("réduit le côté long à 1600 px en gardant les proportions", () => {
    expect(fitWithin(4000, 3000)).toEqual({ width: 1600, height: 1200 });
    expect(fitWithin(3000, 4000)).toEqual({ width: 1200, height: 1600 });
  });

  it("n'agrandit jamais une petite image", () => {
    expect(fitWithin(800, 600)).toEqual({ width: 800, height: 600 });
  });
});

describe("cropPixels", () => {
  it("convertit un recadrage fractionnaire en pixels, borné à l'image", () => {
    expect(cropPixels({ x: 0.25, y: 0.5, w: 0.5, h: 0.5 }, 1000, 800)).toEqual({
      x: 250,
      y: 400,
      width: 500,
      height: 400,
    });
    expect(cropPixels(FULL_CROP, 1000, 800)).toEqual({ x: 0, y: 0, width: 1000, height: 800 });
  });
});

describe("dragCrop", () => {
  const crop = { x: 0.2, y: 0.2, w: 0.6, h: 0.6 };

  it("déplace le cadre sans sortir de l'image", () => {
    expect(dragCrop(crop, "move", 0.5, -0.5)).toEqual({ x: 0.4, y: 0, w: 0.6, h: 0.6 });
  });

  it("tire le coin bas-droit", () => {
    const result = dragCrop(crop, "se", 0.1, 0.5);
    expect(result.w).toBeCloseTo(0.7);
    expect(result.h).toBeCloseTo(0.8); // borné au bord de l'image
  });

  it("tire le coin haut-gauche en gardant le coin opposé fixe", () => {
    const result = dragCrop(crop, "nw", -0.1, 0.1);
    expect(result.x).toBeCloseTo(0.1);
    expect(result.y).toBeCloseTo(0.3);
    expect(result.x + result.w).toBeCloseTo(0.8);
    expect(result.y + result.h).toBeCloseTo(0.8);
  });

  it("ne descend pas sous la taille minimale", () => {
    const result = dragCrop(crop, "nw", 0.9, 0.9);
    expect(result.w).toBeCloseTo(MIN_CROP);
    expect(result.h).toBeCloseTo(MIN_CROP);
  });
});

describe("clampCrop", () => {
  it("ramène un cadre débordant dans l'image", () => {
    expect(clampCrop({ x: 0.8, y: -0.2, w: 0.5, h: 2 })).toEqual({ x: 0.5, y: 0, w: 0.5, h: 1 });
  });
});
