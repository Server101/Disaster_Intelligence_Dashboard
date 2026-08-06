import { useEffect, useMemo, useState } from 'react'
import dashboardSnapshot from './data/dashboardSnapshot.json'
import './App.css'

const STREAMLIT_URL = (import.meta.env.VITE_STREAMLIT_URL || 'https://disaster-intelligence-dashboard.streamlit.app').replace(/\/+$/, '')
const STREAMLIT_EMBED_URL = `${STREAMLIT_URL}/?embed=true&embed_options=dark_theme`
const STREAMLIT_VIEWER = {
  title: 'Search Declarations by State in Streamlit',
  url: STREAMLIT_EMBED_URL,
  externalUrl: `${STREAMLIT_URL}/`,
  note: 'Use the Streamlit state and territory filters to explore declaration records, incident types, trends, regional patterns, and downloadable data. If the embedded view does not load, open it separately.',
}
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
const TABLEAU_VIEW_URL = (
  import.meta.env.VITE_TABLEAU_URL
  || 'https://public.tableau.com/views/DisasterIntelligenceDashboard/TableauDisasterHeatMap'
).split('?')[0].replace(/\/+$/, '')
const TABLEAU_EMBED_URL = `${TABLEAU_VIEW_URL}?:showVizHome=no&:embed=yes&:toolbar=yes&:tabs=no`
const TABLEAU_SHARE_URL = `${TABLEAU_VIEW_URL}?:language=en-US&:display_count=n&:origin=viz_share_link`
const TABLEAU_VIEWER = {
  title: 'Tableau Disaster Heat Map',
  url: TABLEAU_EMBED_URL,
  externalUrl: TABLEAU_SHARE_URL,
  note: 'Hover over a state for detailed statistics, select a state to keep it highlighted, or use the region and incident filters to update the map.',
}
const GITHUB_URL = import.meta.env.VITE_GITHUB_URL || ''
const formatNumber = new Intl.NumberFormat('en-US')
const SNAPSHOT = dashboardSnapshot

const REGION_DETAILS = {
  'Region 1': { name: 'New England', areas: 'CT, ME, MA, NH, RI, VT' },
  'Region 2': { name: 'Northeast & Caribbean', areas: 'NJ, NY, Puerto Rico, U.S. Virgin Islands' },
  'Region 3': { name: 'Mid-Atlantic', areas: 'DE, DC, MD, PA, VA, WV' },
  'Region 4': { name: 'Southeast', areas: 'AL, FL, GA, KY, MS, NC, SC, TN' },
  'Region 5': { name: 'Great Lakes', areas: 'IL, IN, MI, MN, OH, WI' },
  'Region 6': { name: 'South Central', areas: 'AR, LA, NM, OK, TX' },
  'Region 7': { name: 'Central Plains', areas: 'IA, KS, MO, NE' },
  'Region 8': { name: 'Mountain', areas: 'CO, MT, ND, SD, UT, WY' },
  'Region 9': { name: 'Pacific Southwest & Islands', areas: 'AZ, CA, HI, NV and Pacific territories' },
  'Region 10': { name: 'Pacific Northwest', areas: 'AK, ID, OR, WA' },
}

const INSIGHT_OPTIONS = [
  ['seasonality', 'Top month and season'],
  ['states', 'Top five states and territories'],
  ['incidents', 'Top five incident types'],
  ['regions', 'Top five regions'],
  ['trend', 'Long-term trend interpretation'],
  ['spikes', 'Historical spikes and their meaning'],
  ['record-comparison', 'Declaration records vs. unique disasters'],
  ['forecast-comparison', 'Compare three regional forecasts'],
]

const formatRegionLabel = (region, compact = false) => {
  const detail = REGION_DETAILS[region]
  if (!detail) return region
  return compact
    ? `${region} — ${detail.name}`
    : `${region} — ${detail.name} (${detail.areas})`
}

const nextForecastMonthKey = () => {
  const now = new Date()
  const nextMonth = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 1))
  return nextMonth.toISOString().slice(0, 7)
}

const monthLabel = (month) => (month
  ? new Date(`${month}-01T00:00:00Z`).toLocaleDateString('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' })
  : 'N/A')

function buildFallbackInsights({ summary, trend, states, incidents, regions, seasonality }) {
  const topMonth = [...(seasonality?.points || [])].sort((a, b) => b.declaration_records - a.declaration_records)[0] || { name: 'N/A', declaration_records: 0 }
  const seasonMonths = {
    Winter: ['December', 'January', 'February'],
    Spring: ['March', 'April', 'May'],
    Summer: ['June', 'July', 'August'],
    Fall: ['September', 'October', 'November'],
  }
  const monthCounts = Object.fromEntries((seasonality?.points || []).map((point) => [point.name, point.declaration_records]))
  const seasonTotals = Object.entries(seasonMonths).map(([name, months]) => ({
    name,
    months,
    declaration_records: months.reduce((total, month) => total + (monthCounts[month] || 0), 0),
  }))
  const topSeason = seasonTotals.sort((a, b) => b.declaration_records - a.declaration_records)[0] || { name: 'N/A', months: [], declaration_records: 0 }
  const completeTrend = (trend?.points || []).filter((point) => Number(point.period) < new Date().getUTCFullYear())
  const window = Math.min(10, Math.max(2, Math.floor(completeTrend.length / 2)))
  const recent = completeTrend.slice(-window)
  const prior = completeTrend.slice(-window * 2, -window)
  const average = (points) => points.length ? points.reduce((total, point) => total + point.declaration_records, 0) / points.length : 0
  const recentAverage = average(recent)
  const priorAverage = average(prior)
  const percentChange = priorAverage ? ((recentAverage - priorAverage) / priorAverage) * 100 : 0
  const spikes = [...completeTrend]
    .sort((a, b) => b.declaration_records - a.declaration_records)
    .slice(0, 3)
    .map((point) => ({
      year: Number(point.period),
      declaration_records: point.declaration_records,
      top_incident_type: 'Live API detail',
      top_incident_records: 0,
      explanation: `${point.period} is one of the highest declaration-record years in the selected period.`,
      limitation: 'The snapshot identifies the spike, but the live API provides the incident category contributing most to it.',
    }))
  const ratio = summary.unique_disaster_numbers ? summary.declaration_records / summary.unique_disaster_numbers : 0

  return {
    top_month: topMonth,
    top_season: topSeason,
    top_states: (states?.points || []).slice(0, 5),
    top_incident_types: (incidents?.points || []).slice(0, 5),
    top_regions: (regions?.points || []).slice(0, 5),
    long_term_trend: {
      direction: percentChange > 5 ? 'increasing' : percentChange < -5 ? 'decreasing' : 'relatively stable',
      prior_average: priorAverage,
      recent_average: recentAverage,
      percent_change: percentChange,
      interpretation: `Recent complete-year declaration records average ${Math.abs(percentChange).toFixed(1)}% ${percentChange >= 0 ? 'higher' : 'lower'} than the preceding comparison period.`,
      limitation: 'Annual declaration records are administrative counts and do not directly measure disaster severity.',
    },
    historical_spikes: spikes,
    records_vs_disasters: {
      declaration_records: summary.declaration_records,
      unique_disaster_numbers: summary.unique_disaster_numbers,
      records_per_disaster: ratio,
      interpretation: `There are about ${ratio.toFixed(2)} declaration records per distinct disaster number in the selected data.`,
      limitation: 'One disaster can produce multiple records for separate designated areas, so the ratio is not a severity measure.',
    },
  }
}

function MetricCard({ label, value, note }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {note ? <small>{note}</small> : null}
    </article>
  )
}

function EmptyChart({ message }) {
  return <div className="empty-chart">{message}</div>
}

function AnnualTrendChart({ points }) {
  if (!points?.length) {
    return <EmptyChart message="Annual trend data is unavailable." />
  }

  const width = 900
  const height = 330
  const padding = { top: 24, right: 24, bottom: 46, left: 68 }
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom
  const maximum = Math.max(...points.map((point) => point.declaration_records), 1)
  const xFor = (index) => padding.left + (index / Math.max(points.length - 1, 1)) * chartWidth
  const yFor = (value) => padding.top + chartHeight - (value / maximum) * chartHeight
  const linePath = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${xFor(index)} ${yFor(point.declaration_records)}`)
    .join(' ')
  const areaPath = `${linePath} L ${xFor(points.length - 1)} ${padding.top + chartHeight} L ${padding.left} ${padding.top + chartHeight} Z`
  const labelIndexes = Array.from(
    new Set([0, Math.floor(points.length / 4), Math.floor(points.length / 2), Math.floor((points.length * 3) / 4), points.length - 1]),
  )
  const peak = points.reduce((best, point, index) =>
    point.declaration_records > best.point.declaration_records ? { point, index } : best,
  { point: points[0], index: 0 })

  return (
    <svg className="line-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Annual declaration record trend">
      <defs>
        <linearGradient id="trendArea" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.34" />
          <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
        const y = padding.top + chartHeight - ratio * chartHeight
        return (
          <g key={ratio}>
            <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} className="chart-grid-line" />
            <text x={padding.left - 12} y={y + 4} textAnchor="end" className="chart-axis-label">
              {formatNumber.format(Math.round(maximum * ratio))}
            </text>
          </g>
        )
      })}
      <path d={areaPath} fill="url(#trendArea)" />
      <path d={linePath} className="trend-line" />
      {labelIndexes.map((index) => (
        <text key={index} x={xFor(index)} y={height - 14} textAnchor="middle" className="chart-axis-label">
          {points[index].period}
        </text>
      ))}
      <circle cx={xFor(peak.index)} cy={yFor(peak.point.declaration_records)} r="6" className="peak-point" />
      <g transform={`translate(${Math.min(xFor(peak.index) + 12, width - 160)}, ${Math.max(yFor(peak.point.declaration_records) - 40, 8)})`}>
        <rect width="142" height="42" rx="8" className="chart-callout" />
        <text x="10" y="17" className="chart-callout-title">Peak {peak.point.period}</text>
        <text x="10" y="33" className="chart-callout-value">{formatNumber.format(peak.point.declaration_records)} records</text>
      </g>
    </svg>
  )
}

function HorizontalBarChart({ points, compact = false, labelFormatter = (name) => name }) {
  if (!points?.length) {
    return <EmptyChart message="Category data is unavailable." />
  }

  const maximum = Math.max(...points.map((point) => point.declaration_records), 1)
  return (
    <div className={`horizontal-bars ${compact ? 'compact' : ''}`}>
      {points.map((point) => (
        <div className="bar-row" key={point.name}>
          <div className="bar-row-heading">
            <span>{labelFormatter(point.name)}</span>
            <strong>{formatNumber.format(point.declaration_records)}</strong>
          </div>
          <div className="bar-track">
            <i style={{ width: `${Math.max((point.declaration_records / maximum) * 100, 2)}%` }}></i>
          </div>
        </div>
      ))}
    </div>
  )
}

function SeasonalityChart({ points }) {
  if (!points?.length) {
    return <EmptyChart message="Seasonality data is unavailable." />
  }

  const maximum = Math.max(...points.map((point) => point.declaration_records), 1)
  return (
    <div className="seasonality-chart" role="img" aria-label="Monthly declaration-record seasonality">
      {points.map((point) => (
        <div className="season-column" key={point.name} title={`${point.name}: ${formatNumber.format(point.declaration_records)} records`}>
          <strong>{formatNumber.format(point.declaration_records)}</strong>
          <div className="season-track">
            <i style={{ height: `${Math.max((point.declaration_records / maximum) * 100, 3)}%` }}></i>
          </div>
          <span>{point.name.slice(0, 3)}</span>
        </div>
      ))}
    </div>
  )
}

function InsightLimitation({ children }) {
  return (
    <div className="insight-limitation">
      <strong>Helpful context</strong>
      <span>{children}</span>
    </div>
  )
}

function InsightExplorer({
  mode,
  onModeChange,
  insights,
  comparisonRegions,
  onComparisonRegionChange,
  availableRegions,
  comparisonForecasts,
  comparisonLoading,
  forecastFloor,
}) {
  const renderRanked = (points, labelFormatter, limitation) => (
    <div className="insight-ranked">
      <HorizontalBarChart points={(points || []).slice(0, 5)} compact labelFormatter={labelFormatter} />
      <InsightLimitation>{limitation}</InsightLimitation>
    </div>
  )

  return (
    <article className="insight-explorer">
      <div className="insight-toolbar">
        <div>
          <span>Guided findings</span>
          <h3>Insight Explorer</h3>
          <p>Choose a topic to see the strongest result, a brief explanation, and helpful context for interpreting it.</p>
        </div>
        <label>
          <span>Explore a result</span>
          <select value={mode} onChange={(event) => onModeChange(event.target.value)}>
            {INSIGHT_OPTIONS.map(([value, label]) => <option value={value} key={value}>{label}</option>)}
          </select>
        </label>
      </div>

      <div className="insight-stage">
        {mode === 'seasonality' ? (
          <div className="insight-highlight-grid">
            <div className="insight-highlight">
              <span>Top calendar month</span>
              <strong>{insights.top_month.name}</strong>
              <small>{formatNumber.format(insights.top_month.declaration_records)} declaration records</small>
            </div>
            <div className="insight-highlight">
              <span>Top meteorological season</span>
              <strong>{insights.top_season.name}</strong>
              <small>{formatNumber.format(insights.top_season.declaration_records)} records · {insights.top_season.months.join(', ')}</small>
            </div>
            <InsightLimitation>
              Month and season totals combine all selected years. They show historical concentration, not a guarantee that every year follows the same timing.
            </InsightLimitation>
          </div>
        ) : null}

        {mode === 'states'
          ? renderRanked(insights.top_states, (name) => name, 'State rankings count administrative declaration rows. Larger or more widely designated disasters can create more rows without being more severe.')
          : null}

        {mode === 'incidents'
          ? renderRanked(insights.top_incident_types, (name) => name, 'Incident classifications and reporting practices vary over time. Counts do not directly measure losses, fatalities, or event intensity.')
          : null}

        {mode === 'regions'
          ? renderRanked(insights.top_regions, (name) => formatRegionLabel(name, true), 'Region totals are raw counts and are not adjusted for population or geographic size.')
          : null}

        {mode === 'trend' ? (
          <div className="trend-insight-layout">
            <div className="trend-change-card">
              <span>Recent vs. prior complete-year average</span>
              <strong>{insights.long_term_trend.percent_change >= 0 ? '+' : ''}{insights.long_term_trend.percent_change.toFixed(1)}%</strong>
              <small>{insights.long_term_trend.direction}</small>
            </div>
            <div className="trend-interpretation">
              <p>{insights.long_term_trend.interpretation}</p>
              <div className="comparison-mini-grid">
                <div><span>Prior average</span><strong>{formatNumber.format(Math.round(insights.long_term_trend.prior_average))}</strong></div>
                <div><span>Recent average</span><strong>{formatNumber.format(Math.round(insights.long_term_trend.recent_average))}</strong></div>
              </div>
              <InsightLimitation>{insights.long_term_trend.limitation}</InsightLimitation>
            </div>
          </div>
        ) : null}

        {mode === 'spikes' ? (
          <div className="spike-grid">
            {(insights.historical_spikes || []).map((spike) => (
              <article key={spike.year}>
                <span>Historical spike</span>
                <strong>{spike.year}</strong>
                <b>{formatNumber.format(spike.declaration_records)} records</b>
                <p>{spike.explanation}</p>
                <InsightLimitation>{spike.limitation}</InsightLimitation>
              </article>
            ))}
          </div>
        ) : null}

        {mode === 'record-comparison' ? (
          <div className="record-comparison-layout">
            <div className="record-comparison-numbers">
              <div><span>Declaration records</span><strong>{formatNumber.format(insights.records_vs_disasters.declaration_records)}</strong></div>
              <div><span>Unique disaster numbers</span><strong>{formatNumber.format(insights.records_vs_disasters.unique_disaster_numbers)}</strong></div>
              <div><span>Records per disaster number</span><strong>{insights.records_vs_disasters.records_per_disaster.toFixed(2)}</strong></div>
            </div>
            <div>
              <p>{insights.records_vs_disasters.interpretation}</p>
              <InsightLimitation>{insights.records_vs_disasters.limitation}</InsightLimitation>
            </div>
          </div>
        ) : null}

        {mode === 'forecast-comparison' ? (
          <div className="forecast-comparison-panel">
            <div className="comparison-region-controls">
              {comparisonRegions.map((region, index) => (
                <label key={`comparison-${index}`}>
                  <span>Comparison region {index + 1}</span>
                  <select value={region} onChange={(event) => onComparisonRegionChange(index, event.target.value)}>
                    {availableRegions.map((option) => (
                      <option
                        value={option}
                        key={option}
                        disabled={comparisonRegions.some((selected, selectedIndex) => selectedIndex !== index && selected === option)}
                      >
                        {formatRegionLabel(option)}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            {comparisonLoading ? <div className="comparison-loading">Updating regional forecasts…</div> : null}
            <div className="comparison-forecast-grid">
              {comparisonForecasts.map((item) => {
                const rows = (item.points || []).filter((point) => point.record_type === 'Forecast' && point.month >= forecastFloor)
                const total = rows.reduce((sum, point) => sum + point.declaration_records, 0)
                const peak = rows.length ? rows.reduce((best, point) => point.declaration_records > best.declaration_records ? point : best) : null
                const incidentTotals = rows.reduce((totals, point) => {
                  if (!point.likely_incident_type) return totals
                  totals[point.likely_incident_type] = (totals[point.likely_incident_type] || 0) + point.declaration_records
                  return totals
                }, {})
                const likelyType = Object.entries(incidentTotals).sort((left, right) => right[1] - left[1])[0]?.[0] || 'N/A'
                const likelyAreas = rows.find((point) => point.likely_incident_type === likelyType)?.likely_areas || 'Region-wide'
                return (
                  <article key={item.region}>
                    <span>{formatRegionLabel(item.region, true)}</span>
                    <strong>{formatNumber.format(total)}</strong>
                    <small>forecast-period records</small>
                    <div><b>Starts</b><em>{monthLabel(item.forecast_start || rows[0]?.month)}</em></div>
                    <div><b>Peak</b><em>{peak ? `${monthLabel(peak.month)} · ${formatNumber.format(peak.declaration_records)}` : 'N/A'}</em></div>
                    <div><b>Likely type</b><em>{likelyType}</em></div>
                    <div><b>Focus areas</b><em>{likelyAreas}</em></div>
                    <p>{item.method}</p>
                  </article>
                )
              })}
            </div>
            <InsightLimitation>
              Incident categories are based on recurring region-wide patterns for each calendar month. They are not city-level predictions or guarantees that a specific event will occur.
            </InsightLimitation>
          </div>
        ) : null}
      </div>
    </article>
  )
}

function ForecastChart({ points }) {
  if (!points?.length) {
    return <EmptyChart message="Forecast data is unavailable." />
  }

  const history = points.filter((point) => point.record_type === 'Historical').slice(-24)
  const forecast = points.filter((point) => point.record_type === 'Forecast')
  const combined = [...history, ...forecast]
  if (!combined.length) {
    return <EmptyChart message="Forecast data is unavailable." />
  }

  const width = 900
  const height = 330
  const padding = { top: 24, right: 24, bottom: 48, left: 68 }
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom
  const values = combined.flatMap((point) => [point.declaration_records, point.upper_estimate || 0])
  const maximum = Math.max(...values, 1)
  const xFor = (index) => padding.left + (index / Math.max(combined.length - 1, 1)) * chartWidth
  const yFor = (value) => padding.top + chartHeight - (value / maximum) * chartHeight
  const historyPath = history
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${xFor(index)} ${yFor(point.declaration_records)}`)
    .join(' ')
  const forecastStartIndex = Math.max(history.length - 1, 0)
  const forecastSeries = history.length ? [history[history.length - 1], ...forecast] : forecast
  const forecastPath = forecastSeries
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${xFor(forecastStartIndex + index)} ${yFor(point.declaration_records)}`)
    .join(' ')
  const uncertaintyPoints = forecast.filter(
    (point) => point.lower_estimate !== null && point.upper_estimate !== null,
  )
  const uncertaintyPolygon = uncertaintyPoints.length
    ? [
        ...uncertaintyPoints.map((point, index) => `${xFor(history.length + index)},${yFor(point.upper_estimate)}`),
        ...uncertaintyPoints
          .map((point, index) => `${xFor(history.length + index)},${yFor(point.lower_estimate)}`)
          .reverse(),
      ].join(' ')
    : ''
  const labelIndexes = Array.from(new Set([0, Math.floor(combined.length / 3), Math.floor((combined.length * 2) / 3), combined.length - 1]))

  return (
    <svg className="line-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Historical and forecast monthly declaration records">
      {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
        const y = padding.top + chartHeight - ratio * chartHeight
        return (
          <g key={ratio}>
            <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} className="chart-grid-line" />
            <text x={padding.left - 12} y={y + 4} textAnchor="end" className="chart-axis-label">
              {formatNumber.format(Math.round(maximum * ratio))}
            </text>
          </g>
        )
      })}
      {uncertaintyPolygon ? <polygon points={uncertaintyPolygon} className="forecast-range" /> : null}
      {historyPath ? <path d={historyPath} className="trend-line" /> : null}
      {forecastPath ? <path d={forecastPath} className="forecast-line" /> : null}
      {history.length ? (
        <line
          x1={xFor(history.length - 0.5)}
          x2={xFor(history.length - 0.5)}
          y1={padding.top}
          y2={padding.top + chartHeight}
          className="forecast-divider"
        />
      ) : null}
      {labelIndexes.map((index) => (
        <text key={index} x={xFor(index)} y={height - 14} textAnchor="middle" className="chart-axis-label">
          {new Date(`${combined[index].month}-01T00:00:00`).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })}
        </text>
      ))}
      <g transform={`translate(${width - 230}, 12)`}>
        <line x1="0" x2="28" y1="8" y2="8" className="trend-line legend-line" />
        <text x="36" y="12" className="chart-axis-label">Historical</text>
        <line x1="112" x2="140" y1="8" y2="8" className="forecast-line legend-line" />
        <text x="148" y="12" className="chart-axis-label">Forecast</text>
      </g>
    </svg>
  )
}

function TableauHeatMapSection({ onOpen }) {
  return (
    <section className="tableau-section" id="heat-map">
      <div className="section-heading tableau-heading">
        <div>
          <p className="section-label">Interactive geographic analysis</p>
          <h2>Explore the Tableau Disaster Heat Map.</h2>
        </div>
        <p>Hover over a state to view its statistics, select a state to keep it highlighted, and use the year, incident-type, or region controls to update the entire map.</p>
      </div>

      <div className="tableau-embed-shell">
        <div className="tableau-embed-toolbar">
          <div>
            <span>Live interactive worksheet</span>
            <strong>Tableau Disaster Heat Map</strong>
          </div>
          <div className="tableau-embed-actions">
            <button type="button" onClick={onOpen}>Open larger popout</button>
            <a href={TABLEAU_SHARE_URL} target="_blank" rel="noreferrer">Open separately</a>
          </div>
        </div>

        <div className="tableau-embed-frame">
          <tableau-viz
            id="tableau-disaster-heat-map"
            src={TABLEAU_VIEW_URL}
            toolbar="bottom"
            hide-tabs="true"
            style={{ width: '100%', height: '100%' }}
          ></tableau-viz>
        </div>

        <p className="tableau-embed-guidance">
          Hover for state and regional details. Click a state to focus the view, or use Explore a Region to highlight every state in that region.
        </p>
      </div>
    </section>
  )
}

function ViewerModal({ viewer, onClose }) {
  useEffect(() => {
    if (!viewer) return undefined
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') onClose()
    }
    document.body.classList.add('modal-open')
    window.addEventListener('keydown', closeOnEscape)
    return () => {
      document.body.classList.remove('modal-open')
      window.removeEventListener('keydown', closeOnEscape)
    }
  }, [viewer, onClose])

  if (!viewer) return null

  const externalUrl = viewer.externalUrl || viewer.url

  return (
    <div className="viewer-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="viewer-modal" role="dialog" aria-modal="true" aria-label={viewer.title}>
        <header className="viewer-header">
          <div>
            <span>Embedded project view</span>
            <strong>{viewer.title}</strong>
          </div>
          <div className="viewer-actions">
            {externalUrl ? (
              <a href={externalUrl} target="_blank" rel="noreferrer">Open separately</a>
            ) : null}
            <button type="button" onClick={onClose} aria-label="Close embedded view">×</button>
          </div>
        </header>
        {viewer.url ? (
          <iframe
            src={viewer.url}
            title={viewer.title}
            allow="fullscreen; clipboard-read; clipboard-write"
            allowFullScreen
            loading="eager"
            referrerPolicy="strict-origin-when-cross-origin"
          ></iframe>
        ) : (
          <div className="viewer-pending">
            <strong>Tableau heat map publishing link pending</strong>
            <p>Add the published Tableau URL to VITE_TABLEAU_URL before the production frontend build.</p>
          </div>
        )}
        <p className="viewer-note">{viewer.note || 'If the embedded service blocks iframe viewing, use “Open separately” above.'}</p>
      </section>
    </div>
  )
}

function App() {
  const [metadata, setMetadata] = useState(SNAPSHOT.metadata)
  const [summary, setSummary] = useState(SNAPSHOT.summary)
  const [trend, setTrend] = useState(SNAPSHOT.trends)
  const [incidents, setIncidents] = useState(SNAPSHOT.incident_types)
  const [regions, setRegions] = useState(SNAPSHOT.regions)
  const [states, setStates] = useState(SNAPSHOT.states)
  const [seasonality, setSeasonality] = useState(SNAPSHOT.seasonality)
  const [forecast, setForecast] = useState(SNAPSHOT.forecasts['Region 4'])
  const [insights, setInsights] = useState(null)
  const [insightMode, setInsightMode] = useState('seasonality')
  const [comparisonRegions, setComparisonRegions] = useState(['Region 4', 'Region 6', 'Region 9'])
  const [comparisonForecasts, setComparisonForecasts] = useState([])
  const [comparisonLoading, setComparisonLoading] = useState(false)
  const [filters, setFilters] = useState({
    startYear: SNAPSHOT.metadata.years[0],
    endYear: SNAPSHOT.metadata.years[SNAPSHOT.metadata.years.length - 1],
    region: 'All Regions',
  })
  const [forecastRegion, setForecastRegion] = useState('Region 4')
  const [forecastHorizon, setForecastHorizon] = useState(12)
  const [apiState, setApiState] = useState('loading')
  const [analyticsLoading, setAnalyticsLoading] = useState(false)
  const [viewer, setViewer] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    async function loadMetadata() {
      try {
        const response = await fetch(`${API_BASE_URL}/metadata`, { signal: controller.signal })
        if (!response.ok) throw new Error('Metadata request failed.')
        const payload = await response.json()
        setMetadata(payload)
        setFilters({
          startYear: payload.years[0],
          endYear: payload.years[payload.years.length - 1],
          region: 'All Regions',
        })
        setForecastRegion(payload.regions.includes('Region 4') ? 'Region 4' : payload.regions[0])
        const preferredComparison = ['Region 4', 'Region 6', 'Region 9'].filter((region) => payload.regions.includes(region))
        setComparisonRegions([...preferredComparison, ...payload.regions.filter((region) => !preferredComparison.includes(region))].slice(0, 3))
      } catch (error) {
        if (error.name !== 'AbortError') setApiState('snapshot')
      }
    }
    loadMetadata()
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    async function loadAnalytics() {
      setAnalyticsLoading(true)
      const startDate = `${filters.startYear}-01-01`
      const endDate = `${filters.endYear}-12-31`
      const common = new URLSearchParams({ start_date: startDate, end_date: endDate })
      const regional = new URLSearchParams(common)
      if (filters.region !== 'All Regions') regional.set('region', filters.region)

      try {
        const responses = await Promise.all([
          fetch(`${API_BASE_URL}/summary?${regional}`, { signal: controller.signal }),
          fetch(`${API_BASE_URL}/trends?grain=year&${regional}`, { signal: controller.signal }),
          fetch(`${API_BASE_URL}/incident-types?limit=10&${regional}`, { signal: controller.signal }),
          fetch(`${API_BASE_URL}/regions?${common}`, { signal: controller.signal }),
          fetch(`${API_BASE_URL}/states?limit=10&${regional}`, { signal: controller.signal }),
          fetch(`${API_BASE_URL}/seasonality?${regional}`, { signal: controller.signal }),
        ])
        if (responses.some((response) => !response.ok)) {
          throw new Error('An analytics request failed.')
        }
        const [summaryData, trendData, incidentData, regionData, stateData, seasonalityData] = await Promise.all(
          responses.map((response) => response.json()),
        )
        setSummary(summaryData)
        setTrend(trendData)
        setIncidents(incidentData)
        setRegions(regionData)
        setStates(stateData)
        setSeasonality(seasonalityData)
        const insightResponse = await fetch(`${API_BASE_URL}/insights?${regional}`, { signal: controller.signal })
        setInsights(insightResponse.ok ? await insightResponse.json() : null)
        setApiState('connected')
      } catch (error) {
        if (error.name !== 'AbortError') {
          setApiState('snapshot')
          setSummary(SNAPSHOT.summary)
          setTrend(SNAPSHOT.trends)
          setIncidents(SNAPSHOT.incident_types)
          setRegions(SNAPSHOT.regions)
          setStates(SNAPSHOT.states)
          setSeasonality(SNAPSHOT.seasonality)
          setInsights(null)
        }
      } finally {
        setAnalyticsLoading(false)
      }
    }
    loadAnalytics()
    return () => controller.abort()
  }, [filters.startYear, filters.endYear, filters.region])

  useEffect(() => {
    const controller = new AbortController()
    async function loadForecast() {
      try {
        const response = await fetch(
          `${API_BASE_URL}/forecast?region=${encodeURIComponent(forecastRegion)}&horizon=${forecastHorizon}`,
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error('Forecast request failed.')
        setForecast(await response.json())
      } catch (error) {
        if (error.name !== 'AbortError') {
          const fallback = SNAPSHOT.forecasts[forecastRegion] || SNAPSHOT.forecasts['Region 4']
          setForecast({
            ...fallback,
            region: forecastRegion,
            horizon: forecastHorizon,
            points: [
              ...fallback.points.filter((point) => point.record_type === 'Historical'),
              ...fallback.points.filter((point) => point.record_type === 'Forecast').slice(0, forecastHorizon),
            ],
          })
        }
      }
    }
    loadForecast()
    return () => controller.abort()
  }, [forecastRegion, forecastHorizon])

  useEffect(() => {
    if (insightMode !== 'forecast-comparison' || comparisonRegions.length < 3) return undefined
    const controller = new AbortController()
    async function loadComparisonForecasts() {
      setComparisonLoading(true)
      try {
        const responses = await Promise.all(comparisonRegions.map((region) => fetch(
          `${API_BASE_URL}/forecast?region=${encodeURIComponent(region)}&horizon=${forecastHorizon}`,
          { signal: controller.signal },
        )))
        if (responses.some((response) => !response.ok)) throw new Error('Forecast comparison request failed.')
        setComparisonForecasts(await Promise.all(responses.map((response) => response.json())))
      } catch (error) {
        if (error.name !== 'AbortError') {
          setComparisonForecasts(comparisonRegions.map((region) => ({
            ...(SNAPSHOT.forecasts[region] || SNAPSHOT.forecasts['Region 4']),
            region,
            horizon: forecastHorizon,
          })))
        }
      } finally {
        setComparisonLoading(false)
      }
    }
    loadComparisonForecasts()
    return () => controller.abort()
  }, [insightMode, comparisonRegions, forecastHorizon])

  const forecastFloor = useMemo(() => nextForecastMonthKey(), [])
  const forecastDisplayPoints = useMemo(() => [
    ...(forecast?.points?.filter((point) => point.record_type === 'Historical') || []),
    ...(forecast?.points?.filter((point) => point.record_type === 'Forecast' && point.month >= forecastFloor).slice(0, forecastHorizon) || []),
  ], [forecast, forecastFloor, forecastHorizon])
  const forecastRows = useMemo(
    () => forecastDisplayPoints.filter((point) => point.record_type === 'Forecast'),
    [forecastDisplayPoints],
  )
  const activeInsights = useMemo(() => insights || buildFallbackInsights({
    summary,
    trend,
    states,
    incidents,
    regions,
    seasonality,
  }), [insights, summary, trend, states, incidents, regions, seasonality])
  const forecastTotal = forecastRows.reduce((total, row) => total + row.declaration_records, 0)
  const forecastAverage = forecastRows.length ? Math.round(forecastTotal / forecastRows.length) : 0
  const forecastPeak = forecastRows.length
    ? forecastRows.reduce((highest, row) => (row.declaration_records > highest.declaration_records ? row : highest))
    : null
  const forecastIncidentTotals = forecastRows.reduce((totals, row) => {
    if (!row.likely_incident_type) return totals
    totals[row.likely_incident_type] = (totals[row.likely_incident_type] || 0) + row.declaration_records
    return totals
  }, {})
  const forecastLeadingIncident = Object.entries(forecastIncidentTotals)
    .sort((left, right) => right[1] - left[1])[0]?.[0] || 'N/A'
  const forecastLeadingAreas = forecastRows.find(
    (row) => row.likely_incident_type === forecastLeadingIncident,
  )?.likely_areas || 'Region-wide'
  const filterDisabled = apiState !== 'connected'

  const updateStartYear = (value) => {
    const next = Number(value)
    setFilters((current) => ({ ...current, startYear: next, endYear: Math.max(current.endYear, next) }))
  }

  const updateEndYear = (value) => {
    const next = Number(value)
    setFilters((current) => ({ ...current, endYear: next, startYear: Math.min(current.startYear, next) }))
  }

  const updateComparisonRegion = (index, value) => {
    setComparisonRegions((current) => current.map((region, position) => position === index ? value : region))
  }

  const downloadForecast = () => {
    const lines = [
      'region,month,recordType,likelyIncidentType,incidentTypeSupport,incidentTypeConfidence,likelyAreas,declarationRecords,lowerEstimate,upperEstimate',
      ...forecastRows.map((row) => [
        forecast.region,
        `${row.month}-01`,
        row.record_type,
        row.likely_incident_type || '',
        row.incident_type_support ?? '',
        row.incident_type_confidence || '',
        row.likely_areas || '',
        row.declaration_records,
        row.lower_estimate ?? '',
        row.upper_estimate ?? '',
      ].join(',')),
    ]
    const url = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `disaster_intelligence_${forecast.region.toLowerCase().replace(' ', '_')}_${forecastHorizon}_month_forecast.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="site-shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Disaster Intelligence home">
          <span className="brand-mark">DI</span>
          <span>
            <strong>Disaster Intelligence</strong>
            <small>Analytics Capstone</small>
          </span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#analytics">Analytics</a>
          <a href="#heat-map">Heat Map</a>
          <a href="#forecast">Forecast</a>
          <a href="#architecture">Architecture</a>
          <a href="#dashboards">Dashboards</a>
        </nav>
        <button
          className="header-link"
          type="button"
          onClick={() => setViewer(STREAMLIT_VIEWER)}
        >
          Search by State
        </button>
      </header>

      <main id="top">
        <section className="hero-section">
          <div className="hero-copy">
            <p className="eyebrow">Public Data · Python · FastAPI · AWS · Tableau</p>
            <h1>Disaster Intelligence Dashboard</h1>
            <p className="hero-summary">
              Explore declaration history by time, incident type, state, and region. Use the interactive dashboard for quick comparisons, explore the embedded heat map, open Streamlit for state-level searches, and review future monthly estimates in the forecast section.
            </p>
            <div className="hero-actions">
              <a className="primary-button" href="#analytics">Explore Website Analytics</a>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setViewer(STREAMLIT_VIEWER)}
              >
                Search by State in Streamlit
              </button>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setViewer(TABLEAU_VIEWER)}
              >
                View Tableau Heat Map Popout
              </button>
            </div>
            <div className={`api-status ${apiState}`}>
              <span aria-hidden="true"></span>
              {apiState === 'connected'
                ? `Live API connected · ${metadata.data_source}`
                : apiState === 'loading'
                  ? 'Connecting to the project API'
                  : 'Published analytics snapshot active · filters unlock after API deployment'}
            </div>
          </div>
          <div className="hero-data-card">
            <div className="hero-card-heading">
              <span>Project record coverage</span>
              <strong>{formatNumber.format(summary.declaration_records)}</strong>
              <small>Declaration records</small>
            </div>
            <div className="hero-stat-grid">
              <div><span>Years</span><strong>{metadata.years[0]}–{metadata.years[metadata.years.length - 1]}</strong></div>
              <div><span>Regions</span><strong>{metadata.regions.length}</strong></div>
              <div><span>Top incident</span><strong>{summary.top_incident_type}</strong></div>
              <div><span>Peak year</span><strong>{summary.peak_year}</strong></div>
            </div>
            <div className="data-flow-mini">
              <span>Public data</span><b>→</b><span>S3</span><b>→</b><span>FastAPI</span><b>→</b><span>Analytics</span>
            </div>
          </div>
        </section>

        <section className="analytics-section" id="analytics">
          <div className="section-heading analytics-heading">
            <div>
              <p className="section-label">Interactive website analytics</p>
              <h2>Analyze the declaration record history directly on this page.</h2>
            </div>
            <p>Choose a year range and region to update the metrics, charts, and insights. Use Reset filters to return to the complete history.</p>
          </div>

          <div className="filter-panel">
            <label>
              <span>Start year</span>
              <select value={filters.startYear} onChange={(event) => updateStartYear(event.target.value)} disabled={filterDisabled}>
                {metadata.years.map((year) => <option value={year} key={year}>{year}</option>)}
              </select>
            </label>
            <label>
              <span>End year</span>
              <select value={filters.endYear} onChange={(event) => updateEndYear(event.target.value)} disabled={filterDisabled}>
                {metadata.years.map((year) => <option value={year} key={year}>{year}</option>)}
              </select>
            </label>
            <label>
              <span>Region and covered areas</span>
              <select value={filters.region} onChange={(event) => setFilters((current) => ({ ...current, region: event.target.value }))} disabled={filterDisabled}>
                <option>All Regions</option>
                {metadata.regions.map((region) => <option value={region} key={region}>{formatRegionLabel(region)}</option>)}
              </select>
            </label>
            <button
              type="button"
              onClick={() => setFilters({
                startYear: metadata.years[0],
                endYear: metadata.years[metadata.years.length - 1],
                region: 'All Regions',
              })}
              disabled={filterDisabled}
            >
              Reset filters
            </button>
            <div className={`filter-state ${analyticsLoading ? 'loading' : ''}`}>
              <span></span>{analyticsLoading ? 'Updating analytics' : apiState === 'connected' ? 'Live filters ready' : 'Snapshot view'}
            </div>
          </div>

          <div className="metric-strip">
            <MetricCard label="Declaration Records" value={formatNumber.format(summary.declaration_records)} note="Administrative declaration rows" />
            <MetricCard label="Unique Disaster Numbers" value={formatNumber.format(summary.unique_disaster_numbers)} note="Distinct disaster IDs" />
            <MetricCard label="Top State or Territory" value={summary.top_state} />
            <MetricCard label="Top Incident Type" value={summary.top_incident_type} />
            <MetricCard label="Peak Declaration Year" value={summary.peak_year} />
          </div>

          <InsightExplorer
            mode={insightMode}
            onModeChange={setInsightMode}
            insights={activeInsights}
            comparisonRegions={comparisonRegions}
            onComparisonRegionChange={updateComparisonRegion}
            availableRegions={metadata.regions}
            comparisonForecasts={comparisonForecasts}
            comparisonLoading={comparisonLoading}
            forecastFloor={forecastFloor}
          />

          <div className="chart-grid">
            <article className="chart-card chart-wide">
              <div className="chart-heading">
                <div><span>Time series</span><h3>Annual declaration-record trend</h3></div>
                <small>{filters.startYear}–{filters.endYear}</small>
              </div>
              <AnnualTrendChart points={trend.points} />
            </article>

            <article className="chart-card">
              <div className="chart-heading">
                <div><span>Incident analysis</span><h3>Leading incident types</h3></div>
                <small>Top 10</small>
              </div>
              <HorizontalBarChart points={incidents.points} />
            </article>

            <article className="chart-card">
              <div className="chart-heading">
                <div><span>Regional comparison</span><h3>Declaration records by region</h3></div>
                <small>All regions</small>
              </div>
              <HorizontalBarChart points={regions.points} compact labelFormatter={(name) => formatRegionLabel(name, true)} />
            </article>

            <article className="chart-card">
              <div className="chart-heading">
                <div><span>Geographic hotspots</span><h3>Top states and territories</h3></div>
                <small>Top 10</small>
              </div>
              <HorizontalBarChart points={states.points} compact />
            </article>

            <article className="chart-card chart-wide">
              <div className="chart-heading">
                <div><span>Seasonality</span><h3>Declaration records by calendar month</h3></div>
                <small>Historical distribution</small>
              </div>
              <SeasonalityChart points={seasonality.points} />
            </article>
          </div>
        </section>

        <TableauHeatMapSection onOpen={() => setViewer(TABLEAU_VIEWER)} />

        <section className="forecast-section" id="forecast">
          <div className="section-heading forecast-heading">
            <div>
              <p className="section-label">Regional forecasting</p>
              <h2>Forecast future monthly declaration-record volume by region.</h2>
            </div>
            <p>Choose a region and forecast length to view expected monthly record volume, likely incident categories, recent history, and a reasonable range for each future month.</p>
          </div>

          <div className="forecast-controls">
            <label>
              <span>Forecast region and covered areas</span>
              <select value={forecastRegion} onChange={(event) => setForecastRegion(event.target.value)}>
                {metadata.regions.map((region) => <option value={region} key={region}>{formatRegionLabel(region)}</option>)}
              </select>
            </label>
            <label>
              <span>Forecast horizon</span>
              <select value={forecastHorizon} onChange={(event) => setForecastHorizon(Number(event.target.value))}>
                {[6, 7, 8, 9, 10, 11, 12].map((months) => <option value={months} key={months}>{months} months</option>)}
              </select>
            </label>
            <button type="button" onClick={downloadForecast}>Download forecast CSV</button>
          </div>

          <div className="forecast-layout">
            <article className="chart-card forecast-chart-card">
              <div className="chart-heading">
                <div><span>{formatRegionLabel(forecast.region, true)}</span><h3>Historical monthly volume and future forecast</h3></div>
                <small>{forecastHorizon}-month outlook</small>
              </div>
              <ForecastChart points={forecastDisplayPoints} />
            </article>
            <aside className="forecast-summary">
              <div><span>Forecast-period records</span><strong>{formatNumber.format(forecastTotal)}</strong></div>
              <div><span>Average forecast month</span><strong>{formatNumber.format(forecastAverage)}</strong></div>
              <div>
                <span>Highest forecast month</span>
                <strong>{forecastPeak ? monthLabel(forecastPeak.month) : 'N/A'}</strong>
                <small>{forecastPeak ? `${formatNumber.format(forecastPeak.declaration_records)} records` : ''}</small>
              </div>
              <div>
                <span>Forecast begins</span>
                <strong>{monthLabel(forecast.forecast_start || forecastRows[0]?.month)}</strong>
                <small>{forecast.training_through ? `As of ${forecast.as_of_date || 'today'} · trained through ${monthLabel(forecast.training_through)}` : 'Future months only'}</small>
              </div>
              <div>
                <span>Leading incident category</span>
                <strong>{forecastLeadingIncident}</strong>
                <small>{forecastLeadingAreas}</small>
              </div>
              <p>{forecast.method}{forecast.validation_mae !== null && forecast.validation_mae !== undefined ? ` · Validation MAE ${forecast.validation_mae.toFixed(1)} records` : ''}</p>
            </aside>
          </div>

          <div className="forecast-table-wrap">
            <table>
              <thead><tr><th>Month</th><th>Likely incident category</th><th>Historical focus areas</th><th>Historical support</th><th>Forecast records</th><th>Lower estimate</th><th>Upper estimate</th></tr></thead>
              <tbody>
                {forecastRows.map((row) => (
                  <tr key={row.month}>
                    <td>{new Date(`${row.month}-01T00:00:00`).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</td>
                    <td>{row.likely_incident_type || 'N/A'}</td>
                    <td>{row.likely_areas || 'Region-wide'}</td>
                    <td>{row.incident_type_support !== null && row.incident_type_support !== undefined ? `${row.incident_type_support.toFixed(1)}% · ${row.incident_type_confidence || 'Historical pattern'}` : 'N/A'}</td>
                    <td>{formatNumber.format(row.declaration_records)}</td>
                    <td>{row.lower_estimate === null ? '—' : formatNumber.format(row.lower_estimate)}</td>
                    <td>{row.upper_estimate === null ? '—' : formatNumber.format(row.upper_estimate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="forecast-warning">
            Use the monthly volume and likely incident category as planning guides. The category is selected from recurring historical patterns within the chosen region and calendar month, so it will reflect regional conditions rather than claim that a specific event will happen in a specific city.
          </div>
        </section>

        <section className="architecture-section" id="architecture">
          <div className="section-heading">
            <div>
              <p className="section-label">AWS-supported architecture and API documentation</p>
              <h2>How declaration data reaches the public dashboard and API.</h2>
            </div>
            <p>Follow the steps below to see where the data comes from, how it is prepared, and how the dashboard delivers each result.</p>
          </div>
          <div className="architecture-flow">
            {[
              ['OpenFEMA source', 'Public declaration records'],
              ['Python pipeline', 'Extract, clean, curate'],
              ['Amazon S3', 'Datasets and website'],
              ['Forecast service', 'Regional monthly estimates'],
              ['FastAPI on EC2', 'JSON analytics endpoints'],
              ['CloudFront', 'HTTPS website and API routing'],
              ['React + dashboards', 'Public analysis experience'],
            ].map(([title, subtitle], index, items) => (
              <div className="flow-item" key={title}>
                <article><strong>{title}</strong><span>{subtitle}</span></article>
                {index < items.length - 1 ? <b>→</b> : null}
              </div>
            ))}
          </div>
          <div className="dashboard-grid api-documentation-grid">
            <article>
              <span className={`dashboard-tag ${apiState === 'connected' ? 'live' : 'development'}`}>{apiState === 'connected' ? 'Connected' : 'AWS-ready'}</span>
              <h3>FastAPI Documentation and Data Service</h3>
              <p>Open the live documentation to review available data endpoints, see request options, and test dashboard results directly in your browser.</p>
              <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">Open API Documentation</a>
            </article>
          </div>
        </section>

        <section className="dashboard-section" id="dashboards">
          <div className="section-heading">
            <div>
              <p className="section-label">Embedded project dashboards</p>
              <h2>Search declarations by state in Streamlit and explore the disaster heat map in Tableau.</h2>
            </div>
            <p>Use Streamlit to search and filter records by state or territory, or open the Tableau heat map to compare geographic concentrations. Each tool can open here or in a separate window.</p>
          </div>
          <div className="dashboard-grid dashboard-grid-two">
            <article>
              <span className="dashboard-tag live">Live</span>
              <h3>State Search in Streamlit</h3>
              <p>Select a state or territory to review declaration totals, incident types, annual and monthly trends, seasonality, regional comparisons, detailed records, forecasts, and CSV downloads.</p>
              <button type="button" onClick={() => setViewer(STREAMLIT_VIEWER)}>Open State Search Popout</button>
            </article>
            <article>
              <span className="dashboard-tag live">Published</span>
              <h3>Tableau Disaster Heat Map</h3>
              <p>Explore an interactive state-level disaster heat map with geographic hotspots, regional comparisons, incident patterns, filters, and presentation-ready KPIs.</p>
              <button type="button" onClick={() => setViewer(TABLEAU_VIEWER)}>View Heat Map Popout via Tableau</button>
            </article>
          </div>
        </section>

        <section className="details-section">
          <article>
            <p className="section-label">Research question</p>
            <h3>How do disaster declarations change across time and location?</h3>
            <p>The analysis examines long-term trends, seasonal activity, geographic concentrations, regional differences, and incident-type patterns that can support planning and situational awareness.</p>
          </article>
          <article>
            <p className="section-label">Data limitations</p>
            <h3>Declaration records are not a direct measure of disaster severity.</h3>
            <p>A disaster number can appear in multiple rows because designated areas are recorded separately. Declaration records also do not represent every hazardous event or total economic loss.</p>
          </article>
        </section>
      </main>

      <footer>
        <div>
          <strong>Disaster Intelligence Dashboard</strong>
          <p>Data source: Disaster Declarations Summaries v2.</p>
        </div>
        <div className="footer-links">
          <button type="button" onClick={() => setViewer(STREAMLIT_VIEWER)}>Streamlit State Search</button>
          <button type="button" onClick={() => setViewer(TABLEAU_VIEWER)}>Tableau Heat Map</button>
          {GITHUB_URL ? <a href={GITHUB_URL} target="_blank" rel="noreferrer">GitHub</a> : <span>Private GitHub repository</span>}
          <a href="#top">Back to top</a>
        </div>
      </footer>

      <ViewerModal viewer={viewer} onClose={() => setViewer(null)} />
    </div>
  )
}

export default App
