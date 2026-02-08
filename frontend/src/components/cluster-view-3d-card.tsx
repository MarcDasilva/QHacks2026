"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { createClient } from "@/lib/supabase/client";

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

export function ClusterView3DCard() {
  const [points, setPoints] = useState<Request3DRow[]>([]);
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

  const { data, layout } = useMemo(() => {
    const byCluster = new Map<
      number,
      { x: number[]; y: number[]; z: number[] }
    >();
    for (const p of points) {
      const cid = p.top_cluster_id;
      if (cid == null || p.z_2d == null) continue;
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
        xaxis: { title: "UMAP 1" },
        yaxis: { title: "UMAP 2" },
        zaxis: { title: "UMAP 3" },
        aspectmode: "data" as const,
      },
      showlegend: false,
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      font: { size: 11 },
      height: 420,
      autosize: true,
    };
    return { data, layout };
  }, [points]);

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
    <Card>
      <CardHeader>
        <CardTitle>Cluster view (3D)</CardTitle>
        <CardDescription>
          All 25 level-1 clusters in 3D UMAP space. Each dot is one request. Up
          to {MAX_POINTS.toLocaleString()} points.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Plot
          data={data}
          layout={layout}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%" }}
          useResizeHandler
        />
      </CardContent>
      <CardFooter className="text-sm text-muted-foreground">
        Drag to rotate, scroll to zoom
      </CardFooter>
    </Card>
  );
}
