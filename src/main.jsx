import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  BarChart3,
  Bot,
  CalendarDays,
  Camera,
  CheckCircle2,
  CloudSun,
  Database,
  Download,
  Droplets,
  Home,
  History,
  IndianRupee,
  Leaf,
  LineChart,
  MapPin,
  MessageSquareText,
  Save,
  Search,
  Settings,
  ShieldCheck,
  Sprout,
  Upload,
  Wallet,
  Wheat
} from 'lucide-react';
import './styles.css';

// Development talks directly to FastAPI; the production container proxies `/api` to it.
const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '/api');
const FINANCE_STORAGE_KEY = 'annapurna-season-finance-v1';
const HISTORY_STORAGE_KEY = 'annapurna-saved-plans-v1';

const crops = [
  {
    name: 'Rice',
    icon: Wheat,
    season: 'Kharif',
    soils: ['Alluvial', 'Clayey'],
    rainfall: [140, 300],
    temperature: [22, 36],
    ph: [5.5, 7],
    water: 'High',
    cost: 32000,
    marketPrice: 2350,
    yield: 28,
    sustainability: 'Use alternate wetting and drying to reduce water use.',
    rotation: 'Follow with lentil, pea, or mustard.',
    advisory: 'Best where water access is dependable. Watch for blast disease during humid weeks.'
  },
  {
    name: 'Maize',
    icon: Sprout,
    season: 'Kharif',
    soils: ['Alluvial', 'Loamy', 'Sandy loam'],
    rainfall: [50, 120],
    temperature: [18, 32],
    ph: [5.8, 7.5],
    water: 'Medium',
    cost: 26000,
    marketPrice: 2250,
    yield: 24,
    sustainability: 'Moderate water demand and good fit for diversified farms.',
    rotation: 'Rotate with gram, pea, or vegetables.',
    advisory: 'Avoid waterlogging and split nitrogen application across growth stages.'
  },
  {
    name: 'Cotton',
    icon: Sprout,
    season: 'Kharif',
    soils: ['Black', 'Loamy'],
    rainfall: [60, 120],
    temperature: [21, 35],
    ph: [6, 8],
    water: 'Medium',
    cost: 39000,
    marketPrice: 7100,
    yield: 16,
    sustainability: 'Needs pest monitoring; avoid repeated cotton on the same field.',
    rotation: 'Rotate with wheat, gram, or sorghum.',
    advisory: 'Profitable but higher-risk; inspect for sucking pests and bollworm symptoms.'
  },
  {
    name: 'Wheat',
    icon: Wheat,
    season: 'Rabi',
    soils: ['Alluvial', 'Loamy'],
    rainfall: [45, 110],
    temperature: [10, 25],
    ph: [6, 7.8],
    water: 'Medium',
    cost: 28500,
    marketPrice: 2425,
    yield: 25,
    sustainability: 'Works well in rotation after rice or maize.',
    rotation: 'Follow with mung bean, fodder, or maize.',
    advisory: 'Irrigate at crown-root initiation, tillering, and flowering.'
  },
  {
    name: 'Mustard',
    icon: Leaf,
    season: 'Rabi',
    soils: ['Loamy', 'Sandy loam', 'Alluvial'],
    rainfall: [25, 75],
    temperature: [10, 26],
    ph: [6, 8],
    water: 'Low',
    cost: 22000,
    marketPrice: 5650,
    yield: 11,
    sustainability: 'Good low-water option for winter season.',
    rotation: 'Follow after rice, maize, or pearl millet.',
    advisory: 'Protect flowering stage from aphids and avoid excess irrigation.'
  },
  {
    name: 'Chickpea',
    icon: Leaf,
    season: 'Rabi',
    soils: ['Black', 'Loamy', 'Sandy loam'],
    rainfall: [30, 90],
    temperature: [15, 30],
    ph: [6, 8.2],
    water: 'Low',
    cost: 23500,
    marketPrice: 5900,
    yield: 13,
    sustainability: 'Adds nitrogen to soil and reduces fertilizer dependency.',
    rotation: 'Best after wheat, rice, or maize.',
    advisory: 'Avoid waterlogging and use seed treatment against wilt.'
  },
  {
    name: 'Sugarcane',
    icon: Sprout,
    season: 'Annual',
    soils: ['Alluvial', 'Loamy', 'Black'],
    rainfall: [110, 250],
    temperature: [21, 38],
    ph: [6, 8],
    water: 'Very high',
    cost: 62000,
    marketPrice: 360,
    yield: 360,
    sustainability: 'High return but high water footprint; use drip irrigation where possible.',
    rotation: 'Rotate with pulses or vegetables after ratoon cycle.',
    advisory: 'Choose only when irrigation, time, and transport access are strong.'
  },
  {
    name: 'Pearl Millet',
    icon: Wheat,
    season: 'Kharif',
    soils: ['Sandy loam', 'Loamy'],
    rainfall: [25, 70],
    temperature: [25, 40],
    ph: [6, 8.5],
    water: 'Low',
    cost: 18500,
    marketPrice: 2650,
    yield: 15,
    sustainability: 'Climate-resilient crop for low-rainfall regions.',
    rotation: 'Rotate with mustard, chickpea, or wheat.',
    advisory: 'Good fallback when rainfall is uncertain and soil is lighter.'
  }
];

const initialFarm = {
  farmerName: '',
  location: '',
  language: '',
  landSize: '',
  season: '',
  previousCrop: '',
  soilType: '',
  ph: '',
  nitrogen: '',
  phosphorus: '',
  potassium: '',
  temperature: '',
  humidity: '',
  rainfall: '',
  budget: '',
  marketPriority: ''
};

function toApiFarm(farm) {
  return {
    farmer_name: farm.farmerName,
    location: farm.location,
    language: farm.language,
    land_size: Number(farm.landSize),
    season: farm.season,
    previous_crop: farm.previousCrop,
    soil_type: farm.soilType,
    ph: Number(farm.ph),
    nitrogen: Number(farm.nitrogen),
    phosphorus: Number(farm.phosphorus),
    potassium: Number(farm.potassium),
    temperature: Number(farm.temperature),
    humidity: Number(farm.humidity),
    rainfall: Number(farm.rainfall),
    budget: Number(farm.budget),
    market_priority: farm.marketPriority
  };
}

function normalizeRecommendation(item) {
  return {
    ...item,
    name: item.name || item.crop,
    icon: Sprout,
    water: item.water,
    expectedProfit: item.expectedProfit ?? item.expected_profit,
    expectedYield: item.expectedYield ?? item.expected_yield,
    estimatedCost: item.estimatedCost ?? item.estimated_cost,
    estimatedRevenue: item.estimatedRevenue ?? item.estimated_revenue,
    profitMargin: item.profitMargin ?? item.profit_margin,
    marketPrice: item.marketPrice ?? item.market_price,
    marketTrend: item.marketTrend ?? item.market_trend,
    sustainabilityScore: item.sustainabilityScore ?? item.sustainability_score
  };
}

function scoreCrop(crop, farm) {
  let score = 30;
  const reasons = [];
  const cautions = [];

  if (crop.season === farm.season || crop.season === 'Annual') {
    score += 18;
    reasons.push(`Fits ${farm.season} planning`);
  } else {
    cautions.push(`Usually grown in ${crop.season}`);
  }

  if (crop.soils.includes(farm.soilType)) {
    score += 16;
    reasons.push(`${farm.soilType} soil is suitable`);
  } else {
    cautions.push(`Soil match is weaker for ${farm.soilType}`);
  }

  [
    ['pH', Number(farm.ph), crop.ph, 12],
    ['temperature', Number(farm.temperature), crop.temperature, 10],
    ['rainfall', Number(farm.rainfall), crop.rainfall, 12]
  ].forEach(([label, value, range, points]) => {
    if (value >= range[0] && value <= range[1]) {
      score += points;
      reasons.push(`${label} is in range`);
    } else {
      const distance = value < range[0] ? range[0] - value : value - range[1];
      score -= Math.min(points, distance / 2);
      cautions.push(`${label} is outside ideal range`);
    }
  });

  const nutrients =
    (Number(farm.nitrogen) + Number(farm.phosphorus) + Number(farm.potassium)) / 3;
  if (nutrients >= 55) {
    score += 10;
    reasons.push('Nutrient level is strong');
  } else if (nutrients >= 40) {
    score += 6;
    reasons.push('Nutrient level is workable');
  } else {
    cautions.push('Nutrient correction is needed');
  }

  const landSize = Number(farm.landSize || 1);
  const expectedYield = Math.round(crop.yield * landSize);
  const estimatedCost = Math.round(crop.cost * landSize);
  const estimatedRevenue = Math.round(expectedYield * crop.marketPrice);
  const expectedProfit = estimatedRevenue - estimatedCost;
  const profitPerAcre = (crop.yield * crop.marketPrice) - crop.cost;

  if (farm.marketPriority === 'Profit' && profitPerAcre > 40000) score += 6;
  if (farm.marketPriority === 'Sustainability' && crop.water === 'Low') score += 7;
  if (farm.marketPriority === 'Water saving' && ['Low', 'Medium'].includes(crop.water)) score += 7;

  if (Number(farm.budget) < estimatedCost) {
    score -= 5;
    cautions.push('Available budget is below the estimated cultivation cost');
  }
  const suitability = Math.max(36, Math.min(98, Math.round(score)));

  return {
    ...crop,
    suitability,
    expectedProfit,
    expectedYield,
    estimatedCost,
    estimatedRevenue,
    profitMargin: estimatedRevenue ? Math.round((expectedProfit / estimatedRevenue) * 100) : 0,
    reasons: reasons.slice(0, 4),
    cautions: cautions.slice(0, 3)
  };
}

function App() {
  const [route, setRoute] = useState(() => window.location.pathname || '/');
  const [farm, setFarm] = useState(initialFarm);
  const [history, setHistory] = useState([]);
  const [question, setQuestion] = useState('');
  const [chat, setChat] = useState([
    {
      by: 'Annapurna AI',
      text: 'Complete your farm profile and run analysis before asking for advice.'
    }
  ]);
  const [imageName, setImageName] = useState('');
  const [apiStatus, setApiStatus] = useState('Backend not checked yet');
  const [integrationStatus, setIntegrationStatus] = useState(null);
  const [apiRecommendations, setApiRecommendations] = useState(null);
  const [geminiExplanation, setGeminiExplanation] = useState(null);
  const [diseaseAdvisory, setDiseaseAdvisory] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [financialPlan, setFinancialPlan] = useState(null);
  const [actualExpenses, setActualExpenses] = useState({});
  const [manualMarketPrice, setManualMarketPrice] = useState('');
  const [financeLoading, setFinanceLoading] = useState(false);
  const [advisorLoading, setAdvisorLoading] = useState(false);
  const [cropNames, setCropNames] = useState([]);

  const profileComplete = [
    farm.farmerName, farm.location, farm.language, farm.landSize, farm.season, farm.previousCrop,
    farm.soilType, farm.ph, farm.nitrogen, farm.phosphorus, farm.potassium, farm.temperature,
    farm.humidity, farm.rainfall, farm.budget, farm.marketPriority
  ].every((value) => String(value).trim() !== '');
  const recommendations = apiRecommendations || [];
  const topCrop = recommendations[0];
  const weather = analysis?.weather;
  const soilAnalysis = analysis?.soil;
  const marketAnalysis = analysis?.markets?.[0];

  useEffect(() => {
    const storedFinance = localStorage.getItem(FINANCE_STORAGE_KEY);
    if (storedFinance) {
      try {
        const savedFinance = JSON.parse(storedFinance);
        setActualExpenses(savedFinance.actualExpenses || {});
        setManualMarketPrice(savedFinance.manualMarketPrice || '');
      } catch { localStorage.removeItem(FINANCE_STORAGE_KEY); }
    }
    loadHistory();
    loadIntegrationStatus();
    loadCropCatalog();
    const handleRoute = () => setRoute(window.location.pathname || '/');
    window.addEventListener('popstate', handleRoute);
    return () => window.removeEventListener('popstate', handleRoute);
  }, []);

  useEffect(() => {
    if (financialPlan) {
      localStorage.setItem(FINANCE_STORAGE_KEY, JSON.stringify({ crop: financialPlan.crop, actualExpenses, manualMarketPrice }));
    }
  }, [financialPlan, actualExpenses, manualMarketPrice]);

  function navigate(path) {
    if (window.location.pathname !== path) window.history.pushState({}, '', path);
    setRoute(path);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function update(field, value) {
    setFarm((current) => ({ ...current, [field]: value }));
    setApiRecommendations(null);
    setGeminiExplanation(null);
    setAnalysis(null);
    setFinancialPlan(null);
    setManualMarketPrice('');
  }

  function loadHistory() {
    try {
      const savedPlans = JSON.parse(localStorage.getItem(HISTORY_STORAGE_KEY) || '[]');
      setHistory(Array.isArray(savedPlans) ? savedPlans.slice(0, 6) : []);
    } catch {
      localStorage.removeItem(HISTORY_STORAGE_KEY);
      setHistory([]);
    }
  }

  async function loadIntegrationStatus() {
    try {
      const response = await fetch(`${API_BASE}/integrations/status`);
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      setIntegrationStatus(await response.json());
    } catch (error) {
      setIntegrationStatus(null);
    }
  }

  async function loadCropCatalog() {
    try {
      const response = await fetch(`${API_BASE}/crops`);
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const data = await response.json();
      setCropNames((data.crops || []).map((item) => item.crop).filter(Boolean));
    } catch (error) {
      setCropNames([]);
    }
  }

  async function exportReport() {
    if (!topCrop) {
      setApiStatus('Run a backend analysis before exporting a report.');
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/reports/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farm: toApiFarm(farm),
          recommendation: topCrop,
          weather,
          market: marketAnalysis,
          finance: financialPlan
        })
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `annapurna-${topCrop.name.toLowerCase().replace(/\s+/g, '-')}-farm-report.pdf`;
      link.click();
      URL.revokeObjectURL(url);
      setApiStatus('Designed PDF report downloaded.');
    } catch (error) {
      setApiStatus('PDF report could not be generated. Check the backend connection.');
    }
  }

  async function savePlan() {
    if (!topCrop) {
      setApiStatus('Run a backend analysis before saving a plan.');
      return;
    }
    const localRecord = {
      id: crypto.randomUUID(),
      crop: topCrop.name,
      score: topCrop.suitability,
      profit: topCrop.expectedProfit,
      location: farm.location,
      date: new Date().toLocaleString('en-IN')
    };

    setHistory((items) => {
      const nextHistory = [localRecord, ...items].slice(0, 6);
      localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(nextHistory));
      return nextHistory;
    });
    setApiStatus('Plan saved on this device');
  }

  function clearSavedPlans() {
    localStorage.removeItem(HISTORY_STORAGE_KEY);
    setHistory([]);
    setApiStatus('Saved plans cleared from this device');
  }

  function clearFinanceTracker() {
    localStorage.removeItem(FINANCE_STORAGE_KEY);
    setActualExpenses({});
    setManualMarketPrice('');
    setFinancialPlan(null);
    setApiStatus('Finance tracker cleared from this device');
  }

  async function syncBackend() {
    if (!profileComplete) {
      setApiStatus('Complete every farm profile field before analysis.');
      return;
    }
    setAnalysisLoading(true);
    try {
      const response = await fetch(`${API_BASE}/analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(toApiFarm(farm))
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const data = await response.json();
      const normalized = (data.recommendations || []).map(normalizeRecommendation);
      setApiRecommendations(normalized.length ? normalized : null);
      setAnalysis(data);
      setGeminiExplanation(data.ai_explanation || null);
      const top = normalized[0];
      setApiStatus(top ? `${data.ai_provider === 'gemini' ? 'Gemini explanation ready' : 'Analysis ready'}: ${top.name} ${top.suitability}%` : 'No verified recommendation returned');
    } catch (error) {
      setGeminiExplanation(null);
      setApiStatus('Backend offline: run FastAPI on port 8000');
    } finally {
      setAnalysisLoading(false);
    }
  }

  async function runFinancialPlan() {
    if (!topCrop || !profileComplete) {
      setApiStatus('Complete the profile and run crop analysis before creating a finance plan.');
      return;
    }
    setFinanceLoading(true);
    try {
      const response = await fetch(`${API_BASE}/finance/season-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farm: toApiFarm(farm),
          crop: topCrop.name,
          actual_expenses: Object.fromEntries(Object.entries(actualExpenses).map(([key, value]) => [key, Number(value) || 0])),
          market_price_per_quintal: manualMarketPrice.trim() ? Number(manualMarketPrice) : undefined
        })
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const data = await response.json();
      setFinancialPlan(data);
      setActualExpenses(Object.fromEntries(data.expenses.map((item) => [item.category, item.actual])));
      setApiStatus(`Season profit plan ready for ${data.crop}`);
    } catch (error) {
      setApiStatus('Financial planner needs the backend running on port 8000');
    } finally {
      setFinanceLoading(false);
    }
  }

  function exportFinancialPlan() {
    if (!financialPlan) return;
    const { summary } = financialPlan;
    const lines = [
      'Annapurna AI Season Finance Plan',
      '',
      `Farm: ${farm.farmerName}`,
      `Location: ${farm.location}`,
      `Season: ${farm.season}`,
      `Crop: ${financialPlan.crop}`,
      '',
      `Planned cultivation cost: INR ${summary.planned_cost.toLocaleString('en-IN')}`,
      `Current tracked cost: INR ${summary.actual_cost.toLocaleString('en-IN')}`,
      `Expected revenue: INR ${summary.expected_revenue.toLocaleString('en-IN')}`,
      `Expected profit: INR ${summary.expected_profit.toLocaleString('en-IN')}`,
      `Profit margin: ${summary.profit_margin}%`,
      `Break-even price: INR ${summary.break_even_price_per_quintal}/quintal`,
      `Working-capital gap: INR ${summary.working_capital_gap.toLocaleString('en-IN')}`,
      '',
      'Expense tracker:',
      ...financialPlan.expenses.map((item) => `- ${item.category}: planned INR ${item.planned.toLocaleString('en-IN')}; tracked INR ${item.actual.toLocaleString('en-IN')}`),
      '',
      'Risk scenarios:',
      ...financialPlan.scenarios.map((item) => `- ${item.name}: revenue INR ${item.revenue.toLocaleString('en-IN')}; profit INR ${item.profit.toLocaleString('en-IN')}`),
      '',
      'Important: This document is a planning estimate, not a lending, investment, or guaranteed-income recommendation.'
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `annapurna-${financialPlan.crop.toLowerCase().replace(/\s+/g, '-')}-season-finance.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function askBot() {
    const userQuestion = question.trim();
    if (!userQuestion || !topCrop || !profileComplete || advisorLoading) return;
    setChat((items) => [...items, { by: farm.farmerName, text: userQuestion }]);
    setQuestion('');
    setAdvisorLoading(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userQuestion,
          crop: topCrop.name,
          farm: toApiFarm(farm),
          finance: financialPlan ? {
            crop: financialPlan.crop,
            planning_source: financialPlan.planning_source,
            actual_cost: financialPlan.summary.actual_cost,
            expected_revenue: financialPlan.summary.expected_revenue,
            expected_profit: financialPlan.summary.expected_profit,
            break_even_price_per_quintal: financialPlan.summary.break_even_price_per_quintal,
            working_capital_gap: financialPlan.summary.working_capital_gap
          } : null
        })
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const data = await response.json();
      setChat((items) => [...items, { by: 'Annapurna AI', text: data.answer }]);
      setApiStatus(data.provider === 'gemini' ? 'Gemini advisor online' : 'Advisor response unavailable');
    } catch (error) {
      setChat((items) => [...items, { by: 'Annapurna AI', text: 'Advisor is unavailable right now. Please retry after the backend connection is restored.' }]);
      setApiStatus('Advisor request failed; no local answer was generated.');
    } finally {
      setAdvisorLoading(false);
    }
  }

  async function handleImage(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setImageName(file.name);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('crop', topCrop.name);
      const response = await fetch(`${API_BASE}/disease`, {
        method: 'POST',
        body: formData
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const data = await response.json();
      const confidence = Number.isFinite(data.confidence) ? ` · ${Math.round(data.confidence * 100)}% confidence` : '';
      setDiseaseAdvisory(`${data.prediction}${confidence}: ${data.advisory}`);
      setApiStatus(data.provider === 'gemini' ? 'Gemini visual analysis complete' : 'Disease fallback used');
    } catch (error) {
      setDiseaseAdvisory('Image analysis is unavailable. No diagnosis was generated. Please retry or consult a qualified agriculture expert.');
      setApiStatus('Disease analysis request failed; no local diagnosis was generated.');
    }
  }

  if (route === '/' || route === '/about') {
    return <MarketingSite page={route === '/about' ? 'about' : 'home'} navigate={navigate} />;
  }

  if (route === '/register' || route === '/login') {
    return <GuestEntry navigate={navigate} />;
  }

  const navItems = [
    ['/dashboard', 'Overview', Home],
    ['/planner', 'Crop planner', Sprout],
    ['/insights', 'Insights', BarChart3],
    ['/finance', 'Season finance', Wallet],
    ['/disease', 'Disease scan', Camera],
    ['/advisor', 'AI advisor', Bot],
    ['/records', 'Saved plans', History],
    ['/settings', 'System', Settings]
  ];

  const pageMeta = {
    '/dashboard': ['Farm overview', 'Your current season, recommendation, and field signals at a glance.'],
    '/planner': ['Crop planner', 'Enter farm conditions and compare the strongest crop matches.'],
    '/insights': ['Field insights', 'Understand the agronomy, economics, weather, and sustainability behind the recommendation.'],
    '/finance': ['Season finance', 'Plan costs, working capital, break-even price, and profitability scenarios.'],
    '/disease': ['Disease analysis', 'Upload a crop image and receive an initial advisory.'],
    '/advisor': ['AI farm advisor', 'Ask questions using your current crop and field conditions.'],
    '/records': ['Saved plans', 'Review recommendation plans saved for this farmer.'],
    '/settings': ['System & data', 'Review integrations, safeguards, and project readiness.']
  };
  const currentMeta = pageMeta[route] || pageMeta['/dashboard'];

  function renderPage() {
    if (!profileComplete && route !== '/planner') return (
      <section className="page-section empty-records">
        <Sprout size={30} />
        <h3>Complete your farm profile first</h3>
        <p>No crop, weather, finance, or advisor data is generated until you enter your own field details.</p>
        <button className="primary-action" onClick={() => navigate('/planner')}>Complete farm profile</button>
      </section>
    );
    if (profileComplete && !topCrop && route !== '/planner') return (
      <section className="page-section empty-records">
        <Database size={30} />
        <h3>Run your farm analysis</h3>
        <p>Your profile is ready. Generate a backend analysis to view recommendations and ask the advisor.</p>
        <button className="primary-action" onClick={() => navigate('/planner')}>Open crop planner</button>
      </section>
    );
    if (route === '/planner') return (
      <section className="main-grid page-section">
        <Panel title="Farm conditions" eyebrow="Step 01 / Enter data" icon={Search}>
          <div className="form-grid">
            <Field label="Farmer name" value={farm.farmerName} onChange={(value) => update('farmerName', value)} />
            <Field label="Location" value={farm.location} onChange={(value) => update('location', value)} />
            <SelectField label="Language" value={farm.language} values={['', 'English', 'Hindi', 'Punjabi', 'Haryanvi']} onChange={(value) => update('language', value)} />
            <SelectField label="Season" value={farm.season} values={['', 'Kharif', 'Rabi', 'Annual']} onChange={(value) => update('season', value)} />
            <SelectField label="Previous crop" value={farm.previousCrop} values={['', 'None', ...cropNames]} onChange={(value) => update('previousCrop', value)} />
            <SelectField label="Soil type" value={farm.soilType} values={['', 'Alluvial', 'Black', 'Clayey', 'Loamy', 'Sandy loam']} onChange={(value) => update('soilType', value)} />
            <RangeInput label="Land size (acre)" field="landSize" min="0.5" max="10" step="0.5" value={farm.landSize} update={update} />
            <RangeInput label="Soil pH" field="ph" min="4" max="9" step="0.1" value={farm.ph} update={update} />
            <RangeInput label="Nitrogen" field="nitrogen" min="0" max="100" value={farm.nitrogen} update={update} />
            <RangeInput label="Phosphorus" field="phosphorus" min="0" max="100" value={farm.phosphorus} update={update} />
            <RangeInput label="Potassium" field="potassium" min="0" max="100" value={farm.potassium} update={update} />
            <RangeInput label="Temperature (C)" field="temperature" min="5" max="45" value={farm.temperature} update={update} />
            <RangeInput label="Humidity (%)" field="humidity" min="10" max="100" value={farm.humidity} update={update} />
            <RangeInput label="Rainfall (mm)" field="rainfall" min="0" max="300" value={farm.rainfall} update={update} />
            <RangeInput label="Budget (INR)" field="budget" min="5000" max="150000" step="1000" value={farm.budget} update={update} />
            <SelectField label="Priority" value={farm.marketPriority} values={['', 'Balanced', 'Profit', 'Sustainability', 'Water saving']} onChange={(value) => update('marketPriority', value)} />
          </div>
        </Panel>
        <Panel title="Best crop matches" eyebrow="Step 02 / Compare" icon={BarChart3}>
          <div className="crop-list">{recommendations.slice(0, 4).map((crop) => <CropCard crop={crop} key={crop.name} />)}</div>
          {geminiExplanation && <div className="gemini-insight"><div><Bot size={18} /><strong>Gemini explanation</strong></div><p>{geminiExplanation.summary}</p><span><b>Next:</b> {geminiExplanation.priority_action}</span><span><b>Watch:</b> {geminiExplanation.risk_note}</span></div>}
          <div className="planner-actions"><button className="secondary-action" onClick={syncBackend} disabled={analysisLoading || !profileComplete}><Bot size={18} /> {analysisLoading ? 'Analysing farm…' : 'Run complete analysis'}</button><button className="primary-action" onClick={savePlan} disabled={!topCrop}><Save size={18} /> Save this plan</button></div>
        </Panel>
      </section>
    );

    if (route === '/insights') return (
      <section className="module-grid page-section">
        <Panel title={`${topCrop.name} advisory`} eyebrow="Decision support" icon={Leaf}>
          <div className="advice-list"><p>{topCrop.advisory}</p><p>{topCrop.rotation}</p><p>{topCrop.sustainability}</p></div>
        </Panel>
        <Panel title="Yield and profit" eyebrow="Economics" icon={LineChart}>
          <div className="kpi-row"><Metric icon={Wheat} label="Estimated yield" value={`${topCrop.expectedYield} quintal`} /><Metric icon={IndianRupee} label="Expected return" value={`INR ${topCrop.expectedProfit.toLocaleString('en-IN')}`} /></div>
          {topCrop.estimatedCost && <div className="insight-facts"><span><b>Cost</b> INR {topCrop.estimatedCost.toLocaleString('en-IN')}</span><span><b>Revenue</b> INR {topCrop.estimatedRevenue.toLocaleString('en-IN')}</span><span><b>Margin</b> {topCrop.profitMargin}%</span></div>}
          <p className="panel-copy">Planning estimates use crop profile, land size, suitability, budget readiness, and a labelled market baseline.</p>
        </Panel>
        <Panel title="Weather readiness" eyebrow={weather.source} icon={CloudSun}>
          <div className="kpi-row"><Metric icon={CloudSun} label="Temperature" value={`${weather.temperature} C`} /><Metric icon={Droplets} label="Humidity" value={`${weather.humidity}%`} /></div>
          <p className="alert-line">{weather.alert}</p>
        </Panel>
        <Panel title="Soil health" eyebrow={soilAnalysis?.source || 'Run analysis to assess'} icon={Database}>
          {soilAnalysis ? <><div className="kpi-row"><Metric icon={Leaf} label="Health score" value={`${soilAnalysis.health_score}/100`} /><Metric icon={Activity} label="Condition" value={soilAnalysis.classification} /></div><div className="advice-list">{soilAnalysis.actions.map((action) => <p key={action}>{action}</p>)}</div></> : <p className="panel-copy">Run complete analysis in the crop planner to generate soil actions from pH and NPK values.</p>}
        </Panel>
        <Panel title="Market outlook" eyebrow={marketAnalysis?.source || 'Run analysis to compare'} icon={IndianRupee}>
          {marketAnalysis ? <><div className="kpi-row"><Metric icon={IndianRupee} label="Planning price" value={`INR ${marketAnalysis.modal_price_per_quintal}/q`} /><Metric icon={LineChart} label="Direction" value={`${marketAnalysis.trend} ${marketAnalysis.trend_percent > 0 ? '+' : ''}${marketAnalysis.trend_percent}%`} /></div><p className="panel-copy">{marketAnalysis.note}</p></> : <p className="panel-copy">Market context will appear after the complete analysis.</p>}
        </Panel>
        <Panel title="Sustainability" eyebrow="Rotation and resource use" icon={Sprout}>
          <div className="kpi-row"><Metric icon={Leaf} label="Plan score" value={topCrop.sustainabilityScore ? `${topCrop.sustainabilityScore}/100` : 'Pending'} /><Metric icon={Droplets} label="Water demand" value={topCrop.water} /></div><p className="panel-copy">{topCrop.rotation}</p><p className="panel-copy">{topCrop.sustainability}</p>
        </Panel>
      </section>
    );

    if (route === '/finance') return (
      <section className="finance-grid page-section">
        <Panel title="Season profit planner" eyebrow="Plan, track, compare" icon={Wallet}>
          <p className="panel-copy">Turn the {topCrop.name} recommendation into a practical season budget. These are planning estimates, not a loan, credit, or investment recommendation.</p>
          <label className="market-price-input"><span>Verified local mandi price (optional, INR/quintal)</span><input type="number" min="1" max="1000000" value={manualMarketPrice} onChange={(event) => setManualMarketPrice(event.target.value)} placeholder={`Baseline: INR ${topCrop.marketPrice}/q`} /><small>Use only a price you have checked for the correct crop, unit, mandi, and date.</small></label>
          <div className="planner-actions"><button className="primary-action" onClick={runFinancialPlan} disabled={financeLoading}><Wallet size={18} /> {financeLoading ? 'Calculating…' : financialPlan ? 'Recalculate plan' : 'Create season plan'}</button><button className="secondary-action" onClick={() => navigate('/planner')}><Sprout size={18} /> Update crop inputs</button></div>
        </Panel>
        <Panel title="Finance guardrail" eyebrow="Farmer-first planning" icon={ShieldCheck}>
          <StatusLine text="No bank account, loan, credit-score, or payment data is requested" />
          <StatusLine text="Replace planning costs with actual farm expenses" />
          <StatusLine text="Verify selling prices with your selected mandi before acting" />
        </Panel>
        {financialPlan && <>
          <Panel title={`${financialPlan.crop} financial summary`} eyebrow={financialPlan.planning_source} icon={IndianRupee}>
            <div className="kpi-row"><Metric icon={Wallet} label="Working capital" value={`INR ${financialPlan.summary.actual_cost.toLocaleString('en-IN')}`} /><Metric icon={IndianRupee} label="Expected profit" value={`INR ${financialPlan.summary.expected_profit.toLocaleString('en-IN')}`} /></div>
            <div className="insight-facts"><span><b>Revenue</b> INR {financialPlan.summary.expected_revenue.toLocaleString('en-IN')}</span><span><b>Break-even</b> INR {financialPlan.summary.break_even_price_per_quintal}/q</span><span><b>Margin</b> {financialPlan.summary.profit_margin}%</span></div>
            <p className={financialPlan.summary.working_capital_gap ? 'alert-line' : 'panel-copy'}>{financialPlan.summary.working_capital_gap ? `Planned cost exceeds the selected budget by INR ${financialPlan.summary.working_capital_gap.toLocaleString('en-IN')}.` : `Budget remaining after planned cost: INR ${financialPlan.summary.budget_remaining.toLocaleString('en-IN')}.`}</p>
          </Panel>
          <Panel title="Season outlook" eyebrow="Revenue, cost and estimated profit" icon={BarChart3}>
            <FinanceBarChart
              description="Expected revenue compared with the current working-capital cost and estimated profit."
              items={[
                { label: 'Revenue', value: financialPlan.summary.expected_revenue, tone: 'revenue' },
                { label: 'Cost', value: financialPlan.summary.actual_cost, tone: 'cost' },
                { label: 'Profit', value: financialPlan.summary.expected_profit, tone: 'profit' }
              ]}
            />
          </Panel>
          <Panel title="Risk comparison" eyebrow="Profit under changing conditions" icon={Activity}>
            <FinanceBarChart
              description="Compare estimated profit before committing money to the season."
              items={financialPlan.scenarios.map((scenario) => ({ label: scenario.name, value: scenario.profit, tone: scenario.name === 'Combined risk' ? 'risk' : 'profit' }))}
            />
          </Panel>
          <Panel title="Cost tracker" eyebrow="Planned vs actual" icon={LineChart}>
            <div className="expense-list">{financialPlan.expenses.map((expense) => <label className="expense-row" key={expense.category}><span><b>{expense.category}</b><small>Plan: INR {expense.planned.toLocaleString('en-IN')}</small></span><input type="number" min="0" value={actualExpenses[expense.category] ?? expense.actual} onChange={(event) => setActualExpenses((current) => ({ ...current, [expense.category]: event.target.value }))} /><em className={expense.variance > 0 ? 'over' : ''}>{expense.variance > 0 ? '+' : ''}{expense.variance.toLocaleString('en-IN')}</em></label>)}</div>
            <div className="finance-actions"><button className="secondary-action" onClick={runFinancialPlan} disabled={financeLoading}>Refresh actual-cost plan</button><button className="secondary-action" onClick={exportReport}><Download size={17} /> Download PDF report</button></div>
          </Panel>
          <Panel title="Risk scenarios" eyebrow="Do not plan only for the best case" icon={Activity}>
            <div className="scenario-list">{financialPlan.scenarios.map((scenario) => <div className={scenario.name === 'Combined risk' ? 'scenario-row risk' : 'scenario-row'} key={scenario.name}><strong>{scenario.name}</strong><span>Revenue INR {scenario.revenue.toLocaleString('en-IN')}</span><b>Profit INR {scenario.profit.toLocaleString('en-IN')}</b></div>)}</div>
          </Panel>
          <Panel title="Cash-flow timeline" eyebrow="When money moves" icon={CalendarDays} className="finance-chart-panel">
            <FinanceBarChart
              description="Bars below the line are planned spending; bars above it are expected inflows."
              items={financialPlan.cash_flow.map((stage) => ({ label: stage.stage, value: stage.cash_in - stage.cash_out, tone: stage.cash_in ? 'revenue' : 'cost' }))}
            />
            <div className="cashflow-list">{financialPlan.cash_flow.map((stage) => <div className="cashflow-row" key={stage.stage}><strong>{stage.stage}</strong><span>{stage.cash_out ? `Spend INR ${stage.cash_out.toLocaleString('en-IN')}` : `Expected inflow INR ${stage.cash_in.toLocaleString('en-IN')}`}</span></div>)}</div>
          </Panel>
        </>}
      </section>
    );

    if (route === '/disease') return (
      <section className="feature-layout page-section">
        <Panel title="Upload crop image" eyebrow="Gemini multimodal screening" icon={Camera}>
          <label className="upload-box large-upload"><Upload size={28} /><span>{imageName || 'Choose a clear leaf image for diagnosis'}</span><input type="file" accept="image/*" onChange={handleImage} /></label>
          <div className="diagnosis"><strong>{imageName ? 'Analysis result' : 'Before you upload'}</strong><p>{imageName ? diseaseAdvisory : 'Use a well-lit image with one affected leaf in focus. This result is advisory and should be verified locally.'}</p></div>
        </Panel>
        <Panel title="Current crop context" eyebrow="Used in analysis" icon={Leaf}>
          <Metric icon={Wheat} label="Crop" value={topCrop.name} />
          <StatusLine text={`${farm.location} / ${farm.season}`} />
          <StatusLine text={`${farm.humidity}% humidity / ${farm.rainfall} mm rainfall`} />
          <StatusLine text="Farmer confirmation recommended before treatment" />
        </Panel>
      </section>
    );

    if (route === '/advisor') return (
      <section className="advisor-layout page-section">
        <Panel title="Conversation" eyebrow={`Gemini advisor / ${farm.language}`} icon={MessageSquareText}>
          <div className="chat-window expanded-chat">{chat.map((item, index) => <div className={item.by === 'Annapurna AI' ? 'chat-bubble ai' : 'chat-bubble'} key={`${item.by}-${index}`}><strong>{item.by}</strong><span>{item.text}</span></div>)}</div>
          <div className="chat-input"><input value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); askBot(); } }} placeholder="Ask about irrigation, fertilizer, disease, or market planning" disabled={advisorLoading} /><button onClick={askBot} disabled={!question.trim() || advisorLoading}>{advisorLoading ? 'Thinking…' : <><Bot size={18} /> Ask advisor</>}</button></div>
        </Panel>
        <Panel title="Advisor context" eyebrow="Live farm profile" icon={Database}>
          <StatusLine text={`Top crop: ${topCrop.name} (${topCrop.suitability}%)`} />
          <StatusLine text={`Soil: ${farm.soilType}, pH ${farm.ph}`} />
          <StatusLine text={`Season: ${farm.season}`} />
          <StatusLine text={`Priority: ${farm.marketPriority}`} />
          <StatusLine text={financialPlan ? `Finance context linked: ${financialPlan.crop} plan` : 'Finance context: create a season plan to link it'} />
        </Panel>
      </section>
    );

    if (route === '/records') return (
      <section className="page-section records-page">
        <Panel title="Recommendation history" eyebrow="Saved plans" icon={History}>
          {history.length === 0 ? <div className="empty-records"><History size={30} /><h3>No saved plans yet</h3><p>Complete the crop planner and save a recommendation to build your farm record.</p><button className="primary-action" onClick={() => navigate('/planner')}>Open crop planner</button></div> : <><div className="history-list records-list">{history.map((item) => <div className="history-item" key={item.id}><div><strong>{item.crop}</strong><span>{item.location} · {item.date}</span></div><p>{item.score}% match</p></div>)}</div><button className="secondary-action clear-local-data" onClick={clearSavedPlans}>Clear saved plans from this device</button></>}
        </Panel>
      </section>
    );

    if (route === '/settings') return (
      <section className="module-grid page-section">
        <Panel title="Data sources" eyebrow="Integration status" icon={Database}>
          <StatusLine text={apiStatus} /><StatusLine text={`Gemini AI: ${integrationStatus?.gemini || 'checking'} (${integrationStatus?.gemini_model || 'model pending'})`} /><StatusLine text={`SoilGrids: ${integrationStatus?.soilgrids || 'checking'}`} /><StatusLine text={`ISRO Bhuvan: ${integrationStatus?.isro_bhuvan || 'checking'}`} /><StatusLine text={`OpenWeatherMap: ${integrationStatus?.openweather || 'checking'}`} /><StatusLine text={`Market feeds: ${integrationStatus ? `${integrationStatus.agmarknet}/${integrationStatus.enam}` : 'checking'}`} />
        </Panel>
        <Panel title="Operations" eyebrow="This device" icon={Settings}>
          <div className="admin-actions"><button className="secondary-action" onClick={syncBackend}><Database size={18} /> Sync recommendations</button><button className="secondary-action" onClick={loadIntegrationStatus}><Activity size={18} /> Refresh integrations</button><button className="secondary-action" onClick={exportReport}><Download size={18} /> Export current report</button><button className="secondary-action clear-local-data" onClick={clearFinanceTracker}>Clear finance tracker from this device</button></div>
        </Panel>
        <Panel title="Safety & ethics" eyebrow="Advisory safeguards" icon={ShieldCheck}>
          <StatusLine text="Farmer consent for profile and image data" /><StatusLine text="Recommendations are advisory, not guaranteed outcomes" /><StatusLine text="API keys remain in the backend environment" /><StatusLine text="Local verification recommended before treatment" />
        </Panel>
      </section>
    );

    return (
      <>
        <section className="dashboard-hero">
          <div className="dashboard-copy"><p className="eyebrow">{farm.season} season workspace</p><h2>Good decisions begin with a clear field picture.</h2><p className="subhead">Your strongest match is <strong>{topCrop.name}</strong>. Review the current signals or update the planner as conditions change.</p><div className="action-row"><button className="primary-action" onClick={() => navigate('/planner')}><Sprout size={18} /> Plan a crop</button><button className="secondary-action" onClick={() => navigate('/advisor')}><Bot size={18} /> Ask advisor</button></div></div>
          <FieldMap crop={topCrop} moisture={farm.humidity} />
        </section>
        <section className="status-grid dashboard-metrics"><Metric icon={BarChart3} label="Top recommendation" value={`${topCrop.name} · ${topCrop.suitability}%`} /><Metric icon={MapPin} label="Farm location" value={farm.location} /><Metric icon={CloudSun} label="Field weather" value={`${weather.temperature} C · ${weather.humidity}%`} /><Metric icon={IndianRupee} label="Expected return" value={`INR ${topCrop.expectedProfit.toLocaleString('en-IN')}`} /></section>
        <section className="quick-grid">
          <QuickAction icon={Sprout} title="Update crop plan" text="Compare crops using soil, weather, budget, and season." onClick={() => navigate('/planner')} />
          <QuickAction icon={Leaf} title="Review advisory" text={`${topCrop.name} guidance, yield, profit, and sustainability.`} onClick={() => navigate('/insights')} />
          <QuickAction icon={Camera} title="Check crop health" text="Upload a leaf image for an initial disease advisory." onClick={() => navigate('/disease')} />
        </section>
      </>
    );
  }

  return (
    <main className="app-shell saas-shell">
      <aside className="sidebar saas-sidebar">
        <button className="brand brand-button" onClick={() => navigate('/dashboard')}>
          <div className="brand-mark"><Wheat size={22} /></div>
          <div><p className="brand-kicker">ANNAPURNA AI</p><h1>Farm intelligence</h1></div>
        </button>
        <nav className="nav-list" aria-label="Application navigation">
          {navItems.map(([path, label, Icon]) => <button className={`nav-item ${route === path ? 'active' : ''}`} onClick={() => navigate(path)} key={path}><Icon size={18} /><span>{label}</span></button>)}
        </nav>
        <div className="sidebar-profile"><div className="avatar">{farm.farmerName.charAt(0)}</div><div><strong>{farm.farmerName}</strong><span>{farm.location}</span></div></div>
      </aside>
      <section className="workspace saas-workspace">
        <header className="app-topbar"><div><p className="eyebrow">Annapurna workspace</p><h2>{currentMeta[0]}</h2><p>{currentMeta[1]}</p></div><div className="topbar-actions"><span className="live-pill"><i /> Advisory online</span><button className="secondary-action" onClick={exportReport} disabled={!topCrop}><Download size={17} /> Report</button></div></header>
        <div className="page-content">{renderPage()}</div>
      </section>
    </main>
  );
}

function MarketingSite({ page, navigate }) {
  return (
    <main className="marketing-site">
      <PublicHeader page={page} navigate={navigate} />
      {page === 'about' ? <AboutPage navigate={navigate} /> : <LandingPage navigate={navigate} />}
      <PublicFooter navigate={navigate} />
    </main>
  );
}

function PublicHeader({ page, navigate }) {
  return (
    <header className="public-header">
      <button className="public-brand" onClick={() => navigate('/')}>
        <span className="public-brand-mark"><Wheat size={22} /></span>
        <span><strong>Annapurna AI</strong><small>Farm intelligence</small></span>
      </button>
      <nav aria-label="Public navigation">
        <button className={page === 'home' ? 'active' : ''} onClick={() => navigate('/')}>Home</button>
        <button className={page === 'about' ? 'active' : ''} onClick={() => navigate('/about')}>About</button>
        <button className="public-cta" onClick={() => navigate('/dashboard')}>Open workspace <span>→</span></button>
      </nav>
    </header>
  );
}

function LandingPage({ navigate }) {
  return (
    <>
      <section className="landing-hero">
        <div className="landing-copy">
          <p className="marketing-kicker"><span /> Practical AI for Indian agriculture</p>
          <h1>Plan every season with a clearer view of your farm.</h1>
          <p>Annapurna AI combines deterministic crop ranking with Gemini-powered explanations, multimodal disease screening, and multilingual guidance—so every recommendation is easier to understand and act on.</p>
          <div className="landing-actions">
            <button className="marketing-primary" onClick={() => navigate('/dashboard')}>Start your farm plan <span>→</span></button>
            <button className="marketing-secondary" onClick={() => navigate('/about')}>See how it works</button>
          </div>
          <div className="landing-trust">
            <span><CheckCircle2 size={16} /> Explainable recommendations</span>
            <span><CheckCircle2 size={16} /> Profile-led analysis</span>
            <span><CheckCircle2 size={16} /> Farmer-first safeguards</span>
          </div>
        </div>
        <div className="product-preview" aria-label="Annapurna profile-led analysis preview">
          <div className="preview-top"><span><i /> Profile-led workspace</span><small>Data required</small></div>
          <div className="preview-body">
            <div className="preview-heading"><div><small>Farm profile</small><h3>Awaiting your data</h3></div><strong>—</strong></div>
            <div className="preview-progress"><span style={{ width: '22%' }} /></div>
            <div className="preview-metrics"><div><small>Market price</small><strong>Live source</strong></div><div><small>Weather</small><strong>Live source</strong></div><div><small>Finance</small><strong>Your records</strong></div></div>
            <div className="preview-advice"><Leaf size={18} /><div><strong>How it works</strong><p>Enter your field details, then generate a profile-specific analysis from backend services.</p></div></div>
            <div className="preview-chart" aria-hidden="true">{[24, 38, 32, 46, 41, 58, 52, 66].map((height, index) => <span style={{ height: `${height}%` }} key={index} />)}</div>
          </div>
        </div>
      </section>

      <section className="source-strip"><span>Designed to connect with</span><strong>SoilGrids</strong><strong>ISRO Bhuvan</strong><strong>OpenWeather</strong><strong>Agmarknet</strong><strong>eNAM</strong></section>

      <section className="marketing-section" id="features">
        <div className="section-intro"><p className="marketing-kicker">One connected workspace</p><h2>From field conditions to a practical crop plan.</h2><p>Each tool uses the same farmer profile, so recommendations and advisory stay relevant instead of becoming isolated reports.</p></div>
        <div className="feature-cards">
          <MarketingCard icon={Sprout} label="Plan" title="Crop recommendations" text="Compare crops using season, soil, nutrients, rainfall, temperature, water, budget, and market priority." />
          <MarketingCard icon={BarChart3} label="Understand" title="Field and profit insights" text="See suitability, expected yield, estimated return, cautions, rotation advice, and sustainability guidance." />
          <MarketingCard icon={Camera} label="Protect" title="Gemini disease support" text="Use Gemini's multimodal understanding to screen a clear leaf image and receive a cautious crop-aware advisory." />
          <MarketingCard icon={Bot} label="Ask" title="Gemini farm advisor" text="Ask irrigation, fertilizer, disease, and planning questions using the current farm and crop context." />
        </div>
      </section>

      <section className="how-section">
        <div className="section-intro"><p className="marketing-kicker">A simple workflow</p><h2>Three steps from uncertainty to direction.</h2></div>
        <div className="step-list">
          <div><span>01</span><h3>Describe your farm</h3><p>Add the conditions you know. The application works with manual inputs and can connect to external data sources.</p></div>
          <div><span>02</span><h3>Compare the evidence</h3><p>Review ranked crop matches with clear reasons, risks, water needs, yield, and return estimates.</p></div>
          <div><span>03</span><h3>Save and act carefully</h3><p>Keep the plan in your records, export a report, and verify important decisions with local expertise.</p></div>
        </div>
      </section>

      <section className="responsible-section">
        <div className="responsible-mark"><ShieldCheck size={32} /></div>
        <div><p className="marketing-kicker">Responsible by design</p><h2>Advice should support farmers—not hide uncertainty.</h2><p>Annapurna presents recommendations as decision support, explains the factors behind them, and encourages local verification before treatment or investment.</p></div>
        <button className="marketing-secondary" onClick={() => navigate('/about')}>Read about the project</button>
      </section>

      <MarketingCTA navigate={navigate} />
    </>
  );
}

function AboutPage({ navigate }) {
  return (
    <>
      <section className="about-hero">
        <p className="marketing-kicker">About Annapurna AI</p>
        <h1>Building clearer agricultural decisions with practical, explainable technology.</h1>
        <p>Annapurna AI is a crop recommendation and agricultural advisory project designed around the real questions farmers face before and during a growing season.</p>
      </section>

      <section className="about-story marketing-section">
        <div className="about-story-copy"><p className="marketing-kicker">Why this project exists</p><h2>Farm information is available. Turning it into one clear decision is the harder problem.</h2></div>
        <div className="about-prose"><p>Soil readings, weather, crop requirements, market priorities, disease symptoms, and farm budgets often live in separate systems. That fragmentation makes planning slower and recommendations harder to trust.</p><p>Annapurna brings these signals into one understandable workflow. It ranks suitable crops, explains why they fit, identifies cautions, estimates yield and return, and carries the same context into disease support and the AI advisor.</p></div>
      </section>

      <section className="project-pillars">
        <MarketingCard icon={Search} label="Transparent" title="Explain the recommendation" text="Every crop match includes reasons and cautions instead of presenting a score without context." />
        <MarketingCard icon={Database} label="Connected" title="Use the right signals" text="The architecture supports soil, weather, market, farm-profile, image, and historical data." />
        <MarketingCard icon={ShieldCheck} label="Responsible" title="Respect farmer judgment" text="Outputs are advisory, consent-aware, and designed to be checked against local knowledge." />
      </section>

      <section className="architecture-section">
        <div className="section-intro"><p className="marketing-kicker">How it is built</p><h2>A working full-stack agricultural prototype.</h2><p>The repository includes the user-facing application, API services, local persistence, recommendation logic, and a path toward trained machine-learning and live integrations.</p></div>
        <div className="architecture-grid">
          <div><span>Interface</span><h3>React + Vite</h3><p>Responsive multipage workflow for registration, planning, insights, disease analysis, advisory, and saved records.</p></div>
          <div><span>Application API</span><h3>FastAPI</h3><p>Routes for recommendations, finance planning, weather, market data, chat, disease analysis, and reports.</p></div>
          <div><span>Recommendation</span><h3>Rules + scikit-learn</h3><p>A transparent local scoring fallback plus a trainable model pipeline using regional crop data.</p></div>
          <div><span>Storage</span><h3>Browser storage</h3><p>Saved plans and finance expense tracking remain on the current device without an account.</p></div>
        </div>
      </section>

      <section className="project-scope">
        <div><p className="marketing-kicker">Current scope</p><h2>A strong prototype, not a promise of guaranteed outcomes.</h2></div>
        <ul><li><CheckCircle2 size={18} /> Functional browser-only fallbacks when backend services are unavailable</li><li><CheckCircle2 size={18} /> Prepared adapters for soil, weather, market, chatbot, and disease services</li><li><CheckCircle2 size={18} /> Clear production roadmap for validated datasets, trained models, and official feeds</li></ul>
      </section>

      <MarketingCTA navigate={navigate} />
    </>
  );
}

function MarketingCard({ icon: Icon, label, title, text }) {
  return <article className="marketing-card"><span className="marketing-icon"><Icon size={22} /></span><small>{label}</small><h3>{title}</h3><p>{text}</p></article>;
}

function MarketingCTA({ navigate }) {
  return <section className="marketing-cta"><div><p className="marketing-kicker">Ready to explore?</p><h2>Build your first farm plan in minutes.</h2><p>Add the conditions you know and review a complete recommendation. Your saved plans stay on this device.</p></div><button className="marketing-primary light" onClick={() => navigate('/dashboard')}>Open workspace <span>→</span></button></section>;
}

function PublicFooter({ navigate }) {
  return <footer className="public-footer"><button className="public-brand" onClick={() => navigate('/')}><span className="public-brand-mark"><Wheat size={20} /></span><span><strong>Annapurna AI</strong><small>Farm intelligence</small></span></button><p>Decision support for sustainable and informed agriculture.</p><div><button onClick={() => navigate('/')}>Home</button><button onClick={() => navigate('/about')}>About</button><button onClick={() => navigate('/dashboard')}>Open workspace</button></div></footer>;
}

function GuestEntry({ navigate }) {
  return <main className="auth-shell"><section className="auth-story"><div className="auth-brand"><span className="brand-mark"><Wheat size={23} /></span><span><small>ANNAPURNA AI</small><strong>Farm intelligence</strong></span></div><div className="auth-story-copy"><p className="eyebrow">No account required</p><h1>Your farm-planning workspace is ready.</h1><p>Use the tool directly. Saved plans and expense tracking remain in this browser on this device.</p></div><div className="auth-trust"><ShieldCheck size={19} /><span>Recommendations remain advisory and transparent.</span></div></section><section className="auth-form-side"><div className="auth-card"><p className="eyebrow">Guest workspace</p><h2>Start with your farm conditions.</h2><p className="auth-intro">Add your field details, compare crop plans, and use the season finance tracker without registration.</p><button className="primary-action auth-submit" onClick={() => navigate('/dashboard')}><Sprout size={18} /> Open farm workspace</button></div></section></main>;
}

function QuickAction({ icon: Icon, title, text, onClick }) {
  return (
    <button className="quick-action" onClick={onClick}>
      <span className="quick-icon"><Icon size={21} /></span>
      <span><strong>{title}</strong><small>{text}</small></span>
      <span className="quick-arrow">→</span>
    </button>
  );
}

function FieldMap({ crop, moisture }) {
  const [focus, setFocus] = useState({ x: 68, y: 34 });
  const rows = Array.from({ length: 7 }, (_, index) => index);

  function inspectField(event) {
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = Math.max(7, Math.min(93, ((event.clientX - bounds.left) / bounds.width) * 100));
    const y = Math.max(9, Math.min(91, ((event.clientY - bounds.top) / bounds.height) * 100));
    setFocus({ x, y });
  }

  return (
    <figure
      className="field-terminal"
      onPointerMove={inspectField}
      onPointerLeave={() => setFocus({ x: 68, y: 34 })}
      aria-label={`Interactive field map showing ${crop.name} at ${crop.suitability} percent suitability`}
    >
      <div className="field-readout">
        <span>FIELD INTELLIGENCE</span>
        <strong>{crop.name.toUpperCase()} / {crop.suitability}%</strong>
      </div>
      <div className="scene-window">
        <div className="field-map-surface">
          <div className="contour contour-one" />
          <div className="contour contour-two" />
          <div className="field-rows" aria-hidden="true">
            {rows.map((row) => <span style={{ '--row': row }} key={row} />)}
          </div>
          <div className="water-channel" aria-hidden="true" />
          <div
            className="suitability-dial"
            style={{ '--score': `${crop.suitability * 3.6}deg` }}
          >
            <div>
              <strong>{crop.suitability}%</strong>
              <span>SUITABLE</span>
            </div>
          </div>
          <div className="heritage-compass" aria-hidden="true"><span /></div>
          <span
            className="scan-cursor"
            style={{ left: `${focus.x}%`, top: `${focus.y}%` }}
            aria-hidden="true"
          />
        </div>
      </div>
      <figcaption>
        <span><i className="legend-dot soil" /> {crop.water} water</span>
        <span><i className="legend-dot signal" /> {moisture}% humidity</span>
        <span>MOVE TO EXPLORE</span>
      </figcaption>
    </figure>
  );
}

function formatCompactRupees(value) {
  const absolute = Math.abs(value);
  if (absolute >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
  if (absolute >= 1000) return `₹${Math.round(value / 1000)}k`;
  return `₹${Math.round(value)}`;
}

function FinanceBarChart({ items, description }) {
  const chartItems = items.filter((item) => Number.isFinite(Number(item.value)));
  const values = chartItems.map((item) => Number(item.value));
  const maxValue = Math.max(0, ...values);
  const minValue = Math.min(0, ...values);
  const range = maxValue - minValue || 1;
  const top = 24;
  const plotHeight = 140;
  const baseline = top + ((maxValue / range) * plotHeight);
  const barWidth = Math.min(56, Math.max(24, 250 / Math.max(chartItems.length, 1)));
  const step = 330 / Math.max(chartItems.length, 1);
  const yFor = (value) => top + ((maxValue - value) / range) * plotHeight;

  return <figure className="finance-chart">
    <svg viewBox="0 0 390 222" role="img" aria-label={description}>
      <title>{description}</title>
      {[top, top + plotHeight / 2, top + plotHeight].map((y) => <line className="finance-chart-gridline" x1="32" x2="370" y1={y} y2={y} key={y} />)}
      <line className="finance-chart-baseline" x1="32" x2="370" y1={baseline} y2={baseline} />
      {chartItems.map((item, index) => {
        const value = Number(item.value);
        const y = yFor(value);
        const height = Math.max(2, Math.abs(y - baseline));
        const x = 42 + index * step + (step - barWidth) / 2;
        const labelY = value >= 0 ? y - 7 : y + height + 15;
        return <g key={item.label}>
          <rect className={`finance-chart-bar ${item.tone || 'profit'}`} x={x} y={Math.min(y, baseline)} width={barWidth} height={height} />
          <text className="finance-chart-value" x={x + barWidth / 2} y={labelY}>{formatCompactRupees(value)}</text>
          <text className="finance-chart-label" x={x + barWidth / 2} y="192">{item.label}</text>
        </g>;
      })}
      <text className="finance-chart-zero" x="34" y={baseline - 5}>₹0</text>
    </svg>
    <figcaption>{description}</figcaption>
  </figure>;
}

function Panel({ title, eyebrow, icon: Icon, id, className = '', children }) {
  return (
    <section className={`panel ${className}`.trim()} id={id}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h3>{title}</h3>
        </div>
        <Icon size={20} />
      </div>
      {children}
    </section>
  );
}

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="metric">
      <Icon size={18} />
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function Field({ label, value, onChange }) {
  return (
    <label>
      {label}
      <input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function SelectField({ label, value, values, onChange }) {
  return (
    <label>
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {values.map((item) => (
          <option key={item || 'empty'} value={item}>{item || `Select ${label}`}</option>
        ))}
      </select>
    </label>
  );
}

function RangeInput({ label, field, min, max, step = '1', value, update }) {
  return (
    <label>
      <span className="range-label">
        {label}
        <strong>{value}</strong>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => update(field, event.target.value)}
      />
    </label>
  );
}

function CropCard({ crop }) {
  return (
    <article className="crop-card">
      <div className="crop-head">
        <div className="crop-icon">
          <crop.icon size={22} />
        </div>
        <div>
          <h4>{crop.name}</h4>
          <p>{crop.suitability}% suitability</p>
        </div>
      </div>
      <div className="score-track">
        <span style={{ width: `${crop.suitability}%` }} />
      </div>
      <div className="crop-details">
        <div>
          <strong>Why</strong>
          <ul>
            {crop.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
        <div>
          <strong>Watch</strong>
          <ul>
            {(crop.cautions.length ? crop.cautions : ['No major warning from current inputs']).map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      </div>
      <div className="crop-footer">
        <span>{crop.water} water need</span>
        <strong>INR {crop.expectedProfit.toLocaleString('en-IN')}</strong>
      </div>
    </article>
  );
}

function StatusLine({ text }) {
  return (
    <div className="status-line">
      <CheckCircle2 size={18} />
      <span>{text}</span>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}
