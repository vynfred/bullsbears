'use client';

/**
 * Firebase Authentication Hook
 * Supports Google OAuth and Email/Password authentication
 * Manages user session persistence and profile data in Firestore
 */

import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  User,
  setPersistence,
  browserLocalPersistence,
  updateProfile,
  sendPasswordResetEmail,
  sendEmailVerification,
} from 'firebase/auth';
import {
  getFirestore,
  doc,
  setDoc,
  getDoc,
  updateDoc,
  serverTimestamp,
} from 'firebase/firestore';
import { initializeApp, getApps } from 'firebase/app';

// Firebase configuration
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  databaseURL: process.env.NEXT_PUBLIC_FIREBASE_DATABASE_URL,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

// Initialize Firebase (only once)
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
const auth = getAuth(app);
const db = getFirestore(app);
const googleProvider = new GoogleAuthProvider();

// Set persistence to LOCAL (keep users logged in)
setPersistence(auth, browserLocalPersistence).catch((error) => {
  console.error('Failed to set auth persistence:', error);
});

// User profile interface
export interface UserProfile {
  uid: string;
  email: string | null;
  displayName: string | null;
  photoURL: string | null;
  emailVerified: boolean;
  createdAt: Date;
  updatedAt: Date;
  notificationSettings?: {
    pushEnabled: boolean;
    emailEnabled: boolean;
    morningPicks: boolean;
    targetHits: boolean;
    watchlistAlerts: boolean;
  };
}

// Auth context interface
interface AuthContextType {
  user: User | null;
  userProfile: UserProfile | null;
  loading: boolean;
  error: string | null;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signUpWithEmail: (email: string, password: string, displayName: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  updateUserProfile: (data: Partial<UserProfile>) => Promise<void>;
  refreshUserProfile: () => Promise<void>;
}

// Create Auth Context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Auth Provider Component
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch user profile from Firestore
  const fetchUserProfile = useCallback(async (uid: string): Promise<UserProfile | null> => {
    try {
      const userDoc = await getDoc(doc(db, 'users', uid));

      if (userDoc.exists()) {
        const data = userDoc.data();
        return {
          uid,
          email: data.email,
          displayName: data.displayName,
          photoURL: data.photoURL || null,
          emailVerified: data.emailVerified || false,
          createdAt: data.createdAt?.toDate() || new Date(),
          updatedAt: data.updatedAt?.toDate() || new Date(),
          notificationSettings: data.notificationSettings || {
            pushEnabled: true,
            emailEnabled: true,
            morningPicks: true,
            targetHits: true,
            watchlistAlerts: true,
          },
        };
      }

      return null;
    } catch (err) {
      console.error('Error fetching user profile:', err);
      return null;
    }
  }, []);

  // Create user profile in Firestore
  const createUserProfile = useCallback(async (user: User, additionalData?: Partial<UserProfile>) => {
    try {
      const userRef = doc(db, 'users', user.uid);
      const userDoc = await getDoc(userRef);

      if (!userDoc.exists()) {
        const profileData = {
          uid: user.uid,
          email: user.email,
          displayName: additionalData?.displayName || user.displayName || 'Anonymous',
          photoURL: user.photoURL || null,
          emailVerified: user.emailVerified,
          createdAt: serverTimestamp(),
          updatedAt: serverTimestamp(),
          notificationSettings: {
            pushEnabled: true,
            emailEnabled: true,
            morningPicks: true,
            targetHits: true,
            watchlistAlerts: true,
          },
          ...additionalData,
        };

        await setDoc(userRef, profileData);
        console.log('✅ User profile created in Firestore');
      }
    } catch (err) {
      console.error('Error creating user profile:', err);
      throw err;
    }
  }, []);

  // Sign in with email and password
  const signInWithEmail = useCallback(async (email: string, password: string) => {
    try {
      setError(null);
      setLoading(true);
      const result = await signInWithEmailAndPassword(auth, email, password);
      console.log('✅ Signed in with email:', result.user.email);
    } catch (err: any) {
      console.error('Sign in error:', err);
      setError(err.message || 'Failed to sign in');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Sign up with email and password
  const signUpWithEmail = useCallback(async (email: string, password: string, displayName: string) => {
    try {
      setError(null);
      setLoading(true);

      // Create user account
      const result = await createUserWithEmailAndPassword(auth, email, password);

      // Update display name
      await updateProfile(result.user, { displayName });

      // Create user profile in Firestore
      await createUserProfile(result.user, { displayName });

      // Send email verification
      await sendEmailVerification(result.user);

      console.log('✅ Signed up with email:', result.user.email);
    } catch (err: any) {
      console.error('Sign up error:', err);
      setError(err.message || 'Failed to sign up');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [createUserProfile]);

  // Sign in with Google
  const signInWithGoogle = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);

      const result = await signInWithPopup(auth, googleProvider);

      // Create user profile if it doesn't exist
      await createUserProfile(result.user);

      console.log('✅ Signed in with Google:', result.user.email);
    } catch (err: any) {
      console.error('Google sign in error:', err);
      setError(err.message || 'Failed to sign in with Google');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [createUserProfile]);

  // Sign out
  const signOut = useCallback(async () => {
    try {
      setError(null);
      await firebaseSignOut(auth);
      setUser(null);
      setUserProfile(null);
      console.log('✅ Signed out');
    } catch (err: any) {
      console.error('Sign out error:', err);
      setError(err.message || 'Failed to sign out');
      throw err;
    }
  }, []);

  // Reset password
  const resetPassword = useCallback(async (email: string) => {
    try {
      setError(null);
      await sendPasswordResetEmail(auth, email);
      console.log('✅ Password reset email sent to:', email);
    } catch (err: any) {
      console.error('Password reset error:', err);
      setError(err.message || 'Failed to send password reset email');
      throw err;
    }
  }, []);

  // Update user profile
  const updateUserProfile = useCallback(async (data: Partial<UserProfile>) => {
    if (!user) {
      throw new Error('No user logged in');
    }

    try {
      setError(null);

      const userRef = doc(db, 'users', user.uid);
      await updateDoc(userRef, {
        ...data,
        updatedAt: serverTimestamp(),
      });

      // Refresh user profile
      const updatedProfile = await fetchUserProfile(user.uid);
      setUserProfile(updatedProfile);

      console.log('✅ User profile updated');
    } catch (err: any) {
      console.error('Update profile error:', err);
      setError(err.message || 'Failed to update profile');
      throw err;
    }
  }, [user, fetchUserProfile]);

  // Refresh user profile
  const refreshUserProfile = useCallback(async () => {
    if (!user) return;

    const profile = await fetchUserProfile(user.uid);
    setUserProfile(profile);
  }, [user, fetchUserProfile]);

  // Listen to auth state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setLoading(true);

      if (firebaseUser) {
        setUser(firebaseUser);

        // Fetch or create user profile
        let profile = await fetchUserProfile(firebaseUser.uid);

        if (!profile) {
          await createUserProfile(firebaseUser);
          profile = await fetchUserProfile(firebaseUser.uid);
        }

        setUserProfile(profile);
        console.log('✅ User authenticated:', firebaseUser.email);
      } else {
        setUser(null);
        setUserProfile(null);
        console.log('ℹ️ No user authenticated');
      }

      setLoading(false);
    });

    return () => unsubscribe();
  }, [fetchUserProfile, createUserProfile]);

  const value: AuthContextType = {
    user,
    userProfile,
    loading,
    error,
    signInWithEmail,
    signUpWithEmail,
    signInWithGoogle,
    signOut,
    resetPassword,
    updateUserProfile,
    refreshUserProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Hook to use auth context
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}

// Export auth and db instances for direct use
export { auth, db };