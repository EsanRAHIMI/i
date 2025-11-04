'use client';

import { useState, useEffect } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { locales, getLocaleConfig } from '@/lib/utils';
import { Language, UserSettings } from '@/types';

export default function SettingsPage() {
  const { user, settings, updateUser, setSettings } = useAppStore();
  const { updateProfile } = useAuth();
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
      setSuccess('Settings saved successfully');
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
    { id: 'general', name: 'General', icon: '⚙️' },
    { id: 'privacy', name: 'Privacy', icon: '🔒' },
    { id: 'integrations', name: 'Integrations', icon: '🔗' },
    { id: 'language', name: 'Language', icon: '🌐' }
  ];

  return (
    <div className="p-6 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1">Customize your i Assistant experience</p>
      </div>

      {/* Tabs */}
      <div className="mb-8">
        <div className="border-b border-gray-700">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`
                  py-2 px-1 border-b-2 font-medium text-sm transition-colors
                  ${activeTab === tab.id
                    ? 'border-primary-500 text-primary-400'
                    : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-300'
                  }
                `}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.name}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-6 bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {success && (
        <div className="mb-6 bg-green-500/10 border border-green-500/20 rounded-lg p-4">
          <p className="text-green-400 text-sm">{success}</p>
        </div>
      )}

      {/* Tab Content */}
      <div className="bg-dark-800 rounded-lg border border-gray-700">
        {activeTab === 'general' && (
          <div className="p-6 space-y-6">
            <h2 className="text-xl font-semibold text-white mb-4">General Settings</h2>
            
            {/* Profile Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white">Profile Information</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="w-full px-3 py-2 bg-dark-700 border border-gray-600 rounded-lg text-gray-400 cursor-not-allowed"
                  />
                  <p className="text-xs text-gray-500 mt-1">Email cannot be changed</p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Timezone
                  </label>
                  <select
                    value={user?.timezone || 'UTC'}
                    onChange={(e) => setFormData(prev => ({ ...prev, timezone: e.target.value }))}
                    className="w-full px-3 py-2 bg-dark-700 border border-gray-600 rounded-lg text-white"
                  >
                    <option value="UTC">UTC</option>
                    <option value="America/New_York">Eastern Time</option>
                    <option value="America/Chicago">Central Time</option>
                    <option value="America/Denver">Mountain Time</option>
                    <option value="America/Los_Angeles">Pacific Time</option>
                    <option value="Europe/London">London</option>
                    <option value="Europe/Paris">Paris</option>
                    <option value="Asia/Dubai">Dubai</option>
                    <option value="Asia/Tehran">Tehran</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Notification Preferences */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white">Notifications</h3>
              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.notification_preferences.email_notifications !== false}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      notification_preferences: {
                        ...prev.notification_preferences,
                        email_notifications: e.target.checked
                      }
                    }))}
                    className="rounded border-gray-600 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="ml-2 text-sm text-gray-300">Email notifications</span>
                </label>
                
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.notification_preferences.task_reminders !== false}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      notification_preferences: {
                        ...prev.notification_preferences,
                        task_reminders: e.target.checked
                      }
                    }))}
                    className="rounded border-gray-600 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="ml-2 text-sm text-gray-300">Task reminders</span>
                </label>
                
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.notification_preferences.ai_insights !== false}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      notification_preferences: {
                        ...prev.notification_preferences,
                        ai_insights: e.target.checked
                      }
                    }))}
                    className="rounded border-gray-600 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="ml-2 text-sm text-gray-300">AI insights and recommendations</span>
                </label>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'privacy' && (
          <div className="p-6 space-y-6">
            <h2 className="text-xl font-semibold text-white mb-4">Privacy & Data</h2>
            
            {/* Privacy Level */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white">Privacy Level</h3>
              <div className="space-y-3">
                {[
                  { value: 'minimal', label: 'Minimal', desc: 'Basic functionality only, minimal data collection' },
                  { value: 'standard', label: 'Standard', desc: 'Balanced privacy and functionality' },
                  { value: 'enhanced', label: 'Enhanced', desc: 'Full features with comprehensive personalization' }
                ].map((level) => (
                  <label key={level.value} className="flex items-start space-x-3">
                    <input
                      type="radio"
                      name="privacy_level"
                      value={level.value}
                      checked={formData.privacy_level === level.value}
                      onChange={(e) => setFormData(prev => ({ ...prev, privacy_level: e.target.value as any }))}
                      className="mt-1 text-primary-600 focus:ring-primary-500"
                    />
                    <div>
                      <p className="text-sm font-medium text-white">{level.label}</p>
                      <p className="text-xs text-gray-400">{level.desc}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Data Consent */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white">Data Usage Consent</h3>
              <div className="space-y-3">
                <label className="flex items-start space-x-3">
                  <input
                    type="checkbox"
                    checked={formData.voice_training_consent}
                    onChange={(e) => setFormData(prev => ({ ...prev, voice_training_consent: e.target.checked }))}
                    className="mt-1 rounded border-gray-600 text-primary-600 focus:ring-primary-500"
                  />
                  <div>
                    <p className="text-sm font-medium text-white">Voice Training</p>
                    <p className="text-xs text-gray-400">Allow voice data to improve speech recognition accuracy</p>
                  </div>
                </label>
              </div>
            </div>

            {/* Data Management */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white">Data Management</h3>
              <div className="space-y-3">
                <button
                  onClick={handleExportData}
                  disabled={isLoading}
                  className="w-full md:w-auto px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg transition-colors"
                >
                  Export My Data
                </button>
                
                <button
                  onClick={handleDeleteAccount}
                  disabled={isLoading}
                  className="w-full md:w-auto px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg transition-colors"
                >
                  Delete Account
                </button>
              </div>
              <p className="text-xs text-gray-500">
                Export includes your profile, settings, tasks, events, and voice session metadata. 
                Account deletion is permanent and cannot be undone.
              </p>
            </div>
          </div>
        )}

        {activeTab === 'integrations' && (
          <div className="p-6 space-y-6">
            <h2 className="text-xl font-semibold text-white mb-4">Integrations</h2>
            
            {/* WhatsApp Integration */}
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-dark-900 rounded-lg border border-gray-600">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
                    <span className="text-white font-bold">W</span>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-white">WhatsApp</h3>
                    <p className="text-xs text-gray-400">Receive confirmations and updates via WhatsApp</p>
                  </div>
                </div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.whatsapp_opt_in}
                    onChange={(e) => setFormData(prev => ({ ...prev, whatsapp_opt_in: e.target.checked }))}
                    className="rounded border-gray-600 text-primary-600 focus:ring-primary-500"
                  />
                </label>
              </div>
            </div>

            {/* Calendar Integration */}
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-dark-900 rounded-lg border border-gray-600">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                    <span className="text-white font-bold">G</span>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-white">Google Calendar</h3>
                    <p className="text-xs text-gray-400">Sync events and enable intelligent scheduling</p>
                  </div>
                </div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.calendar_sync_enabled}
                    onChange={(e) => setFormData(prev => ({ ...prev, calendar_sync_enabled: e.target.checked }))}
                    className="rounded border-gray-600 text-primary-600 focus:ring-primary-500"
                  />
                </label>
              </div>
            </div>

            {/* Federated Learning */}
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-dark-900 rounded-lg border border-gray-600">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center">
                    <span className="text-white font-bold">AI</span>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-white">Federated Learning</h3>
                    <p className="text-xs text-gray-400">Contribute to AI improvement while preserving privacy</p>
                  </div>
                </div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.notification_preferences.federated_learning !== false}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      notification_preferences: {
                        ...prev.notification_preferences,
                        federated_learning: e.target.checked
                      }
                    }))}
                    className="rounded border-gray-600 text-primary-600 focus:ring-primary-500"
                  />
                </label>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'language' && (
          <div className="p-6 space-y-6">
            <h2 className="text-xl font-semibold text-white mb-4">Language & Localization</h2>
            
            {/* Language Selection */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white">Interface Language</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(locales).map(([code, locale]) => (
                  <label key={code} className="flex items-center space-x-3 p-3 bg-dark-900 rounded-lg border border-gray-600 hover:border-gray-500 cursor-pointer">
                    <input
                      type="radio"
                      name="language"
                      value={code}
                      checked={formData.language_preference === code}
                      onChange={(e) => setFormData(prev => ({ ...prev, language_preference: e.target.value as Language }))}
                      className="text-primary-600 focus:ring-primary-500"
                    />
                    <div className="flex items-center space-x-2">
                      <span className="text-lg">{locale.flag}</span>
                      <div>
                        <p className="text-sm font-medium text-white">{locale.name}</p>
                        <p className="text-xs text-gray-400">{locale.direction.toUpperCase()}</p>
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Language Preview */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white">Preview</h3>
              <div className="p-4 bg-dark-900 rounded-lg border border-gray-600">
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
                      <p className="font-medium">Hello! I'm your intelligent assistant.</p>
                      <p className="text-xs text-gray-400 mt-1">How can I help you today?</p>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Save Button */}
        <div className="px-6 py-4 border-t border-gray-700">
          <div className="flex justify-end space-x-3">
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors"
            >
              Reset
            </button>
            <button
              onClick={handleSave}
              disabled={isLoading}
              className="px-6 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-lg transition-colors flex items-center space-x-2"
            >
              {isLoading ? (
                <>
                  <LoadingSpinner size="sm" />
                  <span>Saving...</span>
                </>
              ) : (
                <span>Save Changes</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}