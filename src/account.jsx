import React, { useState } from 'react';
import { ShieldCheck, Sprout, Wheat } from 'lucide-react';
import { useAuth } from './auth.jsx';
import { Field, Notice, SelectField, Spinner, useAsyncAction } from './components.jsx';
import { LANGUAGES } from './farm.js';

/**
 * Sign in and registration. Both are optional: the planner is fully usable signed out, and this
 * screen says so rather than presenting a wall before any value is delivered.
 */
export function AccountPage({ mode, navigate }) {
  const { signIn, signUp } = useAuth();
  const isRegister = mode === 'register';
  const [form, setForm] = useState({
    name: '', phone: '', password: '', email: '', language: 'English', location: '',
  });
  const [fieldErrors, setFieldErrors] = useState({});

  const submit = useAsyncAction(async () => {
    setFieldErrors({});
    if (isRegister) {
      const problems = {};
      if (!form.name.trim()) problems.name = 'Enter your name';
      if (!/^(\+?91[\s-]?|0)?[6-9]\d{9}$/.test(form.phone.replace(/[\s-]/g, ''))) {
        problems.phone = 'Enter a valid 10-digit Indian mobile number';
      }
      if (form.password.length < 8) problems.password = 'Use at least 8 characters';
      else if (/^\d+$/.test(form.password)) problems.password = 'Do not use only digits';
      if (Object.keys(problems).length) {
        setFieldErrors(problems);
        return undefined;
      }
      await signUp({
        name: form.name,
        phone: form.phone,
        password: form.password,
        email: form.email.trim() || null,
        language: form.language,
        location: form.location,
      });
    } else {
      await signIn({ phone: form.phone, password: form.password });
    }
    navigate('/dashboard');
    return true;
  });

  const update = (field) => (value) => setForm((current) => ({ ...current, [field]: value }));
  const errorFields = submit.error?.fields || {};

  return (
    <main className="auth-shell">
      <section className="auth-story">
        <div className="auth-brand">
          <span className="brand-mark"><Wheat size={23} aria-hidden="true" /></span>
          <span><small>ANNAPURNA AI</small><strong>Farm intelligence</strong></span>
        </div>
        <div className="auth-story-copy">
          <p className="eyebrow">An account is optional</p>
          <h1>{isRegister ? 'Keep your plans beyond this browser.' : 'Welcome back.'}</h1>
          <p>
            Everything in the planner works without signing in. An account stores your saved plans,
            season budgets and farm profiles on the server, so they survive a cleared browser and
            follow you to another phone.
          </p>
        </div>
        <div className="auth-trust">
          <ShieldCheck size={19} aria-hidden="true" />
          <span>We ask for a phone number and password only. No bank, land or payment details, ever.</span>
        </div>
        <button className="auth-skip" onClick={() => navigate('/planner')}>
          <Sprout size={17} aria-hidden="true" /> Continue without an account
        </button>
      </section>

      <section className="auth-form-side">
        <form
          className="auth-card"
          onSubmit={(event) => {
            event.preventDefault();
            submit.run();
          }}
        >
          <p className="eyebrow">{isRegister ? 'Create account' : 'Sign in'}</p>
          <h2>{isRegister ? 'Start with your details.' : 'Enter your phone and password.'}</h2>

          <Notice error={submit.error} onDismiss={submit.clearError} />

          {isRegister && (
            <Field
              label="Your name"
              value={form.name}
              onChange={update('name')}
              error={fieldErrors.name || errorFields.name}
              autoComplete="name"
              required
            />
          )}
          <Field
            label="Mobile number"
            value={form.phone}
            onChange={update('phone')}
            error={fieldErrors.phone || errorFields.phone}
            hint={isRegister ? '10 digits. This is how you sign in.' : undefined}
            type="tel"
            inputMode="numeric"
            autoComplete="tel"
            required
          />
          <Field
            label="Password"
            value={form.password}
            onChange={update('password')}
            error={fieldErrors.password || errorFields.password}
            hint={isRegister ? 'At least 8 characters, not only digits.' : undefined}
            type="password"
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            required
          />
          {isRegister && (
            <>
              <Field
                label="Email (optional)"
                value={form.email}
                onChange={update('email')}
                error={errorFields.email}
                hint="Only used if you ever need to recover the account."
                type="email"
                autoComplete="email"
              />
              <Field
                label="Location (optional)"
                value={form.location}
                onChange={update('location')}
                hint="District, State — fills your planner automatically."
                autoComplete="address-level2"
              />
              <SelectField
                label="Preferred language"
                value={form.language}
                values={LANGUAGES}
                onChange={update('language')}
              />
            </>
          )}

          <button className="primary-action auth-submit" type="submit" disabled={submit.loading}>
            {submit.loading ? <Spinner label={isRegister ? 'Creating account…' : 'Signing in…'} /> : isRegister ? 'Create account' : 'Sign in'}
          </button>

          <p className="auth-switch">
            {isRegister ? 'Already have an account? ' : "Don't have an account? "}
            <button type="button" onClick={() => navigate(isRegister ? '/login' : '/register')}>
              {isRegister ? 'Sign in' : 'Create one'}
            </button>
          </p>
        </form>
      </section>
    </main>
  );
}
