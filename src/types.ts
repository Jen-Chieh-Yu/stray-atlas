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

/** stats/foundplace.json, the fields the analysis page reads. The file holds
 *  more (samples, place kinds, confidence bands). */
export interface FoundplacePayload {
  snapshot_date: string
  rows: number
  /** Where each row's county came from: the found-place text itself, the
   *  shelter holding the animal, or nowhere. */
  county_source: { text: number; shelter: number; none: number }
  /** Rows whose found-place text names a county other than the shelter's. */
  county_from_text_differs_from_shelter: number
}

/** meta.json. The footer reads only snapshot_date; the data quality page
 *  reads the rest, which is why the cleaning report is typed here in full
 *  rather than left as the two fields the footer happened to need. */
export interface DroppedColumn {
  column: string
  reason: 'all_blank' | 'zero_variance'
  distinct_values: number
  /** Present for zero_variance: the single value every row carries. */
  value?: string
}

export interface MetaPayload {
  snapshot_date: string
  generated_at_utc: string
  source_file: string
  rows: number
  columns_in_source: number
  columns_after_clean: number
  /** Source column name to its Chinese name, from data/reference/fields.json.
   *  One reference file rather than a label typed into each component. */
  fields: Record<string, string>
  /** Source columns the reference file has no name for yet. Non-empty means
   *  the source added a column; the cleaner logs a warning for it. */
  fields_without_label: string[]
  dropped_columns: DroppedColumn[]
  duplicate_columns: { dropped: string; identical_to: string }[]
  cleaning_actions: {
    opendate_sentinel_nulled: number
    opendate_in_the_future: number
    rows_without_createtime: number
  }
  /** Share of rows whose value is non-empty, per kept column. */
  coverage: Record<string, number>
  variety_groups: Record<'mixed' | 'breed' | 'unknown', number>
  areas: number
  shelters: number
  /** Four codes cover two shelters each, which is why shelters are keyed on
   *  name everywhere in this project. */
  shelter_pkid_collisions: { pkid: string; shelter_names: string[] }[]
  shelter_address_variants: { shelter_name: string; addresses: string[] }[]
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

/** stats/quality.json. Written by scripts/build_quality.py.
 *
 *  Everything here measures how a county RECORDS its animals, never how it
 *  keeps them. A low score is a gap in that county's open data and nothing
 *  more; the page says so in its own words and the types cannot, so this
 *  comment is the closest a reader of the code gets to the same warning. */
export type Grade = 'good' | 'fair' | 'poor' | 'na'

export interface QualityMetric {
  key: string
  label: string
  description: string
  /** Round numbers fixed by hand, not quantiles of this snapshot: a grade
   *  that moves because other counties moved is not one anyone can act on.
   *  They travel in the payload so the page can print the threshold it is
   *  applying rather than restate it (DESIGN.md 12.9). */
  thresholds: { good: number; fair: number }
  national: number
}

export interface QualityRow {
  rows: number
  scores: Record<string, number>
  /** 'na' wherever rows < min_rows_for_grade — the figure is still shown,
   *  the grade is withheld. */
  grades: Record<string, Grade>
}

export interface QualityCounty extends QualityRow {
  pkid: string
  name: string
  shelters: number
}

export interface QualityShelter extends QualityRow {
  /** Matches Shelter.id, so a row can link to /shelters/<id>. */
  id: string
  name: string
  county: string
}

export interface SterilizationShare {
  pkid: string
  name: string
  rows: number
  /** Shares of the county's rows, not counts. N is 未知／不適用. */
  T: number
  F: number
  N: number
}

export interface QualityPayload {
  snapshot_date: string
  generated_at_utc: string
  rows: number
  min_rows_for_grade: number
  metrics: QualityMetric[]
  counties: QualityCounty[]
  shelters: QualityShelter[]
  spellings: {
    /** One thing written several ways: 混種犬 / 混種狗 / 米克斯. */
    variety: { value: string; count: number }[]
    sterilization_by_county: SterilizationShare[]
  }
}

/** stats/features.json. Written by scripts/build_features.py.
 *
 *  Quantiles only, never means: the distribution is right-skewed by
 *  construction and a mean would mostly report the tail. Every figure is
 *  time already spent by an animal STILL in a shelter — never a speed of
 *  adoption, which this dataset cannot measure at all. */
export interface FeatureItem {
  label: string
  n: number
  p25_days: number
  median_days: number
  p75_days: number
  /** n below the payload's small_sample_below. Drawn, but flagged. */
  small_sample: boolean
}

export interface FeatureGroup {
  key: string
  title: string
  /** Shortest median first, so the rows follow the axis. */
  items: FeatureItem[]
}

export interface CoatShelter {
  id: string
  name: string
  county: string
  dark_n: number
  light_n: number
  dark_median_days: number
  light_median_days: number
  /** dark − light. Negative in the shelters that run the other way, which
   *  stay in the payload: dropping them would turn a tally into a claim. */
  difference_days: number
}

export interface FeaturesPayload {
  snapshot_date: string
  generated_at_utc: string
  /** The log axis both blocks are drawn on, so they cannot drift apart. */
  axis: {
    min_days: number
    max_days: number
    ticks: { days: number; label: string }[]
  }
  small_sample_below: number
  overall: FeatureItem
  groups: FeatureGroup[]
  /** The same coat comparison made within each shelter. The uncontrolled
   *  version is one of the groups above; this is the one that answers
   *  whether the gap is the coat or the shelter holding it. */
  dark_coat: {
    rule: string
    min_group: number
    shelters_compared: number
    shelters_dark_longer: number
    national: { dark: FeatureItem; light: FeatureItem }
    shelters: CoatShelter[]
  }
}
