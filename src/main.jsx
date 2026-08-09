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
  Home,
  History,
  IndianRupee,
  Leaf,
  LineChart,
  Lock,
  LogOut,
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
  const [route, setRoute] = useState(() => window.location.pathname === '/' ? '/dashboard' : window.location.pathname);
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
    const handleRoute = () => setRoute(window.location.pathname === '/' ? '/dashboard' : window.location.pathname);
    window.addEventListener('popstate', handleRoute);
    return () => window.removeEventListener('popstate', handleRoute);
  }, []);

  function navigate(path) {
    if (window.location.pathname !== path) window.history.pushState({}, '', path);
    setRoute(path);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

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
      navigate('/dashboard');
    } catch (error) {
      setAuthUser({ name: farm.farmerName, phone: farm.phone, language: farm.language, location: farm.location });
      setApiStatus('Demo account active locally');
      navigate('/dashboard');
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
      navigate('/dashboard');
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

  if (route === '/register' || route === '/login') {
    return (
      <AuthScreen
        mode={route === '/register' ? 'register' : 'login'}
        farm={farm}
        password={authPassword}
        update={update}
        setPassword={setAuthPassword}
        onSubmit={route === '/register' ? registerUser : loginUser}
        navigate={navigate}
        status={apiStatus}
      />
    );
  }

  const navItems = [
    ['/dashboard', 'Overview', Home],
    ['/planner', 'Crop planner', Sprout],
    ['/insights', 'Insights', BarChart3],
    ['/disease', 'Disease scan', Camera],
    ['/advisor', 'AI advisor', Bot],
    ['/records', 'Saved plans', History],
    ['/settings', 'System', Settings]
  ];

  const pageMeta = {
    '/dashboard': ['Farm overview', 'Your current season, recommendation, and field signals at a glance.'],
    '/planner': ['Crop planner', 'Enter farm conditions and compare the strongest crop matches.'],
    '/insights': ['Field insights', 'Understand the agronomy, economics, weather, and sustainability behind the recommendation.'],
    '/disease': ['Disease analysis', 'Upload a crop image and receive an initial advisory.'],
    '/advisor': ['AI farm advisor', 'Ask questions using your current crop and field conditions.'],
    '/records': ['Saved plans', 'Review recommendation plans saved for this farmer.'],
    '/settings': ['System & data', 'Review integrations, safeguards, and project readiness.']
  };
  const currentMeta = pageMeta[route] || pageMeta['/dashboard'];

  function renderPage() {
    if (route === '/planner') return (
      <section className="main-grid page-section">
        <Panel title="Farm conditions" eyebrow="Step 01 / Enter data" icon={Search}>
          <div className="form-grid">
            <Field label="Farmer name" value={farm.farmerName} onChange={(value) => update('farmerName', value)} />
            <Field label="Phone" value={farm.phone} onChange={(value) => update('phone', value)} />
            <Field label="Location" value={farm.location} onChange={(value) => update('location', value)} />
            <SelectField label="Language" value={farm.language} values={['English', 'Hindi', 'Punjabi', 'Haryanvi']} onChange={(value) => update('language', value)} />
            <SelectField label="Season" value={farm.season} values={['Kharif', 'Rabi', 'Zaid']} onChange={(value) => update('season', value)} />
            <SelectField label="Soil type" value={farm.soilType} values={['Alluvial', 'Black', 'Clayey', 'Loamy', 'Sandy loam']} onChange={(value) => update('soilType', value)} />
            <RangeInput label="Land size (acre)" field="landSize" min="0.5" max="10" step="0.5" value={farm.landSize} update={update} />
            <RangeInput label="Soil pH" field="ph" min="4" max="9" step="0.1" value={farm.ph} update={update} />
            <RangeInput label="Nitrogen" field="nitrogen" min="0" max="100" value={farm.nitrogen} update={update} />
            <RangeInput label="Phosphorus" field="phosphorus" min="0" max="100" value={farm.phosphorus} update={update} />
            <RangeInput label="Potassium" field="potassium" min="0" max="100" value={farm.potassium} update={update} />
            <RangeInput label="Temperature (C)" field="temperature" min="5" max="45" value={farm.temperature} update={update} />
            <RangeInput label="Humidity (%)" field="humidity" min="10" max="100" value={farm.humidity} update={update} />
            <RangeInput label="Rainfall (mm)" field="rainfall" min="0" max="300" value={farm.rainfall} update={update} />
            <RangeInput label="Budget (INR)" field="budget" min="5000" max="150000" step="1000" value={farm.budget} update={update} />
            <SelectField label="Priority" value={farm.marketPriority} values={['Balanced', 'Profit', 'Sustainability', 'Water saving']} onChange={(value) => update('marketPriority', value)} />
          </div>
        </Panel>
        <Panel title="Best crop matches" eyebrow="Step 02 / Compare" icon={BarChart3}>
          <div className="crop-list">{recommendations.slice(0, 4).map((crop) => <CropCard crop={crop} key={crop.name} />)}</div>
          <button className="primary-action save-recommendation" onClick={savePlan}><Save size={18} /> Save this plan</button>
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
          <p className="panel-copy">Estimate uses crop profile, land size, suitability, and budget readiness.</p>
        </Panel>
        <Panel title="Weather readiness" eyebrow={weather.source} icon={CloudSun}>
          <div className="kpi-row"><Metric icon={CloudSun} label="Temperature" value={`${weather.temperature} C`} /><Metric icon={Droplets} label="Humidity" value={`${weather.humidity}%`} /></div>
          <p className="alert-line">{weather.alert}</p>
        </Panel>
      </section>
    );

    if (route === '/disease') return (
      <section className="feature-layout page-section">
        <Panel title="Upload crop image" eyebrow="Computer vision" icon={Camera}>
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
        <Panel title="Conversation" eyebrow={`${farm.language} advisory`} icon={MessageSquareText}>
          <div className="chat-window expanded-chat">{chat.map((item, index) => <div className={item.by === 'Annapurna AI' ? 'chat-bubble ai' : 'chat-bubble'} key={`${item.by}-${index}`}><strong>{item.by}</strong><span>{item.text}</span></div>)}</div>
          <div className="chat-input"><input value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && question.trim() && askBot()} placeholder="Ask about irrigation, fertilizer, disease, or market planning" /><button onClick={askBot} disabled={!question.trim()}><Bot size={18} /> Ask advisor</button></div>
        </Panel>
        <Panel title="Advisor context" eyebrow="Live farm profile" icon={Database}>
          <StatusLine text={`Top crop: ${topCrop.name} (${topCrop.suitability}%)`} />
          <StatusLine text={`Soil: ${farm.soilType}, pH ${farm.ph}`} />
          <StatusLine text={`Season: ${farm.season}`} />
          <StatusLine text={`Priority: ${farm.marketPriority}`} />
        </Panel>
      </section>
    );

    if (route === '/records') return (
      <section className="page-section records-page">
        <Panel title="Recommendation history" eyebrow="Saved plans" icon={History}>
          {history.length === 0 ? <div className="empty-records"><History size={30} /><h3>No saved plans yet</h3><p>Complete the crop planner and save a recommendation to build your farm record.</p><button className="primary-action" onClick={() => navigate('/planner')}>Open crop planner</button></div> : <div className="history-list records-list">{history.map((item) => <div className="history-item" key={item.id}><div><strong>{item.crop}</strong><span>{item.location} · {item.date}</span></div><p>{item.score}% match</p></div>)}</div>}
        </Panel>
      </section>
    );

    if (route === '/settings') return (
      <section className="module-grid page-section">
        <Panel title="Data sources" eyebrow="Integration status" icon={Database}>
          <StatusLine text={apiStatus} /><StatusLine text={`SoilGrids: ${integrationStatus?.soilgrids || 'checking'}`} /><StatusLine text={`ISRO Bhuvan: ${integrationStatus?.isro_bhuvan || 'checking'}`} /><StatusLine text={`OpenWeatherMap: ${integrationStatus?.openweather || 'checking'}`} /><StatusLine text={`Market feeds: ${integrationStatus ? `${integrationStatus.agmarknet}/${integrationStatus.enam}` : 'checking'}`} />
        </Panel>
        <Panel title="Operations" eyebrow="Account & data" icon={Settings}>
          <div className="admin-actions"><button className="secondary-action" onClick={syncBackend}><Database size={18} /> Sync recommendations</button><button className="secondary-action" onClick={loadIntegrationStatus}><Activity size={18} /> Refresh integrations</button><button className="secondary-action" onClick={exportReport}><Download size={18} /> Export current report</button></div>
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
        <section className="status-grid dashboard-metrics"><Metric icon={BarChart3} label="Top recommendation" value={`${topCrop.name} · ${topCrop.suitability}%`} /><Metric icon={MapPin} label="Farm location" value={farm.location} /><Metric icon={CloudSun} label="Field weather" value={`${farm.temperature} C · ${farm.humidity}%`} /><Metric icon={IndianRupee} label="Expected return" value={`INR ${topCrop.expectedProfit.toLocaleString('en-IN')}`} /></section>
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
        <div className="sidebar-profile"><div className="avatar">{(authUser?.name || farm.farmerName).charAt(0)}</div><div><strong>{authUser?.name || farm.farmerName}</strong><span>{farm.location}</span></div><button aria-label="Sign out" onClick={() => { setAuthUser(null); navigate('/login'); }}><LogOut size={17} /></button></div>
      </aside>
      <section className="workspace saas-workspace">
        <header className="app-topbar"><div><p className="eyebrow">Annapurna workspace</p><h2>{currentMeta[0]}</h2><p>{currentMeta[1]}</p></div><div className="topbar-actions"><span className="live-pill"><i /> Advisory online</span><button className="secondary-action" onClick={exportReport}><Download size={17} /> Report</button></div></header>
        <div className="page-content">{renderPage()}</div>
      </section>
    </main>
  );
}

function AuthScreen({ mode, farm, password, update, setPassword, onSubmit, navigate, status }) {
  const isRegister = mode === 'register';
  return (
    <main className="auth-shell">
      <section className="auth-story">
        <button className="auth-brand" onClick={() => navigate('/dashboard')}>
          <span className="brand-mark"><Wheat size={23} /></span>
          <span><small>ANNAPURNA AI</small><strong>Farm intelligence</strong></span>
        </button>
        <div className="auth-story-copy">
          <p className="eyebrow">Built for better farm decisions</p>
          <h1>Technology that respects the land and the people who cultivate it.</h1>
          <p>Bring crop planning, field signals, disease support, and practical advisory into one clear workspace.</p>
        </div>
        <div className="auth-trust"><ShieldCheck size={19} /><span>Your recommendations remain advisory and transparent.</span></div>
      </section>
      <section className="auth-form-side">
        <form className="auth-card" onSubmit={(event) => { event.preventDefault(); onSubmit(); }}>
          <p className="eyebrow">{isRegister ? 'Create your workspace' : 'Welcome back'}</p>
          <h2>{isRegister ? 'Register your farm' : 'Sign in to Annapurna'}</h2>
          <p className="auth-intro">{isRegister ? 'Set up your farmer profile to receive recommendations relevant to your farm.' : 'Continue to your crop plans, field insights, and saved recommendations.'}</p>
          <div className="auth-fields">
            {isRegister && <Field label="Full name" value={farm.farmerName} onChange={(value) => update('farmerName', value)} />}
            <Field label="Phone number" value={farm.phone} onChange={(value) => update('phone', value)} />
            {isRegister && <Field label="Farm location" value={farm.location} onChange={(value) => update('location', value)} />}
            {isRegister && <SelectField label="Preferred language" value={farm.language} values={['English', 'Hindi', 'Punjabi', 'Haryanvi']} onChange={(value) => update('language', value)} />}
            <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength="6" required /></label>
          </div>
          {isRegister && <label className="consent-row"><input type="checkbox" required /><span>I consent to using my farm details to generate advisory recommendations.</span></label>}
          <button className="primary-action auth-submit" type="submit"><UserRound size={18} /> {isRegister ? 'Create farm account' : 'Sign in'}</button>
          <p className="auth-switch">{isRegister ? 'Already have an account?' : 'New to Annapurna?'} <button type="button" onClick={() => navigate(isRegister ? '/login' : '/register')}>{isRegister ? 'Sign in' : 'Create an account'}</button></p>
          <p className="auth-status">{status}</p>
        </form>
      </section>
    </main>
  );
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
