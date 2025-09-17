import React from 'react';
import { Outlet, Link } from 'react-router-dom';

export function Layout() {
  return (
    <div className="min-h-screen grid grid-rows-[auto_1fr]">
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="container mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/dashboard" className="font-semibold">Workspace AI</Link>
          <nav className="flex gap-4 text-sm">
            <Link to="/dashboard">Dashboard</Link>
            <Link to="/sessions">Sessions</Link>
            <Link to="/analytics">Analytics</Link>
            <Link to="/settings">Settings</Link>
            <Link to="/profile">Profile</Link>
          </nav>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
