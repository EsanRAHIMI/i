# Context با Invariant Check

برای جلوگیری از خطاهای silent و دیباگ بهتر، از helper های این فایل استفاده کن:

## استفاده

### 1. ایجاد Context جدید با Invariant

```tsx
import { createContextWithInvariant } from '@/lib/context-helpers';

// ایجاد Context
const { Provider: ThemeProvider, useTheme } = createContextWithInvariant<Theme>(
  'Theme',
  null
);

// در Providers اضافه کن
export function Providers({ children }: { children: ReactNode }) {
  const theme = getTheme(); // دریافت theme از جایی
  
  return (
    <ThemeProvider value={theme}>
      {children}
    </ThemeProvider>
  );
}

// استفاده در کامپوننت
function MyComponent() {
  const theme = useTheme(); // اگر بیرون Provider باشد، خطای واضح می‌دهد
  return <div>{theme.color}</div>;
}
```

### 2. استفاده با Context موجود

```tsx
import { createContext, useContext } from 'react';
import { createContextHook } from '@/lib/context-helpers';

const MyContext = createContext<MyType | null>(null);

export const useMyContext = createContextHook(MyContext, 'MyContext');
```

### 3. استفاده مستقیم از invariant

```tsx
import { invariant } from '@/lib/invariant';

function MyComponent() {
  const context = useContext(MyContext);
  invariant(context, 'MyComponent must be used within MyProvider');
  // بعد از این خط، TypeScript می‌داند که context null نیست
  return <div>{context.value}</div>;
}
```

## مزایا

- ✅ خطای واضح و هدایت‌کننده
- ✅ Stack trace بهتر برای دیباگ
- ✅ TypeScript type narrowing
- ✅ جلوگیری از silent failures

