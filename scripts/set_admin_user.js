#!/usr/bin/env node
/**
 * Set Admin User Script
 * 
 * This script sets a user as admin in Firestore.
 * Usage: node scripts/set_admin_user.js <user_email>
 * 
 * Example: node scripts/set_admin_user.js hellovynfred@gmail.com
 */

const admin = require('firebase-admin');
const path = require('path');

// Initialize Firebase Admin
const serviceAccount = require(path.join(__dirname, '../bullsbears-xyz-firebase-adminsdk-fbsvc-e04781b75d.json'));

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  databaseURL: 'https://bullsbears-xyz-default-rtdb.firebaseio.com'
});

const db = admin.firestore();
const auth = admin.auth();

async function setAdminUser(email) {
  try {
    console.log(`🔍 Looking up user: ${email}`);
    
    // Get user by email
    const userRecord = await auth.getUserByEmail(email);
    console.log(`✅ Found user: ${userRecord.uid}`);
    
    // Update user document in Firestore
    await db.collection('users').doc(userRecord.uid).set({
      role: 'admin',
      email: userRecord.email,
      displayName: userRecord.displayName || null,
      photoURL: userRecord.photoURL || null,
      updatedAt: admin.firestore.FieldValue.serverTimestamp()
    }, { merge: true });
    
    console.log(`✅ User ${email} is now an admin!`);
    console.log(`   User ID: ${userRecord.uid}`);
    console.log(`   Admin page: https://bullsbears-xyz.web.app/admin`);
    
    process.exit(0);
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

// Get email from command line
const email = process.argv[2];

if (!email) {
  console.error('❌ Usage: node scripts/set_admin_user.js <user_email>');
  console.error('   Example: node scripts/set_admin_user.js hellovynfred@gmail.com');
  process.exit(1);
}

setAdminUser(email);

