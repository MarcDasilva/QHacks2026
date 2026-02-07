// Frequency over time: line chart (time vs selected categories) + last row for pie (current population)
export const frequencyLineData = [
  { time: "2019-10", garbage: 860, roads: 331, recreation: 16 },
  { time: "2020-04", garbage: 1363, roads: 286, recreation: 6 },
  { time: "2020-10", garbage: 930, roads: 297, recreation: 97 },
  { time: "2021-04", garbage: 1121, roads: 367, recreation: 34 },
  { time: "2021-10", garbage: 922, roads: 412, recreation: 217 },
  { time: "2022-04", garbage: 761, roads: 532, recreation: 342 },
  { time: "2022-10", garbage: 500, roads: 417, recreation: 163 },
  { time: "2023-04", garbage: 407, roads: 486, recreation: 242 },
  { time: "2023-10", garbage: 552, roads: 392, recreation: 384 },
  { time: "2024-06", garbage: 301, roads: 445, recreation: 588 },
];

// Last row of frequency table = current population for pie chart
export const frequencyPieData = [
  { name: "Arts and culture", value: 9 },
  { name: "Building", value: 338 },
  { name: "City General", value: 154 },
  { name: "Engineering, infrastructure and construction", value: 67 },
  { name: "Environment", value: 2 },
  { name: "Garbage, recycling and organics", value: 301 },
  { name: "Licensing", value: 38 },
  { name: "Office of the City Clerk", value: 76 },
  { name: "Parking", value: 118 },
  { name: "Parks", value: 34 },
  { name: "Planning", value: 3 },
  { name: "Real estate", value: 3 },
  { name: "Recreation and leisure", value: 588 },
  { name: "Roads, traffic and sidewalks", value: 445 },
  { name: "Transit", value: 130 },
  { name: "Trees", value: 273 },
];

// Priority quadrant: scatter (time_to_close_days vs request_count, bubble_size)
export const priorityQuadrantData = [
  {
    group: "Garbage, recycling and organics",
    time_to_close_days: 3,
    request_count: 40526,
    bubble_size: 0,
    priority_category: "Medium Priority",
  },
  {
    group: "Roads, traffic and sidewalks",
    time_to_close_days: 125.2,
    request_count: 24091,
    bubble_size: 82,
    priority_category: "High Priority (Systemic)",
  },
  {
    group: "Parking",
    time_to_close_days: 3,
    request_count: 23199,
    bubble_size: 0,
    priority_category: "Medium Priority",
  },
  {
    group: "Recreation and leisure",
    time_to_close_days: 4,
    request_count: 11875,
    bubble_size: 0,
    priority_category: "Medium Priority",
  },
  {
    group: "Transit",
    time_to_close_days: 8,
    request_count: 7912,
    bubble_size: 0,
    priority_category: "Medium Priority",
  },
  {
    group: "Trees",
    time_to_close_days: 38,
    request_count: 7909,
    bubble_size: 4,
    priority_category: "High Priority (Systemic)",
  },
  {
    group: "City General",
    time_to_close_days: 3,
    request_count: 6627,
    bubble_size: 0,
    priority_category: "Medium Priority",
  },
  {
    group: "Building",
    time_to_close_days: 9,
    request_count: 5059,
    bubble_size: 1,
    priority_category: "High Priority (Systemic)",
  },
  {
    group: "Parks",
    time_to_close_days: 46.5,
    request_count: 4448,
    bubble_size: 2,
    priority_category: "Medium Priority",
  },
  {
    group: "Office of the City Clerk",
    time_to_close_days: 5,
    request_count: 1689,
    bubble_size: 0,
    priority_category: "Low Priority",
  },
  {
    group: "Engineering, infrastructure and construction",
    time_to_close_days: 91.9,
    request_count: 1623,
    bubble_size: 11,
    priority_category: "Medium Priority",
  },
  {
    group: "Planning",
    time_to_close_days: 46.4,
    request_count: 865,
    bubble_size: 0,
    priority_category: "Medium Priority",
  },
  {
    group: "Licensing",
    time_to_close_days: 7,
    request_count: 559,
    bubble_size: 0,
    priority_category: "Low Priority",
  },
  {
    group: "Arts and culture",
    time_to_close_days: 8,
    request_count: 171,
    bubble_size: 1,
    priority_category: "Low Priority",
  },
  {
    group: "Environment",
    time_to_close_days: 8.1,
    request_count: 160,
    bubble_size: 0,
    priority_category: "Medium Priority",
  },
  {
    group: "Real estate",
    time_to_close_days: 55,
    request_count: 31,
    bubble_size: 0,
    priority_category: "Medium Priority",
  },
];

// Backlog rank list: bar (category vs total_unresolved)
export const backlogBarData = [
  { category: "Roads, traffic and sidewalks", total_unresolved: 82 },
  {
    category: "Engineering, infrastructure and construction",
    total_unresolved: 11,
  },
  { category: "Trees", total_unresolved: 4 },
  { category: "Parks", total_unresolved: 2 },
  { category: "Building", total_unresolved: 1 },
  { category: "Arts and culture", total_unresolved: 1 },
];

// Latest change: last period vs previous (for Frequency line chart)
export const frequencyLatestChange = {
  period: "2024-06 vs 2023-10",
  series: [
    {
      key: "garbage",
      label: "Garbage, recycling and organics",
      value: 301,
      prev: 552,
      changePct: -45.5,
    },
    {
      key: "roads",
      label: "Roads, traffic and sidewalks",
      value: 445,
      prev: 392,
      changePct: 13.5,
    },
    {
      key: "recreation",
      label: "Recreation and leisure",
      value: 588,
      prev: 384,
      changePct: 53.1,
    },
  ],
};

// Total requests by category (from fcr_by_category.csv) for population summary
const totalRequestsByCategory = [
  24091, 7909, 865, 5059, 1623, 160, 559, 31, 23199, 4448, 1689, 11875, 171,
  6626, 40526, 7912,
];
const _totalRequestsSum = totalRequestsByCategory.reduce((s, n) => s + n, 0);

// Summary for Current population (pie): total requests from CSV, top category from pie
const _pieTotal = frequencyPieData.reduce((s, d) => s + d.value, 0);
const _topPop = frequencyPieData.length
  ? frequencyPieData.reduce(
      (a, b) => (a.value >= b.value ? a : b),
      frequencyPieData[0],
    )
  : null;
export const populationSummary = {
  total: _totalRequestsSum,
  topCategory: _topPop?.name ?? "Recreation and leisure",
  topValue: _topPop?.value ?? 588,
  topPct: _pieTotal && _topPop ? Math.round((_topPop.value / _pieTotal) * 100) : 0,
};

// Summary for Priority quadrant
export const prioritySummary = {
  highPriorityCount: priorityQuadrantData.filter((d) =>
    d.priority_category?.includes("High"),
  ).length,
  totalRequests: priorityQuadrantData.reduce((s, d) => s + d.request_count, 0),
  avgTimeToClose: Math.round(
    priorityQuadrantData.reduce((s, d) => s + d.time_to_close_days, 0) /
      priorityQuadrantData.length,
  ),
};

// Summary for Backlog rank list
export const backlogSummary = {
  totalUnresolved: backlogBarData.reduce((s, d) => s + d.total_unresolved, 0),
  topCategory: backlogBarData[0]?.category ?? "—",
  topValue: backlogBarData[0]?.total_unresolved ?? 0,
};

// Geographic hot spots: electoral_district, volume, unresolved, slow_p90 (heat map)
export const geographicHotSpotsData = [
  { district: "King's Town", volume: 8394, unresolved: 2, slow_p90: 8 },
  { district: "Sydenham", volume: 6832, unresolved: 1, slow_p90: 5 },
  { district: "Williamsville", volume: 4382, unresolved: 2, slow_p90: 10 },
  { district: "Kingscourt-Rideau", volume: 4363, unresolved: 5, slow_p90: 26 },
  {
    district: "Loyalist-Cataraqui",
    volume: 4336,
    unresolved: 8,
    slow_p90: 29.3,
  },
  { district: "Pittsburgh", volume: 4013, unresolved: 5, slow_p90: 32 },
  { district: "Trillium", volume: 3435, unresolved: 4, slow_p90: 16 },
  { district: "Countryside", volume: 3410, unresolved: 3, slow_p90: 64 },
  { district: "Portsmouth", volume: 3345, unresolved: 2, slow_p90: 23 },
  { district: "Collins-Bayridge", volume: 3331, unresolved: 3, slow_p90: 30 },
  {
    district: "Meadowbrook-Strathcona",
    volume: 3297,
    unresolved: 2,
    slow_p90: 28,
  },
  { district: "Lakeside", volume: 3249, unresolved: 9, slow_p90: 33.1 },
];

export const geographicSummary = {
  highestVolume: { district: "King's Town", volume: 8394 },
  slowestP90: { district: "Countryside", slow_p90: 64 },
  totalDistricts: geographicHotSpotsData.length,
};
