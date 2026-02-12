"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { db } from "@/lib/firebase";
import { collection, doc, setDoc } from "firebase/firestore";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AuthCallbackPage() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");

  // Sync user data to Firestore
  const syncUserToFirestore = async (
    token: string,
    userData: any
  ): Promise<boolean> => {
    try {
      console.log("Syncing user to Firestore:", userData);
      const usersCollection = collection(db, "users");
      const userDocRef = doc(usersCollection, String(userData.id));

      const firestoreData = {
        id: userData.id,
        github_id: userData.github_id,
        github_username: userData.github_username,
        avatar_url: userData.avatar_url || "",
        wallet_address: userData.wallet_address || null,
        created_at: userData.created_at,
        synced_at: new Date().toISOString(),
      };

      await setDoc(userDocRef, firestoreData, { merge: true });
      console.log("User synced to Firestore successfully");
      return true;
    } catch (error) {
      console.error("Error syncing user to Firestore:", error);
      return false;
    }
  };

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      console.error("No code in URL");
      setStatus("error");
      return;
    }
    fetch(`${API_BASE}/auth/github/callback?code=${encodeURIComponent(code)}`)
      .then((res) => {
        if (!res.ok) {
          console.error("Backend returned error:", res.status, res.statusText);
          setStatus("error");
          return null;
        }
        return res.json();
      })
      .then(async (data) => {
        if (!data || !data.access_token) {
          console.error("No access token in response:", data);
          setStatus("error");
          return;
        }
        console.log("Login successful, storing token");
        localStorage.setItem("trustchain_token", data.access_token);

        // Sync user data to Firestore
        if (data.user) {
          const synced = await syncUserToFirestore(data.access_token, data.user);
          if (!synced) {
            console.warn("Failed to sync user to Firestore, but continuing with login");
          }
        }

        setStatus("ok");
        // Redirect after a brief delay to ensure token is stored
        setTimeout(() => {
          window.location.href = "/dashboard";
        }, 500);
      })
      .catch((err) => {
        console.error("Callback error:", err);
        setStatus("error");
      });
  }, [searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      {status === "loading" && <p className="text-muted-foreground">Signing you in...</p>}
      {status === "error" && (
        <div className="text-center">
          <p className="text-destructive">Login failed.</p>
          <a href="/" className="mt-2 inline-block text-primary hover:underline">
            Back to home
          </a>
        </div>
      )}
    </div>
  );
}
