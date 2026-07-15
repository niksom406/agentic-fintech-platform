"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { EmptyState } from "@/components/empty-state";
import { ReviewDecisionDialog } from "@/components/reviews/review-decision-dialog";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getCase, getReviews, submitReviewDecision } from "@/lib/api";
import type { CaseDetail, PendingReview } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

type Tab = "pending" | "completed";

function statusVariant(status: string) {
  if (status === "pending") return "warning";
  if (status === "approved") return "success";
  if (status === "rejected") return "destructive";
  if (status === "overridden") return "outline";
  return "outline";
}

function decisionVariant(decision: string | null | undefined) {
  if (decision === "APPROVE") return "success";
  if (decision === "REJECT") return "destructive";
  return "outline";
}

export default function ReviewsPage() {
  const [tab, setTab] = useState<Tab>("pending");
  const [pending, setPending] = useState<PendingReview[]>([]);
  const [completed, setCompleted] = useState<PendingReview[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedReview, setSelectedReview] = useState<PendingReview | null>(null);
  const [selectedCase, setSelectedCase] = useState<CaseDetail | null>(null);
  const [open, setOpen] = useState(false);

  async function loadReviews() {
    setLoading(true);
    try {
      const [pendingRes, allRes] = await Promise.all([
        getReviews("pending"),
        getReviews(),
      ]);
      setPending(pendingRes.items);
      setPendingCount(pendingRes.pending_count);
      setCompleted(allRes.items.filter((item) => item.review_status !== "pending"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadReviews();
  }, []);

  const rows = useMemo(() => (tab === "pending" ? pending : completed), [tab, pending, completed]);

  async function openReview(review: PendingReview) {
    setSelectedReview(review);
    const detail = await getCase(review.case_id);
    setSelectedCase(detail);
    setOpen(true);
  }

  async function handleDecision(payload: {
    reviewer_name: string;
    decision: "APPROVE" | "REJECT";
    reviewer_note: string;
    override_reason: string | null;
  }) {
    if (!selectedReview) return;
    await submitReviewDecision(selectedReview.review_id, payload);
    await loadReviews();
    setSelectedCase(null);
    setSelectedReview(null);
    setTab("completed");
  }

  return (
    <AppShell>
      <Card className="panel-gradient border-primary/20">
        <CardContent className="space-y-4">
          <Badge variant="outline">Human oversight layer</Badge>
          <h2 className="text-3xl font-semibold">Manual review queue</h2>
          <p className="text-muted-foreground">
            Escalated cases wait here for reviewer decision. Completed reviews stay available for audit history.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              variant={tab === "pending" ? "default" : "secondary"}
              onClick={() => setTab("pending")}
            >
              Pending ({pendingCount})
            </Button>
            <Button
              variant={tab === "completed" ? "default" : "secondary"}
              onClick={() => setTab("completed")}
            >
              Completed ({completed.length})
            </Button>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <Card>
          <CardContent className="py-10 text-sm text-muted-foreground">Loading reviews…</CardContent>
        </Card>
      ) : rows.length === 0 ? (
        <EmptyState
          title={tab === "pending" ? "No cases pending review" : "No completed reviews yet"}
          description={
            tab === "pending"
              ? "Escalated cases will appear here when the governance pipeline routes them for human oversight."
              : "Approved, rejected, and overridden decisions will show up in this history once reviewers act."
          }
        />
      ) : tab === "pending" ? (
        <Card>
          <CardHeader>
            <CardTitle>Escalated cases</CardTitle>
            <CardDescription>Open a case, inspect the trace, and record a final reviewer decision.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Case</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Product</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Flags</TableHead>
                  <TableHead>Queued</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((review) => (
                  <TableRow key={review.review_id}>
                    <TableCell className="font-semibold">{review.case_id}</TableCell>
                    <TableCell>{review.customer_name}</TableCell>
                    <TableCell>{review.requested_product_type}</TableCell>
                    <TableCell>
                      {review.risk_score ?? "N/A"} / {review.risk_level ?? "N/A"}
                    </TableCell>
                    <TableCell>{review.fairness_flag_count}</TableCell>
                    <TableCell>{formatDate(review.created_at)}</TableCell>
                    <TableCell>
                      <Button variant="secondary" onClick={() => void openReview(review)}>
                        Open review
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Completed review history</CardTitle>
            <CardDescription>
              Final human decisions, overrides, and reviewer notes for compliance follow-up.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Case</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Reviewer</TableHead>
                  <TableHead>Reviewed</TableHead>
                  <TableHead>Notes</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((review) => (
                  <TableRow key={review.review_id}>
                    <TableCell className="font-semibold">{review.case_id}</TableCell>
                    <TableCell>{review.customer_name}</TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(review.review_status)}>{review.review_status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={decisionVariant(review.final_decision)}>
                        {review.final_decision ?? "—"}
                      </Badge>
                    </TableCell>
                    <TableCell>{review.reviewer_name ?? "—"}</TableCell>
                    <TableCell>
                      {review.reviewed_at ? formatDate(review.reviewed_at) : formatDate(review.created_at)}
                    </TableCell>
                    <TableCell className="max-w-[220px]">
                      <p className="truncate text-sm text-muted-foreground">
                        {review.override_reason
                          ? `Override: ${review.override_reason}`
                          : review.reviewer_note || "—"}
                      </p>
                    </TableCell>
                    <TableCell>
                      <Link
                        href={`/cases/${review.case_id}`}
                        className={cn(buttonVariants({ variant: "secondary", size: "sm" }))}
                      >
                        View case
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <ReviewDecisionDialog
        open={open}
        onOpenChange={(nextOpen) => {
          setOpen(nextOpen);
          if (!nextOpen) {
            setSelectedReview(null);
            setSelectedCase(null);
          }
        }}
        review={selectedReview}
        caseDetail={selectedCase}
        onSubmit={handleDecision}
      />
    </AppShell>
  );
}
