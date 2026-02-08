"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useDashboard } from "../dashboard-context";

export default function ReportsPage() {
  const { reportPdfUrl } = useDashboard();

  return (
    <div className="flex min-h-0 w-full min-w-0 flex-1 flex-col overflow-hidden py-2">
      <Card className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <CardHeader className="shrink-0">
          <CardTitle>Report</CardTitle>
          <CardDescription>
            Generated CRM analytics report.
          </CardDescription>
        </CardHeader>
        <CardContent className="min-h-0 flex-1 overflow-hidden p-6 pt-0">
          <div className="h-full min-h-[70vh] w-full overflow-hidden rounded-md border bg-muted/30">
            {reportPdfUrl ? (
              <iframe
                src={reportPdfUrl}
                title="CRM Analytics Report"
                className="h-full w-full border-0 min-h-[70vh]"
              />
            ) : (
              <div className="flex h-full min-h-[70vh] w-full items-center justify-center text-muted-foreground">
                No report yet. Complete the flow (cluster → analytics → report) to see the PDF here.
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
