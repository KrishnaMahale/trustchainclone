/**
 * TrustChain API client.
 * Uses NEXT_PUBLIC_API_URL (default http://localhost:8000).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type User = {
  id: number;
  github_id: string;
  github_username: string;
  avatar_url?: string;
  wallet_address?: string;
  created_at: string;
};

export type ProjectMemberResponse = {
  id: number;
  user_id: number;
  github_username: string;
  wallet_address?: string;
  role: string;
};

export type Project = {
  id: number;
  name: string;
  repo_url?: string;
  weight_code: number;
  weight_time: number;
  weight_vote: number;
  deadline_contribution: string;
  deadline_voting: string;
  status: string;
  contract_app_id?: number;
  contract_address?: string;
  created_at: string;
  members: ProjectMemberResponse[];
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type LeaderboardEntry = {
  rank: number;
  member_id: number;
  github_username: string;
  wallet_address?: string;
  final_score: number;
  code_score: number;
  time_score: number;
  peer_score: number;
};

export type DashboardResponse = {
  project: Project;
  leaderboard: LeaderboardEntry[];
  timeline_data?: Record<string, unknown>;
  my_reputation?: number;
};

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("trustchain_token");
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || String(err) || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export function getGitHubLoginUrl(): string {
  return `${API_BASE}/auth/github`;
}

export async function linkWallet(walletAddress: string): Promise<User> {
  return apiFetch<User>("/auth/wallet", {
    method: "POST",
    body: JSON.stringify({ wallet_address: walletAddress }),
  });
}

export async function getMe(): Promise<User> {
  const user = await apiFetch<User>("/auth/me");
  // Sync user data to Firestore
  if (user) {
    import("./firestore-sync").then(({ syncUserToFirestore }) => {
      syncUserToFirestore(user).catch((err) =>
        console.warn("Failed to sync user to Firestore:", err)
      );
    });
  }
  return user;
}

export async function createProject(body: {
  name: string;
  repo_url?: string;
  weight_code: number;
  weight_time: number;
  weight_vote: number;
  deadline_contribution: string;
  deadline_voting: string;
  member_wallet_addresses?: string[];
}): Promise<Project> {
  return apiFetch<Project>("/projects/create", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getProject(projectId: number): Promise<Project> {
  return apiFetch<Project>(`/projects/${projectId}`);
}

export async function analyzeProject(projectId: number): Promise<{
  project_id: number;
  metrics: Record<string, { code_score_raw?: number; time_score_raw?: number }>;
  last_analyzed_at?: string;
}> {
  return apiFetch(`/projects/${projectId}/analyze`, { method: "POST" });
}

export async function submitVote(
  projectId: number,
  memberId: number,
  score: number
): Promise<{ id: number; project_id: number; voter_id: number; member_id: number; score: number }> {
  return apiFetch(`/projects/${projectId}/vote`, {
    method: "POST",
    body: JSON.stringify({ member_id: memberId, score }),
  });
}

export async function finalizeProject(projectId: number): Promise<{
  status: string;
  project_id: number;
  scores?: number;
}> {
  return apiFetch(`/projects/${projectId}/finalize`, { method: "POST" });
}

export async function getDashboard(projectId: number): Promise<DashboardResponse> {
  return apiFetch<DashboardResponse>(`/projects/${projectId}/dashboard`);
}

export async function getFinalScores(
  projectId: number
): Promise<
  Array<{
    member_id: number;
    github_username: string;
    wallet_address?: string;
    code_score: number;
    time_score: number;
    peer_score: number;
    final_score: number;
    score_hash?: string;
    reputation_minted?: number;
  }>
> {
  return apiFetch(`/projects/${projectId}/scores`);
}
