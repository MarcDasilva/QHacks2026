"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { createClient } from "@/lib/supabase/client";
import type { SelectedCluster } from "@/types/clusters";

const PLOT_MIN_HEIGHT = 320;

const Plot = dynamic(
  () => import("react-plotly.js").then((mod) => mod.default),
  { ssr: false },
);

const MAX_POINTS = 2_500;
const LEVEL_1_CLUSTERS_LIMIT = 25;
const PLOTLY_COLORS = [
  "#3b82f6",
  "#22c55e",
  "#eab308",
  "#ef4444",
  "#a855f7",
  "#06b6d4",
  "#f97316",
  "#ec4899",
  "#84cc16",
  "#6366f1",
];

type Request3DRow = {
  request_id: number;
  x_2d: number;
  y_2d: number;
  z_2d: number | null;
  top_cluster_id: number | null;
};

type ClusterRow = {
  cluster_id: number;
  level: number;
  size: number;
};

export function ClusterView3DCard({
  selectedCluster,
  onSelectCluster,
}: {
  selectedCluster: SelectedCluster;
  onSelectCluster: (cluster: SelectedCluster) => void;
}) {
  const [points, setPoints] = useState<Request3DRow[]>([]);
  const [clusters, setClusters] = useState<ClusterRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const plotContainerRef = useRef<HTMLDivElement>(null);
  const [plotHeight, setPlotHeight] = useState(PLOT_MIN_HEIGHT);

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
          .select("request_id, x_2d, y_2d, z_2d, top_cluster_id")
          .in("top_cluster_id", clusterIds)
          .not("z_2d", "is", null)
          .limit(MAX_POINTS)
          .order("request_id");

        if (pointsRes.error) throw new Error(pointsRes.error.message);

        setPoints((pointsRes.data ?? []) as Request3DRow[]);
        setClusters(level1Clusters);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  useEffect(() => {
    const el = plotContainerRef.current;
    if (!el) return;
    const updateHeight = () => {
      const { height } = el.getBoundingClientRect();
      if (height > 0)
        setPlotHeight((prev) => Math.max(PLOT_MIN_HEIGHT, Math.round(height)));
    };
    const ro = new ResizeObserver(updateHeight);
    ro.observe(el);
    updateHeight();
    const t1 = setTimeout(updateHeight, 100);
    const t2 = setTimeout(updateHeight, 600);
    const t3 = setTimeout(updateHeight, 1200);
    return () => {
      ro.disconnect();
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [loading, error, points.length]);

  const { data, layout } = useMemo(() => {
    const byCluster = new Map<
      number,
      { x: number[]; y: number[]; z: number[] }
    >();
    const filterClusterId =
      selectedCluster != null ? selectedCluster.cluster_id : null;
    for (const p of points) {
      const cid = p.top_cluster_id;
      if (cid == null || p.z_2d == null) continue;
      if (filterClusterId != null && cid !== filterClusterId) continue;
      if (!byCluster.has(cid)) byCluster.set(cid, { x: [], y: [], z: [] });
      const t = byCluster.get(cid)!;
      t.x.push(p.x_2d);
      t.y.push(p.y_2d);
      t.z.push(p.z_2d);
    }
    const clusterIds = Array.from(byCluster.keys()).sort((a, b) => a - b);
    const data = clusterIds.map((id, i) => {
      const t = byCluster.get(id)!;
      return {
        x: t.x,
        y: t.y,
        z: t.z,
        mode: "markers" as const,
        type: "scatter3d" as const,
        name: `Cluster ${id}`,
        marker: {
          size: 3,
          opacity: 0.7,
          color: PLOTLY_COLORS[i % PLOTLY_COLORS.length],
        },
      };
    });
    const layout = {
      margin: { l: 0, r: 0, t: 24, b: 0 },
      scene: {
        xaxis: { title: { text: "UMAP 1" } },
        yaxis: { title: { text: "UMAP 2" } },
        zaxis: { title: { text: "UMAP 3" } },
        aspectmode: "data" as const,
      },
      showlegend: false,
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      font: { size: 11 },
      height: plotHeight,
      autosize: true,
    };
    return { data, layout };
  }, [points, plotHeight, selectedCluster]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Cluster view (3D)</CardTitle>
          <CardDescription>
            3D UMAP projection of request embeddings for level-1 clusters.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex min-h-[320px] items-center justify-center">
          <p className="text-muted-foreground">Loading 3D data…</p>
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
          <CardTitle>Cluster view (3D)</CardTitle>
          <CardDescription>
            3D UMAP projection. Run the script with{" "}
            <code className="rounded bg-muted px-1">--3d</code> to generate 3D
            coordinates.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex min-h-[320px] items-center justify-center">
          <p className="text-muted-foreground text-sm">
            No 3D data yet. Run{" "}
            <code className="rounded bg-muted px-1">
              python scripts/compute_2d_umap.py --3d
            </code>{" "}
            and apply the <code className="rounded bg-muted px-1">z_2d</code>{" "}
            column migration.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="flex min-h-0 min-w-0 flex-1 flex-col">
      <CardHeader className="shrink-0">
        <CardTitle>Cluster view (3D)</CardTitle>
        <CardDescription>
          {selectedCluster != null
            ? `Showing Cluster ${selectedCluster.cluster_id} only.`
            : `All 25 level-1 clusters in 3D UMAP space. Each dot is one request. Up to ${MAX_POINTS.toLocaleString()} points.`}
        </CardDescription>
        {selectedCluster != null && (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="mt-2 w-fit"
            onClick={() => onSelectCluster(null)}
          >
            Show all clusters
          </Button>
        )}
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col px-6">
        <div
          ref={plotContainerRef}
          className="min-h-0 w-full flex-1"
          style={{ minHeight: PLOT_MIN_HEIGHT }}
        >
          <Plot
            data={data}
            layout={layout}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: "100%", height: "100%" }}
            useResizeHandler
          />
        </div>
      </CardContent>
      <CardFooter className="shrink-0 text-sm text-muted-foreground">
        Drag to rotate, scroll to zoom
      </CardFooter>
    </Card>
  );
}
