import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BarChart, ErrorBoundary, Notice, RangeInput, VerdictBadge, compactInr, inr, useAsyncAction } from './components.jsx';
import { ApiError } from './api.js';

describe('money formatting', () => {
  it('uses the Indian numbering system', () => {
    expect(inr(100000)).toBe('₹1,00,000');
    expect(inr(1234567)).toBe('₹12,34,567');
  });

  it('shows a dash rather than NaN for a missing value', () => {
    expect(inr(undefined)).toBe('—');
    expect(inr(null)).toBe('—');
    expect(compactInr('not a number')).toBe('—');
  });

  it('compacts to lakh and crore', () => {
    expect(compactInr(150000)).toBe('₹1.5L');
    expect(compactInr(25000000)).toBe('₹2.5Cr');
    expect(compactInr(-46398)).toBe('₹-46k');
  });
});

describe('BarChart', () => {
  it('renders a negative value without pushing its label off the chart', () => {
    // The SVG version placed negative labels one bar-height too low, so the cash-flow chart
    // clipped them in every single plan.
    render(<BarChart description="Profit by scenario" items={[
      { label: 'Good season', value: 97340 },
      { label: 'Poor season', value: -46398 },
    ]} />);
    expect(screen.getByText('₹97k')).toBeInTheDocument();
    const negative = screen.getByText('₹-46k');
    expect(negative).toBeInTheDocument();
    expect(negative).toHaveClass('negative');
  });

  it('survives an all-zero series without dividing by zero', () => {
    render(<BarChart description="Nothing yet" items={[{ label: 'A', value: 0 }, { label: 'B', value: 0 }]} />);
    expect(screen.getAllByText('₹0')).toHaveLength(2);
  });

  it('says so when there is nothing to chart', () => {
    render(<BarChart description="Empty" items={[{ label: 'A', value: null }]} />);
    expect(screen.getByText(/not enough data/i)).toBeInTheDocument();
  });
});

describe('Notice', () => {
  it('marks a connection failure as a warning rather than a server error', () => {
    render(<Notice error={new ApiError(0, 'Cannot reach the Annapurna server.')} />);
    expect(screen.getByRole('status')).toHaveTextContent('Cannot reach');
  });

  it('shows a server error as an alert, with its reference', () => {
    render(<Notice error={new ApiError(500, 'Something went wrong.', { requestId: 'req-9' })} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong.');
    expect(screen.getByText(/req-9/)).toBeInTheDocument();
  });

  it('renders nothing when there is nothing to say', () => {
    const { container } = render(<Notice />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('VerdictBadge', () => {
  it('styles a rejection differently from a strong match', () => {
    const { rerender, container } = render(<VerdictBadge verdict="strong match" suitability={93} />);
    expect(container.firstChild).toHaveClass('verdict-strong');
    rerender(<VerdictBadge verdict="not recommended" suitability={12} />);
    expect(container.firstChild).toHaveClass('verdict-bad');
    expect(screen.getByText(/12% · not recommended/)).toBeInTheDocument();
  });
});

describe('RangeInput', () => {
  it('offers a number box as well as a slider, so an exact value can be entered', async () => {
    const update = vi.fn();
    render(<RangeInput label="Land size" field="landSize" min="0.5" max="50" value="2" update={update} />);
    const exact = screen.getByLabelText('Land size exact value');
    await userEvent.clear(exact);
    await userEvent.type(exact, '25');
    expect(update).toHaveBeenCalledWith('landSize', expect.any(String));
  });
});

describe('ErrorBoundary', () => {
  it('contains a render failure instead of blanking the app', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    function Boom() {
      throw new Error('render exploded');
    }
    render(<ErrorBoundary><Boom /></ErrorBoundary>);
    expect(screen.getByText(/could not be displayed/i)).toBeInTheDocument();
  });
});

describe('useAsyncAction', () => {
  function Harness({ action }) {
    const { run, loading, error } = useAsyncAction(action);
    return (
      <div>
        <button onClick={() => run()}>go</button>
        <span data-testid="state">{loading ? 'loading' : error ? `error:${error.message}` : 'idle'}</span>
      </div>
    );
  }

  it('returns to idle after a success', async () => {
    // StrictMode's mount/cleanup/mount used to leave the "mounted" flag false forever, so the
    // button sat on "loading" and every result was discarded.
    render(
      <React.StrictMode>
        <Harness action={async () => 'ok'} />
      </React.StrictMode>
    );
    await userEvent.click(screen.getByText('go'));
    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('idle'));
  });

  it('surfaces the error and stops loading', async () => {
    render(
      <React.StrictMode>
        <Harness action={async () => { throw new ApiError(503, 'not configured'); }} />
      </React.StrictMode>
    );
    await userEvent.click(screen.getByText('go'));
    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('error:not configured'));
  });
});
