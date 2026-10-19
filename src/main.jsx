import React, { useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { AuthProvider, useAuth } from './auth.jsx';
import { PlannerProvider } from './planner-state.jsx';
import { ErrorBoundary, Spinner } from './components.jsx';
import { MarketingSite } from './marketing.jsx';
import { AccountPage } from './account.jsx';
import { Workspace } from './workspace.jsx';
import './styles.css';

const PUBLIC_ROUTES = new Set(['/', '/about']);
const ACCOUNT_ROUTES = new Set(['/login', '/register']);
const WORKSPACE_ROUTES = new Set([
  '/dashboard', '/planner', '/insights', '/finance', '/disease', '/advisor', '/records', '/settings',
]);

function normalise(pathname) {
  // Tolerate a trailing slash and an unknown path rather than rendering a blank screen.
  const path = (pathname || '/').replace(/\/+$/, '') || '/';
  if (PUBLIC_ROUTES.has(path) || ACCOUNT_ROUTES.has(path) || WORKSPACE_ROUTES.has(path)) return path;
  return '/not-found';
}

function useRoute() {
  const [route, setRoute] = useState(() => normalise(window.location.pathname));

  useEffect(() => {
    const onPop = () => setRoute(normalise(window.location.pathname));
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const navigate = useCallback((path) => {
    const next = normalise(path);
    if (window.location.pathname !== path) window.history.pushState({}, '', path);
    setRoute(next);
    // The workspace scrolls inside `.page-content`, not the window, so scrolling only the window
    // left a new page showing the previous page's scroll offset.
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const behavior = reduced ? 'auto' : 'smooth';
    window.scrollTo({ top: 0, behavior });
    document.querySelector('.page-content')?.scrollTo({ top: 0, behavior });
  }, []);

  return [route, navigate];
}

function NotFound({ navigate }) {
  return (
    <main className="marketing-site">
      <section className="about-hero">
        <p className="marketing-kicker">404</p>
        <h1>That page does not exist.</h1>
        <p>The link may be out of date. The planner is where most work starts.</p>
        <div className="landing-actions">
          <button className="marketing-primary" onClick={() => navigate('/planner')}>Open the planner</button>
          <button className="marketing-secondary" onClick={() => navigate('/')}>Back to home</button>
        </div>
      </section>
    </main>
  );
}

function Shell() {
  const [route, navigate] = useRoute();
  const { isLoading } = useAuth();

  // Keep the document title in step with the route, for history and screen readers.
  useEffect(() => {
    const titles = {
      '/': 'Annapurna AI — Farm intelligence',
      '/about': 'About — Annapurna AI',
      '/login': 'Sign in — Annapurna AI',
      '/register': 'Create account — Annapurna AI',
      '/not-found': 'Page not found — Annapurna AI',
    };
    document.title = titles[route] || `${route.slice(1).replace(/^\w/, (c) => c.toUpperCase())} — Annapurna AI`;
  }, [route]);

  if (isLoading) {
    return (
      <main className="boot-screen">
        <Spinner label="Loading your workspace…" />
      </main>
    );
  }

  if (route === '/not-found') return <NotFound navigate={navigate} />;
  if (PUBLIC_ROUTES.has(route)) return <MarketingSite page={route === '/about' ? 'about' : 'home'} navigate={navigate} />;
  if (ACCOUNT_ROUTES.has(route)) return <AccountPage mode={route === '/register' ? 'register' : 'login'} navigate={navigate} />;

  return (
    <PlannerProvider>
      <Workspace route={route} navigate={navigate} />
    </PlannerProvider>
  );
}

const container = document.getElementById('root');

// Vite re-executes this module on every hot update. Calling createRoot again on a container that
// already has one makes React warn, then tear down the old tree mid-commit, which surfaces as a
// cascade of "removeChild" and missing-context errors that look like application bugs. Keeping
// the root on the container means a hot update re-renders instead of remounting.
const root = container.__annapurnaRoot ?? createRoot(container);
container.__annapurnaRoot = root;

root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>
);

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}
