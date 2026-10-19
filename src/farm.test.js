import { describe, expect, it } from 'vitest';
import { emptyFarm, fromApiFarm, isFarmComplete, normalizeRecommendation, toApiFarm, validateFarm, FALLBACK_CROPS } from './farm.js';

const complete = {
  farmerName: 'Gurmehar', location: 'Sonipat, Haryana', language: 'English', landSize: '2',
  season: 'Kharif', previousCrop: 'Wheat', soilType: 'Alluvial', irrigation: 'Assured',
  ph: '6.6', nitrogen: '62', phosphorus: '41', potassium: '48', temperature: '29',
  humidity: '64', rainfall: '600', budget: '120000', marketPriority: 'Balanced',
};

describe('validation', () => {
  it('reports every missing field on an empty profile', () => {
    const problems = validateFarm(emptyFarm);
    // knownMarketPrices is an optional map, not a required form field.
    expect(Object.keys(problems)).toHaveLength(Object.keys(emptyFarm).length - 1);
    expect(problems.knownMarketPrices).toBeUndefined();
    expect(isFarmComplete(emptyFarm)).toBe(false);
  });

  it('accepts a complete profile', () => {
    expect(validateFarm(complete)).toEqual({});
    expect(isFarmComplete(complete)).toBe(true);
  });

  it('rejects out-of-range values with a message naming the field', () => {
    expect(validateFarm({ ...complete, ph: '99' }).ph).toMatch(/Soil pH must be between 3 and 10/);
    expect(validateFarm({ ...complete, landSize: '0' }).landSize).toBeTruthy();
    expect(validateFarm({ ...complete, rainfall: '-1' }).rainfall).toBeTruthy();
  });

  it('rejects non-numeric input in a numeric field', () => {
    expect(validateFarm({ ...complete, nitrogen: 'lots' }).nitrogen).toMatch(/must be a number/);
  });

  it('treats whitespace as missing', () => {
    expect(validateFarm({ ...complete, farmerName: '   ' }).farmerName).toBeTruthy();
  });
});

describe('API conversion', () => {
  it('converts to the snake_case contract with real numbers', () => {
    const payload = toApiFarm(complete);
    expect(payload.farmer_name).toBe('Gurmehar');
    expect(payload.land_size).toBe(2);
    expect(payload.market_priority).toBe('Balanced');
    expect(payload.irrigation).toBe('Assured');
    expect(typeof payload.ph).toBe('number');
  });

  it('trims the free-text fields', () => {
    expect(toApiFarm({ ...complete, location: '  Sonipat, Haryana  ' }).location).toBe('Sonipat, Haryana');
  });
});

describe('recommendation normalisation', () => {
  it('exposes camelCase without losing the original payload', () => {
    const item = normalizeRecommendation({
      crop: 'Rice', suitability: 93, verdict: 'strong match', expected_profit: 60696,
      expected_yield: 56, estimated_cost: 76000, estimated_revenue: 136696, profit_margin: 44,
      market_price: 2441, price_basis: 'MSP', sustainability_score: 36, duration_days: 135,
      limiters: [], reasons: ['a'], cautions: ['b'], sources: ['s'], economics: {},
    });
    expect(item.name).toBe('Rice');
    expect(item.expectedProfit).toBe(60696);
    expect(item.priceBasis).toBe('MSP');
    expect(item.crop).toBe('Rice');
  });

  it('defaults the list fields so the UI never maps over undefined', () => {
    const item = normalizeRecommendation({ crop: 'Maize' });
    expect(item.limiters).toEqual([]);
    expect(item.reasons).toEqual([]);
    expect(item.cautions).toEqual([]);
    expect(item.sources).toEqual([]);
  });

  it('returns null for a missing item instead of throwing', () => {
    expect(normalizeRecommendation(null)).toBeNull();
  });
});

describe('farmer-entered mandi prices', () => {
  it('are sent to the API, rounded, with blanks and junk dropped', () => {
    const payload = toApiFarm({
      ...complete,
      knownMarketPrices: { Cotton: '8900.4', Wheat: '', Maize: 'abc', Rice: 0 },
    });
    expect(payload.known_market_prices).toEqual({ Cotton: 8900 });
  });

  it('default to an empty map rather than undefined', () => {
    expect(toApiFarm(complete).known_market_prices).toEqual({});
  });

  it('survive a round trip through the API shape', () => {
    const restored = fromApiFarm({ ...toApiFarm({ ...complete, knownMarketPrices: { Cotton: 8900 } }) });
    expect(restored.knownMarketPrices).toEqual({ Cotton: 8900 });
  });
});

describe('offline usability', () => {
  it('ships a crop list so the planner is completable before /crops responds', () => {
    expect(FALLBACK_CROPS).toContain('Wheat');
    expect(FALLBACK_CROPS.length).toBeGreaterThanOrEqual(8);
  });
});
