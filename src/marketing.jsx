import React from 'react';
import { BarChart3, Bot, Camera, CheckCircle2, Database, Search, ShieldCheck, Sprout, Wheat } from 'lucide-react';

export function MarketingSite({ page, navigate }) {
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
        <span className="public-brand-mark"><Wheat size={22} aria-hidden="true" /></span>
        <span><strong>Annapurna AI</strong><small>Farm intelligence</small></span>
      </button>
      <nav aria-label="Site navigation">
        <button className={page === 'home' ? 'active' : ''} onClick={() => navigate('/')}>Home</button>
        <button className={page === 'about' ? 'active' : ''} onClick={() => navigate('/about')}>About</button>
        <button onClick={() => navigate('/login')}>Sign in</button>
        <button className="public-cta" onClick={() => navigate('/planner')}>
          Open workspace <span aria-hidden="true">→</span>
        </button>
      </nav>
    </header>
  );
}

function LandingPage({ navigate }) {
  return (
    <>
      <section className="landing-hero">
        <div className="landing-copy">
          <p className="marketing-kicker"><span aria-hidden="true" /> Practical AI for Indian agriculture</p>
          <h1>Plan every season with a clearer view of your farm.</h1>
          <p>
            Annapurna ranks crops against your own field conditions, shows the money as a range
            rather than a promise, and tells you plainly when a crop is the wrong choice.
          </p>
          <div className="landing-actions">
            <button className="marketing-primary" onClick={() => navigate('/planner')}>
              Start your farm plan <span aria-hidden="true">→</span>
            </button>
            <button className="marketing-secondary" onClick={() => navigate('/about')}>See how it works</button>
          </div>
          <div className="landing-trust">
            <span><CheckCircle2 size={16} aria-hidden="true" /> No account needed to plan</span>
            <span><CheckCircle2 size={16} aria-hidden="true" /> Every number states its source</span>
            <span><CheckCircle2 size={16} aria-hidden="true" /> Estimates, never guarantees</span>
          </div>
        </div>
        <div className="product-preview" aria-label="What the workspace shows">
          <div className="preview-top"><span><i aria-hidden="true" /> Your field, your numbers</span><small>Data required</small></div>
          <div className="preview-body">
            <div className="preview-heading">
              <div><small>Farm profile</small><h3>Awaiting your data</h3></div>
              <strong aria-hidden="true">—</strong>
            </div>
            <div className="preview-progress"><span style={{ width: '22%' }} /></div>
            <div className="preview-metrics">
              <div><small>Crop ranking</small><strong>Your conditions</strong></div>
              <div><small>Mandi price</small><strong>Official feed</strong></div>
              <div><small>Season budget</small><strong>Your costs</strong></div>
            </div>
            <div className="preview-advice">
              <Sprout size={18} aria-hidden="true" />
              <div>
                <strong>How it works</strong>
                <p>Enter your field details once, then compare crops on fit, water, risk and money.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="marketing-section" id="features">
        <div className="section-intro">
          <p className="marketing-kicker">One connected workspace</p>
          <h2>From field conditions to a decision you can defend.</h2>
          <p>Every tool reads the same farm profile, so the advice stays consistent across screens.</p>
        </div>
        <div className="feature-cards">
          <MarketingCard icon={Sprout} label="Plan" title="Crop ranking that says no"
            text="Season, soil, pH, water and irrigation are treated as hard constraints. A crop that does not fit is labelled 'not recommended', with the reason." />
          <MarketingCard icon={BarChart3} label="Budget" title="Season finance with downside"
            text="Category budget, tracked spend, peak working capital, break-even price, and a poor-season case built from real yield and cost ranges." />
          <MarketingCard icon={Camera} label="Protect" title="Crop image screening"
            text="Upload a leaf photo for a cautious, clearly-labelled screening result. Available when a vision model is configured — never a guess." />
          <MarketingCard icon={Bot} label="Ask" title="Advisor in your language"
            text="Ask about irrigation, fertiliser or planning in English, Hindi, Punjabi or Haryanvi, using your current field context." />
        </div>
      </section>

      <section className="how-section">
        <div className="section-intro">
          <p className="marketing-kicker">A simple workflow</p>
          <h2>Three steps from uncertainty to direction.</h2>
        </div>
        <div className="step-list">
          <div><span>01</span><h3>Describe your farm</h3><p>Soil, water, season, budget and what you grew last year.</p></div>
          <div><span>02</span><h3>Compare the evidence</h3><p>Ranked crops with reasons, limits, water need and a profit range.</p></div>
          <div><span>03</span><h3>Save and verify</h3><p>Keep the plan, export a report, and confirm locally before spending.</p></div>
        </div>
      </section>

      <section className="responsible-section">
        <div className="responsible-mark"><ShieldCheck size={32} aria-hidden="true" /></div>
        <div>
          <p className="marketing-kicker">Responsible by design</p>
          <h2>Advice should show its working, not hide its uncertainty.</h2>
          <p>
            Reference prices are announced support prices and say so. Yields are ranges from
            published regional data. When a service is not connected, the screen says that rather
            than showing your own input back as a measurement.
          </p>
        </div>
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
        <h1>Clearer agricultural decisions, with the working shown.</h1>
        <p>
          A crop planning and advisory tool built around the questions a smallholder actually faces
          before a season starts: what to sow, what it will cost, and what happens if the year goes badly.
        </p>
      </section>

      <section className="about-story marketing-section">
        <div className="about-story-copy">
          <p className="marketing-kicker">Why this project exists</p>
          <h2>Farm information is available. Turning it into one clear decision is the hard part.</h2>
        </div>
        <div className="about-prose">
          <p>
            Soil readings, weather, crop requirements, mandi prices and the household budget live in
            separate places. That fragmentation makes planning slow and makes advice hard to trust.
          </p>
          <p>
            Annapurna brings them into one workflow: it ranks suitable crops, explains why, names the
            conditions that rule a crop out, estimates the money as a range, and carries the same
            context into the advisor and the image screening.
          </p>
        </div>
      </section>

      <section className="project-pillars">
        <MarketingCard icon={Search} label="Transparent" title="Show the reason"
          text="Every crop carries its reasons, its cautions, and any condition that disqualifies it." />
        <MarketingCard icon={Database} label="Sourced" title="Cite the number"
          text="Yields, costs and support prices carry the source they came from and the season they apply to." />
        <MarketingCard icon={ShieldCheck} label="Honest" title="Admit the gaps"
          text="When live weather or mandi data is not connected, the screen says so instead of filling the space." />
      </section>

      <section className="architecture-section">
        <div className="section-intro">
          <p className="marketing-kicker">How it is built</p>
          <h2>A working full-stack application.</h2>
        </div>
        <div className="architecture-grid">
          <div><span>Interface</span><h3>React + Vite</h3><p>Planner, insights, season finance, image screening, advisor and saved records.</p></div>
          <div><span>API</span><h3>FastAPI</h3><p>Crop ranking, finance planning, weather, mandi prices, advisory chat, reports and accounts.</p></div>
          <div><span>Ranking</span><h3>Rules + scikit-learn</h3><p>A transparent weighted model with hard constraints, plus an optional trained classifier.</p></div>
          <div><span>Storage</span><h3>PostgreSQL</h3><p>Accounts, saved plans, season budgets and a cache of official mandi prices.</p></div>
        </div>
      </section>

      <section className="project-scope">
        <div><p className="marketing-kicker">Current scope</p><h2>An honest prototype, not a guarantee of outcomes.</h2></div>
        <ul>
          <li><CheckCircle2 size={18} aria-hidden="true" /> Reference data covers the irrigated North-Indian plains; other regions need revalidation</li>
          <li><CheckCircle2 size={18} aria-hidden="true" /> Live weather, mandi prices and AI features each need their own API key</li>
          <li><CheckCircle2 size={18} aria-hidden="true" /> Image screening is a screening aid, never a diagnosis</li>
        </ul>
      </section>

      <MarketingCTA navigate={navigate} />
    </>
  );
}

function MarketingCard({ icon: Icon, label, title, text }) {
  return (
    <article className="marketing-card">
      <span className="marketing-icon"><Icon size={22} aria-hidden="true" /></span>
      <small>{label}</small>
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  );
}

function MarketingCTA({ navigate }) {
  return (
    <section className="marketing-cta">
      <div>
        <p className="marketing-kicker">Ready to start?</p>
        <h2>Build your first farm plan in a few minutes.</h2>
        <p>No account needed. Create one later if you want your plans on more than one device.</p>
      </div>
      <button className="marketing-primary light" onClick={() => navigate('/planner')}>
        Open workspace <span aria-hidden="true">→</span>
      </button>
    </section>
  );
}

function PublicFooter({ navigate }) {
  return (
    <footer className="public-footer">
      <button className="public-brand" onClick={() => navigate('/')}>
        <span className="public-brand-mark"><Wheat size={20} aria-hidden="true" /></span>
        <span><strong>Annapurna AI</strong><small>Farm intelligence</small></span>
      </button>
      <p>Decision support for informed, sustainable farming. Estimates only — verify locally before you spend.</p>
      <div>
        <button onClick={() => navigate('/')}>Home</button>
        <button onClick={() => navigate('/about')}>About</button>
        <button onClick={() => navigate('/planner')}>Open workspace</button>
      </div>
    </footer>
  );
}
