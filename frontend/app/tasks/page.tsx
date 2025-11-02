'use client';

import { GlowingOrb } from '@/components/ui/GlowingOrb';

export default function TasksPage() {
  return (
    <div className="p-6 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Tasks</h1>
        <p className="text-gray-400 mt-1">Manage your AI-powered task list</p>
      </div>

      <div className="bg-dark-800 rounded-lg border border-gray-700 p-8">
        <div className="text-center">
          <GlowingOrb size="large" className="mx-auto mb-6" />
          <h2 className="text-xl font-semibold text-white mb-2">Task Management Coming Soon</h2>
          <p className="text-gray-400 max-w-md mx-auto">
            This will be your central hub for managing AI-generated tasks, setting priorities, 
            and tracking your daily productivity.
          </p>
        </div>
      </div>
    </div>
  );
}