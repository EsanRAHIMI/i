#!/usr/bin/env node

/**
 * Script to check and validate environment variables
 */

const fs = require('fs');
const path = require('path');

const envLocalPath = path.join(__dirname, '.env.local');
const envExamplePath = path.join(__dirname, '.env.example');

console.log('🔍 Checking environment variables...\n');

// Check if .env.local exists
if (!fs.existsSync(envLocalPath)) {
  console.error('❌ .env.local file not found!');
  console.log('\n📝 Creating .env.local from .env.example...\n');
  
  if (fs.existsSync(envExamplePath)) {
    const exampleContent = fs.readFileSync(envExamplePath, 'utf-8');
    fs.writeFileSync(envLocalPath, exampleContent);
    console.log('✅ Created .env.local file');
    console.log('⚠️  Please edit .env.local and set the correct values\n');
  } else {
    console.error('❌ .env.example file not found!');
    console.log('Creating a basic .env.local file...\n');
    const basicEnv = `# Frontend Environment Variables
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
`;
    fs.writeFileSync(envLocalPath, basicEnv);
    console.log('✅ Created basic .env.local file');
    console.log('⚠️  Please edit .env.local and set the correct values\n');
  }
} else {
  console.log('✅ .env.local file exists');
}

// Check required variables
const envContent = fs.existsSync(envLocalPath) 
  ? fs.readFileSync(envLocalPath, 'utf-8') 
  : '';

const requiredVars = [
  'NEXT_PUBLIC_API_URL',
  // NEXT_PUBLIC_WS_URL is optional
];

console.log('\n📋 Checking required variables:\n');

let allValid = true;
for (const varName of requiredVars) {
  const regex = new RegExp(`^${varName}=(.+)$`, 'm');
  const match = envContent.match(regex);
  
  if (match && match[1] && match[1].trim() && !match[1].trim().startsWith('#')) {
    console.log(`✅ ${varName} is set: ${match[1].trim()}`);
  } else {
    console.error(`❌ ${varName} is missing or empty`);
    allValid = false;
  }
}

// Check optional WS URL
const wsMatch = envContent.match(/^NEXT_PUBLIC_WS_URL=(.+)$/m);
if (wsMatch && wsMatch[1] && wsMatch[1].trim() && !wsMatch[1].trim().startsWith('#')) {
  console.log(`✅ NEXT_PUBLIC_WS_URL is set (optional): ${wsMatch[1].trim()}`);
} else {
  console.log(`⚠️  NEXT_PUBLIC_WS_URL is not set (optional - WebSocket features will be disabled)`);
}

console.log('\n' + '='.repeat(50));

if (allValid) {
  console.log('\n✅ All required environment variables are set!');
  console.log('💡 Remember to restart your dev server after changing .env.local\n');
  process.exit(0);
} else {
  console.log('\n❌ Some required environment variables are missing!');
  console.log('📖 Please check ENV_SETUP_GUIDE.md for instructions\n');
  process.exit(1);
}


