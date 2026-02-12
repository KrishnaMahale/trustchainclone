"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createProject } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import Link from "next/link";

export default function NewProjectPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [weightCode, setWeightCode] = useState(0.4);
  const [weightTime, setWeightTime] = useState(0.3);
  const [weightVote, setWeightVote] = useState(0.3);
  const [deadlineContrib, setDeadlineContrib] = useState("");
  const [deadlineVote, setDeadlineVote] = useState("");
  const [memberWallets, setMemberWallets] = useState("");

  const create = useMutation({
    mutationFn: () =>
      createProject({
        name,
        repo_url: repoUrl || undefined,
        weight_code: weightCode,
        weight_time: weightTime,
        weight_vote: weightVote,
        deadline_contribution: deadlineContrib || new Date(Date.now() + 14 * 86400 * 1000).toISOString(),
        deadline_voting: deadlineVote || new Date(Date.now() + 21 * 86400 * 1000).toISOString(),
        member_wallet_addresses: memberWallets
          ? memberWallets.split(/[\n,]/).map((s) => s.trim()).filter(Boolean)
          : undefined,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
      router.push(`/projects/${data.id}`);
    },
  });

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50">
        <div className="container mx-auto flex h-14 items-center px-4">
          <Link href="/" className="font-semibold text-primary">TrustChain</Link>
        </div>
      </header>
      <main className="container mx-auto max-w-2xl px-4 py-8">
        <h1 className="text-2xl font-bold">Create Project</h1>
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Project details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Name</label>
              <Input
                className="mt-1"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Project name"
              />
            </div>
            <div>
              <label className="text-sm font-medium">GitHub repo URL (optional)</label>
              <Input
                className="mt-1"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/org/repo"
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium">Code weight</label>
                <Input
                  type="number"
                  min={0}
                  max={1}
                  step={0.1}
                  className="mt-1"
                  value={weightCode}
                  onChange={(e) => setWeightCode(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Time weight</label>
                <Input
                  type="number"
                  min={0}
                  max={1}
                  step={0.1}
                  className="mt-1"
                  value={weightTime}
                  onChange={(e) => setWeightTime(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Vote weight</label>
                <Input
                  type="number"
                  min={0}
                  max={1}
                  step={0.1}
                  className="mt-1"
                  value={weightVote}
                  onChange={(e) => setWeightVote(Number(e.target.value))}
                />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">Contribution deadline (ISO)</label>
              <Input
                type="datetime-local"
                className="mt-1"
                value={deadlineContrib}
                onChange={(e) => setDeadlineContrib(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Voting deadline (ISO)</label>
              <Input
                type="datetime-local"
                className="mt-1"
                value={deadlineVote}
                onChange={(e) => setDeadlineVote(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Member wallet addresses (one per line or comma-separated)</label>
              <textarea
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                rows={3}
                value={memberWallets}
                onChange={(e) => setMemberWallets(e.target.value)}
                placeholder="Algorand addresses..."
              />
            </div>
            <Button
              onClick={() => create.mutate()}
              disabled={!name || create.isPending}
            >
              {create.isPending ? "Creating..." : "Create Project"}
            </Button>
            {create.error && (
              <p className="text-sm text-destructive">{String(create.error)}</p>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
