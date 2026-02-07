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
] as const

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
]

// Priority quadrant: scatter (time_to_close_days vs request_count, bubble_size)
export const priorityQuadrantData = [
  { group: "Garbage, recycling and organics", time_to_close_days: 3, request_count: 40526, bubble_size: 0, priority_category: "Medium Priority" },
  { group: "Roads, traffic and sidewalks", time_to_close_days: 125.2, request_count: 24091, bubble_size: 82, priority_category: "High Priority (Systemic)" },
  { group: "Parking", time_to_close_days: 3, request_count: 23199, bubble_size: 0, priority_category: "Medium Priority" },
  { group: "Recreation and leisure", time_to_close_days: 4, request_count: 11875, bubble_size: 0, priority_category: "Medium Priority" },
  { group: "Transit", time_to_close_days: 8, request_count: 7912, bubble_size: 0, priority_category: "Medium Priority" },
  { group: "Trees", time_to_close_days: 38, request_count: 7909, bubble_size: 4, priority_category: "High Priority (Systemic)" },
  { group: "City General", time_to_close_days: 3, request_count: 6627, bubble_size: 0, priority_category: "Medium Priority" },
  { group: "Building", time_to_close_days: 9, request_count: 5059, bubble_size: 1, priority_category: "High Priority (Systemic)" },
  { group: "Parks", time_to_close_days: 46.5, request_count: 4448, bubble_size: 2, priority_category: "Medium Priority" },
  { group: "Office of the City Clerk", time_to_close_days: 5, request_count: 1689, bubble_size: 0, priority_category: "Low Priority" },
  { group: "Engineering, infrastructure and construction", time_to_close_days: 91.9, request_count: 1623, bubble_size: 11, priority_category: "Medium Priority" },
  { group: "Planning", time_to_close_days: 46.4, request_count: 865, bubble_size: 0, priority_category: "Medium Priority" },
  { group: "Licensing", time_to_close_days: 7, request_count: 559, bubble_size: 0, priority_category: "Low Priority" },
  { group: "Arts and culture", time_to_close_days: 8, request_count: 171, bubble_size: 1, priority_category: "Low Priority" },
  { group: "Environment", time_to_close_days: 8.1, request_count: 160, bubble_size: 0, priority_category: "Medium Priority" },
  { group: "Real estate", time_to_close_days: 55, request_count: 31, bubble_size: 0, priority_category: "Medium Priority" },
]

// Backlog rank list: bar (category vs total_unresolved)
export const backlogBarData = [
  { category: "Roads, traffic and sidewalks", total_unresolved: 82 },
  { category: "Engineering, infrastructure and construction", total_unresolved: 11 },
  { category: "Trees", total_unresolved: 4 },
  { category: "Parks", total_unresolved: 2 },
  { category: "Building", total_unresolved: 1 },
  { category: "Arts and culture", total_unresolved: 1 },
]
