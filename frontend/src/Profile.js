import React, { useEffect, useState } from 'react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function Profile({ userId }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchUser() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${BACKEND_URL}/api/users/${userId}`);
        if (!res.ok) throw new Error('User not found');
        const data = await res.json();
        setUser(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    if (userId) fetchUser();
  }, [userId]);

  if (loading) return <div className="max-w-xl mx-auto px-4 py-16 text-center">Loading profile...</div>;
  if (error) return <div className="max-w-xl mx-auto px-4 py-16 text-center text-red-600">{error}</div>;
  if (!user) return null;

  // --- User Insight Calculation ---
  // Total purchases
  const totalPurchases = user.purchase_history ? user.purchase_history.length : 0;
  // Most frequent device
  let mostFrequentDevice = null;
  if (user.devices && user.devices.length > 0) {
    const freq = {};
    user.devices.forEach(d => { freq[d] = (freq[d] || 0) + 1 });
    mostFrequentDevice = Object.entries(freq).sort((a, b) => b[1] - a[1])[0][0];
  }
  // Favorite plan (first plan in purchase_history that matches known plan names)
  let favoritePlan = null;
  if (user.purchase_history && user.purchase_history.length > 0) {
    const planNames = user.purchase_history.filter(x => x.toLowerCase().includes('magenta'));
    if (planNames.length > 0) favoritePlan = planNames[0];
  }
  // Pie chart: count plan vs device vs other in purchase_history
  const pieCounts = { plans: 0, devices: 0, other: 0 };
  if (user.purchase_history) {
    user.purchase_history.forEach(item => {
      if (item.toLowerCase().includes('magenta')) pieCounts.plans++;
      else if (user.devices && user.devices.some(d => item.includes(d))) pieCounts.devices++;
      else pieCounts.other++;
    });
  }
  const pieTotal = pieCounts.plans + pieCounts.devices + pieCounts.other;
  const pieAngles = [pieCounts.plans, pieCounts.devices, pieCounts.other].map(x => (x / (pieTotal || 1)) * 360);

  return (
    <div className="max-w-xl mx-auto px-4 py-16">
      {/* User Insight Dashboard */}
      <div className="bg-gradient-to-r from-magenta-100 to-magenta-200 rounded-xl shadow p-6 mb-8 flex flex-col items-center">
        <h2 className="text-xl font-bold text-magenta-700 mb-2">User Insights</h2>
        <div className="flex flex-wrap gap-6 items-center justify-center w-full mb-4">
          <div className="flex flex-col items-center">
            <span className="text-2xl font-bold">{totalPurchases}</span>
            <span className="text-xs text-gray-500">Total Purchases</span>
          </div>
          <div className="flex flex-col items-center">
            <span className="text-lg font-semibold">{mostFrequentDevice || '-'}</span>
            <span className="text-xs text-gray-500">Most Used Device</span>
          </div>
          <div className="flex flex-col items-center">
            <span className="text-lg font-semibold">{favoritePlan || '-'}</span>
            <span className="text-xs text-gray-500">Favorite Plan</span>
          </div>
          <div className="flex flex-col items-center">
            {/* Pie chart using inline SVG */}
            <svg width="60" height="60" viewBox="0 0 32 32">
              <circle r="16" cx="16" cy="16" fill="#f3e8ff" />
              {/* Plans slice */}
              <path d={`M16,16 L16,0 A16,16 0 ${(pieAngles[0] > 180 ? 1 : 0)},1 ${16 + 16 * Math.sin(pieAngles[0] * Math.PI / 180)},${16 - 16 * Math.cos(pieAngles[0] * Math.PI / 180)} Z`} fill="#d946ef" />
              {/* Devices slice */}
              <path d={`M16,16 ${pieAngles[0] ? `L${16 + 16 * Math.sin(pieAngles[0] * Math.PI / 180)},${16 - 16 * Math.cos(pieAngles[0] * Math.PI / 180)}` : ''} A16,16 0 ${(pieAngles[1] > 180 ? 1 : 0)},1 ${16 + 16 * Math.sin((pieAngles[0] + pieAngles[1]) * Math.PI / 180)},${16 - 16 * Math.cos((pieAngles[0] + pieAngles[1]) * Math.PI / 180)} Z`} fill="#6366f1" />
              {/* Other slice */}
              <path d={`M16,16 ${pieAngles[0] + pieAngles[1] ? `L${16 + 16 * Math.sin((pieAngles[0] + pieAngles[1]) * Math.PI / 180)},${16 - 16 * Math.cos((pieAngles[0] + pieAngles[1]) * Math.PI / 180)}` : ''} A16,16 0 1,1 16,0 Z`} fill="#fbbf24" />
            </svg>
            <span className="text-xs text-gray-500">Purchases Breakdown</span>
            <div className="flex gap-1 mt-1 text-xs">
              <span className="inline-block w-2 h-2 rounded-full bg-fuchsia-400 mr-1"></span>Plans
              <span className="inline-block w-2 h-2 rounded-full bg-indigo-500 mx-1"></span>Devices
              <span className="inline-block w-2 h-2 rounded-full bg-yellow-400 mx-1"></span>Other
            </div>
          </div>
        </div>
      </div>
      <div className="bg-white rounded-xl shadow-lg p-8">
        <h1 className="text-3xl font-bold mb-2 text-magenta-700">{user.name}</h1>
        <div className="text-gray-500 mb-4">{user.email} • Age: {user.age} ({user.age_group}) • {user.city}</div>
        <div className="mb-4">
          <span className="font-semibold">Devices:</span>
          <ul className="list-disc ml-6 mt-2">
            {user.devices && user.devices.map((d, i) => <li key={i}>{d}</li>)}
          </ul>
        </div>
        <div className="mb-4">
          <span className="font-semibold">Preferences:</span>
          <pre className="bg-gray-100 rounded p-2 mt-2 text-sm">{JSON.stringify(user.preferences, null, 2)}</pre>
        </div>
        <div>
          <span className="font-semibold">Purchase History:</span>
          <ul className="list-disc ml-6 mt-2">
            {user.purchase_history && user.purchase_history.map((p, i) => <li key={i}>{p}</li>)}
          </ul>
        </div>
      </div>
    </div>
  );
}

export default Profile;
