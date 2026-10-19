import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { ApiError, api, tokens } from './api.js';

// Accounts are optional. Everything in the planner works signed out; an account only makes saved
// plans and season budgets durable and available on another device.

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [farmer, setFarmer] = useState(null);
  const [status, setStatus] = useState('loading'); // loading | guest | signed-in

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!tokens.access() && !tokens.refresh()) {
        if (!cancelled) setStatus('guest');
        return;
      }
      try {
        const me = await api.me();
        if (!cancelled) {
          setFarmer(me);
          setStatus('signed-in');
        }
      } catch {
        // A stale or revoked token must not leave the app stuck on a loading screen.
        tokens.clear();
        if (!cancelled) setStatus('guest');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const adopt = useCallback((pair) => {
    tokens.save(pair);
    setFarmer(pair.farmer);
    setStatus('signed-in');
    return pair.farmer;
  }, []);

  const signIn = useCallback(async (payload) => adopt(await api.login(payload)), [adopt]);
  const signUp = useCallback(async (payload) => adopt(await api.register(payload)), [adopt]);

  const signOut = useCallback(async () => {
    const refreshToken = tokens.refresh();
    if (refreshToken) {
      // Best effort: the local session must end even if the server call fails.
      try {
        await api.logout(refreshToken);
      } catch (error) {
        if (!(error instanceof ApiError)) throw error;
      }
    }
    tokens.clear();
    setFarmer(null);
    setStatus('guest');
  }, []);

  const value = useMemo(
    () => ({
      farmer,
      status,
      isSignedIn: status === 'signed-in',
      isLoading: status === 'loading',
      signIn,
      signUp,
      signOut,
      setFarmer,
    }),
    [farmer, status, signIn, signUp, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
