"use client";

import { useEffect, useState } from "react";

import type { CaseDetail, PendingReview } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { formatCurrency } from "@/lib/utils";

interface ReviewDecisionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  review: PendingReview | null;
  caseDetail: CaseDetail | null;
  onSubmit: (payload: { reviewer_name: string; decision: "APPROVE" | "REJECT"; reviewer_note: string; override_reason: string | null }) => Promise<void>;
}

export function ReviewDecisionDialog({ open, onOpenChange, review, caseDetail, onSubmit }: ReviewDecisionDialogProps) {
  const [reviewerName, setReviewerName] = useState("");
  const [decision, setDecision] = useState<"APPROVE" | "REJECT">("APPROVE");
  const [reviewerNote, setReviewerNote] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (open && review) {
      setReviewerName("");
      setDecision("APPROVE");
      setReviewerNote("");
      setOverrideReason("");
      setFormError(null);
    }
  }, [open, review?.review_id]);

  if (!open || !review) {
    return null;
  }

  async function handleSubmit() {
    const name = reviewerName.trim();
    const note = reviewerNote.trim();
    const override = overrideReason.trim();

    if (!name) {
      setFormError("Reviewer name is required.");
      return;
    }
    if (note.length < 10) {
      setFormError("Reviewer note must be at least 10 characters (required for audit).");
      return;
    }

    setFormError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        reviewer_name: name,
        decision,
        reviewer_note: note,
        override_reason: override || null,
      });
      setReviewerName("");
      setDecision("APPROVE");
      setReviewerNote("");
      setOverrideReason("");
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit review.";
      // Surface FastAPI validation detail more cleanly when present
      try {
        const parsed = JSON.parse(message) as { detail?: Array<{ msg?: string }> | string };
        if (typeof parsed.detail === "string") {
          setFormError(parsed.detail);
        } else if (Array.isArray(parsed.detail) && parsed.detail[0]?.msg) {
          setFormError(parsed.detail.map((d) => d.msg).join(" "));
        } else {
          setFormError(message);
        }
      } catch {
        setFormError(message);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/60 p-4 backdrop-blur">
      <div className="mx-auto mt-10 max-w-5xl rounded-[28px] border border-border/70 bg-card p-6 shadow-panel">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Human Review Decision</p>
            <h3 className="mt-2 text-2xl font-semibold">{review.case_id}</h3>
          </div>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            <Card className="panel-gradient">
              <CardContent className="grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-sm text-muted-foreground">Customer</p>
                  <p className="mt-2 text-lg font-semibold">{review.customer_name}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Product</p>
                  <p className="mt-2 text-lg font-semibold">{review.requested_product_type}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Current routed decision</p>
                  <Badge variant="warning" className="mt-2">
                    {review.system_decision ?? "Pending"}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Risk score</p>
                  <p className="mt-2 text-lg font-semibold">{review.risk_score ?? "N/A"}</p>
                </div>
              </CardContent>
            </Card>

            {caseDetail ? (
              <Card>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="text-sm text-muted-foreground">Loan amount</p>
                      <p className="mt-1 font-semibold">
                        {formatCurrency(Number(caseDetail.case_input?.normalized_payload?.loan_amount ?? 0))}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Annual income</p>
                      <p className="mt-1 font-semibold">
                        {formatCurrency(Number(caseDetail.case_input?.normalized_payload?.annual_income ?? 0))}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Governance status</p>
                      <p className="mt-1 font-semibold">{caseDetail.governance_status}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Fairness flags</p>
                      <p className="mt-1 font-semibold">{caseDetail.fairness_flag_count}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Explainability trace</p>
                    <p className="mt-2 text-sm leading-7">{caseDetail.final_explanation}</p>
                  </div>
                </CardContent>
              </Card>
            ) : null}
          </div>

          <Card>
            <CardContent className="space-y-4">
              <div>
                <p className="mb-2 text-sm font-medium">Reviewer name</p>
                <Input value={reviewerName} onChange={(event) => setReviewerName(event.target.value)} placeholder="Maria Chen" />
              </div>
              <div>
                <p className="mb-2 text-sm font-medium">Decision</p>
                <div className="flex gap-2">
                  <Button variant={decision === "APPROVE" ? "default" : "secondary"} onClick={() => setDecision("APPROVE")}>
                    Approve
                  </Button>
                  <Button variant={decision === "REJECT" ? "destructive" : "secondary"} onClick={() => setDecision("REJECT")}>
                    Reject
                  </Button>
                </div>
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">Reviewer note</p>
                  <p className="text-xs text-muted-foreground">{reviewerNote.trim().length}/10 min</p>
                </div>
                <Textarea
                  value={reviewerNote}
                  onChange={(event) => setReviewerNote(event.target.value)}
                  placeholder="Document the review outcome and any control notes (at least 10 characters)."
                />
              </div>
              <div>
                <p className="mb-2 text-sm font-medium">Override reason</p>
                <Textarea
                  value={overrideReason}
                  onChange={(event) => setOverrideReason(event.target.value)}
                  placeholder="Required only if your decision differs from the system recommendation."
                />
              </div>
              {formError ? (
                <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {formError}
                </div>
              ) : null}
              <Button className="w-full" onClick={() => void handleSubmit()} disabled={submitting}>
                {submitting ? "Submitting..." : "Submit review decision"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
