import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { ApiError, api, storage } from './api.js';
import { FALLBACK_CROPS, emptyFarm, fromApiFarm, isFarmComplete, normalizeRecommendation, toApiFarm, validateFarm } from './farm.js';
import { useAuth } from './auth.jsx';

const FARM_KEY = 'annapurna-farm-v2';
const FINANCE_KEY = 'annapurna-finance-v2';
const GUEST_PLANS_KEY = 'annapurna-guest-plans-v2';

// Changing these cannot alter the ranking, so they must not mark the analysis stale.
const COSMETIC_FIELDS = new Set(['farmerName', 'language']);

const PlannerContext = createContext(null);

export function PlannerProvider({ children }) {
  const { isSignedIn, farmer } = useAuth();

  const [farm, setFarm] = useState(() => ({ ...emptyFarm, ...storage.json(FARM_KEY, {}) }));
  const [analysis, setAnalysis] = useState(null);
  const [financePlan, setFinancePlan] = useState(null);
  const [actualExpenses, setActualExpenses] = useState(() => storage.json(FINANCE_KEY, {}).actualExpenses || {});
  const [manualPrice, setManualPrice] = useState(() => storage.json(FINANCE_KEY, {}).manualPrice || '');
  const [plans, setPlans] = useState([]);
  const [integrations, setIntegrations] = useState(null);
  const [cropNames, setCropNames] = useState(FALLBACK_CROPS);
  const [stale, setStale] = useState(false);
  const [notice, setNotice] = useState(null);

  // One in-flight analysis at a time: a second click must cancel the first, not race it.
  const analysisAbort = useRef(null);

  const problems = useMemo(() => validateFarm(farm), [farm]);
  const profileComplete = useMemo(() => isFarmComplete(farm), [farm]);
  const recommendations = useMemo(
    () => (analysis?.recommendations || []).map(normalizeRecommendation).filter(Boolean),
    [analysis]
  );
  const topCrop = recommendations[0] || null;

  useEffect(() => {
    storage.set(FARM_KEY, JSON.stringify(farm));
  }, [farm]);

  useEffect(() => {
    storage.set(FINANCE_KEY, JSON.stringify({ actualExpenses, manualPrice }));
  }, [actualExpenses, manualPrice]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [status, catalog] = await Promise.allSettled([api.integrations(), api.crops()]);
      if (cancelled) return;
      if (status.status === 'fulfilled') setIntegrations(status.value);
      if (catalog.status === 'fulfilled') {
        const names = (catalog.value.crops || []).map((item) => item.crop).filter(Boolean);
        if (names.length) setCropNames(names);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Prefill the planner from the account the first time a signed-in farmer has nothing entered.
  useEffect(() => {
    if (!farmer) return;
    setFarm((current) => ({
      ...current,
      farmerName: current.farmerName || farmer.name || '',
      location: current.location || farmer.location || '',
      language: current.language || farmer.language || '',
    }));
  }, [farmer]);

  const loadPlans = useCallback(async () => {
    if (!isSignedIn) {
      setPlans(storage.json(GUEST_PLANS_KEY, []));
      return;
    }
    try {
      const page = await api.listPlans(50, 0);
      setPlans(page.items || []);
    } catch (error) {
      if (error instanceof ApiError && !error.isAuth) setNotice({ tone: 'warn', text: error.message });
    }
  }, [isSignedIn]);

  useEffect(() => {
    loadPlans();
  }, [loadPlans]);

  const update = useCallback((field, value) => {
    setFarm((current) => {
      if (current[field] === value) return current;
      // Every keystroke used to delete the analysis outright, so adjusting one slider wiped the
      // results the farmer was reading. The analysis is kept and flagged as stale instead, and
      // only a change that can actually alter the ranking raises the flag.
      if (!COSMETIC_FIELDS.has(field)) setStale(true);
      return { ...current, [field]: value };
    });
  }, []);

  const applyFarm = useCallback((payload) => {
    setFarm(fromApiFarm(payload));
    setAnalysis(null);
    setFinancePlan(null);
    setStale(false);
  }, []);

  const runAnalysis = useCallback(async () => {
    analysisAbort.current?.abort();
    const controller = new AbortController();
    analysisAbort.current = controller;
    const data = await api.analysis(toApiFarm(farm), controller.signal);
    setAnalysis(data);
    setFinancePlan(null);
    setStale(false);
    return data;
  }, [farm]);

  const runFinance = useCallback(
    async (crop, yieldCase = 'typical') => {
      const payload = {
        farm: toApiFarm(farm),
        crop,
        actual_expenses: Object.fromEntries(
          Object.entries(actualExpenses)
            .map(([key, value]) => [key, Number(value)])
            .filter(([, value]) => Number.isFinite(value) && value >= 0)
        ),
        yield_case: yieldCase,
      };
      const trimmed = String(manualPrice).trim();
      if (trimmed !== '' && Number.isFinite(Number(trimmed))) {
        payload.market_price_per_quintal = Number(trimmed);
      }
      const plan = await api.seasonPlan(payload);
      setFinancePlan(plan);
      // Adopt whatever the server actually budgeted, so the tracker and the plan never diverge.
      setActualExpenses(Object.fromEntries(plan.expenses.map((item) => [item.category, String(item.actual)])));
      if (isSignedIn) {
        try {
          await api.saveFinancePlan({
            farm: toApiFarm(farm),
            plan,
            actual_expenses: payload.actual_expenses,
            market_price_per_quintal: payload.market_price_per_quintal ?? null,
          });
        } catch {
          setNotice({ tone: 'warn', text: 'Plan calculated, but it could not be saved to your account.' });
        }
      }
      return plan;
    },
    [farm, actualExpenses, manualPrice, isSignedIn]
  );

  const savePlan = useCallback(async () => {
    if (!topCrop) return null;
    const body = {
      farm: toApiFarm(farm),
      recommendation: analysis.recommendations[0],
      weather: analysis.weather ?? null,
      soil: analysis.soil ?? null,
      market: analysis.markets?.[0] ?? null,
      ai_explanation: analysis.ai_explanation ?? null,
    };
    if (isSignedIn) {
      const saved = await api.savePlan(body);
      await loadPlans();
      return saved;
    }
    // Signed out, the plan is kept in this browser only, and the UI says so.
    const record = {
      id: `local-${Date.now()}`,
      crop: topCrop.crop,
      suitability: topCrop.suitability,
      expected_profit: topCrop.expectedProfit,
      location: farm.location,
      season: farm.season,
      created_at: new Date().toISOString(),
      local: true,
    };
    const next = [record, ...storage.json(GUEST_PLANS_KEY, [])].slice(0, 20);
    storage.set(GUEST_PLANS_KEY, JSON.stringify(next));
    setPlans(next);
    return record;
  }, [topCrop, farm, analysis, isSignedIn, loadPlans]);

  const removePlan = useCallback(
    async (id) => {
      if (String(id).startsWith('local-')) {
        const next = storage.json(GUEST_PLANS_KEY, []).filter((item) => item.id !== id);
        storage.set(GUEST_PLANS_KEY, JSON.stringify(next));
        setPlans(next);
        return;
      }
      await api.deletePlan(id);
      await loadPlans();
    },
    [loadPlans]
  );

  const clearLocalData = useCallback(() => {
    storage.remove(FARM_KEY);
    storage.remove(FINANCE_KEY);
    storage.remove(GUEST_PLANS_KEY);
    setFarm({ ...emptyFarm });
    setAnalysis(null);
    setFinancePlan(null);
    setActualExpenses({});
    setManualPrice('');
    setPlans([]);
    setStale(false);
    setNotice({ tone: 'ok', text: 'Local planner data cleared from this browser.' });
  }, []);

  useEffect(() => () => analysisAbort.current?.abort(), []);

  const value = useMemo(
    () => ({
      farm, update, applyFarm, problems, profileComplete, stale,
      analysis, recommendations, topCrop, runAnalysis,
      financePlan, runFinance, actualExpenses, setActualExpenses, manualPrice, setManualPrice,
      plans, savePlan, removePlan, loadPlans,
      integrations, cropNames, notice, setNotice, clearLocalData,
    }),
    [
      farm, update, applyFarm, problems, profileComplete, stale, analysis, recommendations, topCrop,
      runAnalysis, financePlan, runFinance, actualExpenses, manualPrice, plans, savePlan,
      removePlan, loadPlans, integrations, cropNames, notice, clearLocalData,
    ]
  );

  return <PlannerContext.Provider value={value}>{children}</PlannerContext.Provider>;
}

export function usePlanner() {
  const value = useContext(PlannerContext);
  if (!value) throw new Error('usePlanner must be used inside PlannerProvider');
  return value;
}
