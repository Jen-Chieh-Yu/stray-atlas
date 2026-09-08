export type Kind = '狗' | '貓' | '其他'
export type KindFilter = 'all' | Kind
export type Metric = 'count' | 'median'

export interface Summary {
  count: number
  /** The figure to read. The mean below is dragged up by a right-skewed tail
   *  (a stock snapshot over-samples long stays), and the maximum is one
   *  animal rather than a trend — both are labelled as secondary in the UI. */
  median_days: number | null
  mean_days: number | null
  min_days: number | null
  max_days: number | null
  histogram: number[]
}

export interface CountyStats extends Record<Kind, Summary> {
  pkid: string
  name: string
  shelters: number
  /** Share of this county's rows whose animal_foundplace names a real district. */
  district_coverage: number
  all: Summary
}

export interface CountyPayload {
  snapshot_date: string
  generated_at_utc: string
  county_source: 'shelter'
  buckets: { label: string; min: number; max: number | null }[]
  kinds: Kind[]
  total: Summary
  counties: CountyStats[]
}

export interface CountyFeature {
  type: 'Feature'
  properties: { county: string }
  geometry: { type: 'MultiPolygon'; coordinates: number[][][][] }
}

export interface CountyCollection {
  type: 'FeatureCollection'
  features: CountyFeature[]
}

export interface Shelter extends Record<Kind, Summary> {
  id: string
  name: string
  county: string
  area_pkid: string
  /** Three shelters carry more than one spelling; 瑞芳 is genuinely two sites. */
  addresses: string[]
  tel: string
  all: Summary
}

export interface ShelterPayload {
  snapshot_date: string
  generated_at_utc: string
  buckets: { label: string; min: number; max: number | null }[]
  kinds: Kind[]
  shelters: Shelter[]
}

export interface Animal {
  id: string
  subid: string
  /** Shelter id, matching Shelter.id. */
  shelter: string
  kind: Kind
  variety: string
  group: 'mixed' | 'breed' | 'unknown'
  sex: string
  body: string
  colour: string
  age: string
  sterilized: string
  opendate: string
  remark: string
  photo: string
  /** animal_createtime, not a day count: a count would change for every animal
   *  every day and rewrite the whole file on each rebuild. Days are computed
   *  against the snapshot date, never against today — this is a stock
   *  snapshot, so counting from now overstates it by however stale the deploy
   *  is. */
  created: string
}

export type Scope = 'all' | 'dog' | 'cat'
export type Scale = 'log' | 'linear'
export type Smoothing = 'fine' | 'standard' | 'smooth'

export interface KdeCurve {
  /** Silverman's value times this level's multiplier, in the units of the
   *  axis it was fitted on — log10(days) for the log scale, days for linear. */
  bandwidth: number
  points: [number, number][]
}

export interface HistogramBin {
  x0: number
  x1: number
  count: number
  /** count / (n × bin width), so bars and the KDE share one y axis. */
  density: number
}

export interface ScaleBlock {
  bins: HistogramBin[]
  kde: Record<Smoothing, KdeCurve>
}

export interface ScopeDistribution {
  count: number
  median_days: number
  mean_days: number
  p25_days: number
  p75_days: number
  p90_days: number
  max_days: number
  over_year: number
  over_4_years: number
  linear: ScaleBlock
  log: ScaleBlock
  /** [days, cumulative share], thinned. No bandwidth, no smoothing — the
   *  figures quoted in prose are read off this, not off the KDE. */
  ecdf: [number, number][]
}

export interface DistributionPayload {
  generated_at: string
  snapshot_date: string
  log_ticks: number[]
  bandwidth_levels: Smoothing[]
  scopes: Record<Scope, ScopeDistribution>
}

export interface ShelterPoint {
  id: string
  name: string
  county: string
  district: string
  lon: number
  lat: number
  count: number
  median_days: number | null
  mean_days: number | null
  max_days: number | null
  dogs: number
  cats: number
  tel: string
  /** Every spelling on record: 新北市瑞芳區公立動物之家 is two sites under one
   *  name, and picking one would hide that. */
  addresses: string[]
  /** True where the district came from the stated mapping in
   *  build_shelter_points.py rather than from the address itself. */
  manual: boolean
}

export interface ShelterPointPayload {
  generated_at: string
  snapshot_date: string
  position: 'district_centroid'
  unplaced: string[]
  points: ShelterPoint[]
}
