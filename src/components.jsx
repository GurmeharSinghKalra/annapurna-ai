import React, { useEffect, useId, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, Info, Loader2, X } from 'lucide-react';

export function Panel({ title, eyebrow, icon: Icon, id, className = '', actions, children }) {
  return (
    <section className={`panel ${className}`.trim()} id={id}>
      <div className="panel-heading">
        <div>
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          <h3>{title}</h3>
        </div>
        {actions || (Icon ? <Icon size={20} aria-hidden="true" /> : null)}
      </div>
      {children}
    </section>
  );
}

export function Metric({ icon: Icon, label, value, hint }) {
  return (
    <div className="metric">
      {Icon && <Icon size={18} aria-hidden="true" />}
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        {hint && <small>{hint}</small>}
      </div>
    </div>
  );
}

export function StatusLine({ text, tone = 'ok' }) {
  const Icon = tone === 'warn' ? AlertTriangle : tone === 'info' ? Info : CheckCircle2;
  return (
    <div className={`status-line ${tone}`}>
      <Icon size={18} aria-hidden="true" />
      <span>{text}</span>
    </div>
  );
}

/** A banner that distinguishes a server message from a connection failure. */
export function Notice({ error, message, tone = 'error', onDismiss }) {
  if (!error && !message) return null;
  const text = message || error.message;
  const actualTone = error?.isOffline ? 'warn' : tone;
  return (
    <div className={`notice notice-${actualTone}`} role={actualTone === 'error' ? 'alert' : 'status'}>
      <AlertTriangle size={17} aria-hidden="true" />
      <div>
        <p>{text}</p>
        {error?.requestId && <small>Reference: {error.requestId}</small>}
        {error?.retryAfter ? <small>Try again in about {error.retryAfter} seconds.</small> : null}
      </div>
      {onDismiss && (
        <button type="button" className="notice-dismiss" onClick={onDismiss} aria-label="Dismiss message">
          <X size={15} />
        </button>
      )}
    </div>
  );
}

export function Spinner({ label = 'Loading' }) {
  return (
    <span className="spinner" role="status" aria-live="polite">
      <Loader2 size={16} className="spin" aria-hidden="true" /> {label}
    </span>
  );
}

export function EmptyState({ icon: Icon, title, text, action }) {
  return (
    <section className="page-section empty-records">
      {Icon && <Icon size={30} aria-hidden="true" />}
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </section>
  );
}

export function Field({ label, value, onChange, error, hint, type = 'text', ...rest }) {
  const id = useId();
  return (
    <label htmlFor={id} className={error ? 'field has-error' : 'field'}>
      <span className="field-label">{label}</span>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={error || hint ? `${id}-help` : undefined}
        {...rest}
      />
      {(error || hint) && (
        <small id={`${id}-help`} className={error ? 'field-error' : 'field-hint'}>
          {error || hint}
        </small>
      )}
    </label>
  );
}

export function SelectField({ label, value, values, onChange, hint, error }) {
  const id = useId();
  return (
    <label htmlFor={id} className={error ? 'field has-error' : 'field'}>
      <span className="field-label">{label}</span>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={error || hint ? `${id}-help` : undefined}
      >
        {values.map((item) => (
          <option key={item || 'empty'} value={item}>
            {item || `Select ${label.toLowerCase()}`}
          </option>
        ))}
      </select>
      {(error || hint) && (
        <small id={`${id}-help`} className={error ? 'field-error' : 'field-hint'}>
          {error || hint}
        </small>
      )}
    </label>
  );
}

/**
 * A slider paired with a number input. The slider alone was not operable for anyone who needed an
 * exact value, and it had no accessible name beyond its visual label.
 */
export function RangeInput({ label, field, min, max, step = '1', value, update, unit, hint }) {
  const id = useId();
  return (
    <div className="field range-field">
      <label htmlFor={id} className="range-label">
        <span className="field-label">
          {label}
          {unit ? <em> ({unit})</em> : null}
        </span>
      </label>
      <div className="range-row">
        <input
          id={id}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value === '' ? min : value}
          onChange={(event) => update(field, event.target.value)}
          aria-describedby={hint ? `${id}-help` : undefined}
        />
        <input
          type="number"
          className="range-number"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(event) => update(field, event.target.value)}
          aria-label={`${label} exact value`}
        />
      </div>
      {hint && (
        <small id={`${id}-help`} className="field-hint">
          {hint}
        </small>
      )}
    </div>
  );
}

/** Number(null) and Number('') are both 0, so a missing amount would render as a confident
 *  "₹0". In a finance screen that is a wrong number, not a blank. */
function amount(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function inr(value) {
  const number = amount(value);
  if (number === null) return '—';
  return `₹${Math.round(number).toLocaleString('en-IN')}`;
}

export function compactInr(value) {
  const number = amount(value);
  if (number === null) return '—';
  const absolute = Math.abs(number);
  if (absolute >= 10000000) return `₹${(number / 10000000).toFixed(1)}Cr`;
  if (absolute >= 100000) return `₹${(number / 100000).toFixed(1)}L`;
  if (absolute >= 1000) return `₹${Math.round(number / 1000)}k`;
  return `₹${Math.round(number)}`;
}

const VERDICT_TONE = {
  'strong match': 'strong',
  'good match': 'good',
  'workable with care': 'fair',
  marginal: 'poor',
  'not recommended': 'bad',
};

export function VerdictBadge({ verdict, suitability }) {
  return (
    <span className={`verdict verdict-${VERDICT_TONE[verdict] || 'fair'}`}>
      {suitability}% · {verdict}
    </span>
  );
}

/** Horizontal bar chart that handles negative values and an all-zero series. */
export function BarChart({ items, description }) {
  const points = items.filter((item) => amount(item.value) !== null);
  if (!points.length) return <p className="panel-copy">Not enough data to chart yet.</p>;

  const values = points.map((item) => Number(item.value));
  const maxValue = Math.max(0, ...values);
  const minValue = Math.min(0, ...values);
  const span = maxValue - minValue || 1;

  return (
    <figure className="bar-chart">
      <ul>
        {points.map((item) => {
          const value = Number(item.value);
          const width = (Math.abs(value) / span) * 100;
          const zeroOffset = (Math.abs(minValue) / span) * 100;
          return (
            <li key={item.label}>
              <span className="bar-label">{item.label}</span>
              <span className="bar-track">
                <span
                  className={`bar-fill ${item.tone || 'profit'}${value < 0 ? ' negative' : ''}`}
                  style={{
                    width: `${Math.max(width, 0.6)}%`,
                    marginLeft: value < 0 ? `${zeroOffset - width}%` : `${zeroOffset}%`,
                  }}
                />
              </span>
              <span className={value < 0 ? 'bar-value negative' : 'bar-value'}>{compactInr(value)}</span>
            </li>
          );
        })}
      </ul>
      <figcaption>{description}</figcaption>
    </figure>
  );
}

/** Keeps one render failure from blanking the whole application. */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('Annapurna render error', error, info);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <section className="page-section empty-records">
        <AlertTriangle size={30} aria-hidden="true" />
        <h3>This screen could not be displayed</h3>
        <p>The rest of the application still works. Reload the page to try again.</p>
        <button type="button" className="primary-action" onClick={() => window.location.reload()}>
          Reload
        </button>
      </section>
    );
  }
}

/** Runs an async action, exposing loading state and a typed error, with unmount safety. */
export function useAsyncAction(action) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const mounted = useRef(true);

  // StrictMode mounts, cleans up, then mounts again. Setting the flag only in the cleanup would
  // leave it false for the rest of the session, so every result would be discarded and a button
  // would sit on "loading" forever. Re-arm it on each mount.
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const run = async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await action(...args);
      return result;
    } catch (caught) {
      if (caught?.name !== 'AbortError' && mounted.current) setError(caught);
      return undefined;
    } finally {
      if (mounted.current) setLoading(false);
    }
  };

  return { run, loading, error, clearError: () => setError(null) };
}
