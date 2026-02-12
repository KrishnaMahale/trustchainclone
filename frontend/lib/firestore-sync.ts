/**
 * Firestore sync utilities for user and project data
 */
import { collection, doc, setDoc, writeBatch } from "firebase/firestore";
import { db } from "@/lib/firebase";
import type { User, Project } from "@/lib/api";

/**
 * Sync user data to Firestore
 */
export async function syncUserToFirestore(user: User): Promise<boolean> {
  try {
    console.log("Syncing user to Firestore:", user);
    const usersCollection = collection(db, "users");
    const userDocRef = doc(usersCollection, String(user.id));

    const firestoreData = {
      id: user.id,
      github_id: user.github_id,
      github_username: user.github_username,
      avatar_url: user.avatar_url || "",
      wallet_address: user.wallet_address || null,
      created_at: user.created_at,
      updated_at: new Date().toISOString(),
    };

    await setDoc(userDocRef, firestoreData, { merge: true });
    console.log("User synced to Firestore successfully");
    return true;
  } catch (error) {
    console.error("Error syncing user to Firestore:", error);
    return false;
  }
}

/**
 * Sync project data to Firestore
 */
export async function syncProjectToFirestore(project: Project): Promise<boolean> {
  try {
    console.log("Syncing project to Firestore:", project);
    const projectsCollection = collection(db, "projects");
    const projectDocRef = doc(projectsCollection, String(project.id));

    const firestoreData = {
      id: project.id,
      name: project.name,
      repo_url: project.repo_url || "",
      weight_code: project.weight_code,
      weight_time: project.weight_time,
      weight_vote: project.weight_vote,
      deadline_contribution: project.deadline_contribution,
      deadline_voting: project.deadline_voting,
      status: project.status,
      contract_app_id: project.contract_app_id || null,
      contract_address: project.contract_address || "",
      created_at: project.created_at,
      members: project.members.map((m) => ({
        id: m.id,
        user_id: m.user_id,
        github_username: m.github_username,
        wallet_address: m.wallet_address || "",
        role: m.role,
      })),
    };

    await setDoc(projectDocRef, firestoreData, { merge: true });
    console.log("Project synced to Firestore successfully");
    return true;
  } catch (error) {
    console.error("Error syncing project to Firestore:", error);
    return false;
  }
}

/**
 * Sync multiple projects to Firestore in batch
 */
export async function syncProjectsToFirestore(projects: Project[]): Promise<boolean> {
  try {
    console.log("Syncing projects to Firestore:", projects.length);
    const batch = writeBatch(db);
    const projectsCollection = collection(db, "projects");

    projects.forEach((project) => {
      const projectDocRef = doc(projectsCollection, String(project.id));
      batch.set(
        projectDocRef,
        {
          id: project.id,
          name: project.name,
          repo_url: project.repo_url || "",
          status: project.status,
          created_at: project.created_at,
        },
        { merge: true }
      );
    });

    await batch.commit();
    console.log("Projects synced to Firestore successfully");
    return true;
  } catch (error) {
    console.error("Error syncing projects to Firestore:", error);
    return false;
  }
}
