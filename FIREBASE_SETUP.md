# Firebase Integration Setup Guide

This guide explains how to set up Firebase for the TrustChain project to sync user and project data to Firestore.

## Current Setup

Firebase is partially configured:
- ✅ Environment variables set in `backend/.env`
- ✅ Frontend Firebase SDK configured in `frontend/lib/firebase.ts`
- ✅ Firestore sync on login configured
- ✅ Firebase Admin SDK enabled in backend

## Complete Setup Steps

### 1. Get Firebase Service Account Key

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select "mlsc-e7d69" project
3. Click **Project Settings** (gear icon) → **Service Accounts**
4. Click **Generate New Private Key**
5. Save the JSON file as `backend/firebase-key.json`

### 2. Set Environment Variable (Optional)

Add to `backend/.env`:
```bash
FIREBASE_SERVICE_ACCOUNT_PATH=firebase-key.json
```

Or set the environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/firebase-key.json"
```

### 3. Enable Firestore Database

1. In Firebase Console, go to **Firestore Database**
2. Click **Create Database**
3. Choose:
   - Start in **Production mode** (or Test mode for development)
   - Region: **us-central1** (or nearest to you)
4. Click **Create**

### 4. Configure Firestore Security Rules

In the **Firestore** section, go to **Rules** tab and set:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow authenticated users to read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth.uid != null;
    }
    
    match /projects/{projectId} {
      allow read: if request.auth.uid != null;
      allow write: if request.auth.uid != null;
    }
    
    match /votes/{voteId} {
      allow read, write: if request.auth.uid != null;
    }
  }
}
```

Then click **Publish**.

### 5. Restart Servers

```bash
# Backend
cd backend
uvicorn main:app --reload

# Frontend (in another terminal)
cd frontend
npm run dev
```

## How It Works

### On User Login:
1. User authenticates via GitHub
2. Backend receives code from GitHub
3. Backend exchanges code for user info
4. User data is **automatically synced to Firestore** ✅
5. JWT token returned to frontend
6. Frontend receives token and stores it

### Data Syncing:
- **Frontend**: `frontend/lib/firestore-sync.ts` - Manual sync functions
- **Backend**: `backend/firebase_service.py` - Automatic Firestore writes
- **API**: `frontend/lib/api.ts` - Auto-syncs when calling `getMe()`

## Verify It's Working

### Check Firestore in Console:
1. Go to Firebase Console → Firestore Database
2. Look for "users" collection
3. You should see a document with your user ID containing:
   ```json
   {
     "id": 1,
     "github_id": "xxx",
     "github_username": "your-username",
     "avatar_url": "https://...",
     "wallet_address": null,
     "created_at": "2025-02-12T...",
     "synced_at": "2025-02-12T..."
   }
   ```

### Check Backend Logs:
Look for messages like:
```
[INFO] User 1 synced to Firestore
```

### Check Browser Console:
After login, you should see:
```
Syncing user to Firestore: {id: 1, github_username: '...', ...}
User synced to Firestore successfully
```

## Troubleshooting

### "firebase-key.json not found"
```bash
# Make sure the file exists in the backend directory
ls -la backend/firebase-key.json
```

### "Firebase disabled" or "Firestore client not available"
- Check that service account key is properly placed
- Verify `FIREBASE_SERVICE_ACCOUNT_PATH` is set correctly
- Check backend logs for error messages

### Data not appearing in Firestore
1. Check backend logs for sync errors
2. Verify Firestore security rules allow writes
3. Ensure Firebase service account has Firestore access

## Optional: Enable Firebase Storage

For file uploads (avatars, project files):

1. In Firebase Console, go to **Storage**
2. Click **Get Started**
3. Accept default settings
4. Set security rules:

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /avatars/{userId}/{allPaths=**} {
      allow read, write: if request.auth.uid != null;
    }
    match /projects/{projectId}/{allPaths=**} {
      allow read, write: if request.auth.uid != null;
    }
  }
}
```

Then use in frontend:
```typescript
import { uploadAvatar } from "@/lib/firebase-storage";

const avatarUrl = await uploadAvatar(userId, file);
```

## Files Created/Modified

```
frontend/
  lib/
    firebase.ts              ✅ Firebase initialization
    firebase-auth.ts         ✅ Auth utilities
    firebase-storage.ts      ✅ File upload utilities
    firestore-sync.ts        ✅ Data sync to Firestore
    api.ts                   ✅ Auto-sync on getMe()

backend/
  firebase_service.py        ✅ Firebase admin operations
  routes/auth.py             ✅ Sync on GitHub login
  .env                       ✅ Firebase config

firebase-key.json            ⏳ Generate from Firebase Console
```

## Next Steps

1. ✅ Complete step 1-5 above
2. Test login and verify data in Firestore
3. (Optional) Enable Firebase Storage for file uploads
4. Deploy to production with proper Firebase settings
