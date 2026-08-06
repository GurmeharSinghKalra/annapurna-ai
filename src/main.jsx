import React, { useEffect, useMemo, useState } from 'react';
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
  History,
  IndianRupee,
  Leaf,
  LineChart,
  Lock,
  MapPin,
  MessageSquareText,
  Save,
  Search,
  Settings,
  ShieldCheck,
  Sprout,
  Upload,
  UserRound,
  Wheat
} from 'lucide-react';
import './styles.css';

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
    baseProfit: 42000,
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
    baseProfit: 36000,
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
    baseProfit: 52000,
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
    baseProfit: 38500,
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
    baseProfit: 33000,
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
    baseProfit: 34500,
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
    baseProfit: 65000,
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
    baseProfit: 28000,
    yield: 15,
    sustainability: 'Climate-resilient crop for low-rainfall regions.',
    rotation: 'Rotate with mustard, chickpea, or wheat.',
    advisory: 'Good fallback when rainfall is uncertain and soil is lighter.'
  }
];

const initialFarm = {
  farmerName: 'Demo Farmer',
  phone: '9999999999',
  location: 'Sonipat, Haryana',
  language: 'English',
  landSize: 2,
  season: 'Kharif',
  soilType: 'Alluvial',
  ph: 6.6,
  nitrogen: 62,
  phosphorus: 41,
  potassium: 48,
  temperature: 29,
  humidity: 64,
  rainfall: 115,
  budget: 35000,
  marketPriority: 'Balanced'
};

const diseaseResults = {
  Rice: 'Possible early leaf blast risk. Keep canopy airflow high and avoid excess nitrogen.',
  Maize: 'Possible leaf spot risk. Remove infected residue and monitor lower leaves.',
  Cotton: 'Possible sucking pest stress. Inspect underside of leaves and use IPM before pesticide.',
  Wheat: 'Possible rust risk. Monitor yellow/orange streaks and avoid late irrigation on foliage.',
  Mustard: 'Possible aphid pressure. Check tender shoots during flowering.',
  Chickpea: 'Possible wilt risk. Improve drainage and rotate away from chickpea next season.',
  Sugarcane: 'Possible red rot risk. Use healthy seed cane and remove affected clumps.',
  'Pearl Millet': 'Possible downy mildew risk. Use resistant seed and avoid dense sowing.'
};

const cropIcons = {
  Rice: Wheat,
  Maize: Sprout,
  Cotton: Sprout,
  Wheat,
  Mustard: Leaf,
  Chickpea: Leaf,
  Sugarcane: Sprout,
  'Pearl Millet': Wheat
};

function toApiFarm(farm) {
  return {
    farmer_name: farm.farmerName,
    phone: farm.phone,
    location: farm.location,
    language: farm.language,
    land_size: Number(farm.landSize),
    season: farm.season,
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
    icon: item.icon || cropIcons[item.crop] || Sprout,
    water: item.water,
    expectedProfit: item.expectedProfit ?? item.expected_profit,
    expectedYield: item.expectedYield ?? item.expected_yield
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

  if (farm.marketPriority === 'Profit' && crop.baseProfit > 40000) score += 6;
  if (farm.marketPriority === 'Sustainability' && crop.water === 'Low') score += 7;
  if (farm.marketPriority === 'Water saving' && ['Low', 'Medium'].includes(crop.water)) score += 7;

  const suitability = Math.max(36, Math.min(98, Math.round(score)));
  const landSize = Number(farm.landSize || 1);
  const budgetFactor = Number(farm.budget) >= crop.baseProfit * 0.55 ? 1 : 0.86;
  const expectedProfit = Math.round(crop.baseProfit * landSize * budgetFactor);
  const expectedYield = Math.round(crop.yield * landSize);

  return {
    ...crop,
    suitability,
    expectedProfit,
    expectedYield,
    reasons: reasons.slice(0, 4),
    cautions: cautions.slice(0, 3)
  };
}

function App() {
  const [farm, setFarm] = useState(initialFarm);
  const [authUser, setAuthUser] = useState(null);
  const [authPassword, setAuthPassword] = useState('secret123');
  const [history, setHistory] = useState([]);
  const [question, setQuestion] = useState('How should I irrigate the recommended crop?');
  const [chat, setChat] = useState([
    {
      by: 'Annapurna AI',
      text: 'Enter farm conditions first. I will answer using the top crop, soil, weather, and sustainability rules.'
    }
  ]);
  const [imageName, setImageName] = useState('');
  const [apiStatus, setApiStatus] = useState('Backend not checked yet');
  const [integrationStatus, setIntegrationStatus] = useState(null);
  const [apiRecommendations, setApiRecommendations] = useState(null);
  const [diseaseAdvisory, setDiseaseAdvisory] = useState('');

  const localRecommendations = useMemo(
    () => crops.map((crop) => scoreCrop(crop, farm)).sort((a, b) => b.suitability - a.suitability),
    [farm]
  );
  const recommendations = apiRecommendations || localRecommendations;
  const topCrop = recommendations[0];

  const weather = useMemo(
    () => ({
      source: 'OpenWeatherMap ready',
      temperature: farm.temperature,
      humidity: farm.humidity,
      rainfall: farm.rainfall,
      alert:
        Number(farm.rainfall) < 40
          ? 'Low rainfall alert'
          : Number(farm.rainfall) > 180
            ? 'Waterlogging risk'
            : 'Weather is workable'
    }),
    [farm]
  );

  useEffect(() => {
    loadHistory();
    loadIntegrationStatus();
  }, []);

  function update(field, value) {
    setFarm((current) => ({ ...current, [field]: value }));
    setApiRecommendations(null);
  }

  async function registerUser() {
    try {
      const response = await fetch('http://127.0.0.1:8000/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: farm.farmerName,
          phone: farm.phone,
          password: authPassword,
          language: farm.language,
          location: farm.location
        })
      });
      if (!response.ok && response.status !== 409) throw new Error(`API returned ${response.status}`);
      if (response.status === 409) {
        setApiStatus('Account already exists. Use login.');
        return;
      }
      const data = await response.json();
      setAuthUser(data.user);
      setApiStatus('Account registered');
    } catch (error) {
      setAuthUser({ name: farm.farmerName, phone: farm.phone, language: farm.language, location: farm.location });
      setApiStatus('Demo account active locally');
    }
  }

  async function loginUser() {
    try {
      const response = await fetch('http://127.0.0.1:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: farm.phone, password: authPassword })
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const data = await response.json();
      setAuthUser(data.user);
      setFarm((current) => ({
        ...current,
        farmerName: data.user.name,
        phone: data.user.phone,
        language: data.user.language,
        location: data.user.location
      }));
      setApiStatus('Logged in with backend account');
    } catch (error) {
      setApiStatus('Login failed or backend offline');
    }
  }

  async function loadHistory() {
    try {
      const response = await fetch('http://127.0.0.1:8000/history');
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const data = await response.json();
      setHistory(
        (data.history || []).map((item) => ({
          id: item.id,
          crop: item.crop,
          score: item.suitability,
          profit: item.expected_profit,
          location: item.location,
          date: item.created_at
        }))
      );
    } catch (error) {
      setApiStatus('Backend offline: using browser-only mode');
    }
  }

  async function loadIntegrationStatus() {
    try {
      const response = await fetch('http://127.0.0.1:8000/integrations/status');
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      setIntegrationStatus(await response.json());
    } catch (error) {
      setIntegrationStatus({
        soilgrids: 'adapter_ready',
        isro_bhuvan: 'adapter_ready',
        openweather: 'offline',
        agmarknet: 'offline',
        enam: 'offline',
        genai: 'offline'
      });
    }
  }

  function exportReport() {
    const lines = [
      'Annapurna AI Crop Recommendation Report',
      '',
      `Farmer: ${farm.farmerName}`,
      `Phone: ${farm.phone}`,
      `Location: ${farm.location}`,
      `Language: ${farm.language}`,
      `Season: ${farm.season}`,
      `Soil type: ${farm.soilType}`,
      `Land size: ${farm.landSize} acre`,
      `Budget: INR ${Number(farm.budget).toLocaleString('en-IN')}`,
      '',
      `Top crop: ${topCrop.name}`,
      `Suitability: ${topCrop.suitability}%`,
      `Expected yield: ${topCrop.expectedYield} quintal`,
      `Expected return: INR ${topCrop.expectedProfit.toLocaleString('en-IN')}`,
      `Water need: ${topCrop.water}`,
      '',
      'Why recommended:',
      ...topCrop.reasons.map((reason) => `- ${reason}`),
      '',
      'Warnings:',
      ...topCrop.cautions.map((warning) => `- ${warning}`),
      '',
      'Advisory:',
      topCrop.advisory,
      topCrop.rotation,
      topCrop.sustainability
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `annapurna-ai-${topCrop.name.toLowerCase().replace(/\s+/g, '-')}-report.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function savePlan() {
    const localRecord = {
      id: crypto.randomUUID(),
      crop: topCrop.name,
      score: topCrop.suitability,
      profit: topCrop.expectedProfit,
      location: farm.location,
      date: new Date().toLocaleString('en-IN')
    };

    setHistory((items) => [localRecord, ...items.slice(0, 5)]);

    try {
      const response = await fetch('http://127.0.0.1:8000/history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farmer_name: farm.farmerName,
          location: farm.location,
          crop: topCrop.name,
          suitability: topCrop.suitability,
          expected_profit: topCrop.expectedProfit
        })
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      setApiStatus('Saved to backend history');
      await loadHistory();
    } catch (error) {
      setApiStatus('Saved locally only: backend offline');
    }
  }

  async function syncBackend() {
    try {
      const response = await fetch('http://127.0.0.1:8000/recommendations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(toApiFarm(farm))
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const data = await response.json();
      const normalized = (data.recommendations || []).map(normalizeRecommendation);
      setApiRecommendations(normalized.length ? normalized : null);
      const top = normalized[0];
      setApiStatus(top ? `Backend online: ${top.name} ${top.suitability}%` : 'Backend online');
    } catch (error) {
      setApiStatus('Backend offline: run FastAPI on port 8000');
    }
  }

  async function askBot() {
    const userQuestion = question;
    setChat((items) => [...items, { by: farm.farmerName, text: userQuestion }]);
    setQuestion('');

    try {
      const response = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userQuestion,
          crop: topCrop.name,
          farm: toApiFarm(farm)
        })
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const data = await response.json();
      setChat((items) => [...items, { by: 'Annapurna AI', text: data.answer }]);
      setApiStatus('Chatbot API online');
    } catch (error) {
      const answer = `${topCrop.name} is currently the strongest match. ${topCrop.advisory} ${topCrop.rotation} Expected return is INR ${topCrop.expectedProfit.toLocaleString('en-IN')} for ${farm.landSize} acre.`;
      setChat((items) => [...items, { by: 'Annapurna AI', text: answer }]);
      setApiStatus('Chatbot fallback used');
    }
  }

  async function handleImage(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setImageName(file.name);

    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch('http://127.0.0.1:8000/disease', {
        method: 'POST',
        body: formData
      });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const data = await response.json();
      setDiseaseAdvisory(`${data.prediction}: ${data.advisory}`);
      setApiStatus('Disease API online');
    } catch (error) {
      setDiseaseAdvisory(diseaseResults[topCrop.name]);
      setApiStatus('Disease fallback used');
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Wheat size={24} />
          </div>
          <div>
            <p className="brand-kicker">Annapurna AI</p>
            <h1>Farmer decision system</h1>
          </div>
        </div>

        <nav className="nav-list" aria-label="Primary">
          <a className="nav-item active" href="#planner"><Sprout size={18} /> Planner</a>
          <a className="nav-item" href="#insights"><BarChart3 size={18} /> Insights</a>
          <a className="nav-item" href="#disease"><Camera size={18} /> Disease</a>
          <a className="nav-item" href="#chatbot"><Bot size={18} /> Chatbot</a>
          <a className="nav-item" href="#sources"><Database size={18} /> Data</a>
          <a className="nav-item" href="#admin"><Settings size={18} /> Admin</a>
        </nav>

        <div className="sidebar-note">
          <ShieldCheck size={18} />
          <span>Annapurna is used as a respectful symbol of food security, nourishment, and sustainable farming.</span>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">AI crop recommendation and agricultural advisory</p>
            <h2>Annapurna AI</h2>
            <p className="subhead">Plan crops from soil, climate, market priority, sustainability, and disease signals.</p>
          </div>
          <div className="action-row">
            <button className="secondary-action compact" onClick={syncBackend}><Database size={18} /> Sync API</button>
            <button className="secondary-action compact" onClick={exportReport}><Download size={18} /> Report</button>
            <button className="primary-action" onClick={savePlan}><Save size={18} /> Save plan</button>
          </div>
        </header>

        <section className="status-grid">
          <Metric icon={UserRound} label="Farmer" value={authUser?.name || farm.farmerName} />
          <Metric icon={MapPin} label="Location" value={farm.location} />
          <Metric icon={CalendarDays} label="Season" value={farm.season} />
          <Metric icon={IndianRupee} label="Budget" value={`INR ${Number(farm.budget).toLocaleString('en-IN')}`} />
        </section>

        <section className="account-strip">
          <div>
            <p className="eyebrow">User management</p>
            <h3>{authUser ? `Signed in as ${authUser.name}` : 'Register or login farmer account'}</h3>
          </div>
          <div className="account-controls">
            <input
              type="password"
              value={authPassword}
              onChange={(event) => setAuthPassword(event.target.value)}
              placeholder="Password"
            />
            <button className="secondary-action compact" onClick={registerUser}><UserRound size={18} /> Register</button>
            <button className="primary-action" onClick={loginUser}><Lock size={18} /> Login</button>
          </div>
        </section>

        <section className="main-grid" id="planner">
          <Panel title="Farm Profile" eyebrow="Input data" icon={Search}>
            <div className="form-grid">
              <Field label="Farmer name" value={farm.farmerName} onChange={(value) => update('farmerName', value)} />
              <Field label="Phone" value={farm.phone} onChange={(value) => update('phone', value)} />
              <Field label="Location" value={farm.location} onChange={(value) => update('location', value)} />
              <SelectField label="Language" value={farm.language} values={['English', 'Hindi', 'Punjabi', 'Haryanvi']} onChange={(value) => update('language', value)} />
              <SelectField label="Season" value={farm.season} values={['Kharif', 'Rabi', 'Zaid']} onChange={(value) => update('season', value)} />
              <SelectField label="Soil type" value={farm.soilType} values={['Alluvial', 'Black', 'Clayey', 'Loamy', 'Sandy loam']} onChange={(value) => update('soilType', value)} />
              <RangeInput label="Land size acre" field="landSize" min="0.5" max="10" step="0.5" value={farm.landSize} update={update} />
              <RangeInput label="Soil pH" field="ph" min="4" max="9" step="0.1" value={farm.ph} update={update} />
              <RangeInput label="Nitrogen" field="nitrogen" min="0" max="100" value={farm.nitrogen} update={update} />
              <RangeInput label="Phosphorus" field="phosphorus" min="0" max="100" value={farm.phosphorus} update={update} />
              <RangeInput label="Potassium" field="potassium" min="0" max="100" value={farm.potassium} update={update} />
              <RangeInput label="Temperature C" field="temperature" min="5" max="45" value={farm.temperature} update={update} />
              <RangeInput label="Humidity percent" field="humidity" min="10" max="100" value={farm.humidity} update={update} />
              <RangeInput label="Rainfall mm" field="rainfall" min="0" max="300" value={farm.rainfall} update={update} />
              <RangeInput label="Budget INR" field="budget" min="5000" max="150000" step="1000" value={farm.budget} update={update} />
              <SelectField label="Priority" value={farm.marketPriority} values={['Balanced', 'Profit', 'Sustainability', 'Water saving']} onChange={(value) => update('marketPriority', value)} />
            </div>
          </Panel>

          <Panel title="Top Crop Recommendations" eyebrow="ML output" icon={BarChart3}>
            <div className="crop-list">
              {recommendations.slice(0, 4).map((crop) => (
                <CropCard crop={crop} key={crop.name} />
              ))}
            </div>
          </Panel>
        </section>

        <section className="module-grid" id="insights">
          <Panel title={`${topCrop.name} Advisory`} eyebrow="Decision support" icon={Leaf}>
            <div className="advice-list">
              <p>{topCrop.advisory}</p>
              <p>{topCrop.rotation}</p>
              <p>{topCrop.sustainability}</p>
            </div>
          </Panel>

          <Panel title="Yield and Profit" eyebrow="Economics" icon={LineChart}>
            <div className="kpi-row">
              <Metric icon={Wheat} label="Estimated yield" value={`${topCrop.expectedYield} quintal`} />
              <Metric icon={IndianRupee} label="Expected return" value={`INR ${topCrop.expectedProfit.toLocaleString('en-IN')}`} />
            </div>
            <p className="panel-copy">Current estimate uses crop profile, land size, and budget readiness. Backend can later replace this with live market data.</p>
          </Panel>

          <Panel title="Weather" eyebrow={weather.source} icon={CloudSun}>
            <div className="kpi-row">
              <Metric icon={CloudSun} label="Temperature" value={`${weather.temperature} C`} />
              <Metric icon={Droplets} label="Humidity" value={`${weather.humidity}%`} />
            </div>
            <p className="alert-line">{weather.alert}</p>
          </Panel>
        </section>

        <section className="module-grid">
          <Panel title="Crop Disease Detection" eyebrow="Computer vision module" icon={Camera} id="disease">
            <label className="upload-box">
              <Upload size={22} />
              <span>{imageName || 'Upload a leaf image for prototype diagnosis'}</span>
              <input type="file" accept="image/*" onChange={handleImage} />
            </label>
            <div className="diagnosis">
              <strong>{imageName ? 'Prototype result' : 'Model status'}</strong>
              <p>{imageName ? diseaseAdvisory : 'Frontend is ready. Backend route accepts image upload and returns a disease advisory.'}</p>
            </div>
          </Panel>

          <Panel title="Multilingual Chatbot" eyebrow="Natural language advisory" icon={MessageSquareText} id="chatbot">
            <div className="chat-window">
              {chat.slice(-4).map((item, index) => (
                <div className={item.by === 'Annapurna AI' ? 'chat-bubble ai' : 'chat-bubble'} key={`${item.by}-${index}`}>
                  <strong>{item.by}</strong>
                  <span>{item.text}</span>
                </div>
              ))}
            </div>
            <div className="chat-input">
              <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask crop, irrigation, fertilizer, or disease question" />
              <button onClick={askBot} disabled={!question.trim()}><Bot size={18} /> Ask</button>
            </div>
          </Panel>

          <Panel title="Saved History" eyebrow="Farmer records" icon={History}>
            {history.length === 0 ? (
              <p className="empty-state">Save a plan to create recommendation history.</p>
            ) : (
              <div className="history-list">
                {history.map((item) => (
                  <div className="history-item" key={item.id}>
                    <div>
                      <strong>{item.crop}</strong>
                      <span>{item.location}</span>
                    </div>
                    <p>{item.score}%</p>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </section>

        <section className="module-grid bottom-grid" id="sources">
          <Panel title="Data Sources" eyebrow="Integration map" icon={Database}>
            <StatusLine text={apiStatus} />
            <StatusLine text={`SoilGrids: ${integrationStatus?.soilgrids || 'checking'}`} />
            <StatusLine text={`ISRO Bhuvan: ${integrationStatus?.isro_bhuvan || 'checking'}`} />
            <StatusLine text={`OpenWeatherMap: ${integrationStatus?.openweather || 'checking'}`} />
            <StatusLine text={`Agmarknet/eNAM: ${integrationStatus ? `${integrationStatus.agmarknet}/${integrationStatus.enam}` : 'checking'}`} />
            <StatusLine text="SQLite prototype storage for saved farmer history" />
          </Panel>

          <Panel title="Model Pipeline" eyebrow="Implementation plan" icon={Activity}>
            <StatusLine text="Crop recommendation model with scikit-learn" />
            <StatusLine text="Image disease classifier route prepared" />
            <StatusLine text="Generative AI chatbot route prepared" />
            <StatusLine text="Docker/cloud deployment ready after backend completion" />
          </Panel>

          <Panel title="Security and Ethics" eyebrow="Project compliance" icon={Lock}>
            <StatusLine text="Use clear farmer consent for profile and image data" />
            <StatusLine text="Show recommendations as advisory, not guaranteed outcomes" />
            <StatusLine text="Keep API keys in backend environment variables" />
            <StatusLine text="Explain data sources in project report and defense" />
          </Panel>
        </section>

        <section className="module-grid bottom-grid" id="admin">
          <Panel title="Admin Console" eyebrow="Operations" icon={Settings}>
            <div className="admin-actions">
              <button className="secondary-action" onClick={loadIntegrationStatus}><Database size={18} /> Refresh integrations</button>
              <button className="secondary-action" onClick={loadHistory}><History size={18} /> Refresh history</button>
              <button className="secondary-action" onClick={exportReport}><Download size={18} /> Export report</button>
            </div>
          </Panel>

          <Panel title="Project Deliverables" eyebrow="Proposal coverage" icon={CheckCircle2}>
            <StatusLine text="Web dashboard and mobile responsive PWA" />
            <StatusLine text="User account, crop recommendation, history, chatbot, disease upload" />
            <StatusLine text="FastAPI backend, SQLite storage, scikit-learn model pipeline" />
            <StatusLine text="Docker Compose deployment files" />
          </Panel>

          <Panel title="Live Readiness" eyebrow="External dependencies" icon={Activity}>
            <StatusLine text="Add API keys in .env for live weather and GenAI" />
            <StatusLine text="Replace starter crop dataset with validated regional data" />
            <StatusLine text="Train disease classifier with labelled crop images" />
            <StatusLine text="Use official market feeds before production claims" />
          </Panel>
        </section>
      </section>
    </main>
  );
}

function Panel({ title, eyebrow, icon: Icon, id, children }) {
  return (
    <section className="panel" id={id}>
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
          <option key={item}>{item}</option>
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
