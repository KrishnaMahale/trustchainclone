"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getMe, getDashboard, getProject } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const { data: user } = useQuery({ queryKey: ["me"], queryFn: getMe, retry: false });
  // For a simple dashboard we show "my projects" - we don't have a list endpoint, so show placeholder and link to create
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <Link href="/" className="font-semibold text-primary">TrustChain</Link>
          <nav className="flex gap-4">
            <Link href="/projects/new"><Button variant="outline">New Project</Button></Link>
          </nav>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="mt-2 text-muted-foreground">
          {user ? `Logged in as ${user.github_username}` : "Log in to create and manage projects."}
        </p>
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Projects</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Create a project to get started. You can then add members, connect a Git repo, run analysis, and open voting.
            </p>
            <Link href="/projects/new"><Button className="mt-4">Create Project</Button></Link>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
