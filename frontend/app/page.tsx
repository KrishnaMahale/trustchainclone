"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getMe } from "@/lib/api";
import { WalletConnect } from "@/components/wallet-connect";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function HomePage() {
  const { data: user, isLoading, error } = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
  });

  const handleGitHubLogin = async () => {
    try {
      console.log("Fetching GitHub auth URL from:", `${API_BASE}/auth/github`);
      const res = await fetch(`${API_BASE}/auth/github`);
      
      if (!res.ok) {
        console.error("Backend error:", res.status, res.statusText);
        alert("Failed to get GitHub login URL");
        return;
      }
      
      const data = await res.json();
      console.log("GitHub auth response:", data);
      
      if (data.url) {
        console.log("Redirecting to GitHub:", data.url);
        window.location.href = data.url;
      } else {
        console.error("No URL in response:", data);
        alert("No GitHub login URL returned");
      }
    } catch (e) {
      console.error("Failed to get GitHub login URL:", e);
      alert("Error: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("trustchain_token");
    window.location.href = "/";
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/30">
      <header className="border-b border-border/50 bg-card/50 backdrop-blur">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link href="/" className="text-xl font-bold text-primary">
            TrustChain
          </Link>
          <nav className="flex items-center gap-4">
            {user ? (
              <>
                <Link
                  href="/dashboard"
                  className="rounded-md px-3 py-2 text-sm font-medium text-foreground hover:bg-accent"
                >
                  Dashboard
                </Link>
                <Link
                  href="/projects/new"
                  className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
                >
                  New Project
                </Link>
                <WalletConnect />
                <span className="text-sm text-muted-foreground">
                  {user.github_username}
                </span>
                <button
                  onClick={handleLogout}
                  className="rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90"
                >
                  Logout
                </button>
              </>
            ) : (
              <button
                onClick={handleGitHubLogin}
                className="rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90"
              >
                Login with GitHub
              </button>
            )}
          </nav>
        </div>
      </header>

      <main className="container mx-auto px-4 py-16">
        <section className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            Trustless Group Contribution Evaluation
          </h1>
          <p className="mt-4 text-lg text-muted-foreground">
            Eliminate manipulation in group grading with Git analysis, peer voting,
            and Algorand smart contracts for immutable rules and reputation.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link
              href="/projects/new"
              className="rounded-lg bg-primary px-6 py-3 text-base font-medium text-primary-foreground hover:opacity-90"
            >
              Create Project
            </Link>
            <Link
              href="/dashboard"
              className="rounded-lg border border-border bg-card px-6 py-3 text-base font-medium hover:bg-accent"
            >
              View Dashboard
            </Link>
          </div>
        </section>

        <section className="mx-auto mt-24 grid max-w-4xl gap-8 sm:grid-cols-3">
          <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
            <h3 className="font-semibold text-foreground">Git Analysis</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Commits, lines changed, and time consistency from your repo.
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
            <h3 className="font-semibold text-foreground">Peer Voting</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Teammates rate each other (1–5). No self-voting, one vote per member.
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
            <h3 className="font-semibold text-foreground">On-Chain Rules</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Weights and deadlines locked on Algorand. Reputation ASA minted by contract.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
