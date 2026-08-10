import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  BarChart3,
  Bot,
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
  LogOut,
  MapPin,
  MessageSquareText,
  RefreshCw,
  Save,
  Search,
  Settings,
  ShieldCheck,
  Sprout,
  TriangleAlert,
  Upload,
  UserRound,
  Wheat
} from 'lucide-react';
import { ApiError, analysisCache, api, clearSession, getStoredUser, makeId, setAuthFailureHandler, storeSession } from './api.js';
import './styles.css';

const CROP_ICONS = {
  Rice: Wheat,
  Maize: Sprout,
  Cotton: Sprout,
  Wheat,
  Mustard: Leaf,
  Chickpea: Leaf,
  Sugarcane: Sprout,
  'Pearl Millet': Wheat
};

const CROP_NAMES = Object.keys(CROP_ICONS);
const PROTECTED_ROUTES = ['/dashboard', '/planner', '/insights', '/disease', '/advisor', '/records', '/settings'];

const initialFarm = {
  farmerName: '',
  phone: '',
  location: 'Sonipat, Haryana',
  language: 'English',
  landSize: 2,
  season: 'Kharif',
  previousCrop: 'None',
  soilType: 'Alluvial',
  ph: 6.6,
  nitrogen: 62,
  phosphorus: 41,
  potassium: 48,
  temperature: 29,
  humidity: 64,
  rainfall: 115,
  budget: 95000,
  marketPriority: 'Balanced'
};

const formatINR = (value) =>
  typeof value === 'number' && Number.isFinite(value) ? `INR ${value.toLocaleString('en-IN')}` : '—';

const cropIcon = (name) => CROP_ICONS[name] || Sprout;

/** Compare only the fields that change a recommendation. */
function farmInputsMatch(a, b) {
  if (!a || !b) return false;
  const keys = [
    'location', 'season', 'previousCrop', 'soilType', 'marketPriority',
    'landSize', 'ph', 'nitrogen', 'phosphorus', 'potassium',
    'temperature', 'humidity', 'rainfall', 'budget'
  ];
  return keys.every((key) => String(a[key]) === String(b[key]));
}

function App() {
  const [route, setRoute] = useState(() => window.location.pathname || '/');
  const [farm, setFarm] = useState(initialFarm);
  const [authUser, setAuthUser] = useState(() => getStoredUser());
  const [authPassword, setAuthPassword] = useState('');
  const [authBusy, setAuthBusy] = useState(false);
  const [history, setHistory] = useState([]);
  const [question, setQuestion] = useState('How should I irrigate the recommended crop?');
  const [chat, setChat] = useState([
    {
      by: 'Annapurna AI',
      text: 'Ask me anything about your field. I answer using your current farm profile and the ranked crop from the server.'
    }
  ]);
  const [chatBusy, setChatBusy] = useState(false);
  const [imageName, setImageName] = useState('');
  const [diseaseResult, setDiseaseResult] = useState(null);
  const [diseaseBusy, setDiseaseBusy] = useState(false);
  const [status, setStatus] = useState(null);
  const [integrationStatus, setIntegrationStatus] = useState(null);

  // The only source of recommendations. `source` is 'live' or 'cache'; nothing
  // in the client ever synthesises a ranking of its own.
  const [analysis, setAnalysis] = useState(null);
  const [analysisBusy, setAnalysisBusy] = useState(false);

  const navigateRef = useRef(null);

  const notify = useCallback((tone, message) => setStatus({ tone, message }), []);

  const navigate = useCallback((path) => {
    if (window.location.pathname !== path) window.history.pushState({}, '', path);
    setRoute(path);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);
  navigateRef.current = navigate;

  const signOut = useCallback(
    (message) => {
      clearSession();
      setAuthUser(null);
      setHistory([]);
      if (message) notify('warning', message);
      navigateRef.current?.('/login');
    },
    [notify]
  );

  useEffect(() => {
    setAuthFailureHandler(() => signOut('Your session ended. Please sign in again.'));
  }, [signOut]);

  const recommendations = analysis?.data?.recommendations ?? [];
  const topCrop = recommendations[0] ?? null;
  const weather = analysis?.data?.weather ?? null;
  const soilAnalysis = analysis?.data?.soil ?? null;
  const marketAnalysis = analysis?.data?.markets?.[0] ?? null;
  const geminiExplanation = analysis?.data?.ai_explanation ?? null;
  const analysisStale = Boolean(analysis) && !farmInputsMatch(analysis.farm, farm);

  const loadHistory = useCallback(async () => {
    try {
      const data = await api.listHistory();
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
      if (!(error instanceof ApiError) || !error.isAuthError) {
        notify('warning', 'Saved plans are unavailable while the server is unreachable.');
      }
    }
  }, [notify]);

  const loadIntegrationStatus = useCallback(async () => {
    try {
      setIntegrationStatus(await api.integrationStatus());
    } catch {
      setIntegrationStatus(null);
    }
  }, []);

  useEffect(() => {
    const cached = analysisCache.load();
    if (cached) {
      setAnalysis({ ...cached, source: 'cache' });
      setFarm((current) => ({ ...current, ...cached.farm }));
    }
    loadIntegrationStatus();

    const handleRoute = () => setRoute(window.location.pathname || '/');
    window.addEventListener('popstate', handleRoute);
    return () => window.removeEventListener('popstate', handleRoute);
  }, [loadIntegrationStatus]);

  useEffect(() => {
    if (authUser) loadHistory();
  }, [authUser, loadHistory]);

  function update(field, value) {
    setFarm((current) => ({ ...current, [field]: value }));
  }

  async function runAnalysis() {
    setAnalysisBusy(true);
    try {
      const data = await api.analysis(farm);
      const snapshot = { ...farm };
      setAnalysis({ data, farm: snapshot, cachedAt: new Date().toISOString(), source: 'live' });
      analysisCache.save(data, snapshot);
      const top = data.recommendations?.[0];
      notify(
        'success',
        top
          ? `${data.ai_provider === 'gemini' ? 'Gemini explanation ready' : 'Ranking ready'}: ${top.crop} at ${top.suitability}% suitability`
          : 'Analysis complete'
      );
    } catch (error) {
      const message =
        error instanceof ApiError && error.isOffline
          ? 'Cannot reach the server. Showing your last saved analysis if there is one.'
          : error.message;
      notify('warning', message);
    } finally {
      setAnalysisBusy(false);
    }
  }

  async function submitAuth(mode) {
    setAuthBusy(true);
    try {
      const payload =
        mode === 'register'
          ? {
              name: farm.farmerName || 'Farmer',
              phone: farm.phone,
              password: authPassword,
              language: farm.language,
              location: farm.location
            }
          : { phone: farm.phone, password: authPassword };

      const data = mode === 'register' ? await api.register(payload) : await api.login(payload);
      storeSession(data.user, data.access_token);
      setAuthUser(data.user);
      setAuthPassword('');
      setFarm((current) => ({
        ...current,
        farmerName: data.user.name,
        phone: data.user.phone,
        language: data.user.language,
        location: data.user.location
      }));
      notify('success', mode === 'register' ? 'Account created' : 'Signed in');
      navigate('/dashboard');
    } catch (error) {
      // A failed sign-in leaves you signed out. It never fabricates a local session.
      notify('warning', error.message);
    } finally {
      setAuthBusy(false);
    }
  }

  async function exportReport() {
    try {
      const text = await api.report(farm);
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'annapurna-ai-report.txt';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      notify('success', 'Report downloaded');
    } catch (error) {
      notify('warning', `Report unavailable: ${error.message}`);
    }
  }

  async function savePlan() {
    if (!topCrop) {
      notify('warning', 'Run the analysis before saving a plan.');
      return;
    }
    if (!authUser) {
      notify('warning', 'Sign in to save this plan to your records.');
      navigate('/login');
      return;
    }

    const record = {
      farmer_name: authUser.name,
      location: farm.location,
      crop: topCrop.crop,
      suitability: topCrop.suitability,
      expected_profit: topCrop.expected_profit
    };

    const optimistic = {
      id: makeId(),
      crop: topCrop.crop,
      score: topCrop.suitability,
      profit: topCrop.expected_profit,
      location: farm.location,
      date: new Date().toLocaleString('en-IN'),
      pending: true
    };
    setHistory((items) => [optimistic, ...items]);

    try {
      await api.saveHistory(record);
      notify('success', 'Plan saved to your records');
      await loadHistory();
    } catch (error) {
      setHistory((items) => items.filter((item) => item.id !== optimistic.id));
      notify('warning', `Could not save the plan: ${error.message}`);
    }
  }

  async function askBot() {
    const userQuestion = question.trim();
    if (!userQuestion || chatBusy) return;

    setChat((items) => [...items, { by: authUser?.name || 'You', text: userQuestion }]);
    setQuestion('');
    setChatBusy(true);

    try {
      const data = await api.chat(userQuestion, topCrop?.crop ?? null, farm);
      setChat((items) => [...items, { by: 'Annapurna AI', text: data.answer }]);
      notify('info', data.provider === 'gemini' ? 'Answered by Gemini' : 'Answered by the local advisor');
    } catch (error) {
      setChat((items) => [
        ...items,
        {
          by: 'Annapurna AI',
          text: `I could not reach the advisory service (${error.message}). Your saved analysis is still available, but I cannot answer new questions offline.`,
          error: true
        }
      ]);
    } finally {
      setChatBusy(false);
    }
  }

  async function handleImage(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    event.target.value = '';
    setImageName(file.name);
    setDiseaseResult(null);
    setDiseaseBusy(true);

    try {
      const data = await api.disease(file, topCrop?.crop ?? null);
      setDiseaseResult(data);
      notify('info', data.provider === 'gemini' ? 'Gemini screening complete' : 'Screening unavailable; see the note');
    } catch (error) {
      setDiseaseResult({ error: error.message });
      notify('warning', error.message);
    } finally {
      setDiseaseBusy(false);
    }
  }

  // ----- routing -------------------------------------------------------- //

  if (route === '/' || route === '/about') {
    return <MarketingSite page={route === '/about' ? 'about' : 'home'} navigate={navigate} />;
  }

  if (route === '/register' || route === '/login') {
    const mode = route === '/register' ? 'register' : 'login';
    return (
      <AuthScreen
        mode={mode}
        farm={farm}
        password={authPassword}
        busy={authBusy}
        update={update}
        setPassword={setAuthPassword}
        onSubmit={() => submitAuth(mode)}
        navigate={navigate}
        status={status}
      />
    );
  }

  if (PROTECTED_ROUTES.includes(route) && !authUser) {
    return <SignInRequired navigate={navigate} />;
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
    '/insights': ['Field insights', 'The agronomy, economics, weather, and sustainability behind the recommendation.'],
    '/disease': ['Disease analysis', 'Upload a crop image and receive an initial advisory.'],
    '/advisor': ['AI farm advisor', 'Ask questions using your current crop and field conditions.'],
    '/records': ['Saved plans', 'Recommendation plans saved to your account.'],
    '/settings': ['System & data', 'Integrations, safeguards, and project readiness.']
  };
  const currentMeta = pageMeta[route] || pageMeta['/dashboard'];

  const analysisBanner = analysis ? (
    <AnalysisBanner
      source={analysis.source}
      cachedAt={analysis.cachedAt}
      stale={analysisStale}
      busy={analysisBusy}
      onRefresh={runAnalysis}
    />
  ) : null;

  function renderPage() {
    if (route === '/planner') {
      return (
        <section className="main-grid page-section">
          <Panel title="Farm conditions" eyebrow="Step 01 / Enter data" icon={Search}>
            <div className="form-grid">
              <Field label="Location" value={farm.location} onChange={(value) => update('location', value)} />
              <SelectField label="Language" value={farm.language} values={['English', 'Hindi', 'Punjabi', 'Haryanvi']} onChange={(value) => update('language', value)} />
              <SelectField label="Season" value={farm.season} values={['Kharif', 'Rabi', 'Zaid']} onChange={(value) => update('season', value)} />
              <SelectField label="Previous crop" value={farm.previousCrop} values={['None', ...CROP_NAMES]} onChange={(value) => update('previousCrop', value)} />
              <SelectField label="Soil type" value={farm.soilType} values={['Alluvial', 'Black', 'Clayey', 'Loamy', 'Sandy loam']} onChange={(value) => update('soilType', value)} />
              <RangeInput label="Land size (acre)" field="landSize" min="0.5" max="10" step="0.5" value={farm.landSize} update={update} />
              <RangeInput label="Soil pH" field="ph" min="4" max="9" step="0.1" value={farm.ph} update={update} />
              <RangeInput label="Nitrogen" field="nitrogen" min="0" max="100" value={farm.nitrogen} update={update} />
              <RangeInput label="Phosphorus" field="phosphorus" min="0" max="100" value={farm.phosphorus} update={update} />
              <RangeInput label="Potassium" field="potassium" min="0" max="100" value={farm.potassium} update={update} />
              <RangeInput label="Temperature (C)" field="temperature" min="5" max="45" value={farm.temperature} update={update} />
              <RangeInput label="Humidity (%)" field="humidity" min="10" max="100" value={farm.humidity} update={update} />
              <RangeInput label="Seasonal rainfall (mm)" field="rainfall" min="0" max="300" value={farm.rainfall} update={update} />
              <RangeInput label="Budget (INR)" field="budget" min="5000" max="500000" step="5000" value={farm.budget} update={update} />
              <SelectField label="Priority" value={farm.marketPriority} values={['Balanced', 'Profit', 'Sustainability', 'Water saving']} onChange={(value) => update('marketPriority', value)} />
            </div>
            <div className="planner-actions">
              <button className="primary-action" onClick={runAnalysis} disabled={analysisBusy}>
                <Bot size={18} /> {analysisBusy ? 'Analysing farm…' : 'Run complete analysis'}
              </button>
              <button className="secondary-action" onClick={savePlan} disabled={!topCrop}>
                <Save size={18} /> Save this plan
              </button>
            </div>
          </Panel>

          <Panel title="Best crop matches" eyebrow="Step 02 / Compare" icon={BarChart3}>
            {analysisBanner}
            {topCrop ? (
              <>
                <div className="crop-list">
                  {recommendations.slice(0, 4).map((crop) => (
                    <CropCard crop={crop} key={crop.crop} />
                  ))}
                </div>
                {geminiExplanation && (
                  <div className="gemini-insight">
                    <div><Bot size={18} /><strong>Gemini explanation</strong></div>
                    <p>{geminiExplanation.summary}</p>
                    <span><b>Next:</b> {geminiExplanation.priority_action}</span>
                    <span><b>Watch:</b> {geminiExplanation.risk_note}</span>
                  </div>
                )}
              </>
            ) : (
              <EmptyAnalysis busy={analysisBusy} onRun={runAnalysis} />
            )}
          </Panel>
        </section>
      );
    }

    if (route === '/insights') {
      if (!topCrop) {
        return (
          <section className="page-section">
            <Panel title="Field insights" eyebrow="Waiting for analysis" icon={BarChart3}>
              <EmptyAnalysis busy={analysisBusy} onRun={runAnalysis} />
            </Panel>
          </section>
        );
      }

      return (
        <section className="module-grid page-section">
          <div className="span-all">{analysisBanner}</div>
          <Panel title={`${topCrop.crop} advisory`} eyebrow="Decision support" icon={Leaf}>
            <div className="advice-list">
              <p>{topCrop.advisory}</p>
              <p>{topCrop.rotation}</p>
              <p>{topCrop.sustainability}</p>
            </div>
          </Panel>

          <Panel title="Yield and profit" eyebrow="Economics" icon={LineChart}>
            <div className="kpi-row">
              <Metric icon={Wheat} label="Expected yield" value={`${topCrop.expected_yield} quintal`} />
              <Metric icon={IndianRupee} label="Net return" value={formatINR(topCrop.expected_profit)} />
            </div>
            <div className="insight-facts">
              <span><b>Revenue</b> {formatINR(topCrop.estimated_revenue)}</span>
              <span><b>Cost</b> {formatINR(topCrop.estimated_cost)}</span>
              <span><b>Margin</b> {topCrop.profit_margin}%</span>
            </div>
            <p className="panel-copy">
              Revenue is {topCrop.expected_yield} quintal x {formatINR(topCrop.market_price)} per quintal.
              Net return is revenue minus estimated cost. All three are planning estimates.
            </p>
            {!topCrop.budget_covers_cost && (
              <p className="alert-line warning">
                <TriangleAlert size={16} /> Your budget is short by {formatINR(topCrop.budget_shortfall)} of the estimated cost.
              </p>
            )}
          </Panel>

          <Panel title="Weather readiness" eyebrow={weather?.source || 'Weather'} icon={CloudSun}>
            <div className="kpi-row">
              <Metric icon={CloudSun} label="Temperature" value={`${weather?.temperature ?? '—'} C`} />
              <Metric icon={Droplets} label="Humidity" value={`${weather?.humidity ?? '—'}%`} />
            </div>
            <p className="alert-line">{weather?.alert}</p>
            <p className="panel-copy">
              Seasonal rainfall used in ranking: {weather?.seasonal_rainfall_mm ?? farm.rainfall} mm (your input).
              {weather?.recent_rainfall_mm != null && ` Live feed reports ${weather.recent_rainfall_mm} mm in the last hour.`}
              {weather?.note && ` ${weather.note}`}
            </p>
          </Panel>

          <Panel title="Soil health" eyebrow={soilAnalysis?.source || 'Soil'} icon={Database}>
            <div className="kpi-row">
              <Metric icon={Leaf} label="Health score" value={`${soilAnalysis?.health_score}/100`} />
              <Metric icon={Activity} label="Condition" value={soilAnalysis?.classification} />
            </div>
            <div className="advice-list">
              {(soilAnalysis?.actions || []).map((action) => <p key={action}>{action}</p>)}
            </div>
          </Panel>

          <Panel title="Market outlook" eyebrow={marketAnalysis?.source || 'Market'} icon={IndianRupee}>
            <div className="kpi-row">
              <Metric icon={IndianRupee} label="Planning price" value={`${formatINR(marketAnalysis?.modal_price_per_quintal)}/q`} />
              <Metric icon={LineChart} label="Direction" value={`${marketAnalysis?.trend} ${marketAnalysis?.trend_percent > 0 ? '+' : ''}${marketAnalysis?.trend_percent}%`} />
            </div>
            <p className="panel-copy">{marketAnalysis?.note}</p>
          </Panel>

          <Panel title="Sustainability" eyebrow="Rotation and resource use" icon={Sprout}>
            <div className="kpi-row">
              <Metric icon={Leaf} label="Plan score" value={`${topCrop.sustainability_score}/100`} />
              <Metric icon={Droplets} label="Water demand" value={topCrop.water} />
            </div>
            <p className="panel-copy">{topCrop.rotation}</p>
            <p className="panel-copy">{topCrop.sustainability}</p>
          </Panel>
        </section>
      );
    }

    if (route === '/disease') {
      return (
        <section className="feature-layout page-section">
          <Panel title="Upload crop image" eyebrow="Gemini multimodal screening" icon={Camera}>
            <label className="upload-box large-upload">
              <Upload size={28} />
              <span>{imageName || 'Choose a clear leaf image for screening'}</span>
              <input type="file" accept="image/*" onChange={handleImage} disabled={diseaseBusy} />
            </label>
            <div className="diagnosis">
              <strong>{diseaseBusy ? 'Screening…' : diseaseResult ? 'Screening result' : 'Before you upload'}</strong>
              {diseaseBusy && <p>Sending the image for analysis.</p>}
              {!diseaseBusy && !diseaseResult && (
                <p>Use a well-lit image with one affected leaf in focus. Results are advisory and should be confirmed locally.</p>
              )}
              {!diseaseBusy && diseaseResult?.error && <p className="alert-line warning">{diseaseResult.error}</p>}
              {!diseaseBusy && diseaseResult && !diseaseResult.error && (
                <>
                  <p>
                    <strong>{diseaseResult.prediction}</strong>
                    {Number.isFinite(diseaseResult.confidence) && diseaseResult.confidence > 0 && (
                      <> · {Math.round(diseaseResult.confidence * 100)}% confidence</>
                    )}
                    {diseaseResult.urgency && diseaseResult.urgency !== 'unknown' && <> · urgency {diseaseResult.urgency}</>}
                  </p>
                  <p>{diseaseResult.advisory}</p>
                  {(diseaseResult.observations || []).length > 0 && (
                    <ul className="observation-list">
                      {diseaseResult.observations.map((item) => <li key={item}>{item}</li>)}
                    </ul>
                  )}
                </>
              )}
            </div>
          </Panel>

          <Panel title="Current crop context" eyebrow="Used in analysis" icon={Leaf}>
            <Metric icon={Wheat} label="Crop" value={topCrop?.crop || 'Run analysis first'} />
            <StatusLine text={`${farm.location} / ${farm.season}`} />
            <StatusLine text={`${farm.humidity}% humidity / ${farm.rainfall} mm seasonal rainfall`} />
            <StatusLine text="Confirm with a local expert before any treatment" />
          </Panel>
        </section>
      );
    }

    if (route === '/advisor') {
      return (
        <section className="advisor-layout page-section">
          <Panel title="Conversation" eyebrow={`Farm advisor / ${farm.language}`} icon={MessageSquareText}>
            <div className="chat-window expanded-chat">
              {chat.map((item, index) => (
                <div className={`chat-bubble${item.by === 'Annapurna AI' ? ' ai' : ''}${item.error ? ' error' : ''}`} key={`${item.by}-${index}`}>
                  <strong>{item.by}</strong>
                  <span>{item.text}</span>
                </div>
              ))}
              {chatBusy && <div className="chat-bubble ai"><strong>Annapurna AI</strong><span>Thinking…</span></div>}
            </div>
            <div className="chat-input">
              <input
                aria-label="Ask the farm advisor a question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') askBot();
                }}
                placeholder="Ask about irrigation, fertilizer, disease, or market planning"
                disabled={chatBusy}
              />
              <button onClick={askBot} disabled={!question.trim() || chatBusy}>
                <Bot size={18} /> {chatBusy ? 'Asking…' : 'Ask advisor'}
              </button>
            </div>
          </Panel>

          <Panel title="Advisor context" eyebrow="Live farm profile" icon={Database}>
            <StatusLine text={topCrop ? `Top crop: ${topCrop.crop} (${topCrop.suitability}%)` : 'Top crop: run the analysis'} />
            <StatusLine text={`Soil: ${farm.soilType}, pH ${farm.ph}`} />
            <StatusLine text={`Season: ${farm.season}`} />
            <StatusLine text={`Priority: ${farm.marketPriority}`} />
          </Panel>
        </section>
      );
    }

    if (route === '/records') {
      return (
        <section className="page-section records-page">
          <Panel title="Recommendation history" eyebrow="Saved plans" icon={History}>
            {history.length === 0 ? (
              <div className="empty-records">
                <History size={30} />
                <h3>No saved plans yet</h3>
                <p>Run the crop planner and save a recommendation to build your farm record.</p>
                <button className="primary-action" onClick={() => navigate('/planner')}>Open crop planner</button>
              </div>
            ) : (
              <div className="history-list records-list">
                {history.map((item) => (
                  <div className={`history-item${item.pending ? ' pending' : ''}`} key={item.id}>
                    <div>
                      <strong>{item.crop}</strong>
                      <span>{item.location} · {item.date}{item.pending ? ' · saving…' : ''}</span>
                    </div>
                    <p>{item.score}% match</p>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </section>
      );
    }

    if (route === '/settings') {
      const modelState = integrationStatus ? 'reported by the server' : 'server unreachable';
      return (
        <section className="module-grid page-section">
          <Panel title="Data sources" eyebrow={`Integration status · ${modelState}`} icon={Database}>
            <StatusLine text={`Gemini AI: ${integrationStatus?.gemini || 'unknown'} (${integrationStatus?.gemini_model || 'model unknown'})`} />
            <StatusLine text={`SoilGrids: ${integrationStatus?.soilgrids || 'unknown'}`} />
            <StatusLine text={`ISRO Bhuvan: ${integrationStatus?.isro_bhuvan || 'unknown'}`} />
            <StatusLine text={`OpenWeatherMap: ${integrationStatus?.openweather || 'unknown'}`} />
            <StatusLine text={`Market feeds: ${integrationStatus ? `${integrationStatus.agmarknet} / ${integrationStatus.enam}` : 'unknown'}`} />
          </Panel>

          <Panel title="Operations" eyebrow="Account & data" icon={Settings}>
            <div className="admin-actions">
              <button className="secondary-action" onClick={runAnalysis} disabled={analysisBusy}>
                <Database size={18} /> {analysisBusy ? 'Analysing…' : 'Re-run analysis'}
              </button>
              <button className="secondary-action" onClick={loadIntegrationStatus}>
                <Activity size={18} /> Refresh integrations
              </button>
              <button className="secondary-action" onClick={exportReport}>
                <Download size={18} /> Export report
              </button>
            </div>
          </Panel>

          <Panel title="Safety & ethics" eyebrow="Advisory safeguards" icon={ShieldCheck}>
            <StatusLine text="Recommendations are advisory, not guaranteed outcomes" />
            <StatusLine text="Saved plans are visible only to your own account" />
            <StatusLine text="API keys stay in the backend environment, never in the browser" />
            <StatusLine text="Local verification recommended before treatment or investment" />
          </Panel>
        </section>
      );
    }

    return (
      <>
        {analysisBanner}
        <section className="dashboard-hero">
          <div className="dashboard-copy">
            <p className="eyebrow">{farm.season} season workspace</p>
            <h2>Good decisions begin with a clear field picture.</h2>
            <p className="subhead">
              {topCrop ? (
                <>Your strongest match is <strong>{topCrop.crop}</strong> at {topCrop.suitability}% suitability.</>
              ) : (
                <>Run the complete analysis to see ranked crops for your field.</>
              )}
            </p>
            <div className="action-row">
              <button className="primary-action" onClick={() => navigate('/planner')}><Sprout size={18} /> Plan a crop</button>
              <button className="secondary-action" onClick={() => navigate('/advisor')}><Bot size={18} /> Ask advisor</button>
            </div>
          </div>
          {topCrop ? <FieldMap crop={topCrop} moisture={farm.humidity} /> : <FieldMapPlaceholder />}
        </section>

        <section className="status-grid dashboard-metrics">
          <Metric icon={BarChart3} label="Top recommendation" value={topCrop ? `${topCrop.crop} · ${topCrop.suitability}%` : 'Not analysed'} />
          <Metric icon={MapPin} label="Farm location" value={farm.location} />
          <Metric icon={CloudSun} label="Field weather" value={weather ? `${weather.temperature} C · ${weather.humidity}%` : 'Not analysed'} />
          <Metric icon={IndianRupee} label="Net return" value={topCrop ? formatINR(topCrop.expected_profit) : '—'} />
        </section>

        <section className="quick-grid">
          <QuickAction icon={Sprout} title="Update crop plan" text="Compare crops using soil, weather, budget, and season." onClick={() => navigate('/planner')} />
          <QuickAction icon={Leaf} title="Review advisory" text="Guidance, yield, profit, and sustainability for your top crop." onClick={() => navigate('/insights')} />
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
          {navItems.map(([path, label, Icon]) => (
            <button className={`nav-item ${route === path ? 'active' : ''}`} onClick={() => navigate(path)} key={path}>
              <Icon size={18} /><span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-profile">
          <div className="avatar">{(authUser?.name || 'F').charAt(0)}</div>
          <div><strong>{authUser?.name}</strong><span>{farm.location}</span></div>
          <button
            aria-label="Sign out"
            onClick={async () => {
              try { await api.logout(); } catch { /* the local session is cleared regardless */ }
              signOut();
            }}
          >
            <LogOut size={17} />
          </button>
        </div>
      </aside>

      <section className="workspace saas-workspace">
        <header className="app-topbar">
          <div>
            <p className="eyebrow">Annapurna workspace</p>
            <h2>{currentMeta[0]}</h2>
            <p>{currentMeta[1]}</p>
          </div>
          <div className="topbar-actions">
            <button className="secondary-action" onClick={exportReport}><Download size={17} /> Report</button>
          </div>
        </header>
        {status && <StatusBar tone={status.tone} message={status.message} onDismiss={() => setStatus(null)} />}
        <div className="page-content">{renderPage()}</div>
      </section>
    </main>
  );
}

function StatusBar({ tone, message, onDismiss }) {
  return (
    <div className={`status-bar ${tone}`} role="status">
      <span>{message}</span>
      <button onClick={onDismiss} aria-label="Dismiss message">×</button>
    </div>
  );
}

function AnalysisBanner({ source, cachedAt, stale, busy, onRefresh }) {
  if (source === 'live' && !stale) return null;

  const when = cachedAt ? new Date(cachedAt).toLocaleString('en-IN') : 'earlier';
  const message =
    source === 'cache'
      ? `Showing the analysis saved on ${when}. Re-run it to refresh against current data.`
      : `Your inputs changed after this analysis ran on ${when}. Re-run to update the ranking.`;

  return (
    <div className="analysis-banner" role="status">
      <TriangleAlert size={17} />
      <span>{message}</span>
      <button className="secondary-action" onClick={onRefresh} disabled={busy}>
        <RefreshCw size={15} /> {busy ? 'Re-running…' : 'Re-run analysis'}
      </button>
    </div>
  );
}

function EmptyAnalysis({ busy, onRun }) {
  return (
    <div className="empty-records">
      <Sprout size={30} />
      <h3>No analysis yet</h3>
      <p>
        Recommendations come from the Annapurna server so that every screen, report, and
        advisory answer describes the same decision. Run the analysis to see ranked crops.
      </p>
      <button className="primary-action" onClick={onRun} disabled={busy}>
        {busy ? 'Analysing…' : 'Run complete analysis'}
      </button>
    </div>
  );
}

function SignInRequired({ navigate }) {
  return (
    <main className="auth-shell">
      <section className="auth-form-side full">
        <div className="auth-card">
          <p className="eyebrow">Sign in required</p>
          <h2>This workspace needs an account</h2>
          <p className="auth-intro">Your saved plans and farm records are tied to your account.</p>
          <button className="primary-action auth-submit" onClick={() => navigate('/login')}>
            <UserRound size={18} /> Sign in
          </button>
          <p className="auth-switch">
            New to Annapurna? <button type="button" onClick={() => navigate('/register')}>Create an account</button>
          </p>
        </div>
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
        <button onClick={() => navigate('/login')}>Sign in</button>
        <button className="public-cta" onClick={() => navigate('/register')}>Create account <span>→</span></button>
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
            <button className="marketing-primary" onClick={() => navigate('/register')}>Start your farm plan <span>→</span></button>
            <button className="marketing-secondary" onClick={() => navigate('/about')}>See how it works</button>
          </div>
          <div className="landing-trust">
            <span><CheckCircle2 size={16} /> Explainable recommendations</span>
            <span><CheckCircle2 size={16} /> Figures that reconcile</span>
            <span><CheckCircle2 size={16} /> Farmer-first safeguards</span>
          </div>
        </div>
        <div className="product-preview" aria-label="Annapurna crop recommendation preview">
          <div className="preview-top"><span><i /> Example field plan</span><small>Kharif · Sonipat</small></div>
          <div className="preview-body">
            <div className="preview-heading"><div><small>Best crop match</small><h3>Maize</h3></div><strong>75%</strong></div>
            <div className="preview-progress"><span /></div>
            <div className="preview-metrics"><div><small>Net return</small><strong>₹56,000</strong></div><div><small>Water need</small><strong>Medium</strong></div><div><small>Soil match</small><strong>Strong</strong></div></div>
            <div className="preview-advice"><Leaf size={18} /><div><strong>Why this works</strong><p>Alluvial soil, rainfall, temperature, and budget are aligned with the current crop profile.</p></div></div>
            <div className="preview-chart" aria-hidden="true">{[46, 62, 54, 78, 68, 88, 74, 92].map((height, index) => <span style={{ height: `${height}%` }} key={index} />)}</div>
          </div>
        </div>
      </section>

      <section className="source-strip"><span>Designed to connect with</span><strong>SoilGrids</strong><strong>ISRO Bhuvan</strong><strong>OpenWeather</strong><strong>Agmarknet</strong><strong>eNAM</strong></section>

      <section className="marketing-section" id="features">
        <div className="section-intro"><p className="marketing-kicker">One connected workspace</p><h2>From field conditions to a practical crop plan.</h2><p>Each tool uses the same farmer profile, so recommendations and advisory stay relevant instead of becoming isolated reports.</p></div>
        <div className="feature-cards">
          <MarketingCard icon={Sprout} label="Plan" title="Crop recommendations" text="Compare crops using season, soil, nutrients, rainfall, temperature, water, budget, and market priority." />
          <MarketingCard icon={BarChart3} label="Understand" title="Field and profit insights" text="See suitability, expected yield, revenue, cost, net return, cautions, rotation advice, and sustainability guidance." />
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
          <div><span>Application API</span><h3>FastAPI</h3><p>Routes for authentication, recommendations, weather, market data, chat, disease analysis, reports, and history.</p></div>
          <div><span>Recommendation</span><h3>Rules + scikit-learn</h3><p>Transparent deterministic scoring, with a trained model that may nudge the ranking only when its measured accuracy justifies it.</p></div>
          <div><span>Storage</span><h3>SQLite</h3><p>Prototype persistence for farmer accounts, sessions, and saved recommendation history.</p></div>
        </div>
      </section>

      <section className="project-scope">
        <div><p className="marketing-kicker">Current scope</p><h2>A strong prototype, not a promise of guaranteed outcomes.</h2></div>
        <ul>
          <li><CheckCircle2 size={18} /> One server-side recommendation engine, so no screen can disagree with another</li>
          <li><CheckCircle2 size={18} /> Prepared adapters for soil, weather, market, chatbot, and disease services</li>
          <li><CheckCircle2 size={18} /> Clear production roadmap for validated datasets, trained models, and official feeds</li>
        </ul>
      </section>

      <MarketingCTA navigate={navigate} />
    </>
  );
}

function MarketingCard({ icon: Icon, label, title, text }) {
  return <article className="marketing-card"><span className="marketing-icon"><Icon size={22} /></span><small>{label}</small><h3>{title}</h3><p>{text}</p></article>;
}

function MarketingCTA({ navigate }) {
  return <section className="marketing-cta"><div><p className="marketing-kicker">Ready to explore?</p><h2>Build your first farm plan in minutes.</h2><p>Create a profile, add the conditions you know, and review a complete recommendation.</p></div><button className="marketing-primary light" onClick={() => navigate('/register')}>Create your account <span>→</span></button></section>;
}

function PublicFooter({ navigate }) {
  return <footer className="public-footer"><button className="public-brand" onClick={() => navigate('/')}><span className="public-brand-mark"><Wheat size={20} /></span><span><strong>Annapurna AI</strong><small>Farm intelligence</small></span></button><p>Decision support for sustainable and informed agriculture.</p><div><button onClick={() => navigate('/')}>Home</button><button onClick={() => navigate('/about')}>About</button><button onClick={() => navigate('/login')}>Sign in</button></div></footer>;
}

function AuthScreen({ mode, farm, password, busy, update, setPassword, onSubmit, navigate, status }) {
  const isRegister = mode === 'register';
  return (
    <main className="auth-shell">
      <section className="auth-story">
        <button className="auth-brand" onClick={() => navigate('/')}>
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
            {isRegister && <Field label="Full name" value={farm.farmerName} onChange={(value) => update('farmerName', value)} required />}
            <label>
              Phone number
              <input
                value={farm.phone}
                onChange={(event) => update('phone', event.target.value.replace(/\D/g, '').slice(0, 10))}
                inputMode="numeric"
                pattern="\d{10}"
                placeholder="10-digit number"
                autoComplete="username"
                required
              />
            </label>
            {isRegister && <Field label="Farm location" value={farm.location} onChange={(value) => update('location', value)} required />}
            {isRegister && <SelectField label="Preferred language" value={farm.language} values={['English', 'Hindi', 'Punjabi', 'Haryanvi']} onChange={(value) => update('language', value)} />}
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={8}
                autoComplete={isRegister ? 'new-password' : 'current-password'}
                required
              />
              {isRegister && <small className="field-hint">At least 8 characters.</small>}
            </label>
          </div>

          {isRegister && (
            <label className="consent-row">
              <input type="checkbox" required />
              <span>I consent to using my farm details to generate advisory recommendations.</span>
            </label>
          )}

          <button className="primary-action auth-submit" type="submit" disabled={busy}>
            <UserRound size={18} /> {busy ? 'Please wait…' : isRegister ? 'Create farm account' : 'Sign in'}
          </button>

          <p className="auth-switch">
            {isRegister ? 'Already have an account?' : 'New to Annapurna?'}{' '}
            <button type="button" onClick={() => navigate(isRegister ? '/login' : '/register')}>
              {isRegister ? 'Sign in' : 'Create an account'}
            </button>
          </p>

          {status && <p className={`auth-status ${status.tone}`} role="status">{status.message}</p>}
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

function FieldMapPlaceholder() {
  return (
    <figure className="field-terminal placeholder">
      <div className="field-readout"><span>FIELD INTELLIGENCE</span><strong>AWAITING ANALYSIS</strong></div>
      <div className="scene-window">
        <div className="field-map-surface">
          <div className="contour contour-one" />
          <div className="contour contour-two" />
        </div>
      </div>
      <figcaption><span>Run the complete analysis to populate this view</span></figcaption>
    </figure>
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
      aria-label={`Field map showing ${crop.crop} at ${crop.suitability} percent suitability`}
    >
      <div className="field-readout">
        <span>FIELD INTELLIGENCE</span>
        <strong>{crop.crop.toUpperCase()} / {crop.suitability}%</strong>
      </div>
      <div className="scene-window">
        <div className="field-map-surface">
          <div className="contour contour-one" />
          <div className="contour contour-two" />
          <div className="field-rows" aria-hidden="true">
            {rows.map((row) => <span style={{ '--row': row }} key={row} />)}
          </div>
          <div className="water-channel" aria-hidden="true" />
          <div className="suitability-dial" style={{ '--score': `${crop.suitability * 3.6}deg` }}>
            <div><strong>{crop.suitability}%</strong><span>SUITABLE</span></div>
          </div>
          <div className="heritage-compass" aria-hidden="true"><span /></div>
          <span className="scan-cursor" style={{ left: `${focus.x}%`, top: `${focus.y}%` }} aria-hidden="true" />
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
        <div><p className="eyebrow">{eyebrow}</p><h3>{title}</h3></div>
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
      <div><span>{label}</span><strong>{value}</strong></div>
    </div>
  );
}

function Field({ label, value, onChange, required }) {
  return (
    <label>
      {label}
      <input value={value} onChange={(event) => onChange(event.target.value)} required={required} />
    </label>
  );
}

function SelectField({ label, value, values, onChange }) {
  return (
    <label>
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {values.map((item) => <option key={item} value={item}>{item}</option>)}
      </select>
    </label>
  );
}

function RangeInput({ label, field, min, max, step = '1', value, update }) {
  return (
    <label>
      <span className="range-label">{label}<strong>{value}</strong></span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => update(field, Number(event.target.value))}
      />
    </label>
  );
}

function CropCard({ crop }) {
  const Icon = cropIcon(crop.crop);
  return (
    <article className="crop-card">
      <div className="crop-head">
        <div className="crop-icon"><Icon size={22} /></div>
        <div><h4>{crop.crop}</h4><p>{crop.suitability}% suitability</p></div>
      </div>
      <div className="score-track"><span style={{ width: `${crop.suitability}%` }} /></div>
      <div className="crop-details">
        <div>
          <strong>Why</strong>
          <ul>{crop.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
        </div>
        <div>
          <strong>Watch</strong>
          <ul>{crop.cautions.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        </div>
      </div>
      <div className="crop-footer">
        <span>{crop.water} water need</span>
        <strong>{formatINR(crop.expected_profit)}</strong>
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

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}
