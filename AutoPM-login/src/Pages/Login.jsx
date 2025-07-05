import React, { useState } from 'react';
import supabase from '../utils/supabaseClient';
import { v4 as uuidv4 } from 'uuid';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [otc, setOtc] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();

    // 1. Sign in the user
    const { data: authData, error } = await supabase.auth.signInWithPassword({
      email,
      password
    });

    if (error) return alert(error.message);

    const user_id = authData.user?.id;
    if (!user_id) return alert("Unable to get user ID");

    // 2. Generate OTC
    const oneTimeCode = uuidv4().slice(0, 6).toUpperCase(); // e.g. "A1B2C3"
    setOtc(oneTimeCode);

    // 3. Insert into otc_codes table
    const expires_at = new Date(Date.now() + 10 * 60 * 1000).toISOString(); // Expires in 10 min
    const { error: insertError } = await supabase
      .from('otc_codes')
      .insert([{ code: oneTimeCode, user_id, expires_at }]);

    if (insertError) return alert("OTC creation failed: " + insertError.message);

    // 4. Show modal with the OTC
    setShowModal(true);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 px-4">
      <form onSubmit={handleLogin} className="bg-white p-6 rounded shadow-md w-full max-w-sm">
        <h2 className="text-xl font-bold mb-4">Login</h2>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full p-2 mb-3 border rounded"
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full p-2 mb-3 border rounded"
          required
        />
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded w-full">
          Login
        </button>
      </form>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-sm w-full text-center">
            <h2 className="text-lg font-semibold mb-4">Link Your Telegram</h2>
            <p className="mb-2">Send the following in the Telegram <b>group</b>:</p>
            <pre className="bg-gray-100 text-sm p-2 rounded border border-gray-300">
              /link {otc}
            </pre>
            <p className="text-sm text-gray-500 mt-2">This code expires in 10 minutes.</p>
            <button
              className="mt-4 bg-blue-600 text-white px-4 py-2 rounded"
              onClick={() => setShowModal(false)}
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
