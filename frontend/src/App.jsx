import { useEffect, useMemo, useState } from 'react'
import dashboardSnapshot from './data/dashboardSnapshot.json'
import './App.css'

const STREAMLIT_URL = 'https://disaster-intelligence-dashboard.streamlit.app/'
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
const TABLEAU_URL = import.meta.env.VITE_TABLEAU_URL || ''
const GITHUB_URL = import.meta.env.VITE_GITHUB_URL || ''
const formatNumber = new Intl.NumberFormat('en-US')
const SNAPSHOT = dashboardSnapshot

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
    <svg className="line-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Annual FEMA declaration record trend">
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

function HorizontalBarChart({ points, compact = false }) {
  if (!points?.length) {
    return <EmptyChart message="Category data is unavailable." />
  }

  const maximum = Math.max(...points.map((point) => point.declaration_records), 1)
  return (
    <div className={`horizontal-bars ${compact ? 'compact' : ''}`}>
      {points.map((point) => (
        <div className="bar-row" key={point.name}>
          <div className="bar-row-heading">
            <span>{point.name}</span>
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

  return (
    <div className="viewer-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="viewer-modal" role="dialog" aria-modal="true" aria-label={viewer.title}>
        <header className="viewer-header">
          <div>
            <span>Embedded project view</span>
            <strong>{viewer.title}</strong>
          </div>
          <div className="viewer-actions">
            {viewer.url ? (
              <a href={viewer.url} target="_blank" rel="noreferrer">Open separately</a>
            ) : null}
            <button type="button" onClick={onClose} aria-label="Close embedded view">×</button>
          </div>
        </header>
        {viewer.url ? (
          <iframe
            src={viewer.url}
            title={viewer.title}
            allow="fullscreen"
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
          ></iframe>
        ) : (
          <div className="viewer-pending">
            <strong>Tableau publishing link pending</strong>
            <p>Add the published Tableau URL to VITE_TABLEAU_URL before the production frontend build.</p>
          </div>
        )}
        <p className="viewer-note">If the embedded service blocks iframe viewing, use “Open separately” above.</p>
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

  const forecastRows = useMemo(
    () => forecast?.points?.filter((point) => point.record_type === 'Forecast').slice(0, forecastHorizon) || [],
    [forecast, forecastHorizon],
  )
  const forecastTotal = forecastRows.reduce((total, row) => total + row.declaration_records, 0)
  const forecastAverage = forecastRows.length ? Math.round(forecastTotal / forecastRows.length) : 0
  const forecastPeak = forecastRows.length
    ? forecastRows.reduce((highest, row) => (row.declaration_records > highest.declaration_records ? row : highest))
    : null
  const filterDisabled = apiState !== 'connected'

  const updateStartYear = (value) => {
    const next = Number(value)
    setFilters((current) => ({ ...current, startYear: next, endYear: Math.max(current.endYear, next) }))
  }

  const updateEndYear = (value) => {
    const next = Number(value)
    setFilters((current) => ({ ...current, endYear: next, startYear: Math.min(current.startYear, next) }))
  }

  const downloadForecast = () => {
    const lines = [
      'region,month,recordType,declarationRecords,lowerEstimate,upperEstimate',
      ...forecastRows.map((row) => [
        forecast.region,
        `${row.month}-01`,
        row.record_type,
        row.declaration_records,
        row.lower_estimate ?? '',
        row.upper_estimate ?? '',
      ].join(',')),
    ]
    const url = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `fema_${forecast.region.toLowerCase().replace(' ', '_')}_${forecastHorizon}_month_forecast.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="site-shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="FEMA Disaster Intelligence home">
          <span className="brand-mark">DI</span>
          <span>
            <strong>Disaster Intelligence</strong>
            <small>FEMA Analytics Capstone</small>
          </span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#analytics">Analytics</a>
          <a href="#forecast">Forecast</a>
          <a href="#architecture">Architecture</a>
          <a href="#dashboards">Dashboards</a>
        </nav>
        <button
          className="header-link"
          type="button"
          onClick={() => setViewer({ title: 'Live Streamlit Analytics', url: STREAMLIT_URL })}
        >
          Open Streamlit
        </button>
      </header>

      <main id="top">
        <section className="hero-section">
          <div className="hero-copy">
            <p className="eyebrow">OpenFEMA · Python · FastAPI · AWS · Tableau</p>
            <h1>FEMA declaration data, analytics, and forecasting in one public project.</h1>
            <p className="hero-summary">
              Explore historical declaration records across time, incident type, state, and FEMA region. The website includes its own analytics dashboard and regional forecast, with Streamlit and Tableau available in embedded popout views.
            </p>
            <div className="hero-actions">
              <a className="primary-button" href="#analytics">Explore Website Analytics</a>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setViewer({ title: 'Live Streamlit Analytics', url: STREAMLIT_URL })}
              >
                View Streamlit Popout
              </button>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setViewer({ title: 'Tableau Disaster Dashboard', url: TABLEAU_URL })}
              >
                View Tableau Popout
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
              <small>FEMA declaration records</small>
            </div>
            <div className="hero-stat-grid">
              <div><span>Years</span><strong>{metadata.years[0]}–{metadata.years[metadata.years.length - 1]}</strong></div>
              <div><span>Regions</span><strong>{metadata.regions.length}</strong></div>
              <div><span>Top incident</span><strong>{summary.top_incident_type}</strong></div>
              <div><span>Peak year</span><strong>{summary.peak_year}</strong></div>
            </div>
            <div className="data-flow-mini">
              <span>OpenFEMA</span><b>→</b><span>S3</span><b>→</b><span>FastAPI</span><b>→</b><span>Analytics</span>
            </div>
          </div>
        </section>

        <section className="analytics-section" id="analytics">
          <div className="section-heading analytics-heading">
            <div>
              <p className="section-label">Interactive website analytics</p>
              <h2>Analyze the declaration record history directly on this page.</h2>
            </div>
            <p>Filters update the API-driven metrics and charts after AWS deployment. The verified project snapshot remains visible when the API is offline.</p>
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
              <span>FEMA region</span>
              <select value={filters.region} onChange={(event) => setFilters((current) => ({ ...current, region: event.target.value }))} disabled={filterDisabled}>
                <option>All Regions</option>
                {metadata.regions.map((region) => <option value={region} key={region}>{region}</option>)}
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
            <MetricCard label="Unique Disaster Numbers" value={formatNumber.format(summary.unique_disaster_numbers)} note="Distinct FEMA disaster IDs" />
            <MetricCard label="Top State or Territory" value={summary.top_state} />
            <MetricCard label="Top Incident Type" value={summary.top_incident_type} />
            <MetricCard label="Peak Declaration Year" value={summary.peak_year} />
          </div>

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
                <div><span>Regional comparison</span><h3>Declaration records by FEMA region</h3></div>
                <small>All regions</small>
              </div>
              <HorizontalBarChart points={regions.points} compact />
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

        <section className="forecast-section" id="forecast">
          <div className="section-heading forecast-heading">
            <div>
              <p className="section-label">Regional forecasting</p>
              <h2>Estimate future monthly declaration-record volume.</h2>
            </div>
            <p>The estimate combines recurring monthly patterns with recent regional history. It forecasts administrative record volume, not individual disaster events.</p>
          </div>

          <div className="forecast-controls">
            <label>
              <span>Forecast region</span>
              <select value={forecastRegion} onChange={(event) => setForecastRegion(event.target.value)}>
                {metadata.regions.map((region) => <option value={region} key={region}>{region}</option>)}
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
                <div><span>{forecast.region}</span><h3>Historical monthly volume and forecast</h3></div>
                <small>{forecastHorizon}-month outlook</small>
              </div>
              <ForecastChart points={forecast.points} />
            </article>
            <aside className="forecast-summary">
              <div><span>Forecast-period records</span><strong>{formatNumber.format(forecastTotal)}</strong></div>
              <div><span>Average forecast month</span><strong>{formatNumber.format(forecastAverage)}</strong></div>
              <div>
                <span>Highest forecast month</span>
                <strong>{forecastPeak ? new Date(`${forecastPeak.month}-01T00:00:00`).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : 'N/A'}</strong>
                <small>{forecastPeak ? `${formatNumber.format(forecastPeak.declaration_records)} records` : ''}</small>
              </div>
              <p>{forecast.method}</p>
            </aside>
          </div>

          <div className="forecast-table-wrap">
            <table>
              <thead><tr><th>Month</th><th>Forecast records</th><th>Lower estimate</th><th>Upper estimate</th></tr></thead>
              <tbody>
                {forecastRows.map((row) => (
                  <tr key={row.month}>
                    <td>{new Date(`${row.month}-01T00:00:00`).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</td>
                    <td>{formatNumber.format(row.declaration_records)}</td>
                    <td>{row.lower_estimate === null ? '—' : formatNumber.format(row.lower_estimate)}</td>
                    <td>{row.upper_estimate === null ? '—' : formatNumber.format(row.upper_estimate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="forecast-warning">
            Forecasts can be affected by irregular declaration surges, limited recent observations, policy changes, and conditions that do not follow historical patterns. They must not be interpreted as predictions of disaster timing, location, severity, or occurrence.
          </div>
        </section>

        <section className="architecture-section" id="architecture">
          <div className="section-heading">
            <div>
              <p className="section-label">AWS-supported architecture</p>
              <h2>A complete path from OpenFEMA data to public analytics.</h2>
            </div>
            <p>The project uses the public CloudFront address assigned by AWS, so a custom domain is not required.</p>
          </div>
          <div className="architecture-flow">
            {[
              ['OpenFEMA API', 'Source declarations'],
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
        </section>

        <section className="dashboard-section" id="dashboards">
          <div className="section-heading">
            <div>
              <p className="section-label">Embedded project dashboards</p>
              <h2>Open Streamlit and Tableau without leaving the website.</h2>
            </div>
            <p>Each dashboard launches in a large in-page popout. A separate-window link remains available when a service prevents iframe embedding.</p>
          </div>
          <div className="dashboard-grid">
            <article>
              <span className="dashboard-tag live">Live</span>
              <h3>Streamlit Analytics</h3>
              <p>Detailed filters, KPI cards, annual and monthly trends, seasonality, regional comparisons, data tables, forecasting, and CSV downloads.</p>
              <button type="button" onClick={() => setViewer({ title: 'Live Streamlit Analytics', url: STREAMLIT_URL })}>Open Streamlit Popout</button>
            </article>
            <article>
              <span className={`dashboard-tag ${TABLEAU_URL ? 'live' : 'development'}`}>{TABLEAU_URL ? 'Published' : 'In development'}</span>
              <h3>Tableau Dashboard</h3>
              <p>State map, annual trend, seasonality heatmap, regional comparison, hotspot ranking, incident analysis, filters, and presentation-ready KPIs.</p>
              <button type="button" onClick={() => setViewer({ title: 'Tableau Disaster Dashboard', url: TABLEAU_URL })}>Open Tableau Popout</button>
            </article>
            <article>
              <span className={`dashboard-tag ${apiState === 'connected' ? 'live' : 'development'}`}>{apiState === 'connected' ? 'Connected' : 'AWS-ready'}</span>
              <h3>FastAPI Data Service</h3>
              <p>Health, metadata, summary, trend, region, state, incident-type, seasonality, and forecast endpoints prepared for EC2 and S3.</p>
              <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">Open API Documentation</a>
            </article>
          </div>
        </section>

        <section className="details-section">
          <article>
            <p className="section-label">Research question</p>
            <h3>How do FEMA disaster declarations change across time and location?</h3>
            <p>The analysis examines long-term trends, seasonal activity, geographic concentrations, regional differences, and incident-type patterns that can support planning and situational awareness.</p>
          </article>
          <article>
            <p className="section-label">Data limitations</p>
            <h3>Declaration records are not a direct measure of disaster severity.</h3>
            <p>A disaster number can appear in multiple rows because designated areas are recorded separately. FEMA declarations also do not represent every hazardous event or total economic loss.</p>
          </article>
        </section>
      </main>

      <footer>
        <div>
          <strong>FEMA Disaster Intelligence Dashboard</strong>
          <p>Data source: FEMA OpenFEMA Disaster Declarations Summaries v2.</p>
        </div>
        <div className="footer-links">
          <button type="button" onClick={() => setViewer({ title: 'Live Streamlit Analytics', url: STREAMLIT_URL })}>Streamlit</button>
          <button type="button" onClick={() => setViewer({ title: 'Tableau Disaster Dashboard', url: TABLEAU_URL })}>Tableau</button>
          {GITHUB_URL ? <a href={GITHUB_URL} target="_blank" rel="noreferrer">GitHub</a> : <span>Private GitHub repository</span>}
          <a href="#top">Back to top</a>
        </div>
      </footer>

      <ViewerModal viewer={viewer} onClose={() => setViewer(null)} />
    </div>
  )
}

export default App
