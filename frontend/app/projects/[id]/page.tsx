"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  getProject,
  getDashboard,
  analyzeProject,
  finalizeProject,
  submitVote,
  getMe,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export default function ProjectPage() {
  const params = useParams();
  const queryClient = useQueryClient();
  const id = Number(params.id);
  const { data: project, isLoading } = useQuery({
    queryKey: ["project", id],
    queryFn: () => getProject(id),
  });
  const { data: dashboard } = useQuery({
    queryKey: ["dashboard", id],
    queryFn: () => getDashboard(id),
    enabled: !!project,
  });
  const { data: user } = useQuery({ queryKey: ["me"], queryFn: getMe, retry: false });

  const analyze = useMutation({
    mutationFn: () => analyzeProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", id] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", id] });
    },
  });
  const finalize = useMutation({
    mutationFn: () => finalizeProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", id] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", id] });
    },
  });

  if (isLoading || !project) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  const chartData = dashboard?.leaderboard?.length
    ? {
        labels: dashboard.leaderboard.map((e) => e.github_username),
        datasets: [
          {
            label: "Code",
            data: dashboard.leaderboard.map((e) => e.code_score),
            backgroundColor: "rgba(139, 92, 246, 0.6)",
          },
          {
            label: "Time",
            data: dashboard.leaderboard.map((e) => e.time_score),
            backgroundColor: "rgba(34, 197, 94, 0.6)",
          },
          {
            label: "Peer",
            data: dashboard.leaderboard.map((e) => e.peer_score),
            backgroundColor: "rgba(234, 179, 8, 0.6)",
          },
        ],
      }
    : null;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <Link href="/dashboard" className="font-semibold text-primary">
            TrustChain
          </Link>
          <span className="text-sm text-muted-foreground">{project.name}</span>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-2xl font-bold">{project.name}</h1>
          <div className="flex gap-2">
            {project.repo_url && project.status !== "finalized" && (
              <Button
                variant="outline"
                onClick={() => analyze.mutate()}
                disabled={analyze.isPending}
              >
                {analyze.isPending ? "Analyzing..." : "Analyze Git"}
              </Button>
            )}
            {project.status === "active" &&
              new Date(project.deadline_voting) < new Date() && (
                <Button
                  onClick={() => finalize.mutate()}
                  disabled={finalize.isPending}
                >
                  {finalize.isPending ? "Finalizing..." : "Finalize"}
                </Button>
              )}
          </div>
        </div>

        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Rules</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>Code: {(project.weight_code * 100).toFixed(0)}%</p>
              <p>Time: {(project.weight_time * 100).toFixed(0)}%</p>
              <p>Peer vote: {(project.weight_vote * 100).toFixed(0)}%</p>
              <p>Contribution deadline: {new Date(project.deadline_contribution).toLocaleString()}</p>
              <p>Voting deadline: {new Date(project.deadline_voting).toLocaleString()}</p>
              {project.contract_app_id && (
                <p className="pt-2">
                  <a
                    href={`https://testnet.algoexplorer.io/application/${project.contract_app_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    View on AlgoExplorer (TestNet)
                  </a>
                </p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Members</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1 text-sm">
                {project.members.map((m) => (
                  <li key={m.id}>
                    {m.github_username}
                    {m.wallet_address && (
                      <span className="ml-2 text-muted-foreground">
                        {m.wallet_address.slice(0, 8)}...
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>

        {dashboard?.leaderboard?.length ? (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Leaderboard</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="pb-2 text-left">Rank</th>
                      <th className="pb-2 text-left">Member</th>
                      <th className="pb-2 text-right">Code</th>
                      <th className="pb-2 text-right">Time</th>
                      <th className="pb-2 text-right">Peer</th>
                      <th className="pb-2 text-right">Final</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.leaderboard.map((e) => (
                      <tr key={e.member_id} className="border-b">
                        <td className="py-2">{e.rank}</td>
                        <td>{e.github_username}</td>
                        <td className="text-right">{e.code_score.toFixed(1)}</td>
                        <td className="text-right">{e.time_score.toFixed(1)}</td>
                        <td className="text-right">{e.peer_score.toFixed(1)}</td>
                        <td className="text-right font-medium">{e.final_score.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {chartData && (
                <div className="mt-6 h-64">
                  <Bar
                    data={chartData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      scales: { y: { beginAtZero: true, max: 100 } },
                    }}
                  />
                </div>
              )}
            </CardContent>
          </Card>
        ) : (
          <Card className="mt-6">
            <CardContent className="py-8 text-center text-muted-foreground">
              Run Git analysis and finalize to see leaderboard and scores.
            </CardContent>
          </Card>
        )}

        {project.status !== "finalized" && user && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Vote for teammates</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Rate each member 1–5 (no self-vote). Voting is open between contribution and voting deadlines.
              </p>
              <VoteForm projectId={id} members={project.members} currentUserId={user.id} />
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}

function VoteForm({
  projectId,
  members,
  currentUserId,
}: {
  projectId: number;
  members: { id: number; user_id: number; github_username: string }[];
  currentUserId: number;
}) {
  const queryClient = useQueryClient();
  const [scores, setScores] = useState<Record<number, number>>({});
  const submit = useMutation({
    mutationFn: async () => {
      for (const m of members) {
        if (m.user_id === currentUserId) continue;
        const s = scores[m.id];
        if (s != null && s >= 1 && s <= 5) await submitVote(projectId, m.id, s);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", projectId] });
    },
  });
  const others = members.filter((m) => m.user_id !== currentUserId);
  return (
    <div className="mt-4 space-y-4">
      {others.map((m) => (
        <div key={m.id} className="flex items-center gap-4">
          <span className="w-32 text-sm">{m.github_username}</span>
          <select
            className="rounded border border-input bg-background px-2 py-1 text-sm"
            value={scores[m.id] ?? ""}
            onChange={(e) =>
              setScores((prev) => ({ ...prev, [m.id]: Number(e.target.value) }))
            }
          >
            <option value="">—</option>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
      ))}
      <Button
        onClick={() => submit.mutate()}
        disabled={submit.isPending || Object.keys(scores).length === 0}
      >
        {submit.isPending ? "Submitting..." : "Submit votes"}
      </Button>
    </div>
  );
}
