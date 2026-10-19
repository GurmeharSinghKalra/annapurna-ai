// The farm profile: its shape, its defaults, and the single place it is converted for the API.

export const SEASONS = ['Kharif', 'Rabi', 'Annual'];
export const LANGUAGES = ['English', 'Hindi', 'Punjabi', 'Haryanvi'];
export const SOIL_TYPES = ['Alluvial', 'Black', 'Clayey', 'Loamy', 'Sandy loam'];
export const IRRIGATION = ['Rainfed', 'Limited', 'Assured'];
export const PRIORITIES = ['Balanced', 'Profit', 'Sustainability', 'Water saving'];

// "Previous crop" is a required field whose options used to come only from GET /crops, so the
// planner could not be completed at all while the API was unreachable. This is the fallback list;
// the server's catalogue replaces it as soon as it arrives.
export const FALLBACK_CROPS = [
  'Rice', 'Maize', 'Cotton', 'Wheat', 'Mustard', 'Chickpea', 'Sugarcane', 'Pearl Millet',
];

export const IRRIGATION_HELP = {
  Rainfed: 'No assured source — the crop depends on rain alone.',
  Limited: 'A canal turn or a shared borewell you cannot always rely on.',
  Assured: 'Your own reliable source, available when the crop needs it.',
};

export const emptyFarm = {
  farmerName: '',
  location: '',
  language: '',
  landSize: '',
  season: '',
  previousCrop: '',
  soilType: '',
  irrigation: '',
  ph: '',
  nitrogen: '',
  phosphorus: '',
  potassium: '',
  temperature: '',
  humidity: '',
  rainfall: '',
  budget: '',
  marketPriority: '',
  knownMarketPrices: {},
};

// knownMarketPrices is an optional map, not a form field, so it is excluded from validation.
export const FARM_FIELDS = Object.keys(emptyFarm).filter((key) => key !== 'knownMarketPrices');

// Field label and valid range, used for both the form and client-side validation so the farmer
// is told what is wrong before a request is sent.
export const FIELD_RULES = {
  farmerName: { label: 'Your name' },
  location: { label: 'Location', hint: 'District, State — for example Sonipat, Haryana' },
  language: { label: 'Language' },
  landSize: { label: 'Land size', unit: 'acre', min: 0.1, max: 2000 },
  season: { label: 'Season' },
  previousCrop: { label: 'Previous crop' },
  soilType: { label: 'Soil type' },
  irrigation: { label: 'Irrigation access' },
  ph: { label: 'Soil pH', min: 3, max: 10 },
  nitrogen: { label: 'Nitrogen', unit: 'index 0-100', min: 0, max: 100 },
  phosphorus: { label: 'Phosphorus', unit: 'index 0-100', min: 0, max: 100 },
  potassium: { label: 'Potassium', unit: 'index 0-100', min: 0, max: 100 },
  temperature: { label: 'Average temperature', unit: '°C', min: -10, max: 55 },
  humidity: { label: 'Humidity', unit: '%', min: 0, max: 100 },
  rainfall: {
    label: 'Seasonal rainfall',
    unit: 'mm for the whole season',
    min: 0,
    max: 5000,
    hint: 'The total across the season, not per day. Kharif in Haryana is roughly 400-700 mm.',
  },
  budget: { label: 'Planning budget', unit: '₹', min: 0, max: 100000000 },
  marketPriority: { label: 'What matters most' },
};

export function toApiFarm(farm) {
  return {
    farmer_name: farm.farmerName.trim(),
    location: farm.location.trim(),
    language: farm.language,
    land_size: Number(farm.landSize),
    season: farm.season,
    previous_crop: farm.previousCrop,
    soil_type: farm.soilType,
    irrigation: farm.irrigation,
    ph: Number(farm.ph),
    nitrogen: Number(farm.nitrogen),
    phosphorus: Number(farm.phosphorus),
    potassium: Number(farm.potassium),
    temperature: Number(farm.temperature),
    humidity: Number(farm.humidity),
    rainfall: Number(farm.rainfall),
    budget: Number(farm.budget),
    market_priority: farm.marketPriority,
    known_market_prices: Object.fromEntries(
      Object.entries(farm.knownMarketPrices || {})
        .map(([crop, value]) => [crop, Math.round(Number(value))])
        .filter(([, value]) => Number.isFinite(value) && value >= 1)
    ),
  };
}

export function fromApiFarm(payload) {
  if (!payload) return { ...emptyFarm };
  return {
    farmerName: payload.farmer_name ?? '',
    location: payload.location ?? '',
    language: payload.language ?? '',
    landSize: String(payload.land_size ?? ''),
    season: payload.season ?? '',
    previousCrop: payload.previous_crop ?? '',
    soilType: payload.soil_type ?? '',
    irrigation: payload.irrigation ?? '',
    ph: String(payload.ph ?? ''),
    nitrogen: String(payload.nitrogen ?? ''),
    phosphorus: String(payload.phosphorus ?? ''),
    potassium: String(payload.potassium ?? ''),
    temperature: String(payload.temperature ?? ''),
    humidity: String(payload.humidity ?? ''),
    rainfall: String(payload.rainfall ?? ''),
    budget: String(payload.budget ?? ''),
    marketPriority: payload.market_priority ?? '',
    knownMarketPrices: payload.known_market_prices ?? {},
  };
}

/** Per-field problems, so the planner can point at the offending input instead of failing late. */
export function validateFarm(farm) {
  const problems = {};
  for (const [field, rule] of Object.entries(FIELD_RULES)) {
    const raw = farm[field];
    if (String(raw ?? '').trim() === '') {
      problems[field] = `${rule.label} is required`;
      continue;
    }
    if (rule.min === undefined) continue;
    const value = Number(raw);
    if (!Number.isFinite(value)) {
      problems[field] = `${rule.label} must be a number`;
    } else if (value < rule.min || value > rule.max) {
      problems[field] = `${rule.label} must be between ${rule.min} and ${rule.max}`;
    }
  }
  return problems;
}

export function isFarmComplete(farm) {
  return Object.keys(validateFarm(farm)).length === 0;
}

/** The API returns snake_case; the UI reads camelCase. One conversion, in one place. */
export function normalizeRecommendation(item) {
  if (!item) return null;
  return {
    ...item,
    name: item.crop,
    expectedProfit: item.expected_profit,
    expectedYield: item.expected_yield,
    estimatedCost: item.estimated_cost,
    estimatedRevenue: item.estimated_revenue,
    profitMargin: item.profit_margin,
    marketPrice: item.market_price,
    priceBasis: item.price_basis,
    sustainabilityScore: item.sustainability_score,
    durationDays: item.duration_days,
    limiters: item.limiters || [],
    reasons: item.reasons || [],
    cautions: item.cautions || [],
    sources: item.sources || [],
    economics: item.economics,
  };
}
