/**
 * Test utility to manually verify data isolation between users
 * Run this in the browser console to test user switching behavior
 */

export const testDataIsolation = () => {
  console.log('🧪 Data isolation test');
  console.log('JWT-based authentication manages user isolation on the server.');
  console.log('There is no longer any localStorage-stored session data to verify.');
  console.log('Use backend tools or logs to confirm isolation between users.');
  return true;
};

/**
 * Function to simulate user switching in React context
 * This should be called after user switching to verify state
 */
export const logCurrentUserState = (userId, messages) => {
  console.log('📱 Current User State:');
  console.log('User ID:', userId);
  console.log('Messages count:', messages.length);
  console.log('First message:', messages[0]);
  console.log('Last message:', messages[messages.length - 1]);
};

// Make functions available globally for testing
if (typeof window !== 'undefined') {
  window.testDataIsolation = testDataIsolation;
  window.logCurrentUserState = logCurrentUserState;
} 