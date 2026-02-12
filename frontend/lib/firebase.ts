/**
 * Firebase configuration and initialization
 */
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";
import { getAnalytics } from "firebase/analytics";

const firebaseConfig = {
  apiKey: "AIzaSyBabppFzopT8Ebb3T9ehvgiIHHzIHTn9qI",
  authDomain: "mlsc-e7d69.firebaseapp.com",
  projectId: "mlsc-e7d69",
  storageBucket: "mlsc-e7d69.firebasestorage.app",
  messagingSenderId: "857119699101",
  appId: "1:857119699101:web:10ee72b7c6f7c5aec86474",
  measurementId: "G-718JCRC3XM",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase services
export const auth = getAuth(app);
export const db = getFirestore(app);
export const storage = getStorage(app);
export const analytics = typeof window !== "undefined" ? getAnalytics(app) : null;

export default app;
