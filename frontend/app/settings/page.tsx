'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/store/useAppStore';
import { useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { locales, getLocaleConfig } from '@/lib/utils';
import { Language, UserSettings } from '@/types';
import { useT } from '@/i18n/useT';
import { GlassCard } from '@/components/ui/GlassCard';
import { AppPageShell } from '@/components/layout/AppPageShell';

export default function SettingsPage() {
  const { user, settings, updateUser, setSettings } = useAppStore();
  const { updateProfile } = useAuth();
  const router = useRouter();
  const t = useT();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'general' | 'privacy' | 'integrations' | 'language'>('general');

  // Local state for form data
  const [formData, setFormData] = useState({
    language_preference: user?.language_preference || 'en-US' as Language,
    whatsapp_opt_in: settings?.whatsapp_opt_in || false,
    voice_training_consent: settings?.voice_training_consent || false,
    calendar_sync_enabled: settings?.calendar_sync_enabled || false,
    privacy_level: settings?.privacy_level || 'standard' as 'minimal' | 'standard' | 'enhanced',
    notification_preferences: settings?.notification_preferences || {}
  });

  useEffect(() => {
    if (user && settings) {
      setFormData({
        language_preference: user.language_preference,
        whatsapp_opt_in: settings.whatsapp_opt_in,
        voice_training_consent: settings.voice_training_consent,
        calendar_sync_enabled: settings.calendar_sync_enabled,
        privacy_level: settings.privacy_level,
        notification_preferences: settings.notification_preferences
      });
    }
  }, [user, settings]);

  const handleSave = async () => {
    try {
      setIsLoading(true);
      setError(null);
      setSuccess(null);

      const locale = getLocaleConfig(formData.language_preference);
      // Persist locale for server-rendered RootLayout (lang/dir) on refresh/navigation
      document.cookie = `i_locale=${encodeURIComponent(locale.code)}; path=/; max-age=31536000; samesite=lax`;

      // Update user profile
      await updateProfile({
        language_preference: formData.language_preference
      });

      // Update user settings
      const updatedSettings = await apiClient.updateUserSettings({
        whatsapp_opt_in: formData.whatsapp_opt_in,
        voice_training_consent: formData.voice_training_consent,
        calendar_sync_enabled: formData.calendar_sync_enabled,
        privacy_level: formData.privacy_level,
        notification_preferences: formData.notification_preferences
      });

      setSettings(updatedSettings);
      setSuccess(t('settings.saved'));
      // Force App Router to re-render server components with updated cookie.
      router.refresh();
    } catch (err: any) {
      setError(err.message || 'Failed to save settings');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportData = async () => {
    try {
      setIsLoading(true);
      // In a real implementation, this would call an API to export user data
      const exportData = {
        user_profile: user,
        settings: settings,
        export_date: new Date().toISOString(),
        data_types: ['profile', 'settings', 'tasks', 'events', 'voice_sessions']
      };

      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `i-assistant-data-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setSuccess('Data exported successfully');
    } catch (err: any) {
      setError('Failed to export data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
      return;
    }

    try {
      setIsLoading(true);
      // In a real implementation, this would call an API to delete the account
      await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate API call
      
      // Redirect to login after account deletion
      window.location.href = '/auth/login';
    } catch (err: any) {
      setError('Failed to delete account');
      setIsLoading(false);
    }
  };

  const tabs = [
    { id: 'general', name: t('settings.tabs.general'), icon: '⚙️' },
    { id: 'privacy', name: t('settings.tabs.privacy'), icon: '🔒' },
    { id: 'integrations', name: t('settings.tabs.integrations'), icon: '🔗' },
    { id: 'language', name: t('settings.tabs.language'), icon: '🌐' }
  ];

  return (
    <AppPageShell>
      <div className="flex flex-col gap-6 w-full max-w-7xl mx-auto">
        
        {/* Page Header */}
        <GlassCard className="overflow-hidden p-6 sm:p-8">
          <div className="space-y-3">
            <span className="inline-flex items-center rounded-full bg-primary-500/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.2em] text-primary-400 border border-primary-500/20">
              System Configuration
            </span>
            <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Account <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-accent-400">Settings</span>
            </h1>
            <p className="max-w-2xl text-sm leading-relaxed text-white/50">{t('settings.subtitle')}</p>
          </div>
        </GlassCard>

        {/* Tabs */}
        <div className="w-full">
          <nav className="flex flex-wrap gap-2 p-1.5 bg-black/20 rounded-2xl border border-white/5 backdrop-blur-md w-fit mx-auto lg:mx-0">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`
                  flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm transition-all focus:outline-none 
                  ${activeTab === tab.id
                    ? 'bg-white/10 text-white shadow-[0_0_15px_rgba(255,255,255,0.05)] border border-white/10'
                    : 'text-white/40 hover:text-white/80 hover:bg-white/5 border border-transparent'
                  }
                `}
              >
                <span>{tab.icon}</span>
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-red-400 animate-pulse"></div>
          <p className="text-red-400 text-sm font-medium">{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
          <p className="text-emerald-400 text-sm font-medium">{success}</p>
        </div>
      )}

      {/* Tab Content */}
      <GlassCard className="p-0 overflow-hidden relative border-white/5 transition-all duration-500">
        <div className="absolute inset-0 bg-gradient-to-br from-white/5 via-transparent to-transparent opacity-50 pointer-events-none"></div>
        {activeTab === 'general' && (
          <div className="p-6 sm:p-8 space-y-10 relative z-10">
            
            {/* Profile Information */}
            <div className="space-y-6">
              <div>
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <span className="w-1.5 h-6 rounded-full bg-primary-500/50"></span>
                  Profile Information
                </h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-white/60 pl-1">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="w-full px-4 py-3 bg-black/20 border border-white/10 rounded-xl text-white/50 cursor-not-allowed shadow-inner"
                  />
                  <p className="text-[11px] text-white/30 pl-2">Email address cannot be changed</p>
                </div>
                
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-white/60 pl-1">
                    Timezone
                  </label>
                  <select
                    value={user?.timezone || 'UTC'}
                    onChange={(e) => setFormData(prev => ({ ...prev, timezone: e.target.value }))}
                    className="w-full px-4 py-3 bg-black/20 border border-white/10 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500/50 transition-all shadow-inner hover:border-white/20"
                  >
                    <option value="UTC" className="bg-slate-900 text-white">UTC</option>
                    <option value="America/New_York" className="bg-slate-900 text-white">Eastern Time</option>
                    <option value="America/Chicago" className="bg-slate-900 text-white">Central Time</option>
                    <option value="America/Denver" className="bg-slate-900 text-white">Mountain Time</option>
                    <option value="America/Los_Angeles" className="bg-slate-900 text-white">Pacific Time</option>
                    <option value="Europe/London" className="bg-slate-900 text-white">London</option>
                    <option value="Europe/Paris" className="bg-slate-900 text-white">Paris</option>
                    <option value="Asia/Dubai" className="bg-slate-900 text-white">Dubai</option>
                    <option value="Asia/Tehran" className="bg-slate-900 text-white">Tehran</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Notification Preferences */}
            <div className="space-y-6 pt-6 border-t border-white/5">
              <div>
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <span className="w-1.5 h-6 rounded-full bg-accent-500/50"></span>
                  Notifications
                </h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[
                  { id: 'email_notifications', label: 'Email Summaries', desc: 'Daily digests of tasks' },
                  { id: 'task_reminders', label: 'Task Reminders', desc: 'Alerts before deadlines' },
                  { id: 'ai_insights', label: 'AI Insights', desc: 'Direct recommendations' }
                ].map((item) => (
                  <label key={item.id} className="flex items-start gap-4 p-4 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 transition-all cursor-pointer group">
                    <div className="relative flex items-center mt-0.5">
                      <input
                        type="checkbox"
                        checked={(formData.notification_preferences as any)[item.id] !== false}
                        onChange={(e) => setFormData(prev => ({
                          ...prev,
                          notification_preferences: {
                            ...prev.notification_preferences,
                            [item.id]: e.target.checked
                          }
                        }))}
                        className="peer sr-only"
                      />
                      <div className="w-5 h-5 border-2 border-white/30 rounded bg-transparent peer-checked:bg-primary-500 peer-checked:border-primary-500 transition-all"></div>
                      <svg className="absolute w-3.5 h-3.5 top-[3px] left-[3px] text-white opacity-0 peer-checked:opacity-100 transition-opacity pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white group-hover:text-primary-300 transition-colors">{item.label}</p>
                      <p className="text-[11px] text-white/40 mt-1">{item.desc}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'privacy' && (
          <div className="p-6 sm:p-8 space-y-10 relative z-10">
            {/* Privacy Level */}
            <div className="space-y-6">
              <div>
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <span className="w-1.5 h-6 rounded-full bg-purple-500/50"></span>
                  Privacy Level
                </h3>
                <p className="text-sm text-white/50 mt-1 pl-3.5">Set how much data the AI uses to craft personal insights.</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  { value: 'minimal', label: 'Minimal', desc: 'Basic functionality only, no data storage.' },
                  { value: 'standard', label: 'Standard', desc: 'Balanced privacy and intelligent tracking.' },
                  { value: 'enhanced', label: 'Enhanced', desc: 'Full features with proactive personalization.' }
                ].map((level) => (
                  <label key={level.value} className={`relative p-5 rounded-2xl border transition-all duration-300 cursor-pointer ${
                    formData.privacy_level === level.value 
                      ? 'bg-purple-500/10 border-purple-500/50 shadow-[0_0_20px_rgba(168,85,247,0.15)]'
                      : 'bg-white/5 border-white/10 hover:border-white/20 hover:bg-white/10'
                  }`}>
                    <input
                      type="radio"
                      name="privacy_level"
                      value={level.value}
                      checked={formData.privacy_level === level.value}
                      onChange={(e) => setFormData(prev => ({ ...prev, privacy_level: e.target.value as any }))}
                      className="sr-only"
                    />
                    <div className="flex justify-between items-start mb-2">
                       <p className={`text-base font-bold ${formData.privacy_level === level.value ? 'text-purple-300' : 'text-white/80'}`}>{level.label}</p>
                       <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${formData.privacy_level === level.value ? 'border-purple-400' : 'border-white/30'}`}>
                         {formData.privacy_level === level.value && <div className="w-2 h-2 rounded-full bg-purple-400"></div>}
                       </div>
                    </div>
                    <p className="text-xs text-white/50 leading-relaxed">{level.desc}</p>
                  </label>
                ))}
              </div>
            </div>

            {/* Data Consent */}
            <div className="space-y-6 pt-6 border-t border-white/5">
              <div>
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <span className="w-1.5 h-6 rounded-full bg-accent-500/50"></span>
                  Data Usage Consent
                </h3>
              </div>
              <label className="flex items-center justify-between p-5 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 transition-all cursor-pointer">
                <div>
                   <p className="text-sm font-medium text-white">On-device Voice Training</p>
                   <p className="text-xs text-white/50 mt-1">Allow anonymous voice data to improve speech recognition locally.</p>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={formData.voice_training_consent}
                    onChange={(e) => setFormData(prev => ({ ...prev, voice_training_consent: e.target.checked }))}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div>
                </div>
              </label>
            </div>

            {/* Data Management */}
            <div className="space-y-6 pt-6 border-t border-red-500/10">
              <div>
                <h3 className="text-xl font-bold text-red-400 flex items-center gap-2">
                  <span className="w-1.5 h-6 rounded-full bg-red-500/50"></span>
                  Danger Zone
                </h3>
                <p className="text-xs text-white/40 mt-1 pl-3.5">
                  Export includes your profile, settings, tasks, events, and metadata. Deletion is permanent.
                </p>
              </div>
              <div className="flex flex-col sm:flex-row gap-4">
                <button
                  onClick={handleExportData}
                  disabled={isLoading}
                  className="px-6 py-3 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 disabled:opacity-50 text-white rounded-xl transition-all text-sm font-medium"
                >
                  Export Workspace Data
                </button>
                
                <button
                  onClick={handleDeleteAccount}
                  disabled={isLoading}
                  className="px-6 py-3 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 hover:border-red-500/30 disabled:opacity-50 text-red-400 rounded-xl transition-all text-sm font-medium"
                >
                  Permanently Delete Account
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'integrations' && (
          <div className="p-6 sm:p-8 space-y-6 relative z-10">
            <div>
              <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-6">
                <span className="w-1.5 h-6 rounded-full bg-blue-500/50"></span>
                Connected Services
              </h3>
            </div>
            
            {/* WhatsApp Integration */}
            <label className="flex items-center justify-between p-5 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 rounded-2xl cursor-pointer transition-all">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-[#25D366]/20 border border-[#25D366]/30 rounded-xl flex items-center justify-center text-[#25D366]">
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M12.031 2c-5.466 0-9.886 4.419-9.886 9.886 0 1.742.456 3.444 1.325 4.939L2 22l5.352-1.405c1.442.793 3.085 1.212 4.678 1.212 5.465 0 9.885-4.419 9.885-9.885S17.496 2 12.031 2" /></svg>
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">WhatsApp Assistant</h3>
                  <p className="text-xs text-white/50 mt-0.5">Receive reminders and notifications directly on WhatsApp.</p>
                </div>
              </div>
              <div className="relative">
                <input
                  type="checkbox"
                  checked={formData.whatsapp_opt_in}
                  onChange={(e) => setFormData(prev => ({ ...prev, whatsapp_opt_in: e.target.checked }))}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-500"></div>
              </div>
            </label>

            {/* Calendar Integration */}
            <label className="flex items-center justify-between p-5 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 rounded-2xl cursor-pointer transition-all">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-500/20 border border-blue-500/30 rounded-xl flex items-center justify-center text-blue-400">
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  </svg>
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Google Calendar Data</h3>
                  <p className="text-xs text-white/50 mt-0.5">Let AI read and write directly to your Google Calendar.</p>
                </div>
              </div>
              <div className="relative">
                <input
                  type="checkbox"
                  checked={formData.calendar_sync_enabled}
                  onChange={(e) => setFormData(prev => ({ ...prev, calendar_sync_enabled: e.target.checked }))}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-500"></div>
              </div>
            </label>

          </div>
        )}

        {activeTab === 'language' && (
          <div className="p-6 sm:p-8 space-y-10 relative z-10">
            <div>
              <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-6">
                <span className="w-1.5 h-6 rounded-full bg-emerald-500/50"></span>
                Language & Localization
              </h3>
            </div>
            
            {/* Language Selection */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white">Interface Language</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {Object.entries(locales).map(([code, locale]) => (
                  <label key={code} className={`flex items-center justify-between gap-3 p-4 rounded-2xl border cursor-pointer transition-all duration-300 ${
                    formData.language_preference === code
                      ? 'bg-emerald-500/10 border-emerald-500/50 shadow-[0_0_20px_rgba(16,185,129,0.15)]'
                      : 'bg-white/5 border-white/10 hover:border-white/20 hover:bg-white/10'
                  }`}>
                    <div className="flex flex-col gap-1">
                      <span className="text-2xl mb-1">{locale.flag}</span>
                      <p className={`text-sm font-bold ${formData.language_preference === code ? 'text-emerald-300' : 'text-white/80'}`}>{locale.name}</p>
                      <p className="text-[10px] uppercase text-white/40 tracking-wider font-semibold">{locale.direction}</p>
                    </div>
                    <input
                      type="radio"
                      name="language"
                      value={code}
                      checked={formData.language_preference === code}
                      onChange={(e) => setFormData(prev => ({ ...prev, language_preference: e.target.value as Language }))}
                      className="sr-only"
                    />
                  </label>
                ))}
              </div>
            </div>

            {/* Language Preview */}
            <div className="space-y-4 pt-6 border-t border-white/5">
              <h3 className="text-lg font-medium text-white">Preview</h3>
              <div className="p-6 bg-black/20 rounded-2xl border border-white/5">
                <div className={`text-sm text-gray-300 ${getLocaleConfig(formData.language_preference).direction === 'rtl' ? 'text-right' : 'text-left'}`}>
                  {formData.language_preference === 'fa-IR' && (
                    <>
                      <p className="font-medium">سلام! من دستیار هوشمند شما هستم.</p>
                      <p className="text-xs text-gray-400 mt-1">چگونه می‌توانم به شما کمک کنم؟</p>
                    </>
                  )}
                  {formData.language_preference === 'ar-UA' && (
                    <>
                      <p className="font-medium">مرحباً! أنا مساعدك الذكي.</p>
                      <p className="text-xs text-gray-400 mt-1">كيف يمكنني مساعدتك؟</p>
                    </>
                  )}
                  {formData.language_preference === 'en-US' && (
                    <>
                      <p className="font-medium">Hello! I&apos;m your intelligent assistant.</p>
                      <p className="text-xs text-gray-400 mt-1">How can I help you today?</p>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Save Button */}
        <div className="px-6 py-5 border-t border-white/10 bg-white/5 flex justify-end gap-3 z-10 relative">
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-2.5 bg-transparent border border-white/10 text-white/80 rounded-xl hover:bg-white/10 hover:text-white transition-all text-sm font-medium"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isLoading}
            className="px-8 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-xl shadow-[0_0_20px_rgba(99,102,241,0.3)] hover:shadow-[0_0_30px_rgba(99,102,241,0.5)] transition-all font-medium flex items-center gap-2 disabled:opacity-50 text-sm"
          >
            {isLoading ? (
              <>
                <LoadingSpinner size="sm" />
                <span>{t('settings.saving')}</span>
              </>
            ) : (
              <span>{t('settings.save')}</span>
            )}
          </button>
        </div>
      </GlassCard>
      </div>
    </AppPageShell>
  );
}
