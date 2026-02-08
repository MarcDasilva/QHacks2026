"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";
import type { SelectedCluster } from "@/types/clusters";
import { cn } from "@/lib/utils";
import { IconChevronDown, IconChevronRight } from "@tabler/icons-react";
import * as Collapsible from "@radix-ui/react-collapsible";

/** Matches clusters table: cluster_id, parent_cluster_id (null for level 1), level, size. Each level-2 cluster has exactly one parent (level-1). */
type ClusterRow = {
  cluster_id: number;
  parent_cluster_id: number | null;
  level: number;
  size: number;
};

export function ClusterListCard({
  selectedCluster,
  onSelectCluster,
}: {
  selectedCluster: SelectedCluster;
  onSelectCluster: (cluster: SelectedCluster) => void;
}) {
  const [level1, setLevel1] = useState<ClusterRow[]>([]);
  const [level2ByParent, setLevel2ByParent] = useState<
    Map<number, ClusterRow[]>
  >(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();

    async function load() {
      try {
        const l1Res = await supabase
          .from("clusters")
          .select("cluster_id, parent_cluster_id, level, size")
          .eq("level", 1)
          .order("size", { ascending: false });

        if (l1Res.error) throw new Error(l1Res.error.message);
        setLevel1((l1Res.data ?? []) as ClusterRow[]);

        const l2Res = await supabase
          .from("clusters")
          .select("cluster_id, parent_cluster_id, level, size")
          .eq("level", 2)
          .order("size", { ascending: false });

        if (l2Res.error) throw new Error(l2Res.error.message);
        const l2 = (l2Res.data ?? []) as ClusterRow[];
        const byParent = new Map<number, ClusterRow[]>();
        for (const row of l2) {
          const parent = row.parent_cluster_id;
          if (parent == null) continue;
          if (!byParent.has(parent)) byParent.set(parent, []);
          byParent.get(parent)!.push(row);
        }
        setLevel2ByParent(byParent);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load clusters");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Clusters by size</CardTitle>
          <CardDescription>
            Level-1 clusters (sorted by request count). Click one to show all
            its sub-clusters in the 3D view above.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex min-h-[120px] items-center justify-center">
          <p className="text-muted-foreground text-sm">Loading clusters…</p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="flex min-h-[120px] items-center justify-center">
          <p className="text-destructive text-sm">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (level1.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Clusters by size</CardTitle>
          <CardDescription>
            No level-1 clusters in the database. Run hierarchical clustering
            first.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Clusters by size</CardTitle>
        <CardDescription>
          Expand with the chevron to see sub-clusters. Use View to show that
          cluster in the 3D view above.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {selectedCluster != null && (
          <button
            type="button"
            onClick={() => onSelectCluster(null)}
            className="mb-3 rounded-md border border-border bg-muted/50 px-2 py-1.5 text-sm font-medium transition-colors hover:bg-muted"
          >
            Clear selection
          </button>
        )}
        <ul className="space-y-0.5 text-sm">
          {level1.map((row, rankIndex) => {
            const subClusters = level2ByParent.get(row.cluster_id) ?? [];
            const subClustersBySize = [...subClusters].sort(
              (a, b) => b.size - a.size,
            );
            const isSelected =
              selectedCluster != null &&
              selectedCluster.cluster_id === row.cluster_id;
            const labelBySize = rankIndex + 1;

            return (
              <li key={`l1-${row.cluster_id}`}>
                <Collapsible.Root defaultOpen={false}>
                  <div
                    className={cn(
                      "flex items-center gap-1 rounded-md px-1 py-1",
                      isSelected && "bg-primary/10 ring-1 ring-primary/30",
                    )}
                  >
                    <Collapsible.Trigger asChild>
                      <button
                        type="button"
                        className="group flex size-7 shrink-0 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                        aria-label="Expand sub-clusters"
                      >
                        <IconChevronRight className="size-4 group-data-[state=open]:hidden" />
                        <IconChevronDown className="hidden size-4 group-data-[state=open]:block" />
                      </button>
                    </Collapsible.Trigger>
                    <span
                      className="shrink-0 font-medium tabular-nums text-black"
                      style={{ fontFamily: "Zodiak, sans-serif" }}
                    >
                      {labelBySize}
                    </span>
                    <span className="min-w-0 flex-1 font-medium">
                      Level 1, Cluster {row.cluster_id}
                    </span>
                    <span className="shrink-0 text-muted-foreground">
                      {row.size.toLocaleString()} requests
                    </span>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      className="shrink-0"
                      onClick={() =>
                        onSelectCluster({
                          level: 1,
                          cluster_id: row.cluster_id,
                        })
                      }
                    >
                      View
                    </Button>
                  </div>
                  <Collapsible.Content>
                    <ul className="ml-6 mt-0.5 space-y-0.5 border-l border-border pl-3">
                      {subClustersBySize.map((sub, subRankIndex) => (
                        <li
                          key={`l2-${row.cluster_id}-${sub.cluster_id}`}
                          className="flex items-center gap-2 py-1 text-muted-foreground"
                        >
                          <span
                            className="shrink-0 font-medium tabular-nums text-black"
                            style={{ fontFamily: "Zodiak, sans-serif" }}
                          >
                            {subRankIndex + 1}
                          </span>
                          <span>Level 2, Cluster {sub.cluster_id}</span>
                          <span className="text-muted-foreground/80">
                            {sub.size.toLocaleString()} requests
                          </span>
                        </li>
                      ))}
                    </ul>
                  </Collapsible.Content>
                </Collapsible.Root>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
