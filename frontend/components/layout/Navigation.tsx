'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { useAppStore } from '@/store/useAppStore';
import { cn } from '@/lib/utils';
import { GlowingOrb } from '@/components/ui/GlowingOrb';
import { useT } from '@/i18n/useT';
import { Surface } from '@/components/ui/Surface';
import { Button } from '@/components/ui/Button';

// Simple icon components
const HomeIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>
);

const TaskIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
  </svg>
);

const CalendarIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
  </svg>
);

const SettingsIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

const LogoutIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
  </svg>
);

export function Navigation() {
  const t = useT();
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { voiceSession } = useAppStore();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [avatarError, setAvatarError] = useState(false);

  const profileAvatarUrl = useMemo(() => {
    const avatarUrl = user?.avatar_url;
    if (!avatarUrl || avatarError) return null;
    if (avatarUrl.startsWith('http://') || avatarUrl.startsWith('https://')) return avatarUrl;

    let authApiUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || 'http://localhost:8001';
    if (authApiUrl.endsWith('/v1')) {
      authApiUrl = authApiUrl.replace(/\/v1$/, '');
    }

    const cleanUrl = avatarUrl.startsWith('/') ? avatarUrl : `/${avatarUrl}`;
    return `${authApiUrl}${cleanUrl}`;
  }, [user?.avatar_url, avatarError]);

  const handleLogout = async () => {
    await logout();
  };

  const navigation = useMemo(
    () => [
      { name: t('nav.dashboard'), href: '/dashboard', icon: HomeIcon },
      { name: t('nav.tasks'), href: '/tasks', icon: TaskIcon },
      { name: t('nav.calendar'), href: '/calendar', icon: CalendarIcon },
      { name: t('nav.settings'), href: '/settings', icon: SettingsIcon },
    ],
    [t]
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <div className="hidden xl:flex xl:fixed xl:inset-y-0 xl:w-72 xl:flex-col">
        <Surface
          as="aside"
          material="thick"
          className="flex h-full flex-col overflow-y-auto rounded-none border-0 border-e border-(--glass-border) bg-(--glass-ultraThick) px-3 py-4 shadow-none"
          role="navigation"
          aria-label="Primary"
        >
          <div className="flex items-center gap-3 px-2 pt-1">
            <GlowingOrb 
              size="sm" 
              isActive={voiceSession?.status === 'listening' || voiceSession?.status === 'processing'} 
            />
            <div className="min-w-0">
              <p className="text-sm font-semibold tracking-tight text-white">i Assistant</p>
              <p className="text-xs text-white/45">Personal OS dashboard</p>
            </div>
          </div>
          
          <div className="mt-5 flex grow flex-col">
            <nav className="flex-1 space-y-1 px-1">
              {navigation.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      'group flex h-(--tap-target) items-center rounded-control px-3 text-sm font-medium transition-colors',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50',
                      isActive
                        ? 'bg-linear-to-b from-primary-500/20 to-primary-700/10 text-white border border-primary-500/20'
                        : 'text-white/70 hover:bg-white/8 hover:text-white'
                    )}
                  >
                    <item.icon
                      className={cn(
                        'me-3 shrink-0 h-5 w-5',
                        isActive ? 'text-primary-200' : 'text-white/40 group-hover:text-white/60'
                      )}
                    />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
            
            {/* User Profile Section */}
            <div className="shrink-0 px-2 pt-3">
              <div className="rounded-control border border-(--glass-border) bg-(--glass-thin) p-3 backdrop-blur-2xl">
                <div className="flex items-center">
                <div className="shrink-0">
                  <div className="h-9 w-9 rounded-full bg-primary-600/25 border border-primary-500/20 flex items-center justify-center overflow-hidden">
                    {profileAvatarUrl ? (
                      <img
                        src={profileAvatarUrl}
                        alt={user?.email || 'Profile'}
                        className="h-9 w-9 object-cover"
                        onError={() => setAvatarError(true)}
                      />
                    ) : (
                      <span className="text-sm font-semibold text-white">
                        {user?.email?.charAt(0).toUpperCase()}
                      </span>
                    )}
                  </div>
                </div>
                <div className="ms-3 flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">
                    {user?.email}
                  </p>
                  <p className="mt-0.5 text-xs text-white/45">Signed in</p>
                </div>
                <Button
                  onClick={handleLogout}
                  variant="ghost"
                  size="sm"
                  className="ms-2 h-10 w-10 p-0"
                  title={t('nav.logout')}
                  aria-label={t('nav.logout')}
                >
                  <LogoutIcon className="h-5 w-5" />
                </Button>
                </div>
              </div>
            </div>
          </div>
        </Surface>
      </div>

      {/* Mobile Navigation */}
      <div className="xl:hidden">
        <Surface
          as="header"
          material="thick"
          className="sticky top-0 z-40 flex items-center justify-between rounded-none border-0 border-b border-(--glass-border) bg-(--glass-ultraThick) px-4 py-3 shadow-none"
        >
          <div className="flex items-center">
            <GlowingOrb 
              size="sm" 
              isActive={voiceSession?.status === 'listening' || voiceSession?.status === 'processing'} 
            />
            <span className="ms-3 text-sm font-semibold tracking-tight text-white">i Assistant</span>
          </div>
          
          <Button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            variant="ghost"
            size="sm"
            className="h-10 w-10 p-0"
            aria-label="Toggle navigation"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </Button>
        </Surface>

        {isMobileMenuOpen && (
          <div className="px-3 pt-3">
            <Surface material="regular" className="p-2">
            <nav className="space-y-1">
              {navigation.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={cn(
                      'group flex h-(--tap-target) items-center rounded-control px-3 text-base font-medium transition-colors',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/50',
                      isActive
                        ? 'bg-linear-to-b from-primary-500/20 to-primary-700/10 text-white border border-primary-500/20'
                        : 'text-white/75 hover:bg-white/8 hover:text-white'
                    )}
                  >
                    <item.icon
                      className={cn(
                        'me-3 shrink-0 h-5 w-5',
                        isActive ? 'text-primary-200' : 'text-white/40 group-hover:text-white/60'
                      )}
                    />
                    {item.name}
                  </Link>
                );
              })}
              
              <Button
                onClick={handleLogout}
                variant="secondary"
                size="md"
                className="w-full justify-start px-3"
              >
                <LogoutIcon className="me-3 shrink-0 h-5 w-5 text-gray-400 group-hover:text-gray-300" />
                {t('nav.logout')}
              </Button>
            </nav>
            </Surface>
          </div>
        )}
      </div>
    </>
  );
}
