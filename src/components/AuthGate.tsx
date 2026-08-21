import React, { useEffect, useState } from 'react';
import { LogIn, ShieldAlert, Loader2, Crosshair, Ruler, Palette, UploadCloud, Sprout, Rocket, Images, LineChart } from 'lucide-react';
import { watchAuth, signInWithGoogle, signOut, type AuthState } from '../lib/auth';

const LOGO = `${import.meta.env.BASE_URL}cose/cose-logo.png`;

function applyTheme() {
  const saved = localStorage.getItem('cose-theme');
  const theme = saved === 'light' || saved === 'dark'
    ? saved
    : (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);
}

// Wraps the whole app. In unconfigured mode (no Supabase keys) it renders the
// app openly, exactly as before. Once configured, visitors land on this public
// page and must sign in with Google to enter; banned users are locked out.
export const AuthGate: React.FC<{ children: (auth: AuthState) => React.ReactNode }> = ({ children }) => {
  const [auth, setAuth] = useState<AuthState>({ status: 'loading', session: null, profile: null });
  useEffect(() => { applyTheme(); return watchAuth(setAuth); }, []);

  if (auth.status === 'unconfigured' || auth.status === 'signed-in') return <>{children(auth)}</>;

  // Loading / banned: a compact card is enough.
  if (auth.status === 'loading' || auth.status === 'banned') {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <img src={LOGO} alt="CoSE" className="auth-logo" />
          <div className="auth-eyebrow">CoSE Cloud · AstroBotany</div>
          <h1>Calibration Image Database</h1>
          {auth.status === 'loading'
            ? <p className="auth-msg"><Loader2 className="spin" size={16} /> Checking your session…</p>
            : <>
                <div className="auth-msg" style={{ color: 'var(--danger)' }}><ShieldAlert size={18} /> Your access to this database has been revoked by an administrator.</div>
                <button className="btn btn-ghost" onClick={() => signOut()}>Sign out</button>
              </>}
        </div>
        <div className="auth-foot">Space biology · CoSE Cloud</div>
      </div>
    );
  }

  // signed-out → the public landing page.
  return (
    <div className="land">
      <header className="land-nav">
        <div className="land-brand"><img src={LOGO} alt="CoSE" /> <span>CoSE&nbsp;Cloud</span></div>
        <button className="btn btn-primary btn-sm" onClick={() => signInWithGoogle()}><LogIn size={15} /> Sign in</button>
      </header>

      <section className="land-hero">
        <div className="land-eyebrow"><Rocket size={13} /> Space biology · AstroBotany</div>
        <h1>The Regolith Plant&nbsp;Database</h1>
        <p className="land-sub">
          Growing food off Earth means growing it in regolith. This is an open record of what has been
          tried — the images, the substrates, the transcriptomes, and what the plants actually did —
          gathered so the next experiment does not start from scratch.
        </p>
        <div className="land-cta">
          <button className="btn btn-primary auth-google" onClick={() => signInWithGoogle()}><LogIn size={16} /> Continue with Google</button>
          <span className="land-fine">Free · signing in creates your account automatically <Sprout size={12} style={{ verticalAlign: -1, color: 'var(--accent2)' }} /></span>
        </div>
      </section>

      <section className="land-features">
        {[
          { icon: <Images size={18} />, t: 'Browse regolith imagery', d: 'Apollo-regolith plate scans, asteroid-simulant crop photographs and community contributions, side by side.' },
          { icon: <Crosshair size={18} />, t: 'Detect the marker', d: 'The calibration card is found in your browser to recover pixels-per-mm scale and a 15-chip colour correction — no upload to a server.' },
          { icon: <LineChart size={18} />, t: 'Link growth to expression', d: 'Every sequenced OSD-476 plant is joined to its own growth trajectory, so you can ask which genes track how a plant actually fared.' },
          { icon: <UploadCloud size={18} />, t: 'Share your own', d: 'A free phone app, a calibration card, and your regolith experiment becomes part of a dataset no single lab could build.' },
        ].map((f, i) => (
          <div className="land-card" key={i}>
            <div className="land-ico">{f.icon}</div>
            <h3>{f.t}</h3>
            <p>{f.d}</p>
          </div>
        ))}
      </section>

      <section className="land-inside">
        <div className="land-inside-h"><Ruler size={14} /> Inside the collection</div>
        <div className="land-chips">
          {['OSD-476 · Apollo 11/12/17 regolith', 'OSD-670 · CI asteroid simulant', 'LHS-1 vs Chang\u2019e-5 soil chemistry', 'Substrate probe time series', 'Community uploads'].map(c => (
            <span className="land-chip" key={c}><Sprout size={11} /> {c}</span>
          ))}
        </div>
        <p className="land-note"><Palette size={12} style={{ verticalAlign: -1 }} /> Marker detection, scale, colour and pigment analysis all run locally in your browser; your account governs access and your own contributions.</p>
      </section>

      <footer className="land-footer">
        <span>AstroBotany Calibration Image Database</span>
        <span className="land-dot">·</span>
        <span>CoSE Cloud — Space Biology</span>
      </footer>
    </div>
  );
};
