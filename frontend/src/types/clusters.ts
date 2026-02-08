/** Selected level-1 cluster for the 3D view. null = show all level-1 clusters. When set, 3D view shows that cluster's points grouped by its sub-clusters (level-2). */
export type SelectedCluster = { level: 1; cluster_id: number } | null;
