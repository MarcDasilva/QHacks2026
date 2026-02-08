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
import Image from "next/image";

const DATABASE_OPTIONS = [
  { value: "capital-projects", label: "Capital Projects" },
  { value: "kingston-fire-rescue", label: "Kingston Fire and Rescue Dashboard" },
  { value: CRM_DATABASE_VALUE, label: "CRM Service Requests" },
  { value: "homelessness-services", label: "Homelessness Services" },
  { value: "kfla-children-youth", label: "KFLA Children and Youth Community Profiles" },
  { value: "road-closures", label: "Road Closures and Detours" },
  { value: "waste-collection", label: "Waste Collection Areas" },
  { value: "airport-zoning", label: "Airport Zoning Regulations" },
  { value: "road-snow-plow", label: "Road Snow Plow Routes" },
  { value: "parking-lot-areas", label: "Parking Lot Areas" },
  { value: "community-safety-zones", label: "Community Safety Zones" },
  { value: "walking-cycling", label: "Walking and Cycling Infrastructure" },
  { value: "household-travel-2019", label: "Household Travel Survey 2019" },
  { value: "ferry-docks", label: "Ferry Docks and Terminals" },
  { value: "transit-bus-gtfs", label: "Transit Bus Routes and Stops (GTFS-Static)" },
  { value: "building-permits", label: "Building Permits" },
  { value: "local-improvements", label: "Local Improvements Charge Registry" },
  { value: "mayoral-decision", label: "Mayoral Decision Registry" },
  { value: "neighborhood-boundaries", label: "Neighborhood Boundaries" },
  { value: "municipal-historic", label: "Municipal Historic Monuments" },
  { value: "active-heritage", label: "Active Heritage Applications" },
  { value: "electoral-district", label: "Electoral District Boundary" },
  { value: "unesco-heritage", label: "UNESCO World Heritage Sites" },
  { value: "voting-locations-2018", label: "Voting Locations (2018)" },
  { value: "air-photo-1957", label: "1957 Air Photo Service" },
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
        <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-4 px-4">
          <header className="flex flex-col items-center text-center">
            <p
              className="text-muted-foreground mt-8 text-lg md:text-xl"
              style={{ fontFamily: "Zodiak, sans-serif" }}
            >
              welcome to
            </p>
            <Image
              src="/Kingston.png"
              alt="Kingston"
              width={200}
              height={80}
              className="mt-1 mb-0 object-contain"
            />
            <h1
              className="text-center text-4xl font-normal tracking-tight sm:text-5xl md:text-7xl lg:text-8xl xl:text-9xl 2xl:text-[10rem] -mt-3 leading-tight"
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
            <SelectTrigger className="w-[320px] max-w-full">
              <SelectValue placeholder="Choose a dataset…" />
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
                Cluster view is only available for CRM Service Requests.
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
