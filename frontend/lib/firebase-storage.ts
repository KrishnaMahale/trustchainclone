/**
 * Firebase Storage utilities for file uploads
 */
import {
  ref,
  uploadBytes,
  downloadURL,
  deleteObject,
  listAll,
} from "firebase/storage";
import { storage } from "./firebase";

/**
 * Upload file to Firebase Storage
 */
export async function uploadFile(
  path: string,
  file: File
): Promise<string> {
  try {
    const fileRef = ref(storage, path);
    await uploadBytes(fileRef, file);
    const url = await downloadURL(fileRef);
    console.log("File uploaded successfully:", url);
    return url;
  } catch (error) {
    console.error("Upload error:", error);
    throw error;
  }
}

/**
 * Upload avatar for user
 */
export async function uploadAvatar(userId: number, file: File): Promise<string> {
  return uploadFile(`avatars/${userId}/${file.name}`, file);
}

/**
 * Upload project file
 */
export async function uploadProjectFile(
  projectId: number,
  file: File
): Promise<string> {
  return uploadFile(`projects/${projectId}/${file.name}`, file);
}

/**
 * Download file from Firebase Storage
 */
export async function downloadFile(path: string): Promise<string> {
  try {
    const fileRef = ref(storage, path);
    const url = await downloadURL(fileRef);
    return url;
  } catch (error) {
    console.error("Download error:", error);
    throw error;
  }
}

/**
 * Delete file from Firebase Storage
 */
export async function deleteFile(path: string): Promise<void> {
  try {
    const fileRef = ref(storage, path);
    await deleteObject(fileRef);
    console.log("File deleted successfully");
  } catch (error) {
    console.error("Delete error:", error);
    throw error;
  }
}

/**
 * List files in a storage folder
 */
export async function listFiles(folderPath: string): Promise<string[]> {
  try {
    const folderRef = ref(storage, folderPath);
    const result = await listAll(folderRef);
    const urls = await Promise.all(
      result.items.map((item) => downloadURL(item))
    );
    return urls;
  } catch (error) {
    console.error("List files error:", error);
    throw error;
  }
}
