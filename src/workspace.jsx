import React, { useEffect, useRef, useState } from 'react';
import {
  Activity, BarChart3, Bot, CalendarDays, Camera, CloudSun, Database, Download, Droplets,
  History, Home, IndianRupee, Leaf, LineChart, LogOut, MapPin, MessageSquareText, Save,
  Search, Settings, ShieldCheck, Sprout, Trash2, Upload, UserRound, Wallet, Wheat,
} from 'lucide-react';
import { api, downloadBlob } from './api.js';
import { useAuth } from './auth.jsx';
import { usePlanner } from './planner-state.jsx';
import {
  BarChart, EmptyState, ErrorBoundary, Field, Metric, Notice, Panel, RangeInput, SelectField,
  Spinner, StatusLine, VerdictBadge, compactInr, inr, useAsyncAction,
} from './components.jsx';
import {
  FIELD_RULES, IRRIGATION, IRRIGATION_HELP, LANGUAGES, PRIORITIES, SEASONS, SOIL_TYPES, toApiFarm,
} from './farm.js';

const NAV = [
  ['/dashboard', 'Overview', Home],
  ['/planner', 'Crop planner', Sprout],
  ['/insights', 'Insights', BarChart3],
  ['/finance', 'Season finance', Wallet],
  ['/disease', 'Crop health', Camera],
  ['/advisor', 'Advisor', Bot],
  ['/records', 'Saved plans', History],
  ['/settings', 'System', Settings],
];

const PAGE_META = {
  '/dashboard': ['Farm overview', 'Your season, your strongest match, and the signals behind it.'],
  '/planner': ['Crop planner', 'Enter your field conditions and compare the crops that fit them.'],
  '/insights': ['Field insights', 'The agronomy, economics, weather and sustainability behind the ranking.'],
  '/finance': ['Season finance', 'Costs, working capital, break-even price and the downside case.'],
  '/disease': ['Crop health', 'Upload a leaf image for a cautious screening result.'],
  '/advisor': ['Farm advisor', 'Ask questions against your current field conditions.'],
  '/records': ['Saved plans', 'Plans you have kept.'],
  '/settings': ['System & data', 'What is connected, what is not, and what is stored.'],
};

export function Workspace({ route, navigate }) {
  const headingRef = useRef(null);
  const { farmer, isSignedIn, signOut } = useAuth();
  const { farm, profileComplete, topCrop, analysis, financePlan, notice, setNotice, stale } = usePlanner();
  const [meta0, meta1] = PAGE_META[route] || PAGE_META['/dashboard'];

  const exportPdf = useAsyncAction(async () => {
    if (!analysis?.recommendations?.length) return;
    // The server recomputes the recommendation from the farm profile, so only the crop name
    // is sent. A client cannot make the branded PDF claim a yield or profit of its choosing.
    const blob = await api.pdfReport({
      farm: toApiFarm(farm),
      crop: topCrop?.crop,
      weather: analysis.weather ?? null,
      market: analysis.markets?.[0] ?? null,
      finance: financePlan ?? null,
    });
    const slug = (topCrop?.crop || 'crop').toLowerCase().replace(/\s+/g, '-');
    downloadBlob(blob, `annapurna-${slug}-report.pdf`);
  });

  // A single-page navigation changes nothing a screen reader notices on its own, so move focus
  // to the new page's heading. tabIndex={-1} makes it focusable without adding a tab stop.
  useEffect(() => {
    headingRef.current?.focus();
  }, [route]);

  return (
    <main className="app-shell saas-shell">
      <a className="skip-link" href="#workspace-main">Skip to main content</a>
      <aside className="sidebar saas-sidebar">
        <button className="brand brand-button" onClick={() => navigate('/dashboard')}>
          <div className="brand-mark"><Wheat size={22} aria-hidden="true" /></div>
          <div><p className="brand-kicker">ANNAPURNA AI</p><h1>Farm intelligence</h1></div>
        </button>
        <nav className="nav-list" aria-label="Workspace navigation">
          {NAV.map(([path, label, Icon]) => (
            <button
              key={path}
              className={`nav-item ${route === path ? 'active' : ''}`}
              onClick={() => navigate(path)}
              aria-current={route === path ? 'page' : undefined}
            >
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-profile">
          <div className="avatar" aria-hidden="true">
            {(farmer?.name || farm.farmerName || '?').charAt(0).toUpperCase()}
          </div>
          <div>
            <strong>{farmer?.name || farm.farmerName || 'Guest'}</strong>
            <span>{isSignedIn ? farmer.location || 'Signed in' : 'Not signed in'}</span>
          </div>
          {isSignedIn ? (
            <button className="icon-button" onClick={signOut} aria-label="Sign out" title="Sign out">
              <LogOut size={16} />
            </button>
          ) : (
            <button className="icon-button" onClick={() => navigate('/login')} aria-label="Sign in" title="Sign in">
              <UserRound size={16} />
            </button>
          )}
        </div>
      </aside>

      <section className="workspace saas-workspace">
        <header className="app-topbar">
          <div>
            <p className="eyebrow">Annapurna workspace</p>
            <h2 ref={headingRef} tabIndex={-1}>{meta0}</h2>
            <p>{meta1}</p>
          </div>
          <div className="topbar-actions">
            {!isSignedIn && (
              <button className="secondary-action" onClick={() => navigate('/register')}>
                <UserRound size={16} /> Save to an account
              </button>
            )}
            <button className="secondary-action" onClick={exportPdf.run} disabled={!topCrop || exportPdf.loading}>
              {exportPdf.loading ? <Spinner label="Building…" /> : <><Download size={16} /> PDF report</>}
            </button>
          </div>
        </header>

        <div className="page-content" id="workspace-main">
          <Notice error={exportPdf.error} onDismiss={exportPdf.clearError} />
          {notice && <Notice message={notice.text} tone={notice.tone} onDismiss={() => setNotice(null)} />}
          {stale && topCrop && route !== '/planner' && (
            <Notice
              tone="warn"
              message="Your field inputs changed after this analysis. The figures below describe the earlier inputs until you re-run it."
            />
          )}
          <ErrorBoundary key={route}>
            <Routes route={route} navigate={navigate} profileComplete={profileComplete} topCrop={topCrop} />
          </ErrorBoundary>
        </div>
      </section>
    </main>
  );
}

function Routes({ route, navigate, profileComplete, topCrop }) {
  if (route === '/planner') return <PlannerPage />;
  if (route === '/settings') return <SettingsPage />;
  if (route === '/records') return <RecordsPage navigate={navigate} />;

  // Every other screen describes a specific analysed farm, so it cannot render without one.
  if (!profileComplete) {
    return (
      <EmptyState
        icon={Sprout}
        title="Complete your farm profile first"
        text="Nothing is generated until you enter your own field details — no sample data is shown."
        action={<button className="primary-action" onClick={() => navigate('/planner')}>Open the planner</button>}
      />
    );
  }
  if (!topCrop) {
    return (
      <EmptyState
        icon={Database}
        title="Run your farm analysis"
        text="Your profile is complete. Generate an analysis to see recommendations, finance and advisory."
        action={<button className="primary-action" onClick={() => navigate('/planner')}>Open the planner</button>}
      />
    );
  }

  if (route === '/insights') return <InsightsPage />;
  if (route === '/finance') return <FinancePage navigate={navigate} />;
  if (route === '/disease') return <DiseasePage />;
  if (route === '/advisor') return <AdvisorPage />;
  return <DashboardPage navigate={navigate} />;
}

// --------------------------------------------------------------------------- planner

function PlannerPage() {
  const { farm, update, setKnownPrice, problems, profileComplete, recommendations, analysis, topCrop, runAnalysis, savePlan, cropNames, stale } = usePlanner();
  const { isSignedIn } = useAuth();
  const [showProblems, setShowProblems] = useState(false);

  const analyse = useAsyncAction(runAnalysis);
  const save = useAsyncAction(savePlan);
  const [saved, setSaved] = useState(false);

  const rule = (field) => FIELD_RULES[field];
  const problemFor = (field) => (showProblems ? problems[field] : undefined);

  return (
    <section className="main-grid page-section">
      <Panel title="Your field" eyebrow="Step 1 — describe the farm" icon={Search}>
        <div className="form-grid">
          <Field label={rule('farmerName').label} value={farm.farmerName} onChange={(v) => update('farmerName', v)} error={problemFor('farmerName')} autoComplete="name" />
          <Field label={rule('location').label} value={farm.location} onChange={(v) => update('location', v)} error={problemFor('location')} hint={rule('location').hint} autoComplete="address-level2" />
          <SelectField label={rule('language').label} value={farm.language} values={['', ...LANGUAGES]} onChange={(v) => update('language', v)} error={problemFor('language')} />
          <SelectField label={rule('season').label} value={farm.season} values={['', ...SEASONS]} onChange={(v) => update('season', v)} error={problemFor('season')} />
          <SelectField label={rule('previousCrop').label} value={farm.previousCrop} values={['', 'None', ...cropNames]} onChange={(v) => update('previousCrop', v)} error={problemFor('previousCrop')} hint="Last season's crop, so rotation can be scored." />
          <SelectField label={rule('soilType').label} value={farm.soilType} values={['', ...SOIL_TYPES]} onChange={(v) => update('soilType', v)} error={problemFor('soilType')} />
          <SelectField label={rule('irrigation').label} value={farm.irrigation} values={['', ...IRRIGATION]} onChange={(v) => update('irrigation', v)} error={problemFor('irrigation')} hint={IRRIGATION_HELP[farm.irrigation] || 'This decides whether a thirsty crop is possible at all.'} />
          <SelectField label={rule('marketPriority').label} value={farm.marketPriority} values={['', ...PRIORITIES]} onChange={(v) => update('marketPriority', v)} error={problemFor('marketPriority')} />
          <RangeInput label={rule('landSize').label} unit={rule('landSize').unit} field="landSize" min="0.5" max="50" step="0.5" value={farm.landSize} update={update} />
          <RangeInput label={rule('ph').label} field="ph" min="3" max="10" step="0.1" value={farm.ph} update={update} hint="Neutral is 6.5–7.5." />
          <RangeInput label={rule('nitrogen').label} unit={rule('nitrogen').unit} field="nitrogen" min="0" max="100" value={farm.nitrogen} update={update} />
          <RangeInput label={rule('phosphorus').label} unit={rule('phosphorus').unit} field="phosphorus" min="0" max="100" value={farm.phosphorus} update={update} />
          <RangeInput label={rule('potassium').label} unit={rule('potassium').unit} field="potassium" min="0" max="100" value={farm.potassium} update={update} />
          <RangeInput label={rule('temperature').label} unit={rule('temperature').unit} field="temperature" min="-5" max="50" value={farm.temperature} update={update} />
          <RangeInput label={rule('humidity').label} unit={rule('humidity').unit} field="humidity" min="0" max="100" value={farm.humidity} update={update} />
          <RangeInput label={rule('rainfall').label} unit={rule('rainfall').unit} field="rainfall" min="0" max="2500" step="10" value={farm.rainfall} update={update} hint={rule('rainfall').hint} />
          <RangeInput label={rule('budget').label} unit={rule('budget').unit} field="budget" min="0" max="500000" step="1000" value={farm.budget} update={update} />
        </div>
        {showProblems && Object.keys(problems).length > 0 && (
          <Notice message={`${Object.keys(problems).length} field${Object.keys(problems).length > 1 ? 's' : ''} still needed before analysis.`} tone="warn" />
        )}
      </Panel>

      <Panel title="Crops that fit" eyebrow="Step 2 — compare" icon={BarChart3}>
        <Notice error={analyse.error} onDismiss={analyse.clearError} />
        {stale && recommendations.length > 0 && (
          <Notice tone="warn" message="You changed a field since this analysis ran. Run it again to update the ranking." />
        )}
        {analysis?.ai_explanation && (
          <div className="gemini-insight">
            <div><Bot size={18} aria-hidden="true" /><strong>AI explanation</strong></div>
            <p>{analysis.ai_explanation.summary}</p>
            <span><b>Next:</b> {analysis.ai_explanation.priority_action}</span>
            <span><b>Watch:</b> {analysis.ai_explanation.risk_note}</span>
          </div>
        )}
        <div className="crop-list">
          {recommendations.length === 0 ? (
            <p className="panel-copy">Run the analysis to see which crops suit this field and which do not.</p>
          ) : (
            recommendations.map((crop) => (
              <CropCard
                crop={crop}
                key={crop.crop}
                knownPrice={farm.knownMarketPrices?.[crop.crop] ?? ''}
                onKnownPrice={(value) => setKnownPrice(crop.crop, value)}
              />
            ))
          )}
        </div>
        <div className="planner-actions">
          <button
            className="secondary-action"
            onClick={() => {
              setShowProblems(true);
              if (profileComplete) analyse.run();
            }}
            disabled={analyse.loading}
          >
            {analyse.loading ? <Spinner label="Analysing…" /> : <><Bot size={18} /> Run full analysis</>}
          </button>
          <button
            className="primary-action"
            onClick={async () => {
              const result = await save.run();
              if (result) setSaved(true);
            }}
            disabled={!topCrop || save.loading}
          >
            {save.loading ? <Spinner label="Saving…" /> : <><Save size={18} /> Save this plan</>}
          </button>
        </div>
        <Notice error={save.error} onDismiss={save.clearError} />
        {saved && (
          <Notice
            tone="ok"
            message={isSignedIn ? 'Saved to your account.' : 'Saved in this browser only. Create an account to keep it on other devices.'}
            onDismiss={() => setSaved(false)}
          />
        )}
      </Panel>
    </section>
  );
}

function CropCard({ crop, knownPrice, onKnownPrice }) {
  const economics = crop.economics;
  const usingOwnPrice = crop.priceBasis === 'the price you entered for your own mandi';
  return (
    <article className={`crop-card tone-${crop.verdict.replace(/\s+/g, '-')}`}>
      <div className="crop-head">
        <div className="crop-icon"><Sprout size={22} aria-hidden="true" /></div>
        <div>
          <h4>{crop.crop}</h4>
          <VerdictBadge verdict={crop.verdict} suitability={crop.suitability} />
        </div>
      </div>
      <div className="score-track" role="img" aria-label={`${crop.suitability} percent suitability`}>
        <span style={{ width: `${crop.suitability}%` }} />
      </div>

      {crop.limiters.length > 0 && (
        <ul className="crop-limiters">
          {crop.limiters.map((item) => <li key={item}>{item}</li>)}
        </ul>
      )}

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

      {onKnownPrice && (
        <label className="own-price">
          <span>
            Your mandi price
            <small>{usingOwnPrice ? 'Used for every figure below.' : 'Know a better rate? It replaces the one below.'}</small>
          </span>
          <span className="own-price-input">
            <i aria-hidden="true">₹</i>
            <input
              type="number"
              min="1"
              step="10"
              inputMode="numeric"
              value={knownPrice}
              placeholder={String(crop.marketPrice)}
              onChange={(event) => onKnownPrice(event.target.value)}
              aria-label={`Your own mandi price for ${crop.crop}, rupees per quintal`}
            />
            <em>/quintal</em>
          </span>
        </label>
      )}

      {economics && (
        <table className="crop-economics">
          <caption>
            Estimated for {crop.durationDays} days · price {inr(crop.marketPrice)}/quintal
            {' '}<b className={usingOwnPrice ? 'price-basis own' : 'price-basis'}>({crop.priceBasis})</b>
          </caption>
          <thead>
            <tr><th scope="col" /><th scope="col">Poor</th><th scope="col">Typical</th><th scope="col">Good</th></tr>
          </thead>
          <tbody>
            <tr><th scope="row">Yield (q)</th><td>{economics.expected_yield_quintal.low}</td><td>{economics.expected_yield_quintal.typical}</td><td>{economics.expected_yield_quintal.high}</td></tr>
            <tr><th scope="row">Cost</th><td>{compactInr(economics.estimated_cost_inr.high)}</td><td>{compactInr(economics.estimated_cost_inr.typical)}</td><td>{compactInr(economics.estimated_cost_inr.low)}</td></tr>
            <tr className="row-profit">
              <th scope="row">Profit</th>
              <td className={economics.expected_profit_inr.low < 0 ? 'negative' : ''}>{compactInr(economics.expected_profit_inr.low)}</td>
              <td>{compactInr(economics.expected_profit_inr.typical)}</td>
              <td>{compactInr(economics.expected_profit_inr.high)}</td>
            </tr>
          </tbody>
        </table>
      )}

      <div className="crop-footer">
        <span>{crop.water} water</span>
        <span>{crop.sustainabilityScore}/100 sustainability</span>
      </div>
    </article>
  );
}

// --------------------------------------------------------------------------- dashboard

function DashboardPage({ navigate }) {
  const { farm, topCrop, analysis } = usePlanner();
  const weather = analysis?.weather;
  return (
    <>
      <section className="dashboard-hero">
        <div className="dashboard-copy">
          <p className="eyebrow">{farm.season} season workspace</p>
          <h2>Your strongest match is {topCrop.crop}.</h2>
          <p className="subhead">
            Rated {topCrop.suitability}% — {topCrop.verdict}. Typical profit around {inr(topCrop.expectedProfit)},
            ranging {compactInr(topCrop.economics.expected_profit_inr.low)} to {compactInr(topCrop.economics.expected_profit_inr.high)}.
          </p>
          <div className="action-row">
            <button className="primary-action" onClick={() => navigate('/finance')}><Wallet size={18} /> Build the budget</button>
            <button className="secondary-action" onClick={() => navigate('/insights')}><BarChart3 size={18} /> See the evidence</button>
          </div>
        </div>
        <SuitabilityDial crop={topCrop} />
      </section>
      <section className="status-grid dashboard-metrics">
        <Metric icon={BarChart3} label="Top recommendation" value={`${topCrop.crop} · ${topCrop.suitability}%`} hint={topCrop.verdict} />
        <Metric icon={MapPin} label="Location" value={farm.location} hint={`${farm.irrigation} irrigation`} />
        <Metric
          icon={CloudSun}
          label="Weather"
          value={weather ? `${weather.temperature}°C · ${weather.humidity}%` : '—'}
          hint={weather?.live ? 'Live observation' : 'Your own entered values'}
        />
        <Metric icon={IndianRupee} label="Typical profit" value={inr(topCrop.expectedProfit)} hint={`at ${inr(topCrop.marketPrice)}/quintal`} />
      </section>
      <section className="quick-grid">
        <QuickAction icon={Sprout} title="Update the plan" text="Change conditions and re-rank." onClick={() => navigate('/planner')} />
        <QuickAction icon={Leaf} title="Read the advisory" text={`${topCrop.crop} guidance, rotation and sustainability.`} onClick={() => navigate('/insights')} />
        <QuickAction icon={Camera} title="Check crop health" text="Screen a leaf photo for visible symptoms." onClick={() => navigate('/disease')} />
      </section>
    </>
  );
}

function SuitabilityDial({ crop }) {
  return (
    <figure className="field-terminal">
      <div className="field-readout">
        <span>FIELD INTELLIGENCE</span>
        <strong>{crop.crop.toUpperCase()}</strong>
      </div>
      <div className="scene-window">
        <div className="suitability-dial" style={{ '--score': `${crop.suitability * 3.6}deg` }}>
          <div>
            <strong>{crop.suitability}%</strong>
            <span>{crop.verdict.toUpperCase()}</span>
          </div>
        </div>
      </div>
      <figcaption>
        <span>{crop.water} water need</span>
        <span>{crop.durationDays} days to harvest</span>
      </figcaption>
    </figure>
  );
}

function QuickAction({ icon: Icon, title, text, onClick }) {
  return (
    <button className="quick-action" onClick={onClick}>
      <span className="quick-icon"><Icon size={21} aria-hidden="true" /></span>
      <span><strong>{title}</strong><small>{text}</small></span>
      <span className="quick-arrow" aria-hidden="true">→</span>
    </button>
  );
}

// --------------------------------------------------------------------------- insights

function InsightsPage() {
  const { topCrop, analysis } = usePlanner();
  const weather = analysis?.weather;
  const soil = analysis?.soil;
  const market = analysis?.markets?.[0];

  return (
    <section className="module-grid page-section">
      <Panel title={`${topCrop.crop} advisory`} eyebrow="Decision support" icon={Leaf}>
        <div className="advice-list">
          <p>{topCrop.advisory}</p>
          <p><b>Rotation:</b> {topCrop.rotation}</p>
          <p><b>Sustainability:</b> {topCrop.sustainability}</p>
        </div>
        {topCrop.sources.length > 0 && (
          <details className="sources">
            <summary>Where these figures come from</summary>
            <ul>{topCrop.sources.map((source) => <li key={source}>{source}</li>)}</ul>
          </details>
        )}
      </Panel>

      <Panel title="Yield and money" eyebrow="Economics" icon={LineChart}>
        <div className="kpi-row">
          <Metric icon={Wheat} label="Typical yield" value={`${topCrop.expectedYield} quintal`} />
          <Metric icon={IndianRupee} label="Typical profit" value={inr(topCrop.expectedProfit)} hint={`${topCrop.profitMargin}% margin`} />
        </div>
        <BarChart
          description="Profit across a poor, typical and good season."
          items={[
            { label: 'Poor season', value: topCrop.economics.expected_profit_inr.low, tone: 'risk' },
            { label: 'Typical', value: topCrop.economics.expected_profit_inr.typical, tone: 'profit' },
            { label: 'Good season', value: topCrop.economics.expected_profit_inr.high, tone: 'revenue' },
          ]}
        />
        <p className="panel-copy">
          Priced at {inr(topCrop.marketPrice)} per quintal — {topCrop.priceBasis}. Plan against the
          poor-season figure, not the typical one.
        </p>
      </Panel>

      <Panel title="Weather" eyebrow={weather?.live ? weather.source : 'Not connected'} icon={CloudSun}>
        {weather?.live ? (
          <>
            <div className="kpi-row">
              <Metric icon={CloudSun} label="Temperature" value={`${weather.temperature}°C`} hint={weather.conditions} />
              <Metric icon={Droplets} label="Humidity" value={`${weather.humidity}%`} hint={`${weather.forecast_rain_mm_5d ?? 0} mm forecast (5 days)`} />
            </div>
            <StatusLine text={weather.alert} tone={weather.alert_severity === 'high' ? 'warn' : 'info'} />
            {weather.resolved_location && <p className="panel-copy">Resolved to {weather.resolved_location}.</p>}
          </>
        ) : (
          <>
            <StatusLine text="No live weather is connected — the values below are the ones you entered." tone="warn" />
            <div className="kpi-row">
              <Metric icon={CloudSun} label="Your temperature" value={`${weather?.temperature ?? '—'}°C`} />
              <Metric icon={Droplets} label="Your humidity" value={`${weather?.humidity ?? '—'}%`} />
            </div>
            <p className="panel-copy">{weather?.note}</p>
          </>
        )}
      </Panel>

      <Panel title="Soil" eyebrow={soil?.source || 'Run analysis'} icon={Database}>
        {soil ? (
          <>
            <div className="kpi-row">
              <Metric icon={Leaf} label="Health score" value={`${soil.health_score}/100`} hint={soil.classification} />
              <Metric icon={Activity} label="pH" value={`${soil.ph} (${soil.ph_classification})`} />
            </div>
            <ul className="nutrient-bands">
              {Object.entries(soil.nutrients || {}).map(([name, detail]) => (
                <li key={name}><span>{name}</span><strong>{detail.value}</strong><em>{detail.band}</em></li>
              ))}
            </ul>
            <div className="advice-list">{soil.actions.map((action) => <p key={action}>{action}</p>)}</div>
            <p className="panel-copy">{soil.note}</p>
          </>
        ) : (
          <p className="panel-copy">Run the analysis to interpret your pH and NPK readings.</p>
        )}
      </Panel>

      <Panel title="Mandi price" eyebrow={market?.source || 'Not connected'} icon={IndianRupee}>
        {market ? (
          <>
            <div className="kpi-row">
              <Metric icon={IndianRupee} label="Modal price" value={`${inr(market.modal_price_per_quintal)}/q`} hint={market.commodity} />
              <Metric
                icon={LineChart}
                label="Direction"
                value={market.trend_percent === null || market.trend_percent === undefined ? 'Not measurable yet' : `${market.trend} ${market.trend_percent > 0 ? '+' : ''}${market.trend_percent}%`}
              />
            </div>
            {market.market && <StatusLine text={`${market.market} · ${market.observed_at}`} tone="info" />}
            <p className="panel-copy">{market.note}</p>
          </>
        ) : (
          <p className="panel-copy">No market data for this crop and location.</p>
        )}
      </Panel>

      <Panel title="Sustainability" eyebrow="Water, rotation and soil" icon={Sprout}>
        <div className="kpi-row">
          <Metric icon={Leaf} label="Plan score" value={`${topCrop.sustainabilityScore}/100`} />
          <Metric icon={Droplets} label="Water demand" value={topCrop.water} />
        </div>
        <p className="panel-copy">{topCrop.sustainability}</p>
      </Panel>
    </section>
  );
}

// --------------------------------------------------------------------------- finance

function FinancePage({ navigate }) {
  const {
    topCrop, recommendations, financePlan, runFinance, actualExpenses, setActualExpenses,
    expenseCrop, manualPrice, setManualPrice,
  } = usePlanner();
  const [crop, setCrop] = useState(topCrop.crop);
  const [yieldCase, setYieldCase] = useState('typical');
  const build = useAsyncAction(runFinance);

  const summary = financePlan?.summary;

  return (
    <section className="finance-grid page-section">
      <Panel title="Season budget" eyebrow="Plan, track, compare" icon={Wallet}>
        <p className="panel-copy">
          Turn a recommendation into a working budget. These are planning estimates, not a loan,
          credit or investment recommendation.
        </p>
        <div className="form-grid two">
          <SelectField label="Crop" value={crop} values={recommendations.map((item) => item.crop)} onChange={setCrop} />
          {expenseCrop && expenseCrop !== crop && (
            <p className="field-hint cross-crop-note">
              Costs you tracked for {expenseCrop} stay with {expenseCrop}. This budget starts from
              the planned figures for {crop}.
            </p>
          )}
          <SelectField
            label="Budget against"
            value={yieldCase}
            values={['low', 'typical', 'high']}
            onChange={setYieldCase}
            hint="Budgeting against the low yield is the safe choice."
          />
          <Field
            label="Your verified mandi price (optional)"
            value={manualPrice}
            onChange={setManualPrice}
            type="number"
            min="1"
            hint={`Leave blank to use ${inr(topCrop.marketPrice)}/quintal — ${topCrop.priceBasis}.`}
          />
        </div>
        <div className="planner-actions">
          <button className="primary-action" onClick={() => build.run(crop, yieldCase)} disabled={build.loading}>
            {build.loading ? <Spinner label="Calculating…" /> : <><Wallet size={18} /> {financePlan ? 'Recalculate' : 'Create budget'}</>}
          </button>
          <button className="secondary-action" onClick={() => navigate('/planner')}><Sprout size={18} /> Change field inputs</button>
        </div>
        <Notice error={build.error} onDismiss={build.clearError} />
      </Panel>

      <Panel title="What this does not do" eyebrow="Farmer-first" icon={ShieldCheck}>
        <StatusLine text="No bank account, loan, credit score or payment data is ever requested" />
        <StatusLine text="Replace the planned costs with what you actually spend" />
        <StatusLine text="Confirm the selling price at your own mandi before you commit money" tone="warn" />
      </Panel>

      {financePlan && summary && (
        <>
          <Panel title={`${financePlan.crop} summary`} eyebrow={financePlan.planning_source} icon={IndianRupee}>
            <div className="kpi-row">
              <Metric icon={Wallet} label="Total cost" value={inr(summary.actual_cost)} hint={`peak cash needed ${inr(summary.peak_working_capital)}`} />
              <Metric icon={IndianRupee} label="Expected profit" value={inr(summary.expected_profit)} hint={`${summary.profit_margin}% margin`} />
            </div>
            <div className="insight-facts">
              <span><b>Revenue</b> {inr(summary.expected_revenue)}</span>
              <span><b>Break-even</b> {inr(summary.break_even_price_per_quintal)}/q</span>
              <span><b>Break-even yield</b> {summary.break_even_yield_quintal} q</span>
            </div>
            <StatusLine
              text={`Worst case (${summary.worst_case_name}): ${inr(summary.worst_case_profit)}`}
              tone={summary.worst_case_profit < 0 ? 'warn' : 'info'}
            />
            <p className={summary.working_capital_gap ? 'alert-line' : 'panel-copy'}>
              {summary.working_capital_gap
                ? `Your budget is short by ${inr(summary.working_capital_gap)}.`
                : `Budget remaining after costs: ${inr(summary.budget_remaining)}.`}
            </p>
            <p className="panel-copy">{financePlan.price_note}</p>
          </Panel>

          <Panel title="Risk comparison" eyebrow="Profit under different seasons" icon={Activity}>
            <BarChart
              description="Profit in each scenario, so the downside is visible before money is committed."
              items={financePlan.scenarios.map((scenario) => ({
                label: scenario.name,
                value: scenario.profit,
                tone: scenario.profit < 0 ? 'risk' : 'profit',
              }))}
            />
            <table className="scenario-table">
              <thead><tr><th scope="col">Scenario</th><th scope="col">Yield</th><th scope="col">Price</th><th scope="col">Profit</th></tr></thead>
              <tbody>
                {financePlan.scenarios.map((scenario) => (
                  <tr key={scenario.name} className={scenario.profit < 0 ? 'negative' : ''}>
                    <th scope="row">{scenario.name}<small>{scenario.basis}</small></th>
                    <td>{scenario.yield_quintal} q</td>
                    <td>{inr(scenario.price_per_quintal)}</td>
                    <td>{inr(scenario.profit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>

          <Panel title="Cost tracker" eyebrow="Planned against actual" icon={LineChart}>
            <div className="expense-list">
              {financePlan.expenses.map((expense) => (
                <div className="expense-row" key={expense.category}>
                  <label htmlFor={`exp-${expense.category}`}>
                    <b>{expense.category}</b>
                    <small>Planned {inr(expense.planned)}</small>
                  </label>
                  <input
                    id={`exp-${expense.category}`}
                    type="number"
                    min="0"
                    step="100"
                    value={
                      expenseCrop === financePlan.crop
                        ? actualExpenses[expense.category] ?? String(expense.actual)
                        : String(expense.actual)
                    }
                    onChange={(event) =>
                      setActualExpenses((current) => ({ ...current, [expense.category]: event.target.value }))
                    }
                  />
                  <em className={expense.variance > 0 ? 'over' : expense.variance < 0 ? 'under' : ''}>
                    {expense.variance > 0 ? '+' : ''}{expense.variance.toLocaleString('en-IN')}
                  </em>
                </div>
              ))}
            </div>
            <button className="secondary-action" onClick={() => build.run(crop, yieldCase)} disabled={build.loading}>
              {build.loading ? <Spinner label="Updating…" /> : 'Update with my actual costs'}
            </button>
          </Panel>

          <Panel title="Cash flow" eyebrow="When the money moves" icon={CalendarDays}>
            <div className="cashflow-list">
              {financePlan.cash_flow.map((stage) => (
                <div className="cashflow-row" key={stage.stage}>
                  <strong>{stage.stage}</strong>
                  <span>{stage.cash_in ? `Expected in ${inr(stage.cash_in)}` : `Spend ${inr(stage.cash_out)}`}</span>
                  <em>cumulative {inr(stage.cumulative_cash_out)}</em>
                </div>
              ))}
            </div>
            <p className="panel-copy">
              The number that decides whether you can fund this season is the peak cumulative
              spend — {inr(summary.peak_working_capital)} — not the season total.
            </p>
          </Panel>
        </>
      )}
    </section>
  );
}

// --------------------------------------------------------------------------- crop health

function DiseasePage() {
  const { topCrop, farm } = usePlanner();
  const [fileName, setFileName] = useState('');
  const [result, setResult] = useState(null);
  const inputRef = useRef(null);

  const screen = useAsyncAction(async (file) => {
    const body = new FormData();
    body.append('file', file);
    if (topCrop?.crop) body.append('crop', topCrop.crop);
    const data = await api.disease(body);
    setResult(data);
    return data;
  });

  async function onPick(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setResult(null);
    if (file.size > 8 * 1024 * 1024) {
      setFileName(file.name);
      screen.clearError();
      event.target.value = '';
      setResult({ tooLarge: true });
      return;
    }
    setFileName(file.name);
    await screen.run(file);
    event.target.value = '';
  }

  return (
    <section className="feature-layout page-section">
      <Panel title="Upload a leaf image" eyebrow="Visual screening" icon={Camera}>
        <label className="upload-box large-upload" htmlFor="disease-upload">
          <Upload size={28} aria-hidden="true" />
          <span>{fileName || 'Choose a clear, well-lit photo of one affected leaf'}</span>
          <input
            id="disease-upload"
            ref={inputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={onPick}
          />
        </label>
        <p className="field-hint">PNG, JPEG or WebP, up to 8 MB.</p>

        <Notice error={screen.error} onDismiss={screen.clearError} />
        {screen.loading && <Spinner label="Screening the image…" />}
        {result?.tooLarge && <Notice tone="warn" message="That image is larger than 8 MB. Please choose a smaller one." />}

        {result && !result.tooLarge && (
          <div className="diagnosis">
            <strong>{result.prediction}</strong>
            {Number.isFinite(result.confidence) && (
              <span className="confidence">{Math.round(result.confidence * 100)}% confidence</span>
            )}
            {result.observations?.length > 0 && (
              <ul>{result.observations.map((item) => <li key={item}>{item}</li>)}</ul>
            )}
            <p>{result.advisory}</p>
            <StatusLine text={result.disclaimer || 'A screening aid, not a diagnosis.'} tone="warn" />
          </div>
        )}
      </Panel>

      <Panel title="Context used" eyebrow="From your current plan" icon={Leaf}>
        <Metric icon={Wheat} label="Crop" value={topCrop.crop} />
        <StatusLine text={`${farm.location} · ${farm.season}`} tone="info" />
        <StatusLine text={`${farm.humidity}% humidity · ${farm.rainfall} mm seasonal rainfall`} tone="info" />
        <StatusLine text="Always confirm with a qualified agriculture expert before any treatment" tone="warn" />
      </Panel>
    </section>
  );
}

// --------------------------------------------------------------------------- advisor

function AdvisorPage() {
  const { farm, topCrop, financePlan } = usePlanner();
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([
    { by: 'Annapurna AI', text: `Ask anything about your ${topCrop.crop} plan — irrigation, fertiliser, timing or budget.` },
  ]);
  const listRef = useRef(null);

  const ask = useAsyncAction(async (text) => {
    const payload = {
      question: text,
      crop: topCrop.crop,
      farm: toApiFarm(farm),
      finance: financePlan
        ? {
            crop: financePlan.crop,
            planning_source: financePlan.planning_source,
            actual_cost: financePlan.summary.actual_cost,
            expected_revenue: financePlan.summary.expected_revenue,
            expected_profit: financePlan.summary.expected_profit,
            break_even_price_per_quintal: financePlan.summary.break_even_price_per_quintal,
            working_capital_gap: financePlan.summary.working_capital_gap,
          }
        : null,
    };
    const data = await api.chat(payload);
    setMessages((items) => [...items, { by: 'Annapurna AI', text: data.answer, provider: data.provider }]);
    return data;
  });

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, ask.loading]);

  async function submit(event) {
    event.preventDefault();
    const text = question.trim();
    if (!text || ask.loading) return;
    setMessages((items) => [...items, { by: 'You', text }]);
    setQuestion('');
    await ask.run(text);
  }

  return (
    <section className="advisor-layout page-section">
      <Panel title="Conversation" eyebrow={`Advisor · ${farm.language}`} icon={MessageSquareText}>
        <div className="chat-window expanded-chat" ref={listRef} role="log" aria-live="polite" aria-label="Advisor conversation">
          {messages.map((item, index) => (
            <div className={item.by === 'You' ? 'chat-bubble' : 'chat-bubble ai'} key={`${item.by}-${index}`}>
              <strong>{item.by}</strong>
              <span>{item.text}</span>
              {item.provider === 'local_fallback' && <em className="chat-note">Offline template — the AI advisor is not configured.</em>}
            </div>
          ))}
          {ask.loading && <div className="chat-bubble ai"><Spinner label="Thinking…" /></div>}
        </div>
        <Notice error={ask.error} onDismiss={ask.clearError} />
        <form className="chat-input" onSubmit={submit}>
          <label className="sr-only" htmlFor="advisor-question">Your question</label>
          <input
            id="advisor-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about irrigation, fertiliser, disease or budget"
            disabled={ask.loading}
            maxLength={1200}
          />
          <button type="submit" disabled={!question.trim() || ask.loading}>
            <Bot size={18} aria-hidden="true" /> Ask
          </button>
        </form>
      </Panel>

      <Panel title="What the advisor can see" eyebrow="Your current context" icon={Database}>
        <StatusLine text={`Crop: ${topCrop.crop} (${topCrop.suitability}% — ${topCrop.verdict})`} />
        <StatusLine text={`Soil: ${farm.soilType}, pH ${farm.ph}`} />
        <StatusLine text={`Season: ${farm.season} · ${farm.irrigation} irrigation`} />
        <StatusLine
          text={financePlan ? `Season budget for ${financePlan.crop} is linked` : 'No season budget linked yet'}
          tone={financePlan ? 'ok' : 'info'}
        />
      </Panel>
    </section>
  );
}

// --------------------------------------------------------------------------- records

function RecordsPage({ navigate }) {
  const { plans, removePlan, applyFarm } = usePlanner();
  const { isSignedIn } = useAuth();
  const remove = useAsyncAction(removePlan);
  const load = useAsyncAction(async (id) => {
    const plan = await api.getPlan(id);
    applyFarm(plan.farm_snapshot);
    navigate('/planner');
  });

  if (!plans.length) {
    return (
      <EmptyState
        icon={History}
        title="No saved plans yet"
        text="Run an analysis in the planner and save it to build your record."
        action={<button className="primary-action" onClick={() => navigate('/planner')}>Open the planner</button>}
      />
    );
  }

  return (
    <section className="page-section records-page">
      <Panel title="Saved plans" eyebrow={isSignedIn ? 'Stored in your account' : 'Stored in this browser only'} icon={History}>
        {!isSignedIn && (
          <Notice
            tone="warn"
            message="These plans live in this browser. Clearing site data deletes them. Create an account to keep them."
          />
        )}
        <Notice error={remove.error} onDismiss={remove.clearError} />
        <Notice error={load.error} onDismiss={load.clearError} />
        <ul className="history-list records-list">
          {plans.map((item) => (
            <li className="history-item" key={item.id}>
              <div>
                <strong>{item.crop}</strong>
                <span>
                  {item.location} · {item.season} · {new Date(item.created_at).toLocaleDateString('en-IN')}
                </span>
                {item.note && <small>{item.note}</small>}
              </div>
              <p>{item.suitability}% · {inr(item.expected_profit)}</p>
              <div className="record-actions">
                {!item.local && (
                  <button className="secondary-action small" onClick={() => load.run(item.id)} disabled={load.loading}>
                    Reopen
                  </button>
                )}
                <button
                  className="icon-button danger"
                  onClick={() => remove.run(item.id)}
                  disabled={remove.loading}
                  aria-label={`Delete the ${item.crop} plan`}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      </Panel>
    </section>
  );
}

// --------------------------------------------------------------------------- settings

function SettingsPage() {
  const { integrations, clearLocalData } = usePlanner();
  const { isSignedIn, farmer, signOut } = useAuth();
  const [health, setHealth] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.health().then(
      (data) => !cancelled && setHealth(data),
      () => !cancelled && setHealth(null)
    );
    return () => {
      cancelled = true;
    };
  }, []);

  const deleteAccount = useAsyncAction(async () => {
    await api.deleteAccount();
    await signOut();
  });

  return (
    <section className="module-grid page-section">
      <Panel title="Connected services" eyebrow="What is actually working" icon={Database}>
        {integrations ? (
          <ul className="integration-list">
            {Object.entries(integrations).map(([key, detail]) => (
              <li key={key} className={`integration ${detail.status}`}>
                <div>
                  <strong>{detail.provider}</strong>
                  <small>{detail.effect}</small>
                </div>
                <span className={`badge badge-${detail.status === 'connected' ? 'ok' : detail.status === 'not_implemented' ? 'off' : 'warn'}`}>
                  {detail.status.replace(/_/g, ' ')}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="panel-copy">Could not reach the server to list integrations.</p>
        )}
      </Panel>

      <Panel title="Server" eyebrow="Health" icon={Activity}>
        {health ? (
          <>
            <StatusLine text={`Version ${health.version} · ${health.environment}`} />
            <StatusLine text={`Crop model: ${health.ml_model.replace(/_/g, ' ')}`} tone={health.ml_model === 'available' ? 'ok' : 'info'} />
            <StatusLine text={`Database: ${health.database}`} />
            <StatusLine text={`Rate limiter: ${health.rate_limiter}`} tone="info" />
          </>
        ) : (
          <StatusLine text="The server is not reachable from this browser." tone="warn" />
        )}
      </Panel>

      <Panel title="Your data" eyebrow={isSignedIn ? 'Account' : 'This browser'} icon={ShieldCheck}>
        {isSignedIn ? (
          <>
            <StatusLine text={`Signed in as ${farmer.name} (${farmer.phone})`} />
            <StatusLine text="Saved plans and budgets are stored on the server against your account" />
            <div className="admin-actions">
              <button className="secondary-action" onClick={signOut}><LogOut size={16} /> Sign out</button>
              {confirmDelete ? (
                <>
                  <button className="danger-action" onClick={deleteAccount.run} disabled={deleteAccount.loading}>
                    {deleteAccount.loading ? <Spinner label="Deleting…" /> : 'Yes, delete everything'}
                  </button>
                  <button className="secondary-action" onClick={() => setConfirmDelete(false)}>Cancel</button>
                </>
              ) : (
                <button className="secondary-action danger" onClick={() => setConfirmDelete(true)}>
                  <Trash2 size={16} /> Delete my account and all data
                </button>
              )}
            </div>
            <Notice error={deleteAccount.error} onDismiss={deleteAccount.clearError} />
          </>
        ) : (
          <>
            <StatusLine text="You are not signed in. Plans are stored only in this browser." tone="warn" />
            <StatusLine text="No account, bank, land or payment data is collected" />
          </>
        )}
        <div className="admin-actions">
          <button className="secondary-action" onClick={clearLocalData}>
            <Trash2 size={16} /> Clear planner data from this browser
          </button>
        </div>
      </Panel>

      <Panel title="How to read the numbers" eyebrow="Limits of this tool" icon={ShieldCheck}>
        <StatusLine text="Reference prices are announced support prices, not what a buyer will pay" tone="info" />
        <StatusLine text="Yields and costs are regional ranges, not a forecast for your field" tone="info" />
        <StatusLine text="Image screening is a screening aid and never a diagnosis" tone="warn" />
        <StatusLine text="Confirm any costly or health-related decision with a local agriculture officer" tone="warn" />
      </Panel>
    </section>
  );
}
