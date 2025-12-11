// Simple script to clear all users from the database
// Run with: node scripts/clear-users.js

console.log('To clear users from the database, run one of these commands:');
console.log('');
console.log('Local database:');
console.log('  npx wrangler d1 execute whatsapp_clone_db --local --command "DELETE FROM users"');
console.log('');
console.log('Remote database:');
console.log('  npx wrangler d1 execute whatsapp_clone_db --remote --command "DELETE FROM users"');
console.log('');
console.log('To also clear messages:');
console.log('  npx wrangler d1 execute whatsapp_clone_db --local --command "DELETE FROM messages; DELETE FROM users"');
