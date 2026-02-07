"use client";

import { Cell, Pie, PieChart } from "recharts";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { AnalyticsFooter } from "../analytics-footer";
import { frequencyPieData, populationSummary } from "../data";

const PIE_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "oklch(0.55 0.2 220)",
  "oklch(0.58 0.18 280)",
  "oklch(0.52 0.16 160)",
  "oklch(0.62 0.2 30)",
  "oklch(0.58 0.2 340)",
  "oklch(0.55 0.18 200)",
  "oklch(0.55 0.18 260)",
  "oklch(0.52 0.16 140)",
  "oklch(0.65 0.22 20)",
  "oklch(0.58 0.2 320)",
  "oklch(0.55 0.18 180)",
];

export default function PopulationPage() {
  return (
    <div className="min-h-0 w-full min-w-0 flex-1 space-y-6 overflow-auto py-2">
      <Card>
        <CardHeader>
          <CardTitle>Current population (last period)</CardTitle>
          <CardDescription>
            Distribution of requests by category for the most recent period.
            Last row of the frequency table.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={{}} className="h-[420px] w-full">
            <PieChart>
              <ChartTooltip content={<ChartTooltipContent />} />
              <Pie
                data={frequencyPieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={85}
                outerRadius={130}
                paddingAngle={1}
                label={({ name, percent }) =>
                  `${name.slice(0, 12)}… ${(percent * 100).toFixed(0)}%`
                }
              >
                {frequencyPieData.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          </ChartContainer>
        </CardContent>
        <CardFooter className="p-0">
          <AnalyticsFooter
            title="Key metrics"
            columns={2}
            items={[
              {
                label: "Total requests",
                value: populationSummary.total.toLocaleString(),
              },
              {
                label: "Top category",
                value: `${populationSummary.topCategory} (${populationSummary.topPct}%)`,
              },
            ]}
          />
        </CardFooter>
      </Card>
    </div>
  );
}
