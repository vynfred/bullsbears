// Test script to verify frontend-backend integration
const axios = require('axios');

const API_BASE_URL = 'http://127.0.0.1:8000';

async function testIntegration() {
  console.log('🧪 Testing Frontend-Backend Integration...\n');

  try {
    // Test 1: Health check
    console.log('1️⃣ Testing health endpoint...');
    const healthResponse = await axios.get(`${API_BASE_URL}/health`);
    console.log('✅ Health check passed:', healthResponse.data.status);

    // Test 2: Moon alerts
    console.log('\n2️⃣ Testing moon alerts endpoint...');
    const moonResponse = await axios.get(`${API_BASE_URL}/api/v1/moon_alerts/latest?limit=3`);
    console.log(`✅ Moon alerts: ${moonResponse.data.length} alerts found`);
    if (moonResponse.data.length > 0) {
      const alert = moonResponse.data[0];
      console.log(`   📈 Sample: ${alert.symbol} (${alert.confidence.toFixed(1)}% confidence)`);
    }

    // Test 3: Rug alerts
    console.log('\n3️⃣ Testing rug alerts endpoint...');
    const rugResponse = await axios.get(`${API_BASE_URL}/api/v1/rug_alerts/latest?limit=3`);
    console.log(`✅ Rug alerts: ${rugResponse.data.length} alerts found`);
    if (rugResponse.data.length > 0) {
      const alert = rugResponse.data[0];
      console.log(`   📉 Sample: ${alert.symbol} (${alert.confidence.toFixed(1)}% confidence)`);
    }

    // Test 4: Data transformation
    console.log('\n4️⃣ Testing data transformation...');
    const allAlerts = [...moonResponse.data, ...rugResponse.data];
    const sortedAlerts = allAlerts.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    console.log(`✅ Combined and sorted: ${sortedAlerts.length} total alerts`);

    console.log('\n🎉 All integration tests passed!');
    console.log('\n📊 Summary:');
    console.log(`   • Backend: Running on ${API_BASE_URL}`);
    console.log(`   • Moon alerts: ${moonResponse.data.length} available`);
    console.log(`   • Rug alerts: ${rugResponse.data.length} available`);
    console.log(`   • Total alerts: ${allAlerts.length}`);

  } catch (error) {
    console.error('❌ Integration test failed:', error.message);
    if (error.response) {
      console.error('   Status:', error.response.status);
      console.error('   Data:', error.response.data);
    }
  }
}

testIntegration();
