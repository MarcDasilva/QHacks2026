"use client";

import {
  CRM_DATABASE_VALUE,
  useDashboard,
} from "@/app/dashboard/dashboard-context";
import { ClusterListCard } from "@/components/cluster-list-card";
import { ClusterView3DCard } from "@/components/cluster-view-3d-card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const DATABASE_OPTIONS = [
  { value: "analytics", label: "Analytics Warehouse" },
  { value: "logs", label: "Logs Archive" },
  { value: CRM_DATABASE_VALUE, label: "CRM Database" },
  { value: "inventory", label: "Inventory DB" },
  { value: "support", label: "Support Tickets" },
];

export default function DashboardPage() {
  const {
    selectedDatabase,
    setSelectedDatabase,
    showClusterView,
    selectedCluster,
    setSelectedCluster,
  } = useDashboard();

  return (
    <div
      className={`min-h-0 w-full min-w-0 flex-1 overflow-auto py-2 ${
        showClusterView ? "flex flex-col gap-6" : "space-y-6"
      }`}
    >
      {!showClusterView ? (
        <div className="flex min-h-[50vh] flex-col items-center justify-center gap-6 px-4">
          <header className="flex flex-col items-center text-center">
            <p
              className="text-muted-foreground text-lg md:text-xl"
              style={{ fontFamily: "Zodiak, sans-serif" }}
            >
              welcome to
            </p>
            <h1
              className="text-center text-4xl font-normal tracking-tight sm:text-5xl md:text-7xl lg:text-8xl xl:text-9xl 2xl:text-[10rem]"
              style={{ fontFamily: "Array, sans-serif" }}
            >
              compass
            </h1>
          </header>
          <p
            className="text-muted-foreground text-sm"
            style={{ fontFamily: "Zodiak, sans-serif" }}
          >
            Select a dataset to begin
          </p>
          <Select
            value={selectedDatabase ?? ""}
            onValueChange={(value) => setSelectedDatabase(value || null)}
          >
            <SelectTrigger className="w-[240px]">
              <SelectValue placeholder="Choose a database…" />
            </SelectTrigger>
            <SelectContent>
              {DATABASE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {selectedDatabase != null &&
            selectedDatabase !== CRM_DATABASE_VALUE && (
              <p className="text-muted-foreground text-center text-sm">
                Cluster view is only available for CRM Database.
              </p>
            )}
        </div>
      ) : (
        <>
          <div className="min-h-0 min-w-0 flex-1">
            <ClusterView3DCard
              selectedCluster={selectedCluster}
              onSelectCluster={setSelectedCluster}
            />
          </div>
          <div className="shrink-0">
            <ClusterListCard
              selectedCluster={selectedCluster}
              onSelectCluster={setSelectedCluster}
            />
          </div>
        </>
      )}
    </div>
  );
}
