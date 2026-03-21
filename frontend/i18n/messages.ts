import type { Language } from '@/types';

export type MessageKey =
  | 'nav.dashboard'
  | 'nav.tasks'
  | 'nav.calendar'
  | 'nav.settings'
  | 'nav.logout'
  | 'auth.welcomeBack'
  | 'auth.signIn'
  | 'auth.signingIn'
  | 'auth.email'
  | 'auth.password'
  | 'auth.forgotPassword'
  | 'settings.title'
  | 'settings.subtitle'
  | 'settings.tabs.general'
  | 'settings.tabs.privacy'
  | 'settings.tabs.integrations'
  | 'settings.tabs.language'
  | 'settings.save'
  | 'settings.saving'
  | 'settings.saved'
  | 'auth.orContinueWith';

type Dict = Record<MessageKey, string>;

const en: Dict = {
  'nav.dashboard': 'Dashboard',
  'nav.tasks': 'Tasks',
  'nav.calendar': 'Calendar',
  'nav.settings': 'Settings',
  'nav.logout': 'Logout',
  'auth.welcomeBack': 'Welcome back',
  'auth.signIn': 'Sign in',
  'auth.signingIn': 'Signing in...',
  'auth.email': 'Email address',
  'auth.password': 'Password',
  'auth.forgotPassword': 'Forgot password?',
  'settings.title': 'Settings',
  'settings.subtitle': 'Customize your Ai Department experience',
  'settings.tabs.general': 'General',
  'settings.tabs.privacy': 'Privacy',
  'settings.tabs.integrations': 'Integrations',
  'settings.tabs.language': 'Language',
  'settings.save': 'Save Changes',
  'settings.saving': 'Saving...',
  'settings.saved': 'Settings saved successfully',
  'auth.orContinueWith': 'Or continue with',
};

const fa: Dict = {
  'nav.dashboard': 'داشبورد',
  'nav.tasks': 'وظایف',
  'nav.calendar': 'تقویم',
  'nav.settings': 'تنظیمات',
  'nav.logout': 'خروج',
  'auth.welcomeBack': 'خوش آمدید',
  'auth.signIn': 'ورود',
  'auth.signingIn': 'در حال ورود…',
  'auth.email': 'ایمیل',
  'auth.password': 'رمز عبور',
  'auth.forgotPassword': 'فراموشی رمز عبور؟',
  'settings.title': 'تنظیمات',
  'settings.subtitle': 'تجربه Ai Department را شخصی‌سازی کنید',
  'settings.tabs.general': 'عمومی',
  'settings.tabs.privacy': 'حریم خصوصی',
  'settings.tabs.integrations': 'اتصال‌ها',
  'settings.tabs.language': 'زبان',
  'settings.save': 'ذخیره تغییرات',
  'settings.saving': 'در حال ذخیره…',
  'settings.saved': 'تنظیمات با موفقیت ذخیره شد',
  'auth.orContinueWith': 'یا ادامه با',
};

const ar: Dict = {
  'nav.dashboard': 'لوحة التحكم',
  'nav.tasks': 'المهام',
  'nav.calendar': 'التقويم',
  'nav.settings': 'الإعدادات',
  'nav.logout': 'تسجيل الخروج',
  'auth.welcomeBack': 'مرحباً بعودتك',
  'auth.signIn': 'تسجيل الدخول',
  'auth.signingIn': 'جارٍ تسجيل الدخول…',
  'auth.email': 'البريد الإلكتروني',
  'auth.password': 'كلمة المرور',
  'auth.forgotPassword': 'نسيت كلمة المرور؟',
  'settings.title': 'الإعدادات',
  'settings.subtitle': 'خصص تجربة Ai Department',
  'settings.tabs.general': 'عام',
  'settings.tabs.privacy': 'الخصوصية',
  'settings.tabs.integrations': 'التكامل',
  'settings.tabs.language': 'اللغة',
  'settings.save': 'حفظ التغييرات',
  'settings.saving': 'جارٍ الحفظ…',
  'settings.saved': 'تم حفظ الإعدادات بنجاح',
  'auth.orContinueWith': 'أو المتابعة مع',
};

export function getMessages(language: Language | string | undefined): Dict {
  switch (language) {
    case 'fa-IR':
      return fa;
    case 'ar-UA':
      return ar;
    case 'en-US':
    default:
      return en;
  }
}

