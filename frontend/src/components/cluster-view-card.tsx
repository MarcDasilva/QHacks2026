"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Scatter,
  ScatterChart,
  Text,
  XAxis,
  YAxis,
} from "recharts";
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
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { createClient } from "@/lib/supabase/client";

/** Load all UMAP points (2D chart auto-fits domain with padding). */
const MAX_POINTS = 12_000;
const LEVEL_1_CLUSTERS_LIMIT = 25;
const CHART_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

type Request2DRow = {
  request_id: number;
  x_2d: number;
  y_2d: number;
  top_cluster_id: number | null;
};

type ClusterRow = {
  cluster_id: number;
  level: number;
  size: number;
};

function buildConfig(clusterIds: number[]): ChartConfig {
  const config: ChartConfig = {
    x_2d: { label: "x" },
    y_2d: { label: "y" },
  };
  clusterIds.forEach((id, i) => {
    config[`cluster_${id}`] = {
      label: `Cluster ${id}`,
      color: CHART_COLORS[i % CHART_COLORS.length],
    };
  });
  return config;
}

export function ClusterViewCard() {
  const [points, setPoints] = useState<Request2DRow[]>([]);
  const [clusters, setClusters] = useState<ClusterRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();

    async function load() {
      try {
        const clustersRes = await supabase
          .from("clusters")
          .select("cluster_id, level, size")
          .eq("level", 1)
          .order("cluster_id")
          .limit(LEVEL_1_CLUSTERS_LIMIT);

        if (clustersRes.error) throw new Error(clustersRes.error.message);

        const level1Clusters = (clustersRes.data ?? []) as ClusterRow[];
        const clusterIds = level1Clusters.map((c) => c.cluster_id);
        if (clusterIds.length === 0) {
          setClusters([]);
          setPoints([]);
          setLoading(false);
          return;
        }

        const pointsRes = await supabase
          .from("request_2d")
          .select("request_id, x_2d, y_2d, top_cluster_id")
          .in("top_cluster_id", clusterIds)
          .order("request_id")
          .limit(MAX_POINTS);

        if (pointsRes.error) throw new Error(pointsRes.error.message);

        setPoints((pointsRes.data ?? []) as Request2DRow[]);
        setClusters(level1Clusters);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  const allowedClusterIds = useMemo(
    () => new Set(clusters.map((c) => c.cluster_id)),
    [clusters],
  );

  const { seriesByCluster, clusterIds, config, domain } = useMemo(() => {
    const byCluster = new Map<
      number,
      { x_2d: number; y_2d: number; request_id: number }[]
    >();
    for (const p of points) {
      const cid = p.top_cluster_id;
      if (cid == null || !allowedClusterIds.has(cid)) continue;
      if (!byCluster.has(cid)) byCluster.set(cid, []);
      byCluster
        .get(cid)!
        .push({ x_2d: p.x_2d, y_2d: p.y_2d, request_id: p.request_id });
    }
    const ids = Array.from(byCluster.keys()).sort((a, b) => a - b);
    const series = ids.map((id) => ({
      clusterId: id,
      data: byCluster.get(id) ?? [],
    }));

    // Domain with padding so all points fit and chart is zoomed out
    const pad = 0.08;
    let xMin = Infinity,
      xMax = -Infinity,
      yMin = Infinity,
      yMax = -Infinity;
    for (const p of points) {
      if (p.top_cluster_id == null || !allowedClusterIds.has(p.top_cluster_id))
        continue;
      xMin = Math.min(xMin, p.x_2d);
      xMax = Math.max(xMax, p.x_2d);
      yMin = Math.min(yMin, p.y_2d);
      yMax = Math.max(yMax, p.y_2d);
    }
    const xRange = xMax - xMin || 1;
    const yRange = yMax - yMin || 1;
    const domain = {
      x: [xMin - pad * xRange, xMax + pad * xRange] as [number, number],
      y: [yMin - pad * yRange, yMax + pad * yRange] as [number, number],
    };

    return {
      seriesByCluster: series,
      clusterIds: ids,
      config: buildConfig(ids),
      domain,
    };
  }, [points, allowedClusterIds]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Cluster view (level 1)</CardTitle>
          <CardDescription>
            2D projection of request embeddings for all 25 level-1 clusters.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex min-h-[320px] items-center justify-center">
          <p className="text-muted-foreground">Loading cluster data…</p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="flex min-h-[200px] items-center justify-center">
          <p className="text-destructive">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (points.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Cluster view (level 1)</CardTitle>
          <CardDescription>
            2D projection of request embeddings for all 25 level-1 clusters.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex min-h-[320px] items-center justify-center">
          <p className="text-muted-foreground text-sm">
            No 2D data yet. Run{" "}
            <code className="rounded bg-muted px-1">
              python scripts/compute_2d_umap.py
            </code>{" "}
            and apply the request_2d migration.
          </p>
        </CardContent>
      </Card>
    );
  }

  const clusterSizes = Object.fromEntries(
    clusters.map((c) => [c.cluster_id, c.size]),
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cluster view (level 1)</CardTitle>
        <CardDescription>
          All 25 level-1 clusters. Each dot is one request (2D UMAP). Showing
          all points (up to {MAX_POINTS.toLocaleString()}) with zoomed-out fit.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={config} className="h-[420px] w-full">
          <ScatterChart margin={{ left: 48, right: 12, bottom: 28, top: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              type="number"
              dataKey="x_2d"
              name="x"
              domain={domain.x}
              tickLine={false}
              axisLine={false}
              label={{
                value: "x (UMAP 1)",
                position: "insideBottom",
                offset: -8,
              }}
            />
            <YAxis
              type="number"
              dataKey="y_2d"
              name="y"
              domain={domain.y}
              tickLine={false}
              axisLine={false}
              label={{
                value: "y (UMAP 2)",
                content: (props: {
                  viewBox?: {
                    x: number;
                    y: number;
                    width: number;
                    height: number;
                  };
                  value?: string;
                }) => {
                  const vb = props.viewBox;
                  if (!vb) return null;
                  const x = vb.x - 20;
                  const y = vb.y + vb.height / 2;
                  return (
                    <Text
                      x={x}
                      y={y}
                      textAnchor="middle"
                      verticalAnchor="middle"
                      angle={-90}
                    >
                      {props.value}
                    </Text>
                  );
                },
              }}
            />
            <ChartTooltip
              content={<ChartTooltipContent />}
              cursor={{ strokeDasharray: "3 3" }}
            />
            <ChartLegend
              align="right"
              verticalAlign="top"
              content={<ChartLegendContent />}
            />
            {seriesByCluster.map((s) => (
              <Scatter
                key={s.clusterId}
                data={s.data}
                name={`Cluster ${s.clusterId}`}
                dataKey={`cluster_${s.clusterId}`}
                fill={config[`cluster_${s.clusterId}`]?.color as string}
                fillOpacity={0.6}
              />
            ))}
          </ScatterChart>
        </ChartContainer>
      </CardContent>
      <CardFooter className="flex flex-wrap gap-4 text-sm text-muted-foreground">
        <span>Showing {points.length.toLocaleString()} points</span>
        <span>{clusterIds.length} level-1 clusters</span>
        <span>
          {clusterIds
            .map(
              (id) =>
                `Cluster ${id}: ${(clusterSizes[id] ?? "—").toLocaleString()}`,
            )
            .join(" · ")}
        </span>
      </CardFooter>
    </Card>
  );
}
