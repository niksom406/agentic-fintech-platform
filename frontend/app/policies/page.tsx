"use client";

import { useEffect, useState } from "react";
import { History, RotateCcw } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PolicyTable } from "@/components/policies/policy-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  getPolicies,
  getPolicyHistory,
  getPolicyVersion,
  rollbackPolicy,
  updatePolicies,
} from "@/lib/api";
import type { PolicyRule, PolicyVersion, PolicyVersionSummary } from "@/lib/types";
import { formatDate } from "@/lib/utils";

export default function PoliciesPage() {
  const [policy, setPolicy] = useState<PolicyVersion | null>(null);
  const [versions, setVersions] = useState<PolicyVersionSummary[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [rules, setRules] = useState<PolicyRule[]>([]);
  const [createdBy, setCreatedBy] = useState("policy-admin");
  const [saving, setSaving] = useState(false);
  const [rollingBackId, setRollingBackId] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadActive() {
    const activePolicy = await getPolicies();
    setPolicy(activePolicy);
    setName(activePolicy.name);
    setDescription(activePolicy.description ?? "");
    setRules(activePolicy.rules);
  }

  async function loadHistory() {
    const history = await getPolicyHistory();
    setVersions(history.versions);
  }

  useEffect(() => {
    async function load() {
      try {
        await Promise.all([loadActive(), loadHistory()]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load policies.");
      }
    }
    void load();
  }, []);

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const publishResult = await updatePolicies({
        name,
        description,
        rules,
        created_by: createdBy,
      });
      await Promise.all([loadActive(), loadHistory()]);
      setMessage(`Saved as new active policy version ${publishResult.new_version}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to publish policy.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRollback(version: PolicyVersionSummary) {
    if (version.is_active) return;
    const confirmed = window.confirm(
      `Roll back to ${version.version} (${version.name})? This reactivates that version and deactivates the current one.`,
    );
    if (!confirmed) return;

    setRollingBackId(version.id);
    setMessage(null);
    setError(null);
    try {
      const restored = await rollbackPolicy(version.id);
      await Promise.all([loadActive(), loadHistory()]);
      setMessage(`Rolled back to ${restored.version}. It is now the active policy.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rollback failed.");
    } finally {
      setRollingBackId(null);
    }
  }

  async function handleLoadVersion(version: PolicyVersionSummary) {
    setError(null);
    try {
      const detail = await getPolicyVersion(version.id);
      setName(detail.name);
      setDescription(detail.description ?? "");
      setRules(detail.rules as PolicyRule[]);
      setMessage(`Loaded ${detail.version} into the editor. Save to publish as a new version, or roll back to reactivate it.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load policy version.");
    }
  }

  return (
    <AppShell>
      <Card className="panel-gradient border-primary/20">
        <CardContent className="space-y-4">
          <Badge variant="outline">Policy management</Badge>
          <h2 className="text-3xl font-semibold">Governance rule administration</h2>
          <p className="text-muted-foreground">
            Adjust active thresholds, publish immutable versions, and roll back when a change needs reversing.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Active policy metadata</CardTitle>
            <CardDescription>Policy version context and editable governance notes.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-border/70 p-4">
                <p className="text-sm text-muted-foreground">Version</p>
                <p className="mt-2 text-xl font-semibold">{policy?.version ?? "Loading..."}</p>
              </div>
              <div className="rounded-2xl border border-border/70 p-4">
                <p className="text-sm text-muted-foreground">Updated</p>
                <p className="mt-2 text-xl font-semibold">
                  {policy ? formatDate(policy.updated_at ?? policy.created_at) : "Loading..."}
                </p>
              </div>
            </div>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Policy name" />
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Policy description"
            />
            <Input
              value={createdBy}
              onChange={(e) => setCreatedBy(e.target.value)}
              placeholder="Policy editor name"
            />
            <Button onClick={() => void handleSave()} disabled={saving}>
              {saving ? "Saving..." : "Save new policy version"}
            </Button>
            {message ? <p className="text-sm text-success">{message}</p> : null}
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active governance rules</CardTitle>
            <CardDescription>Threshold editing is persisted as a new active version on save.</CardDescription>
          </CardHeader>
          <CardContent>
            <PolicyTable rules={rules} onChange={setRules} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-muted-foreground" />
            <CardTitle>Version history</CardTitle>
          </div>
          <CardDescription>
            Every publish is kept. Load a version into the editor, or roll back to reactivate it immediately.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {versions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No policy versions found.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Version</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Rules</TableHead>
                  <TableHead>Created by</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {versions.map((version) => (
                  <TableRow key={version.id}>
                    <TableCell className="font-semibold">{version.version}</TableCell>
                    <TableCell>
                      <div>
                        <p>{version.name}</p>
                        {version.description ? (
                          <p className="text-xs text-muted-foreground line-clamp-1">{version.description}</p>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell>{version.rule_count}</TableCell>
                    <TableCell>{version.created_by}</TableCell>
                    <TableCell>{formatDate(version.created_at)}</TableCell>
                    <TableCell>
                      <Badge variant={version.is_active ? "success" : "outline"}>
                        {version.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2 justify-end">
                        <Button variant="secondary" size="sm" onClick={() => void handleLoadVersion(version)}>
                          Load
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={version.is_active || rollingBackId === version.id}
                          onClick={() => void handleRollback(version)}
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                          {rollingBackId === version.id ? "Rolling back..." : "Rollback"}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
